"""Data validator for code_blocks and clone_pairs CSV files."""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


class DataValidator:
    """Validates CSV data for code_blocks and clone_pairs."""

    # Required columns for code_blocks.csv
    CODE_BLOCKS_COLUMNS = [
        "block_id",
        "file_path",
        "start_line",
        "end_line",
        "function_name",
        "return_type",
        "parameters",
        "token_hash",
        "token_sequence",
    ]

    # Required columns for clone_pairs.csv
    CLONE_PAIRS_COLUMNS = [
        "block_id_1",
        "block_id_2",
        "ngram_similarity",
        "lcs_similarity",
    ]

    # Required columns for method_tracking.csv
    METHOD_TRACKING_COLUMNS = [
        "revision",
        "block_id",
        "function_name",
        "file_path",
        "start_line",
        "end_line",
        "loc",
        "state",
        "state_detail",
        "matched_block_id",
        "match_type",
        "match_similarity",
        "clone_count",
        "clone_group_id",
        "clone_group_size",
        "avg_similarity_to_group",
        "lifetime_revisions",
        "lifetime_days",
    ]

    def validate_code_blocks(self, df: pd.DataFrame, source: str = "") -> pd.DataFrame:
        """Validate code_blocks DataFrame.

        Args:
            df: DataFrame to validate
            source: Source identifier for logging (e.g., file path)

        Returns:
            Validated DataFrame (same as input)

        Note:
            Validation errors are logged as warnings but do not stop processing.
        """
        source_info = f" ({source})" if source else ""

        # Check required columns
        missing_cols = set(self.CODE_BLOCKS_COLUMNS) - set(df.columns)
        if missing_cols:
            logger.warning(f"code_blocks missing required columns{source_info}: {missing_cols}")

        # Check for missing values in critical columns
        critical_cols = ["block_id", "file_path", "start_line", "end_line", "function_name"]
        for col in critical_cols:
            if col in df.columns and df[col].isna().any():
                missing_count = df[col].isna().sum()
                logger.warning(
                    f"code_blocks has {missing_count} missing values in '{col}'{source_info}"
                )

        # Validate data types for numeric columns
        numeric_cols = ["start_line", "end_line"]
        for col in numeric_cols:
            if col in df.columns:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    logger.warning(f"code_blocks column '{col}' should be numeric{source_info}")

        # Validate line number ranges (start_line <= end_line)
        if "start_line" in df.columns and "end_line" in df.columns:
            invalid_ranges = df[df["start_line"] > df["end_line"]]
            if len(invalid_ranges) > 0:
                logger.warning(
                    f"code_blocks has {len(invalid_ranges)} rows with "
                    f"start_line > end_line{source_info}"
                )

            # Check for non-positive line numbers
            if (df["start_line"] <= 0).any():
                invalid_count = (df["start_line"] <= 0).sum()
                logger.warning(
                    f"code_blocks has {invalid_count} rows with start_line <= 0{source_info}"
                )

        return df

    def validate_clone_pairs(self, df: pd.DataFrame, source: str = "") -> pd.DataFrame:
        """Validate clone_pairs DataFrame.

        Args:
            df: DataFrame to validate
            source: Source identifier for logging (e.g., file path)

        Returns:
            Validated DataFrame (same as input)

        Note:
            Validation errors are logged as warnings but do not stop processing.
            Empty DataFrame is valid (no clones case).
        """
        # Empty DataFrame is valid
        if len(df) == 0:
            return df

        source_info = f" ({source})" if source else ""

        # Check required columns
        missing_cols = set(self.CLONE_PAIRS_COLUMNS) - set(df.columns)
        if missing_cols:
            logger.warning(f"clone_pairs missing required columns{source_info}: {missing_cols}")

        # Check for missing values
        for col in self.CLONE_PAIRS_COLUMNS:
            if col in df.columns and df[col].isna().any():
                missing_count = df[col].isna().sum()
                logger.warning(
                    f"clone_pairs has {missing_count} missing values in '{col}'{source_info}"
                )

        # Validate similarity ranges (0-100)
        similarity_cols = ["ngram_similarity", "lcs_similarity"]
        for col in similarity_cols:
            if col in df.columns:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    logger.warning(f"clone_pairs column '{col}' should be numeric{source_info}")
                else:
                    # Check range
                    out_of_range = df[(df[col] < 0) | (df[col] > 100)]
                    if len(out_of_range) > 0:
                        logger.warning(
                            f"clone_pairs has {len(out_of_range)} rows with "
                            f"'{col}' outside 0-100 range{source_info}"
                        )

        return df

    def validate_method_tracking(self, df: pd.DataFrame, source: str = "") -> pd.DataFrame:
        """Validate method_tracking DataFrame.

        Args:
            df: DataFrame to validate
            source: Source identifier for logging (e.g., file path)

        Returns:
            Validated DataFrame (same as input)

        Note:
            Validation errors are logged as warnings but do not stop processing.
            For state="deleted" or state="added", matched_block_id/match_type/match_similarity
            are allowed to be missing. However, for other states (e.g., "survived"),
            missing values in these fields will be logged as unexpected.
        """
        source_info = f" ({source})" if source else ""

        # Check required columns
        missing_cols = set(self.METHOD_TRACKING_COLUMNS) - set(df.columns)
        if missing_cols:
            logger.warning(f"method_tracking missing required columns{source_info}: {missing_cols}")

        # Check for missing values in critical columns (always required)
        critical_cols = ["revision", "block_id", "function_name", "file_path", "state"]
        for col in critical_cols:
            if col in df.columns and df[col].isna().any():
                missing_count = df[col].isna().sum()
                logger.warning(
                    f"method_tracking has {missing_count} missing values in '{col}'{source_info}"
                )

        # Validate state values
        if "state" in df.columns:
            valid_states = {"added", "deleted", "survived"}
            invalid_states = df[~df["state"].isin(valid_states) & df["state"].notna()]
            if len(invalid_states) > 0:
                unique_invalid = invalid_states["state"].unique()
                logger.warning(
                    f"method_tracking has {len(invalid_states)} rows with "
                    f"invalid state values{source_info}: {unique_invalid}"
                )

            # Check match-related fields for survived methods
            # For "added", these fields are expected to be missing
            # For "deleted", matched_block_id is set to the block's own ID for lineage tracking
            if all(col in df.columns for col in ["state", "matched_block_id", "match_type"]):
                survived_df = df[df["state"] == "survived"]

                if not survived_df.empty:
                    # Check matched_block_id
                    if survived_df["matched_block_id"].isna().any():
                        missing_count = survived_df["matched_block_id"].isna().sum()
                        logger.warning(
                            f"method_tracking has {missing_count} survived methods with "
                            f"missing matched_block_id{source_info}"
                        )

                    # Check match_type
                    if survived_df["match_type"].isna().any():
                        missing_count = survived_df["match_type"].isna().sum()
                        logger.warning(
                            f"method_tracking has {missing_count} survived methods with "
                            f"missing match_type{source_info}"
                        )

                    # Check match_similarity
                    if (
                        "match_similarity" in df.columns
                        and survived_df["match_similarity"].isna().any()
                    ):
                        missing_count = survived_df["match_similarity"].isna().sum()
                        logger.warning(
                            f"method_tracking has {missing_count} survived methods with "
                            f"missing match_similarity{source_info}"
                        )

        # Validate data types for numeric columns
        numeric_cols = ["start_line", "end_line", "loc", "lifetime_revisions", "lifetime_days"]
        for col in numeric_cols:
            if col in df.columns:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    logger.warning(f"method_tracking column '{col}' should be numeric{source_info}")

        # Validate line number ranges (start_line <= end_line)
        if "start_line" in df.columns and "end_line" in df.columns:
            invalid_ranges = df[df["start_line"] > df["end_line"]]
            if len(invalid_ranges) > 0:
                logger.warning(
                    f"method_tracking has {len(invalid_ranges)} rows with "
                    f"start_line > end_line{source_info}"
                )

            # Check for non-positive line numbers
            if (df["start_line"] <= 0).any():
                invalid_count = (df["start_line"] <= 0).sum()
                logger.warning(
                    f"method_tracking has {invalid_count} rows with start_line <= 0{source_info}"
                )

        # Validate similarity ranges (0-100) if numeric
        similarity_cols = ["match_similarity", "avg_similarity_to_group"]
        for col in similarity_cols:
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                out_of_range = df[(df[col] < 0) | (df[col] > 100)]
                if len(out_of_range) > 0:
                    logger.warning(
                        f"method_tracking has {len(out_of_range)} rows with "
                        f"'{col}' outside 0-100 range{source_info}"
                    )

        return df
