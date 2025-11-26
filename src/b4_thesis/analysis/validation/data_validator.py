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
