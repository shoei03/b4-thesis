"""Strict CSV validator for deletion prediction analysis.

This validator provides strict validation (raises exceptions) for CSV data
used in deletion prediction, complementing the warning-based DataValidator.
"""

from pathlib import Path
from typing import Set

import pandas as pd


class CsvValidator:
    """Strict CSV validator with exception-based error handling.

    Unlike DataValidator (which logs warnings), this validator raises
    exceptions for validation failures, ensuring data integrity for
    critical deletion prediction workflows.
    """

    @staticmethod
    def validate_file_exists(csv_path: Path) -> None:
        """Validate that CSV file exists.

        Args:
            csv_path: Path to CSV file

        Raises:
            FileNotFoundError: If CSV file not found
        """
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

    @staticmethod
    def load_csv(csv_path: Path) -> pd.DataFrame:
        """Load CSV file after validating existence.

        Args:
            csv_path: Path to CSV file

        Returns:
            Loaded DataFrame

        Raises:
            FileNotFoundError: If CSV file not found
            pd.errors.EmptyDataError: If CSV is empty
            pd.errors.ParserError: If CSV parsing fails
        """
        CsvValidator.validate_file_exists(csv_path)
        return pd.read_csv(csv_path)

    @staticmethod
    def validate_required_columns(
        df: pd.DataFrame,
        required_columns: Set[str],
        context: str = "DataFrame",
    ) -> None:
        """Validate that all required columns exist in DataFrame.

        Args:
            df: DataFrame to validate
            required_columns: Set of required column names
            context: Context description for error messages (e.g., "features CSV")

        Raises:
            ValueError: If any required columns are missing
        """
        missing_columns = required_columns - set(df.columns)
        if missing_columns:
            raise ValueError(f"{context} missing required columns: {missing_columns}")

    @staticmethod
    def validate_non_empty(df: pd.DataFrame, context: str = "DataFrame") -> None:
        """Validate that DataFrame is not empty.

        Args:
            df: DataFrame to validate
            context: Context description for error messages

        Raises:
            ValueError: If DataFrame is empty
        """
        if len(df) == 0:
            raise ValueError(f"{context} is empty")

    @classmethod
    def load_and_validate(
        cls,
        csv_path: Path,
        required_columns: Set[str],
        allow_empty: bool = False,
        context: str | None = None,
    ) -> pd.DataFrame:
        """Load CSV and validate required columns in one step.

        Args:
            csv_path: Path to CSV file
            required_columns: Set of required column names
            allow_empty: If False, raise error for empty DataFrame
            context: Context description (default: filename)

        Returns:
            Validated DataFrame

        Raises:
            FileNotFoundError: If CSV file not found
            ValueError: If validation fails
        """
        # Use filename as default context
        if context is None:
            context = csv_path.name

        # Load CSV
        df = cls.load_csv(csv_path)

        # Validate columns
        cls.validate_required_columns(df, required_columns, context)

        # Validate non-empty if required
        if not allow_empty:
            cls.validate_non_empty(df, context)

        return df


# Predefined column sets for deletion prediction
class DeletionPredictionColumns:
    """Predefined required column sets for deletion prediction workflows."""

    # Basic columns needed for CSV loading (csv_loader.py)
    BASIC = {
        "global_block_id",
        "revision",
        "function_name",
        "file_path",
        "start_line",
        "end_line",
        "loc",
        "state",
    }

    # Minimal columns for label generation (label_generator.py)
    LABEL_GENERATION = {
        "global_block_id",
        "revision",
        "state",
    }

    # Columns needed for evaluation (evaluator.py)
    EVALUATION_BASIC = {
        "is_deleted_soon",
    }

    # Additional columns needed for detailed evaluation mode
    EVALUATION_DETAILED = {
        "global_block_id",
        "revision",
        "function_name",
        "file_path",
        "lifetime_revisions",
        "lifetime_days",
    }

    @classmethod
    def get_evaluation_columns(cls, detailed: bool = False) -> Set[str]:
        """Get required columns for evaluation mode.

        Args:
            detailed: If True, include columns for detailed mode

        Returns:
            Set of required column names
        """
        if detailed:
            return cls.EVALUATION_BASIC | cls.EVALUATION_DETAILED
        return cls.EVALUATION_BASIC
