"""Generate ground truth labels for deletion prediction."""

import pandas as pd


class LabelGenerator:
    """Generate ground truth labels for method deletion prediction.

    This class determines whether a method is deleted in the next revision
    by tracking its state across consecutive revisions using global_block_id.
    """

    def generate_labels(self, df: pd.DataFrame) -> pd.Series:
        """Generate is_deleted_next labels for each method.

        For each method in the DataFrame, this function checks if the method
        is deleted in the next revision by:
        1. Getting all revisions in sorted order
        2. For each row, checking if the same global_block_id exists in next revision
        3. If not exists in next revision, the method is deleted

        Args:
            df: DataFrame with columns:
                - global_block_id: Unified ID tracking same method
                - revision: Revision timestamp (YYYYMMDD_HHMMSS_<hash>)

        Returns:
            Boolean Series indicating whether each method is deleted
            in the next revision (True) or not (False).

        Raises:
            ValueError: If required columns are missing

        Example:
            >>> df = pd.DataFrame({
            ...     'global_block_id': ['id1', 'id2', 'id2'],
            ...     'revision': ['rev1', 'rev1', 'rev2']
            ... })
            >>> generator = LabelGenerator()
            >>> labels = generator.generate_labels(df)
            >>> labels.tolist()
            [True, False, False]  # id1 deleted in rev2, id2 survives
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

            # Check if there's a next revision
            if current_rev_idx == len(all_revisions) - 1:
                # Last revision in dataset - cannot determine if deleted
                labels.append(False)
            else:
                # Check if this block exists in next revision
                next_revision = all_revisions[current_rev_idx + 1]
                exists_in_next = (block_id, next_revision) in existing_pairs
                labels.append(not exists_in_next)  # True if deleted (not exists)

        return pd.Series(labels, index=df.index, name="is_deleted_next")
