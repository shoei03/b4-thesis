"""State classification for methods and clone groups."""

from enum import Enum

from b4_thesis.analysis.group_detector import CloneGroup
from b4_thesis.analysis.group_matcher import GroupMatch
from b4_thesis.analysis.matching import MatchResult


class MethodState(Enum):
    """Main state of a method across revisions."""

    DELETED = "deleted"
    SURVIVED = "survived"
    ADDED = "added"


class MethodStateDetail(Enum):
    """Detailed state classification for methods."""

    # Deleted states
    DELETED_ISOLATED = "deleted_isolated"
    DELETED_FROM_GROUP = "deleted_from_group"
    DELETED_LAST_MEMBER = "deleted_last_member"

    # Survived states
    SURVIVED_UNCHANGED = "survived_unchanged"
    SURVIVED_MODIFIED = "survived_modified"
    SURVIVED_CLONE_GAINED = "survived_clone_gained"
    SURVIVED_CLONE_LOST = "survived_clone_lost"

    # Added states
    ADDED_ISOLATED = "added_isolated"
    ADDED_TO_GROUP = "added_to_group"
    ADDED_NEW_GROUP = "added_new_group"


class GroupState(Enum):
    """State of a clone group across revisions."""

    CONTINUED = "continued"
    GROWN = "grown"
    SHRUNK = "shrunk"
    SPLIT = "split"
    MERGED = "merged"
    DISSOLVED = "dissolved"
    BORN = "born"


class StateClassifier:
    """Classifies method and group states across revisions."""

    def __init__(self, size_tolerance: float = 0.1) -> None:
        """Initialize state classifier.

        Args:
            size_tolerance: Tolerance for group size changes (default: 0.1 = 10%)
        """
        self.size_tolerance = size_tolerance

    def classify_method_state(
        self,
        block_id: str,
        match_result: MatchResult,
        direction: str,
        group_old: CloneGroup | None,
        group_new: CloneGroup | None,
        is_last_member: bool = False,
        is_new_group: bool = False,
    ) -> tuple[MethodState, MethodStateDetail]:
        """Classify method state between revisions.

        Args:
            block_id: Block ID to classify
            match_result: Result of method matching
            direction: "forward" for old->new, "backward" for new->old
            group_old: Clone group in old revision (None if not in a group)
            group_new: Clone group in new revision (None if not in a group)
            is_last_member: True if this was the last member of its group
            is_new_group: True if the new group is newly formed

        Returns:
            Tuple of (MethodState, MethodStateDetail)
        """
        # Check if method has a match
        if direction == "forward":
            has_match = block_id in match_result.forward_matches
            match_type = match_result.match_types.get(block_id) if has_match else None
        else:  # backward
            has_match = block_id in match_result.backward_matches
            # For backward, we need to find the match_type by looking in forward direction
            if has_match:
                matched_block = match_result.backward_matches[block_id]
                match_type = match_result.match_types.get(matched_block)
            else:
                match_type = None

        # Classify based on match existence
        if not has_match:
            if direction == "forward":
                # Method deleted
                return self._classify_deleted(group_old, is_last_member)
            else:
                # Method added
                return self._classify_added(group_new, is_new_group)
        else:
            # Method survived
            return self._classify_survived(match_type, group_old, group_new)

    def _classify_deleted(
        self, group_old: CloneGroup | None, is_last_member: bool
    ) -> tuple[MethodState, MethodStateDetail]:
        """Classify deleted method detail."""
        if group_old is None:
            detail = MethodStateDetail.DELETED_ISOLATED
        elif is_last_member:
            detail = MethodStateDetail.DELETED_LAST_MEMBER
        else:
            detail = MethodStateDetail.DELETED_FROM_GROUP

        return MethodState.DELETED, detail

    def _classify_survived(
        self,
        match_type: str | None,
        group_old: CloneGroup | None,
        group_new: CloneGroup | None,
    ) -> tuple[MethodState, MethodStateDetail]:
        """Classify survived method detail."""
        # Check for clone status changes
        had_clones = group_old is not None and group_old.size > 1
        has_clones = group_new is not None and group_new.size > 1

        # Determine detail based on modification and clone status
        if not had_clones and has_clones:
            # Gained clones
            detail = MethodStateDetail.SURVIVED_CLONE_GAINED
        elif had_clones and not has_clones:
            # Lost clones
            detail = MethodStateDetail.SURVIVED_CLONE_LOST
        elif match_type == "token_hash":
            # Unchanged (token_hash match)
            detail = MethodStateDetail.SURVIVED_UNCHANGED
        else:
            # Modified (similarity match)
            detail = MethodStateDetail.SURVIVED_MODIFIED

        return MethodState.SURVIVED, detail

    def _classify_added(
        self, group_new: CloneGroup | None, is_new_group: bool
    ) -> tuple[MethodState, MethodStateDetail]:
        """Classify added method detail."""
        if group_new is None:
            detail = MethodStateDetail.ADDED_ISOLATED
        elif is_new_group:
            detail = MethodStateDetail.ADDED_NEW_GROUP
        else:
            detail = MethodStateDetail.ADDED_TO_GROUP

        return MethodState.ADDED, detail

    def classify_group_state(
        self,
        group_match: GroupMatch | None,
        is_split: bool = False,
        is_merged: bool = False,
    ) -> GroupState:
        """Classify group state between revisions.

        Args:
            group_match: Result of group matching (None for new groups)
            is_split: True if group split into multiple groups
            is_merged: True if multiple groups merged into this one

        Returns:
            GroupState classification
        """
        # Handle new groups
        if group_match is None:
            return GroupState.BORN

        # Handle dissolved groups
        if group_match.target_group_id is None:
            return GroupState.DISSOLVED

        # Split and merge take precedence
        if is_split:
            return GroupState.SPLIT
        if is_merged:
            return GroupState.MERGED

        # Calculate size change ratio
        size_ratio = group_match.target_size / group_match.source_size

        # Classify based on size change
        if size_ratio > (1 + self.size_tolerance):
            return GroupState.GROWN
        elif size_ratio < (1 - self.size_tolerance):
            return GroupState.SHRUNK
        else:
            return GroupState.CONTINUED
