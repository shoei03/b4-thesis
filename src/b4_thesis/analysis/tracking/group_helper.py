"""Helper functions for clone group operations."""

from b4_thesis.analysis.group_detector import CloneGroup


def find_group_for_block(block_id: str | None, groups: dict[str, CloneGroup]) -> CloneGroup | None:
    """Find which group a block belongs to.

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


def calculate_avg_similarity_to_group(block_id: str, group: CloneGroup | None) -> int | None:
    """Calculate average similarity of a block to other group members.

    Args:
        block_id: Block ID to calculate similarity for
        group: Clone group (None if block is not in a group)

    Returns:
        Average similarity (0-100) to other group members, or None if:
        - group is None
        - group size is 1 (no other members)
        - block_id is not in the group
    """
    if group is None or group.size <= 1:
        return None

    if block_id not in group.members:
        return None

    # Collect similarities to all other group members
    similarities = []
    for member in group.members:
        if member == block_id:
            continue

        # Create sorted tuple for lookup
        pair = tuple(sorted([block_id, member]))
        if pair in group.similarities:
            similarities.append(group.similarities[pair])

    if not similarities:
        return None

    return int(sum(similarities) / len(similarities))
