"""Clone group tracking across revisions."""

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from b4_thesis.analysis.group_detector import CloneGroup, GroupDetector
from b4_thesis.analysis.group_matcher import GroupMatcher
from b4_thesis.analysis.matching import MatchResult, MatchingDefaults, MethodMatcher
from b4_thesis.analysis.state_classifier import StateClassifier
from b4_thesis.core.revision_manager import RevisionInfo, RevisionManager


@dataclass
class GroupTrackingResult:
    """Result of group tracking analysis."""

    revision: str
    group_id: str
    member_count: int
    avg_similarity: float | None
    min_similarity: int | None
    max_similarity: int | None
    density: float
    state: str
    matched_group_id: str | None
    overlap_ratio: float | None
    member_added: int
    member_removed: int
    lifetime_revisions: int
    lifetime_days: int


@dataclass
class GroupMembershipResult:
    """Group membership snapshot."""

    revision: str
    group_id: str
    block_id: str
    function_name: str
    is_clone: bool


class CloneGroupTracker:
    """Tracks clone group evolution across revisions."""

    def __init__(
        self,
        data_dir: Path,
        similarity_threshold: int = MatchingDefaults.SIMILARITY_THRESHOLD,
        overlap_threshold: float = 0.5,
        use_lsh: bool = False,
        lsh_threshold: float = MatchingDefaults.LSH_THRESHOLD,
        lsh_num_perm: int = MatchingDefaults.LSH_NUM_PERM,
        top_k: int = MatchingDefaults.TOP_K_CANDIDATES,
        use_optimized_similarity: bool = False,
        progressive_thresholds: list[int] | None = None,
    ) -> None:
        """
        Initialize clone group tracker.

        Args:
            data_dir: Directory containing revision subdirectories
            similarity_threshold: Similarity threshold for matching (0-100)
            overlap_threshold: Overlap threshold for group matching (0-1)
            use_lsh: Enable LSH indexing for candidate filtering (Phase 5.3.2)
            lsh_threshold: LSH similarity threshold 0.0-1.0 (Phase 5.3.2)
            lsh_num_perm: Number of LSH permutations (Phase 5.3.2)
            top_k: Number of top candidates to consider per source block (Phase 5.3.2)
            use_optimized_similarity: Use optimized similarity with banded LCS (Phase 5.3.2)
            progressive_thresholds: List of thresholds to try progressively (Phase 5.3.3)
        """
        self.data_dir = data_dir
        self.similarity_threshold = similarity_threshold
        self.overlap_threshold = overlap_threshold
        self.use_lsh = use_lsh
        self.lsh_threshold = lsh_threshold
        self.lsh_num_perm = lsh_num_perm
        self.top_k = top_k
        self.use_optimized_similarity = use_optimized_similarity
        self.progressive_thresholds = progressive_thresholds
        self.revision_manager = RevisionManager(data_dir)
        self.group_detector = GroupDetector(similarity_threshold=similarity_threshold)
        self.group_matcher = GroupMatcher(overlap_threshold=overlap_threshold)
        self.method_matcher = MethodMatcher(
            similarity_threshold=similarity_threshold,
            use_lsh=use_lsh,
            lsh_threshold=lsh_threshold,
            lsh_num_perm=lsh_num_perm,
            top_k=top_k,
            use_optimized_similarity=use_optimized_similarity,
            progressive_thresholds=progressive_thresholds,
        )
        self.state_classifier = StateClassifier()

    def track(
        self, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Track clone groups across revisions.

        Args:
            start_date: Start date for filtering revisions
            end_date: End date for filtering revisions

        Returns:
            Tuple of (group_tracking_df, membership_df)
        """
        revisions = self.revision_manager.get_revisions(start_date=start_date, end_date=end_date)

        if len(revisions) == 0:
            # Return empty DataFrames with correct columns
            group_tracking_df = pd.DataFrame(
                columns=[
                    "revision",
                    "group_id",
                    "member_count",
                    "avg_similarity",
                    "min_similarity",
                    "max_similarity",
                    "density",
                    "state",
                    "matched_group_id",
                    "overlap_ratio",
                    "member_added",
                    "member_removed",
                    "lifetime_revisions",
                    "lifetime_days",
                ]
            )
            membership_df = pd.DataFrame(
                columns=[
                    "revision",
                    "group_id",
                    "block_id",
                    "function_name",
                    "is_clone",
                ]
            )
            return group_tracking_df, membership_df

        all_group_results: list[GroupTrackingResult] = []
        all_membership_results: list[GroupMembershipResult] = []
        lifetime_tracker: dict[str, dict] = {}

        # Process first revision (all groups are "BORN")
        first_revision = revisions[0]
        code_blocks_first, clone_pairs_first = self.revision_manager.load_revision_data(
            first_revision
        )
        groups_first = self.group_detector.detect_groups(code_blocks_first, clone_pairs_first)

        # Create block_id to function_name mapping
        block_to_function = dict(
            zip(code_blocks_first["block_id"], code_blocks_first["function_name"])
        )

        for group_id, group in groups_first.items():
            # Group tracking result
            result = GroupTrackingResult(
                revision=first_revision.revision_id,
                group_id=group_id,
                member_count=group.size,
                avg_similarity=group.avg_similarity,
                min_similarity=group.min_similarity,
                max_similarity=group.max_similarity,
                density=group.density,
                state="born",
                matched_group_id=None,
                overlap_ratio=None,
                member_added=0,
                member_removed=0,
                lifetime_revisions=1,
                lifetime_days=0,
            )
            all_group_results.append(result)

            # Initialize lifetime tracking
            lifetime_tracker[group_id] = {
                "first_seen": first_revision.timestamp,
                "last_seen": first_revision.timestamp,
                "revision_count": 1,
            }

            # Membership results
            for member_id in group.members:
                membership_result = GroupMembershipResult(
                    revision=first_revision.revision_id,
                    group_id=group_id,
                    block_id=member_id,
                    function_name=block_to_function.get(member_id, ""),
                    is_clone=group.is_clone,
                )
                all_membership_results.append(membership_result)

        # Process consecutive revision pairs
        for i in range(len(revisions) - 1):
            revision_old = revisions[i]
            revision_new = revisions[i + 1]

            pair_group_results, pair_membership_results = self._process_revision_pair(
                revision_old, revision_new, lifetime_tracker
            )
            all_group_results.extend(pair_group_results)
            all_membership_results.extend(pair_membership_results)

        # Convert to DataFrames
        group_tracking_df = pd.DataFrame([asdict(r) for r in all_group_results])
        membership_df = pd.DataFrame([asdict(r) for r in all_membership_results])

        # Ensure correct data types
        if len(group_tracking_df) > 0:
            group_tracking_df["member_count"] = group_tracking_df["member_count"].astype(int)
            group_tracking_df["member_added"] = group_tracking_df["member_added"].astype(int)
            group_tracking_df["member_removed"] = group_tracking_df["member_removed"].astype(int)
            group_tracking_df["lifetime_revisions"] = group_tracking_df[
                "lifetime_revisions"
            ].astype(int)
            group_tracking_df["lifetime_days"] = group_tracking_df["lifetime_days"].astype(int)
            group_tracking_df["density"] = group_tracking_df["density"].astype(float)

        if len(membership_df) > 0:
            membership_df["is_clone"] = membership_df["is_clone"].astype(bool)

        return group_tracking_df, membership_df

    def _process_revision_pair(
        self,
        revision_old: RevisionInfo,
        revision_new: RevisionInfo,
        lifetime_tracker: dict[str, dict],
    ) -> tuple[list[GroupTrackingResult], list[GroupMembershipResult]]:
        """
        Process a pair of consecutive revisions.

        Args:
            revision_old: Previous revision
            revision_new: Current revision
            lifetime_tracker: Dictionary tracking group lifetimes

        Returns:
            Tuple of (group_results, membership_results)
        """
        # Load data for both revisions
        code_blocks_old, clone_pairs_old = self.revision_manager.load_revision_data(revision_old)
        code_blocks_new, clone_pairs_new = self.revision_manager.load_revision_data(revision_new)

        # Detect groups in both revisions
        groups_old = self.group_detector.detect_groups(code_blocks_old, clone_pairs_old)
        groups_new = self.group_detector.detect_groups(code_blocks_new, clone_pairs_new)

        # Match methods between revisions (needed for member change calculation)
        method_match_result = self.method_matcher.match_blocks(code_blocks_old, code_blocks_new)

        # Match groups between revisions
        group_matches = self.group_matcher.match_groups(groups_old, groups_new, method_match_result)

        # Detect splits and merges
        splits = self.group_matcher.detect_splits(group_matches)
        merges = self.group_matcher.detect_merges(group_matches)

        # Create sets for fast lookup
        split_groups = {old_id for old_id, _ in splits}
        merged_groups = {new_id for _, new_id in merges}

        # Create reverse mapping: new_group_id -> old_group_id
        reverse_group_matches: dict[str, str] = {}
        for old_id, match in group_matches.items():
            if match.target_group_id is not None:
                reverse_group_matches[match.target_group_id] = old_id

        # Create block_id to function_name mapping for new revision
        block_to_function = dict(zip(code_blocks_new["block_id"], code_blocks_new["function_name"]))

        group_results: list[GroupTrackingResult] = []
        membership_results: list[GroupMembershipResult] = []

        # Process all groups in new revision
        for group_id, group_new in groups_new.items():
            # Find matched old group
            old_group_id = reverse_group_matches.get(group_id)

            # Determine state and member changes
            if old_group_id is None:
                # New group (born)
                state = "born"
                member_added = 0
                member_removed = 0
                overlap_ratio = None
                lifetime_revisions = 1
                lifetime_days = 0

                # Initialize lifetime tracking
                lifetime_tracker[group_id] = {
                    "first_seen": revision_new.timestamp,
                    "last_seen": revision_new.timestamp,
                    "revision_count": 1,
                }
            else:
                # Existing group - get the GroupMatch object
                group_match = group_matches[old_group_id]
                overlap_ratio = group_match.overlap_ratio

                # Check if this is a split or merge
                is_split = old_group_id in split_groups
                is_merged = group_id in merged_groups

                # Classify group state
                state_enum = self.state_classifier.classify_group_state(
                    group_match, is_split=is_split, is_merged=is_merged
                )
                state = state_enum.value

                # Calculate member changes
                group_old = groups_old[old_group_id]
                member_added, member_removed = self._calculate_member_changes(
                    group_old, group_new, method_match_result
                )

                # Update lifetime tracking
                if old_group_id in lifetime_tracker:
                    lifetime_tracker[old_group_id]["last_seen"] = revision_new.timestamp
                    lifetime_tracker[old_group_id]["revision_count"] += 1
                    lifetime_revisions = lifetime_tracker[old_group_id]["revision_count"]
                    lifetime_days = (
                        revision_new.timestamp - lifetime_tracker[old_group_id]["first_seen"]
                    ).days
                else:
                    # Fallback if not tracked
                    lifetime_revisions = 2
                    lifetime_days = (revision_new.timestamp - revision_old.timestamp).days

                # Track under new ID as well
                lifetime_tracker[group_id] = lifetime_tracker.get(
                    old_group_id,
                    {
                        "first_seen": revision_old.timestamp,
                        "last_seen": revision_new.timestamp,
                        "revision_count": lifetime_revisions,
                    },
                )

            # Create group tracking result
            result = GroupTrackingResult(
                revision=revision_new.revision_id,
                group_id=group_id,
                member_count=group_new.size,
                avg_similarity=group_new.avg_similarity,
                min_similarity=group_new.min_similarity,
                max_similarity=group_new.max_similarity,
                density=group_new.density,
                state=state,
                matched_group_id=old_group_id,
                overlap_ratio=overlap_ratio,
                member_added=member_added,
                member_removed=member_removed,
                lifetime_revisions=lifetime_revisions,
                lifetime_days=lifetime_days,
            )
            group_results.append(result)

            # Create membership results for all members
            for member_id in group_new.members:
                membership_result = GroupMembershipResult(
                    revision=revision_new.revision_id,
                    group_id=group_id,
                    block_id=member_id,
                    function_name=block_to_function.get(member_id, ""),
                    is_clone=group_new.is_clone,
                )
                membership_results.append(membership_result)

        return group_results, membership_results

    def _calculate_member_changes(
        self, group_old: CloneGroup, group_new: CloneGroup, match_result: MatchResult
    ) -> tuple[int, int]:
        """
        Calculate member_added and member_removed.

        Args:
            group_old: Old group
            group_new: New group
            match_result: Method match result

        Returns:
            Tuple of (member_added, member_removed)
        """
        # Get matched members (members that survived from old to new)
        matched_members_old = set()
        matched_members_new = set()

        for old_member in group_old.members:
            if old_member in match_result.forward_matches:
                new_member = match_result.forward_matches[old_member]
                if new_member in group_new.members:
                    matched_members_old.add(old_member)
                    matched_members_new.add(new_member)

        # Calculate added and removed
        member_added = len(group_new.members) - len(matched_members_new)
        member_removed = len(group_old.members) - len(matched_members_old)

        return member_added, member_removed
