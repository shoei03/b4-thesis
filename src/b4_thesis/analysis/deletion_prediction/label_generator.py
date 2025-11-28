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
        1. Grouping methods by global_block_id
        2. Sorting by revision within each group
        3. Checking if state='deleted' in the next revision

        Args:
            df: DataFrame with columns:
                - global_block_id: Unified ID tracking same method
                - revision: Revision timestamp (YYYYMMDD_HHMMSS_<hash>)
                - state: Method state ('survived', 'deleted', 'added')

        Returns:
            Boolean Series indicating whether each method is deleted
            in the next revision (True) or not (False).

        Raises:
            ValueError: If required columns are missing

        Example:
            >>> df = pd.DataFrame({
            ...     'global_block_id': ['id1', 'id1', 'id2', 'id2'],
            ...     'revision': ['rev1', 'rev2', 'rev1', 'rev2'],
            ...     'state': ['survived', 'deleted', 'survived', 'survived']
            ... })
            >>> generator = LabelGenerator()
            >>> labels = generator.generate_labels(df)
            >>> labels.tolist()
            [True, False, False, False]  # id1 deleted in rev2, id2 survives
        """
        # Validate required columns
        required_columns = {"global_block_id", "revision", "state"}
        missing_columns = required_columns - set(df.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        # Sort by global_block_id and revision, keeping track of original index
        df_with_index = df.reset_index()
        df_sorted = df_with_index.sort_values(["global_block_id", "revision"])

        # Generate labels for each row in sorted order
        labels_dict = {}  # Map from original index to label

        for block_id, group in df_sorted.groupby("global_block_id", sort=False):
            group_sorted = group.sort_values("revision")
            group_list = list(group_sorted.itertuples())

            for i, row in enumerate(group_list):
                original_idx = row.index
                if i == len(group_list) - 1:
                    # Last revision in the group - no next revision exists
                    labels_dict[original_idx] = False
                else:
                    # Check if state is 'deleted' in the next revision
                    next_state = group_list[i + 1].state
                    labels_dict[original_idx] = next_state == "deleted"

        # Create Series with labels in original DataFrame order
        result = pd.Series(
            [labels_dict[i] for i in range(len(df))],
            index=df.index,
            name="is_deleted_next",
        )

        return result
