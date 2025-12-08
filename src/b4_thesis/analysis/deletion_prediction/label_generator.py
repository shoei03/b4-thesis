"""Generate ground truth labels for deletion prediction."""

import pandas as pd

from b4_thesis.analysis.validation import CsvValidator, DeletionPredictionColumns


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

    def generate_labels(self, df: pd.DataFrame, deleted_df: pd.DataFrame) -> pd.Series:
        """Generate is_deleted_soon labels for each method.

        For each method in the DataFrame (including deleted methods), this function
        checks if the method is deleted within the lookahead window by:
        1. Combining df and deleted_df to get the complete dataset
        2. Getting all revisions in sorted order
        3. For each row in df, checking if the same global_block_id has state='deleted'
           in ANY of the next X revisions (where X = lookahead_window)
        4. If state='deleted' exists in any of the next X revisions, label is True

        Args:
            df: DataFrame with non-deleted methods
            deleted_df: DataFrame with deleted methods (state='deleted')
                Both DataFrames should have columns:
                - global_block_id: Unified ID tracking same method
                - revision: Revision timestamp (YYYYMMDD_HHMMSS_<hash>)
                - state: Method state ('added', 'modified', 'deleted', etc.)

        Returns:
            Boolean Series indicating whether each method is deleted
            within the lookahead window (True) or survives (False).
            Index matches the input df.

        Raises:
            ValueError: If required columns are missing

        Example:
            >>> df = pd.DataFrame({
            ...     'global_block_id': ['id1', 'id1', 'id2'],
            ...     'revision': ['rev1', 'rev2', 'rev1'],
            ...     'state': ['added', 'modified', 'added']
            ... })
            >>> deleted_df = pd.DataFrame({
            ...     'global_block_id': ['id1'],
            ...     'revision': ['rev3'],
            ...     'state': ['deleted']
            ... })
            >>> generator = LabelGenerator(lookahead_window=2)
            >>> labels = generator.generate_labels(df, deleted_df)
            >>> labels.tolist()
            [True, True, False]  # id1 deleted within 2 revs from rev1 and rev2
        """
        # Validate required columns
        CsvValidator.validate_required_columns(
            df,
            DeletionPredictionColumns.LABEL_GENERATION,
            context="label generation DataFrame",
        )

        # Combine df and deleted_df for complete dataset
        combined_df = pd.concat([df, deleted_df], ignore_index=True)

        # Get all revisions in sorted order
        all_revisions = sorted(combined_df["revision"].unique())
        revision_to_idx = {rev: idx for idx, rev in enumerate(all_revisions)}

        # Create a mapping of (global_block_id, revision) -> state for fast lookup
        state_map = {
            (row["global_block_id"], row["revision"]): row["state"]
            for _, row in combined_df.iterrows()
        }

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

            # Check if block has state='deleted' in ANY of the next X revisions
            is_deleted = False
            for future_idx in range(current_rev_idx + 1, max_future_idx + 1):
                future_revision = all_revisions[future_idx]
                state = state_map.get((block_id, future_revision))
                if state == "deleted":
                    is_deleted = True
                    break

            labels.append(is_deleted)

        return pd.Series(labels, index=df.index, name="is_deleted_soon")
