"""Method tracking across revisions."""

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from b4_thesis.analysis.group_detector import CloneGroup, GroupDetector
from b4_thesis.analysis.matching import MatchingDefaults, MethodMatcher
from b4_thesis.analysis.state_classifier import StateClassifier
from b4_thesis.core.revision_manager import RevisionInfo, RevisionManager


@dataclass
class MethodTrackingResult:
    """Result of method tracking analysis."""

    revision: str
    block_id: str
    function_name: str
    file_path: str
    start_line: int
    end_line: int
    loc: int
    state: str
    state_detail: str
    matched_block_id: str | None
    match_type: str
    match_similarity: int | None
    clone_count: int
    clone_group_id: str | None
    clone_group_size: int
    lifetime_revisions: int
    lifetime_days: int


class MethodTracker:
    """Tracks method evolution across revisions."""

    def __init__(
        self,
        data_dir: Path,
        similarity_threshold: int = MatchingDefaults.SIMILARITY_THRESHOLD,
        use_lsh: bool = False,
        lsh_threshold: float = MatchingDefaults.LSH_THRESHOLD,
        lsh_num_perm: int = MatchingDefaults.LSH_NUM_PERM,
        top_k: int = MatchingDefaults.TOP_K_CANDIDATES,
        use_optimized_similarity: bool = False,
        progressive_thresholds: list[int] | None = None,
    ) -> None:
        """
        Initialize method tracker.

        Args:
            data_dir: Directory containing revision subdirectories
            similarity_threshold: Similarity threshold for matching (0-100)
            use_lsh: Enable LSH indexing for candidate filtering (Phase 5.3.2)
            lsh_threshold: LSH similarity threshold 0.0-1.0 (Phase 5.3.2)
            lsh_num_perm: Number of LSH permutations (Phase 5.3.2)
            top_k: Number of top candidates to consider per source block (Phase 5.3.2)
            use_optimized_similarity: Use optimized similarity with banded LCS (Phase 5.3.2)
            progressive_thresholds: List of thresholds to try progressively (Phase 5.3.3)
                                   (e.g., [90, 80, 70]). If None, uses single threshold.
        """
        self.data_dir = data_dir
        self.similarity_threshold = similarity_threshold
        self.use_lsh = use_lsh
        self.lsh_threshold = lsh_threshold
        self.lsh_num_perm = lsh_num_perm
        self.top_k = top_k
        self.use_optimized_similarity = use_optimized_similarity
        self.progressive_thresholds = progressive_thresholds
        self.revision_manager = RevisionManager(data_dir)
        self.method_matcher = MethodMatcher(
            similarity_threshold=similarity_threshold,
            use_lsh=use_lsh,
            lsh_threshold=lsh_threshold,
            lsh_num_perm=lsh_num_perm,
            top_k=top_k,
            use_optimized_similarity=use_optimized_similarity,
            progressive_thresholds=progressive_thresholds,
        )
        self.group_detector = GroupDetector(similarity_threshold=similarity_threshold)
        self.state_classifier = StateClassifier()

        # Internal state for lineage tracking
        self._global_block_id_map: dict[tuple[str, str], str] = {}
        self._results_df: pd.DataFrame | None = None

    def track(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        parallel: bool = False,
        max_workers: int | None = None,
    ) -> pd.DataFrame:
        """
        Track methods across revisions.

        Args:
            start_date: Start date for filtering revisions
            end_date: End date for filtering revisions
            parallel: If True, use parallel processing for similarity calculation
            max_workers: Maximum number of worker processes (if parallel=True)

        Returns:
            DataFrame with method tracking results
        """
        revisions = self.revision_manager.get_revisions(start_date=start_date, end_date=end_date)

        if len(revisions) == 0:
            # Return empty DataFrame with correct columns
            return pd.DataFrame(
                columns=[
                    "revision",
                    "block_id",
                    "function_name",
                    "file_path",
                    "start_line",
                    "end_line",
                    "loc",
                    "state",
                    "state_detail",
                    "matched_block_id",
                    "match_type",
                    "match_similarity",
                    "clone_count",
                    "clone_group_id",
                    "clone_group_size",
                    "lifetime_revisions",
                    "lifetime_days",
                ]
            )

        all_results: list[MethodTrackingResult] = []
        lifetime_tracker: dict[str, dict] = {}

        # Reset global block ID map for new tracking session
        self._global_block_id_map = {}

        # Process first revision (all methods are "added")
        first_revision = revisions[0]
        code_blocks_first, clone_pairs_first = self.revision_manager.load_revision_data(
            first_revision
        )
        groups_first = self.group_detector.detect_groups(code_blocks_first, clone_pairs_first)

        for _, block_row in code_blocks_first.iterrows():
            block_id = block_row["block_id"]
            group = self._find_group_for_block(block_id, groups_first)

            result = MethodTrackingResult(
                revision=first_revision.revision_id,
                block_id=block_id,
                function_name=block_row["function_name"],
                file_path=block_row["file_path"],
                start_line=int(block_row["start_line"]),
                end_line=int(block_row["end_line"]),
                loc=int(block_row["end_line"]) - int(block_row["start_line"]) + 1,
                state="added",
                state_detail="added_isolated"
                if group is None
                else ("added_to_group" if group.size > 1 else "added_isolated"),
                matched_block_id=None,
                match_type="none",
                match_similarity=None,
                clone_count=group.size - 1 if group and group.is_clone else 0,
                clone_group_id=group.group_id if group and group.is_clone else None,
                clone_group_size=group.size if group else 1,
                lifetime_revisions=1,
                lifetime_days=0,
            )
            all_results.append(result)

            # Initialize lifetime tracking
            lifetime_tracker[block_id] = {
                "first_seen": first_revision.timestamp,
                "last_seen": first_revision.timestamp,
                "revision_count": 1,
            }

            # Initialize global_block_id (first revision: global_block_id = block_id)
            self._global_block_id_map[(first_revision.revision_id, block_id)] = block_id

        # Process consecutive revision pairs
        for i in range(len(revisions) - 1):
            revision_old = revisions[i]
            revision_new = revisions[i + 1]

            pair_results = self._process_revision_pair(
                revision_old,
                revision_new,
                lifetime_tracker,
                parallel=parallel,
                max_workers=max_workers,
            )
            all_results.extend(pair_results)

        # Convert to DataFrame
        df = pd.DataFrame([asdict(r) for r in all_results])

        # Ensure correct data types
        if len(df) > 0:
            df["start_line"] = df["start_line"].astype(int)
            df["end_line"] = df["end_line"].astype(int)
            df["loc"] = df["loc"].astype(int)
            df["clone_count"] = df["clone_count"].astype(int)
            df["clone_group_size"] = df["clone_group_size"].astype(int)
            df["lifetime_revisions"] = df["lifetime_revisions"].astype(int)
            df["lifetime_days"] = df["lifetime_days"].astype(int)
            
            # Sort by revision, file_path, state, state_detail
            df = df.sort_values(["revision", "clone_group_id", "state", "state_detail", "file_path"])

        # Store results for lineage format conversion
        self._results_df = df

        return df

    def _process_revision_pair(
        self,
        revision_old: RevisionInfo,
        revision_new: RevisionInfo,
        lifetime_tracker: dict[str, dict],
        parallel: bool = False,
        max_workers: int | None = None,
    ) -> list[MethodTrackingResult]:
        """
        Process a pair of consecutive revisions.

        Args:
            revision_old: Previous revision
            revision_new: Current revision
            lifetime_tracker: Dictionary tracking method lifetimes
            parallel: If True, use parallel processing for similarity calculation
            max_workers: Maximum number of worker processes (if parallel=True)

        Returns:
            List of tracking results for the new revision
        """
        # Load data for both revisions
        code_blocks_old, clone_pairs_old = self.revision_manager.load_revision_data(revision_old)
        code_blocks_new, clone_pairs_new = self.revision_manager.load_revision_data(revision_new)

        # Detect groups in both revisions
        groups_old = self.group_detector.detect_groups(code_blocks_old, clone_pairs_old)
        groups_new = self.group_detector.detect_groups(code_blocks_new, clone_pairs_new)

        # Match methods between revisions
        match_result = self.method_matcher.match_blocks(
            code_blocks_old, code_blocks_new, parallel=parallel, max_workers=max_workers
        )

        # Use backward_matches for reverse mapping (new -> old)
        reverse_matches = match_result.backward_matches

        results: list[MethodTrackingResult] = []

        # Process all blocks in new revision
        for _, block_row in code_blocks_new.iterrows():
            block_id = block_row["block_id"]
            old_block_id = reverse_matches.get(block_id)

            # Determine state
            if old_block_id is None:
                # New method (added)
                state = "added"
                matched_block_id = None
                match_type = "none"
                match_similarity = None
                lifetime_revisions = 1
                lifetime_days = 0

                # Initialize lifetime tracking
                lifetime_tracker[block_id] = {
                    "first_seen": revision_new.timestamp,
                    "last_seen": revision_new.timestamp,
                    "revision_count": 1,
                }

                # New lineage: global_block_id = block_id
                self._global_block_id_map[(revision_new.revision_id, block_id)] = block_id
            else:
                # Existing method (survived)
                state = "survived"
                matched_block_id = old_block_id
                match_type = match_result.match_types.get(old_block_id, "none")
                match_similarity = match_result.match_similarities.get(old_block_id)

                # Update lifetime tracking
                if old_block_id in lifetime_tracker:
                    lifetime_tracker[old_block_id]["last_seen"] = revision_new.timestamp
                    lifetime_tracker[old_block_id]["revision_count"] += 1
                    lifetime_revisions = lifetime_tracker[old_block_id]["revision_count"]
                    lifetime_days = (
                        revision_new.timestamp - lifetime_tracker[old_block_id]["first_seen"]
                    ).days
                else:
                    # Fallback if not tracked
                    lifetime_revisions = 2
                    lifetime_days = (revision_new.timestamp - revision_old.timestamp).days

                # Track under new ID as well
                lifetime_tracker[block_id] = lifetime_tracker.get(
                    old_block_id,
                    {
                        "first_seen": revision_old.timestamp,
                        "last_seen": revision_new.timestamp,
                        "revision_count": lifetime_revisions,
                    },
                )

                # Inherit global_block_id from old block
                old_global_block_id = self._global_block_id_map.get(
                    (revision_old.revision_id, old_block_id), old_block_id
                )
                self._global_block_id_map[(revision_new.revision_id, block_id)] = (
                    old_global_block_id
                )

            # Find group membership
            group_old = (
                self._find_group_for_block(old_block_id, groups_old) if old_block_id else None
            )
            group_new = self._find_group_for_block(block_id, groups_new)

            # Classify detailed state
            is_last_member = False
            if group_old and group_old.size == 1 and old_block_id:
                is_last_member = True

            is_new_group = False
            if group_new and group_new.size == 1:
                is_new_group = True

            _, state_detail_enum = self.state_classifier.classify_method_state(
                block_id=block_id,
                match_result=match_result,
                direction="backward",  # We're looking from new to old
                group_old=group_old,
                group_new=group_new,
                is_last_member=is_last_member,
                is_new_group=is_new_group,
            )
            state_detail = state_detail_enum.value

            # Create result
            result = MethodTrackingResult(
                revision=revision_new.revision_id,
                block_id=block_id,
                function_name=block_row["function_name"],
                file_path=block_row["file_path"],
                start_line=int(block_row["start_line"]),
                end_line=int(block_row["end_line"]),
                loc=int(block_row["end_line"]) - int(block_row["start_line"]) + 1,
                state=state,
                state_detail=state_detail,
                matched_block_id=matched_block_id,
                match_type=match_type,
                match_similarity=match_similarity,
                clone_count=group_new.size - 1 if group_new and group_new.is_clone else 0,
                clone_group_id=group_new.group_id if group_new and group_new.is_clone else None,
                clone_group_size=group_new.size if group_new else 1,
                lifetime_revisions=lifetime_revisions,
                lifetime_days=lifetime_days,
            )
            results.append(result)

        # Process deleted blocks (exist in old but not matched in new)
        forward_matches = match_result.forward_matches
        for _, old_block_row in code_blocks_old.iterrows():
            old_block_id = old_block_row["block_id"]

            # Skip if this block was matched (survived)
            if old_block_id in forward_matches:
                continue

            # This block was deleted
            group_old = self._find_group_for_block(old_block_id, groups_old)

            # Classify detailed state for deleted method
            is_last_member = group_old.size == 1 if group_old else False
            _, state_detail_enum = self.state_classifier.classify_method_state(
                block_id=old_block_id,
                match_result=match_result,
                direction="forward",  # We're looking from old (no match in new)
                group_old=group_old,
                group_new=None,
                is_last_member=is_last_member,
                is_new_group=False,
            )
            state_detail = state_detail_enum.value

            # Calculate lifetime
            if old_block_id in lifetime_tracker:
                lifetime_tracker[old_block_id]["last_seen"] = revision_new.timestamp
                lifetime_revisions = lifetime_tracker[old_block_id]["revision_count"]
                lifetime_days = (
                    revision_new.timestamp - lifetime_tracker[old_block_id]["first_seen"]
                ).days
            else:
                # Fallback (shouldn't happen, but handle gracefully)
                lifetime_revisions = 1
                lifetime_days = 0

            # Inherit global_block_id from old revision
            old_global_block_id = self._global_block_id_map.get(
                (revision_old.revision_id, old_block_id), old_block_id
            )
            # Map deleted block to new revision with inherited global_block_id
            self._global_block_id_map[(revision_new.revision_id, old_block_id)] = (
                old_global_block_id
            )

            # Create result for deleted method
            result = MethodTrackingResult(
                revision=revision_new.revision_id,
                block_id=old_block_id,
                function_name=old_block_row["function_name"],
                file_path=old_block_row["file_path"],
                start_line=int(old_block_row["start_line"]),
                end_line=int(old_block_row["end_line"]),
                loc=int(old_block_row["end_line"]) - int(old_block_row["start_line"]) + 1,
                state="deleted",
                state_detail=state_detail,
                matched_block_id=None,
                match_type="none",
                match_similarity=None,
                clone_count=group_old.size - 1 if group_old and group_old.is_clone else 0,
                clone_group_id=group_old.group_id if group_old and group_old.is_clone else None,
                clone_group_size=group_old.size if group_old else 1,
                lifetime_revisions=lifetime_revisions,
                lifetime_days=lifetime_days,
            )
            results.append(result)

        return results

    def _find_group_for_block(
        self, block_id: str | None, groups: dict[str, CloneGroup]
    ) -> CloneGroup | None:
        """
        Find which group a block belongs to.

        Args:
            block_id: Block ID to search for
            groups: Dictionary of groups

        Returns:
            CloneGroup if found, None otherwise
        """
        if block_id is None:
            return None

        for group in groups.values():
            if block_id in group.members:
                return group
        return None

    def _calculate_lifetime(
        self, block_id: str, current_revision: datetime, lifetime_tracker: dict[str, dict]
    ) -> tuple[int, int]:
        """
        Calculate lifetime_revisions and lifetime_days.

        Args:
            block_id: Block ID
            current_revision: Current revision timestamp
            lifetime_tracker: Lifetime tracking dictionary

        Returns:
            Tuple of (lifetime_revisions, lifetime_days)
        """
        if block_id not in lifetime_tracker:
            return (1, 0)

        track_info = lifetime_tracker[block_id]
        lifetime_revisions = track_info["revision_count"]
        lifetime_days = (current_revision - track_info["first_seen"]).days

        return (lifetime_revisions, lifetime_days)

    def to_tracking_format(self) -> pd.DataFrame:
        """
        Return method tracking results in the original format.

        Returns method_tracking.csv format with block_id and matched_block_id columns.
        Must be called after track().

        Returns:
            DataFrame with 17 columns including block_id and matched_block_id

        Raises:
            RuntimeError: If called before track()
        """
        if self._results_df is None:
            raise RuntimeError("Must call track() before to_tracking_format()")

        return self._results_df.copy()

    def to_lineage_format(self) -> pd.DataFrame:
        """
        Return method tracking results in lineage format.

        Converts block_id to global_block_id (unified across revisions) and removes
        matched_block_id column. Must be called after track().

        Returns:
            DataFrame with 16 columns: global_block_id replaces block_id,
            matched_block_id is removed

        Raises:
            RuntimeError: If called before track()
        """
        if self._results_df is None:
            raise RuntimeError("Must call track() before to_lineage_format()")

        df = self._results_df.copy()

        # Add global_block_id column by looking up in the map
        df["global_block_id"] = df.apply(
            lambda row: self._global_block_id_map.get(
                (row["revision"], row["block_id"]),
                row["block_id"],  # Fallback to block_id if not found
            ),
            axis=1,
        )

        # Define column order: global_block_id first, others except block_id/matched_block_id
        columns = ["global_block_id", "revision", "function_name", "file_path"]
        columns.extend(
            [
                "start_line",
                "end_line",
                "loc",
                "state",
                "state_detail",
                "match_type",
                "match_similarity",
                "clone_count",
                "clone_group_id",
                "clone_group_size",
                "lifetime_revisions",
                "lifetime_days",
            ]
        )

        return df[columns]
