"""Lifetime tracker for method evolution."""

from datetime import datetime


class LifetimeTracker:
    """Tracks lifetime information for methods across revisions.

    This class maintains a dictionary tracking when each method was first
    and last seen, and how many revisions it has appeared in.
    """

    def __init__(self) -> None:
        """Initialize lifetime tracker with empty tracking dictionary."""
        self._tracking: dict[str, dict] = {}

    def initialize_block(self, block_id: str, timestamp: datetime) -> None:
        """Initialize tracking for a new block.

        Args:
            block_id: Block ID to track
            timestamp: Timestamp when block was first seen
        """
        self._tracking[block_id] = {
            "first_seen": timestamp,
            "last_seen": timestamp,
            "revision_count": 1,
        }

    def update_block(self, old_id: str, new_id: str, timestamp: datetime) -> None:
        """Update tracking when a block survives to next revision.

        Args:
            old_id: Block ID in previous revision
            new_id: Block ID in current revision
            timestamp: Current revision timestamp
        """
        if old_id in self._tracking:
            # Update existing tracking
            self._tracking[old_id]["last_seen"] = timestamp
            self._tracking[old_id]["revision_count"] += 1

            # Copy tracking to new ID
            self._tracking[new_id] = self._tracking[old_id].copy()
        else:
            # Fallback: initialize as if it's a new block
            self.initialize_block(new_id, timestamp)

    def get_lifetime(self, block_id: str) -> tuple[int, int]:
        """Get lifetime statistics for a block.

        Args:
            block_id: Block ID to query

        Returns:
            Tuple of (lifetime_revisions, lifetime_days)
            Returns (1, 0) if block is not tracked.
        """
        if block_id not in self._tracking:
            return (1, 0)

        track_info = self._tracking[block_id]
        lifetime_revisions = track_info["revision_count"]
        lifetime_days = (track_info["last_seen"] - track_info["first_seen"]).days

        return (lifetime_revisions, lifetime_days)

    def update_last_seen(self, block_id: str, timestamp: datetime) -> None:
        """Update last_seen timestamp for a block (for deleted blocks).

        Args:
            block_id: Block ID to update
            timestamp: Timestamp when block was last seen
        """
        if block_id in self._tracking:
            self._tracking[block_id]["last_seen"] = timestamp
