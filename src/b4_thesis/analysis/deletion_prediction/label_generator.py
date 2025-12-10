"""Generate ground truth labels for deletion prediction."""

import numpy as np
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
        self.lookahead_window = lookahead_window

    def generate_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate is_deleted_soon labels for each method.
        Args:
            df: DataFrame containing method lineage data with required columns.

        Returns:
            DataFrame with an additional 'target_label' column indicating the
            multiclass target label for deletion prediction.

        """

        sorted_df = df.sort_values(by=["global_block_id", "revision"]).copy()
        sorted_df = self._assign_state_with_clone(sorted_df)
        labeled_df = self._create_future_multiclass_target(sorted_df)

        return labeled_df

    def _assign_state_with_clone(self, df: pd.DataFrame) -> pd.DataFrame:
        """Assign state_with_clone labels based on state and rev_status.

        Args:
            df: DataFrame containing 'state' and 'rev_status' columns.

        Returns:
            DataFrame with an additional 'state_with_clone' column.
        """

        conditions = [
            (df["state"] == "added"),
            (df["state"] == "survived") & (df["rev_status"] == "partial_deleted"),
            (df["state"] == "survived") & (df["rev_status"].isna()),
            (df["state"] == "survived"),
            (df["state"] == "deleted") & (df["rev_status"] == "partial_deleted"),
            (df["state"] == "deleted") & (df["rev_status"] == "all_deleted"),
            (df["state"] == "deleted") & (df["rev_status"].isna()),
        ]

        choices = [
            "added",
            "partial_survived",
            "single_survived",
            "survived",
            "partial_deleted",
            "all_deleted",
            "single_deleted",
        ]

        df["state_with_clone"] = np.select(conditions, choices, default="unknown")

        return df

    def _create_future_multiclass_target(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create multiclass target labels for future method states.

        Args:
            df: DataFrame containing method lineage data with 'global_block_id'
                and 'state_with_clone' columns.
        Returns:
            DataFrame with an additional 'target_label' column indicating the
            multiclass target label based on future method states within the lookahead window.
        """
        future_cols = []
        grouped_series = df.groupby("global_block_id")["state_with_clone"]

        # create future state columns
        for i in range(1, self.lookahead_window + 1):
            future_col = f"future_state_{i}"
            df[future_col] = grouped_series.shift(-i)
            future_cols.append(future_col)

        futures_df = df[future_cols]

        # deletion events
        is_all_deleted = (futures_df == "all_deleted").any(axis=1)
        is_single_deleted = (futures_df == "single_deleted").any(axis=1)
        is_partial_deleted = (futures_df == "partial_deleted").any(axis=1)

        # survival events
        is_partial_survived = (futures_df == "partial_survived").any(axis=1)

        # survived events
        is_survived = futures_df.notna().any(axis=1) & ~(
            is_all_deleted | is_single_deleted | is_partial_deleted | is_partial_survived
        )

        conditions = [
            is_all_deleted,
            is_single_deleted,
            is_partial_deleted,
            is_partial_survived,
            is_survived,
        ]

        choices = [
            "class_all_deleted",
            "class_single_deleted",
            "class_partial_deleted",
            "class_partial_survived",
            "class_survived",
        ]

        # assign multiclass target labels
        df["is_deleted_soon"] = np.select(conditions, choices, default="unknown")

        # clean up future columns
        df.drop(columns=future_cols, inplace=True)

        return df
