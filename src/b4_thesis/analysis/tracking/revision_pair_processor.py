"""Revision pair processor for tracking method evolution."""

# Import MethodTrackingResult from method_tracker to avoid circular import
# We'll use TYPE_CHECKING to avoid runtime circular import
from typing import TYPE_CHECKING

from b4_thesis.analysis.group_detector import GroupDetector
from b4_thesis.analysis.matching import MethodMatcher
from b4_thesis.analysis.state_classifier import StateClassifier
from b4_thesis.analysis.tracking.group_helper import (
    calculate_avg_similarity_to_group,
    find_group_for_block,
)
from b4_thesis.analysis.tracking.lifetime_tracker import LifetimeTracker
from b4_thesis.core.revision_manager import RevisionInfo, RevisionManager

if TYPE_CHECKING:
    from b4_thesis.analysis.method_tracker import MethodTrackingResult


class RevisionPairProcessor:
    """Processes pairs of consecutive revisions to track method evolution."""

    def __init__(
        self,
        revision_manager: RevisionManager,
        method_matcher: MethodMatcher,
        group_detector: GroupDetector,
        state_classifier: StateClassifier,
    ) -> None:
        """Initialize revision pair processor.

        Args:
            revision_manager: Manager for loading revision data
            method_matcher: Matcher for identifying method correspondence
            group_detector: Detector for finding clone groups
            state_classifier: Classifier for determining method state
        """
        self.revision_manager = revision_manager
        self.method_matcher = method_matcher
        self.group_detector = group_detector
        self.state_classifier = state_classifier

    def process_pair(
        self,
        revision_old: RevisionInfo,
        revision_new: RevisionInfo,
        lifetime_tracker: LifetimeTracker,
        parallel: bool = False,
        max_workers: int | None = None,
    ) -> list["MethodTrackingResult"]:
        """Process a pair of consecutive revisions.

        Args:
            revision_old: Previous revision
            revision_new: Current revision
            lifetime_tracker: LifetimeTracker instance
            parallel: If True, use parallel processing for similarity calculation
            max_workers: Maximum number of worker processes (if parallel=True)

        Returns:
            List of tracking results for the new revision
        """
        # Import here to avoid circular import at module level
        from b4_thesis.analysis.method_tracker import MethodTrackingResult

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
                lifetime_tracker.initialize_block(block_id, revision_new.timestamp)
            else:
                # Existing method (survived)
                state = "survived"
                matched_block_id = old_block_id
                match_type = match_result.match_types.get(old_block_id, "none")
                match_similarity = match_result.match_similarities.get(old_block_id)

                # Update lifetime tracking
                lifetime_tracker.update_block(old_block_id, block_id, revision_new.timestamp)
                lifetime_revisions, lifetime_days = lifetime_tracker.get_lifetime(block_id)

            # Find group membership
            group_old = find_group_for_block(old_block_id, groups_old) if old_block_id else None
            group_new = find_group_for_block(block_id, groups_new)

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

            # Calculate average similarity to group members
            avg_similarity = calculate_avg_similarity_to_group(block_id, group_new)

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
                avg_similarity_to_group=avg_similarity,
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
            group_old = find_group_for_block(old_block_id, groups_old)

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
            lifetime_tracker.update_last_seen(old_block_id, revision_new.timestamp)
            lifetime_revisions, lifetime_days = lifetime_tracker.get_lifetime(old_block_id)

            # Calculate average similarity to group members (using old group)
            avg_similarity = calculate_avg_similarity_to_group(old_block_id, group_old)

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
                matched_block_id=old_block_id,
                match_type="none",
                match_similarity=None,
                clone_count=group_old.size - 1 if group_old and group_old.is_clone else 0,
                clone_group_id=group_old.group_id if group_old and group_old.is_clone else None,
                clone_group_size=group_old.size if group_old else 1,
                avg_similarity_to_group=avg_similarity,
                lifetime_revisions=lifetime_revisions,
                lifetime_days=lifetime_days,
            )
            results.append(result)

        return results
