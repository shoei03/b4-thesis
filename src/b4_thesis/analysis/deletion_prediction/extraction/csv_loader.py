"""CSV data loader for deletion prediction feature extraction."""

from pathlib import Path

import pandas as pd

from b4_thesis.analysis.deletion_prediction.extraction.result_types import CsvLoadResult
from b4_thesis.analysis.validation import CsvValidator, DeletionPredictionColumns


class CsvDataLoader:
    """Load and validate method lineage CSV data.

    This component handles:
    - Loading CSV file
    - Validating required columns
    - Filtering deleted methods (code doesn't exist for them)
    """

    REQUIRED_COLUMNS = DeletionPredictionColumns.BASIC

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
        # Load and validate CSV using CsvValidator
        df = CsvValidator.load_and_validate(
            csv_path,
            self.REQUIRED_COLUMNS,
            allow_empty=True,  # We'll validate after filtering
            context="method_lineage CSV",
        )

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
