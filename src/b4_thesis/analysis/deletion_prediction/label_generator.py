"""Generate ground truth labels for deletion prediction."""

import pandas as pd


class LabelGenerator:
    """Generate ground truth labels for method deletion prediction.

    This class determines whether a method is deleted within a lookahead window
    by tracking its state across consecutive revisions using global_block_id.
    """

    def __init__(self, lookahead_window: int = 5):
        """Initialize LabelGenerator.

        Args:
            lookahead_window: Number of future revisions to check for deletion.
                             Default is 5, meaning a method is marked as "to-be-deleted"
                             if it's deleted within the next 5 revisions.
        """
        if lookahead_window < 1:
            raise ValueError(f"lookahead_window must be >= 1, got {lookahead_window}")
        self.lookahead_window = lookahead_window

    def generate_labels(self, df: pd.DataFrame) -> pd.Series:
        """Generate is_deleted_soon labels for each method.

        For each method in the DataFrame, this function checks if the method
        is deleted within the lookahead window by:
        1. Getting all revisions in sorted order
        2. For each row, checking if the same global_block_id exists in ANY of
           the next X revisions (where X = lookahead_window)
        3. If not exists in any of the next X revisions, the method is deleted

        Args:
            df: DataFrame with columns:
                - global_block_id: Unified ID tracking same method
                - revision: Revision timestamp (YYYYMMDD_HHMMSS_<hash>)

        Returns:
            Boolean Series indicating whether each method is deleted
            within the lookahead window (True) or survives (False).

        Raises:
            ValueError: If required columns are missing

        Example:
            >>> df = pd.DataFrame({
            ...     'global_block_id': ['id1', 'id2', 'id2', 'id2'],
            ...     'revision': ['rev1', 'rev1', 'rev2', 'rev3']
            ... })
            >>> generator = LabelGenerator(lookahead_window=2)
            >>> labels = generator.generate_labels(df)
            >>> labels.tolist()
            [True, False, False, False]  # id1 deleted within 2 revisions, id2 survives
        """
        # Validate required columns
        required_columns = {"global_block_id", "revision"}
        missing_columns = required_columns - set(df.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        # Get all revisions in sorted order
        all_revisions = sorted(df["revision"].unique())
        revision_to_idx = {rev: idx for idx, rev in enumerate(all_revisions)}

        # Create a set of (global_block_id, revision) pairs for fast lookup
        existing_pairs = set(zip(df["global_block_id"], df["revision"]))

        # Generate labels for each row
        labels = []
        for _, row in df.iterrows():
            block_id = row["global_block_id"]
            current_revision = row["revision"]

            current_rev_idx = revision_to_idx[current_revision]

            # Calculate how many future revisions we can actually check
            max_future_idx = min(current_rev_idx + self.lookahead_window, len(all_revisions) - 1)

            # If no future revisions available, cannot determine deletion
            if current_rev_idx >= len(all_revisions) - 1:
                labels.append(False)
                continue

            # Check if block exists in ANY of the next X revisions
            survives = False
            for future_idx in range(current_rev_idx + 1, max_future_idx + 1):
                future_revision = all_revisions[future_idx]
                if (block_id, future_revision) in existing_pairs:
                    survives = True
                    break

            # Deleted within X revisions = not survives
            labels.append(not survives)

        return pd.Series(labels, index=df.index, name="is_deleted_soon")
