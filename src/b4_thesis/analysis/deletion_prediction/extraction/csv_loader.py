"""CSV data loader for deletion prediction feature extraction."""

from pathlib import Path

import pandas as pd

from b4_thesis.analysis.deletion_prediction.extraction.result_types import CsvLoadResult


class CsvDataLoader:
    """Load and validate method lineage CSV data.

    This component handles:
    - Loading CSV file
    - Validating required columns
    - Filtering deleted methods (code doesn't exist for them)
    """

    REQUIRED_COLUMNS = {
        "global_block_id",
        "revision",
        "function_name",
        "file_path",
        "start_line",
        "end_line",
        "loc",
        "state",
    }

    def load_and_validate(self, csv_path: Path) -> CsvLoadResult:
        """Load CSV and validate required columns.

        Args:
            csv_path: Path to method_lineage_labeled.csv

        Returns:
            CsvLoadResult with validated DataFrame and statistics

        Raises:
            FileNotFoundError: If CSV file not found
            ValueError: If CSV missing required columns or no methods after filtering
        """
        # Load CSV
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        df = pd.read_csv(csv_path)

        # Validate required columns
        missing_columns = self.REQUIRED_COLUMNS - set(df.columns)
        if missing_columns:
            raise ValueError(f"CSV missing required columns: {missing_columns}")

        # Filter out deleted methods (code doesn't exist for them)
        original_count = len(df)
        df = df[df["state"] != "deleted"].copy()
        deleted_count = original_count - len(df)

        if len(df) == 0:
            raise ValueError("No methods to process after filtering deleted methods")

        return CsvLoadResult(
            df=df,
            original_count=original_count,
            deleted_count=deleted_count,
            filtered_count=len(df),
        )
