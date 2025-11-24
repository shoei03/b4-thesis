"""Revision labeling for clone group state classification."""

from enum import Enum

import pandas as pd


class RevisionStatus(Enum):
    """Status of a clone group in a specific revision based on deleted state."""

    ALL_DELETED = "all_deleted"
    PARTIAL_DELETED = "partial_deleted"
    NO_DELETED = "no_deleted"


class RevisionLabeler:
    """Labels clone groups per revision based on member states.

    Classifies each (clone_group_id, revision) pair based on the distribution
    of 'deleted' states among its members:
    - all_deleted: All members are deleted
    - partial_deleted: Some members are deleted
    - no_deleted: No members are deleted
    """

    REQUIRED_COLUMNS = ["clone_group_id", "revision", "state"]

    def label_revisions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add rev_status label to each row based on clone group revision state.

        Args:
            df: DataFrame with method lineage data containing at least
                clone_group_id, revision, and state columns.

        Returns:
            DataFrame with added 'rev_status' column.

        Raises:
            ValueError: If required columns are missing.
        """
        self._validate_columns(df)

        # Sort for readability
        df = df.sort_values(["clone_group_id", "revision"])

        # Count states per (clone_group_id, revision)
        rev_state_counts = (
            df.groupby(["clone_group_id", "revision"])["state"].value_counts().unstack(fill_value=0)
        )

        # Ensure required state columns exist
        for col in ["added", "deleted", "survived"]:
            if col not in rev_state_counts.columns:
                rev_state_counts[col] = 0

        # Calculate total and assign status
        rev_state_counts["n_total"] = rev_state_counts[["added", "deleted", "survived"]].sum(axis=1)

        # Default: no_deleted
        rev_state_counts["rev_status"] = RevisionStatus.NO_DELETED.value

        # partial_deleted: at least one deleted
        rev_state_counts.loc[rev_state_counts["deleted"] > 0, "rev_status"] = (
            RevisionStatus.PARTIAL_DELETED.value
        )

        # all_deleted: all rows are deleted
        rev_state_counts.loc[
            rev_state_counts["deleted"] == rev_state_counts["n_total"], "rev_status"
        ] = RevisionStatus.ALL_DELETED.value

        # Extract rev_status and merge back
        rev_status = rev_state_counts["rev_status"].rename("rev_status")

        result = df.merge(
            rev_status,
            left_on=["clone_group_id", "revision"],
            right_index=True,
            how="left",
        )

        return result

    def get_revision_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Get summary of clone groups per revision by status.

        Args:
            df: DataFrame with rev_status column (output of label_revisions).

        Returns:
            DataFrame with columns: revision, rev_status, n_groups
        """
        if "rev_status" not in df.columns:
            raise ValueError("DataFrame must have 'rev_status' column. Run label_revisions first.")

        # Get unique (clone_group_id, revision) pairs
        groups_per_rev = df.drop_duplicates(["clone_group_id", "revision"])

        # Count unique clone_group_ids per (revision, rev_status)
        summary = (
            groups_per_rev.groupby(["revision", "rev_status"])["clone_group_id"]
            .nunique()
            .reset_index(name="n_groups")
        )

        return summary

    def _validate_columns(self, df: pd.DataFrame) -> None:
        """Validate that required columns exist in the DataFrame.

        Args:
            df: DataFrame to validate.

        Raises:
            ValueError: If any required columns are missing.
        """
        missing = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
