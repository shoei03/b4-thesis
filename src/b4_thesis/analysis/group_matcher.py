"""Group matching between revisions for clone group tracking."""

from dataclasses import dataclass

from b4_thesis.analysis.group_detector import CloneGroup
from b4_thesis.analysis.method_matcher import MatchResult


@dataclass
class GroupMatch:
    """Result of matching a group between revisions.

    Attributes:
        source_group_id: ID of the source group in old revision
        target_group_id: ID of the matched target group in new revision (None if no match)
        overlap_count: Number of matched members between source and target
        overlap_ratio: Ratio of matched members to source group size
        source_size: Size of source group
        target_size: Size of target group (None if no match)
    """

    source_group_id: str
    target_group_id: str | None
    overlap_count: int
    overlap_ratio: float
    source_size: int
    target_size: int | None


class GroupMatcher:
    """Matches clone groups between consecutive revisions.

    This class matches groups based on member overlap. A group from the old
    revision matches a group in the new revision if a sufficient percentage
    of its members are matched to members of the new group.
    """

    def __init__(self, overlap_threshold: float = 0.5) -> None:
        """Initialize GroupMatcher.

        Args:
            overlap_threshold: Minimum overlap ratio (0.0-1.0) for matching.
                             Default is 0.5 (50% of members must match).
        """
        self.overlap_threshold = overlap_threshold
        # Internal state to track all overlaps for split/merge detection
        self._all_overlaps: dict[str, dict[str, int]] = {}

    def match_groups(
        self,
        groups_old: dict[str, CloneGroup],
        groups_new: dict[str, CloneGroup],
        method_matches: MatchResult,
    ) -> dict[str, GroupMatch]:
        """Match groups from old revision to new revision.

        For each group in the old revision, find which group in the new revision
        contains the most matched members. If the overlap ratio meets the threshold,
        consider it a match.

        Args:
            groups_old: Groups in old revision {group_id -> CloneGroup}
            groups_new: Groups in new revision {group_id -> CloneGroup}
            method_matches: Method matching results from MethodMatcher

        Returns:
            Dictionary mapping old_group_id -> GroupMatch
        """
        matches: dict[str, GroupMatch] = {}
        # Reset internal overlap tracking
        self._all_overlaps = {}

        for old_group_id, old_group in groups_old.items():
            # Track which new groups the old group members matched to
            new_group_counts: dict[str, int] = {}

            # For each member in the old group, find where it matched
            for old_block_id in old_group.members:
                # Check if this block matched to a new block
                if old_block_id in method_matches.forward_matches:
                    new_block_id = method_matches.forward_matches[old_block_id]

                    # Find which new group contains this new block
                    new_group_id = self._find_group_of_block(new_block_id, groups_new)

                    if new_group_id is not None:
                        new_group_counts[new_group_id] = new_group_counts.get(new_group_id, 0) + 1

            # Store all overlaps for split/merge detection
            self._all_overlaps[old_group_id] = new_group_counts.copy()

            # Find the new group with the most matches
            if new_group_counts:
                best_new_group_id = max(new_group_counts, key=new_group_counts.get)
                overlap_count = new_group_counts[best_new_group_id]
                overlap_ratio = overlap_count / old_group.size

                # Check if overlap meets threshold
                if overlap_ratio >= self.overlap_threshold:
                    target_group = groups_new[best_new_group_id]
                    matches[old_group_id] = GroupMatch(
                        source_group_id=old_group_id,
                        target_group_id=best_new_group_id,
                        overlap_count=overlap_count,
                        overlap_ratio=overlap_ratio,
                        source_size=old_group.size,
                        target_size=target_group.size,
                    )
                else:
                    # Below threshold - no match
                    matches[old_group_id] = GroupMatch(
                        source_group_id=old_group_id,
                        target_group_id=None,
                        overlap_count=overlap_count,
                        overlap_ratio=overlap_ratio,
                        source_size=old_group.size,
                        target_size=None,
                    )
            else:
                # No members matched - group dissolved
                matches[old_group_id] = GroupMatch(
                    source_group_id=old_group_id,
                    target_group_id=None,
                    overlap_count=0,
                    overlap_ratio=0.0,
                    source_size=old_group.size,
                    target_size=None,
                )

        return matches

    def _find_group_of_block(self, block_id: str, groups: dict[str, CloneGroup]) -> str | None:
        """Find which group a block belongs to.

        Args:
            block_id: Block ID to search for
            groups: Dictionary of groups to search in

        Returns:
            Group ID if found, None otherwise
        """
        for group_id, group in groups.items():
            if block_id in group.members:
                return group_id
        return None

    def detect_splits(self, matches: dict[str, GroupMatch]) -> list[tuple[str, list[str]]]:
        """Detect split groups (1 old group -> multiple new groups).

        A split occurs when members of one old group match to multiple different
        new groups, each with significant overlap.

        Args:
            matches: Group matching results from match_groups()

        Returns:
            List of (old_group_id, [new_group_ids]) tuples
        """
        splits: list[tuple[str, list[str]]] = []

        # For each old group, check if it has significant overlaps with multiple new groups
        for old_group_id, overlaps in self._all_overlaps.items():
            # Get the source group size
            match = matches.get(old_group_id)
            if match is None:
                continue

            source_size = match.source_size

            # Find all new groups with significant overlap (>= threshold)
            significant_targets = []
            for new_group_id, overlap_count in overlaps.items():
                overlap_ratio = overlap_count / source_size
                if overlap_ratio >= self.overlap_threshold:
                    significant_targets.append(new_group_id)

            # If members went to multiple new groups, it's a split
            if len(significant_targets) > 1:
                splits.append((old_group_id, sorted(significant_targets)))

        return splits

    def detect_merges(self, matches: dict[str, GroupMatch]) -> list[tuple[list[str], str]]:
        """Detect merged groups (multiple old groups -> 1 new group).

        A merge occurs when multiple old groups all match to the same new group.

        Args:
            matches: Group matching results from match_groups()

        Returns:
            List of ([old_group_ids], new_group_id) tuples
        """
        # Build reverse mapping: new_group_id -> list of old_group_ids that matched to it
        new_to_old: dict[str, list[str]] = {}

        for old_group_id, match in matches.items():
            if match.target_group_id is not None:
                if match.target_group_id not in new_to_old:
                    new_to_old[match.target_group_id] = []
                new_to_old[match.target_group_id].append(old_group_id)

        # Find new groups that have multiple old groups matched to them
        merges: list[tuple[list[str], str]] = []
        for new_group_id, old_group_ids in new_to_old.items():
            if len(old_group_ids) > 1:
                merges.append((sorted(old_group_ids), new_group_id))

        return merges
