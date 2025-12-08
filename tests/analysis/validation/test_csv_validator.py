"""Tests for CsvValidator."""

from pathlib import Path

import pandas as pd
import pytest

from b4_thesis.analysis.validation.csv_validator import (
    CsvValidator,
    DeletionPredictionColumns,
)


class TestCsvValidator:
    """Tests for CsvValidator class."""

    def test_validate_file_exists_success(self, tmp_path):
        """Test successful file existence validation."""
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("col1,col2\n1,2\n")

        # Should not raise
        CsvValidator.validate_file_exists(csv_path)

    def test_validate_file_exists_not_found(self, tmp_path):
        """Test FileNotFoundError when file doesn't exist."""
        csv_path = tmp_path / "nonexistent.csv"

        with pytest.raises(FileNotFoundError, match="CSV file not found"):
            CsvValidator.validate_file_exists(csv_path)

    def test_load_csv_success(self, tmp_path):
        """Test successful CSV loading."""
        csv_path = tmp_path / "test.csv"
        test_data = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        test_data.to_csv(csv_path, index=False)

        df = CsvValidator.load_csv(csv_path)

        assert len(df) == 2
        assert list(df.columns) == ["col1", "col2"]

    def test_load_csv_file_not_found(self, tmp_path):
        """Test FileNotFoundError when loading non-existent file."""
        csv_path = tmp_path / "nonexistent.csv"

        with pytest.raises(FileNotFoundError):
            CsvValidator.load_csv(csv_path)

    def test_validate_required_columns_success(self):
        """Test successful column validation."""
        df = pd.DataFrame({"col1": [1], "col2": [2], "col3": [3]})
        required = {"col1", "col2"}

        # Should not raise
        CsvValidator.validate_required_columns(df, required)

    def test_validate_required_columns_missing(self):
        """Test ValueError when required columns are missing."""
        df = pd.DataFrame({"col1": [1], "col2": [2]})
        required = {"col1", "col2", "col3", "col4"}

        with pytest.raises(ValueError, match="missing required columns"):
            CsvValidator.validate_required_columns(df, required)

    def test_validate_required_columns_with_context(self):
        """Test that context appears in error message."""
        df = pd.DataFrame({"col1": [1]})
        required = {"col1", "col2"}

        with pytest.raises(ValueError, match="features CSV missing required columns"):
            CsvValidator.validate_required_columns(df, required, "features CSV")

    def test_validate_non_empty_success(self):
        """Test successful non-empty validation."""
        df = pd.DataFrame({"col1": [1, 2]})

        # Should not raise
        CsvValidator.validate_non_empty(df)

    def test_validate_non_empty_failure(self):
        """Test ValueError when DataFrame is empty."""
        df = pd.DataFrame({"col1": []})

        with pytest.raises(ValueError, match="is empty"):
            CsvValidator.validate_non_empty(df)

    def test_validate_non_empty_with_context(self):
        """Test that context appears in error message."""
        df = pd.DataFrame()

        with pytest.raises(ValueError, match="test data is empty"):
            CsvValidator.validate_non_empty(df, "test data")

    def test_load_and_validate_success(self, tmp_path):
        """Test successful load and validate."""
        csv_path = tmp_path / "test.csv"
        test_data = pd.DataFrame({"col1": [1, 2], "col2": [3, 4], "col3": [5, 6]})
        test_data.to_csv(csv_path, index=False)

        required = {"col1", "col2"}
        df = CsvValidator.load_and_validate(csv_path, required)

        assert len(df) == 2
        assert "col1" in df.columns
        assert "col2" in df.columns

    def test_load_and_validate_missing_columns(self, tmp_path):
        """Test ValueError when required columns are missing."""
        csv_path = tmp_path / "test.csv"
        test_data = pd.DataFrame({"col1": [1, 2]})
        test_data.to_csv(csv_path, index=False)

        required = {"col1", "col2", "col3"}

        with pytest.raises(ValueError, match="missing required columns"):
            CsvValidator.load_and_validate(csv_path, required)

    def test_load_and_validate_empty_dataframe(self, tmp_path):
        """Test ValueError when DataFrame is empty (default behavior)."""
        csv_path = tmp_path / "empty.csv"
        test_data = pd.DataFrame({"col1": [], "col2": []})
        test_data.to_csv(csv_path, index=False)

        required = {"col1", "col2"}

        with pytest.raises(ValueError, match="is empty"):
            CsvValidator.load_and_validate(csv_path, required)

    def test_load_and_validate_allow_empty(self, tmp_path):
        """Test that allow_empty=True permits empty DataFrames."""
        csv_path = tmp_path / "empty.csv"
        test_data = pd.DataFrame({"col1": [], "col2": []})
        test_data.to_csv(csv_path, index=False)

        required = {"col1", "col2"}
        df = CsvValidator.load_and_validate(csv_path, required, allow_empty=True)

        assert len(df) == 0
        assert list(df.columns) == ["col1", "col2"]

    def test_load_and_validate_custom_context(self, tmp_path):
        """Test custom context in error messages."""
        csv_path = tmp_path / "test.csv"
        test_data = pd.DataFrame({"col1": []})
        test_data.to_csv(csv_path, index=False)

        required = {"col1", "col2"}

        with pytest.raises(ValueError, match="my custom CSV missing required columns"):
            CsvValidator.load_and_validate(csv_path, required, context="my custom CSV")

    def test_load_and_validate_default_context(self, tmp_path):
        """Test that default context uses filename."""
        csv_path = tmp_path / "features.csv"
        test_data = pd.DataFrame({"col1": []})
        test_data.to_csv(csv_path, index=False)

        required = {"col1", "col2"}

        with pytest.raises(ValueError, match="features.csv missing required columns"):
            CsvValidator.load_and_validate(csv_path, required)


class TestDeletionPredictionColumns:
    """Tests for DeletionPredictionColumns constants."""

    def test_basic_columns(self):
        """Test BASIC column set."""
        expected = {
            "global_block_id",
            "revision",
            "function_name",
            "file_path",
            "start_line",
            "end_line",
            "loc",
            "state",
        }
        assert DeletionPredictionColumns.BASIC == expected

    def test_label_generation_columns(self):
        """Test LABEL_GENERATION column set."""
        expected = {"global_block_id", "revision", "state"}
        assert DeletionPredictionColumns.LABEL_GENERATION == expected

    def test_evaluation_basic_columns(self):
        """Test EVALUATION_BASIC column set."""
        expected = {"is_deleted_soon"}
        assert DeletionPredictionColumns.EVALUATION_BASIC == expected

    def test_evaluation_detailed_columns(self):
        """Test EVALUATION_DETAILED column set."""
        expected = {
            "global_block_id",
            "revision",
            "function_name",
            "file_path",
            "lifetime_revisions",
            "lifetime_days",
        }
        assert DeletionPredictionColumns.EVALUATION_DETAILED == expected

    def test_get_evaluation_columns_basic(self):
        """Test get_evaluation_columns with detailed=False."""
        cols = DeletionPredictionColumns.get_evaluation_columns(detailed=False)
        assert cols == {"is_deleted_soon"}

    def test_get_evaluation_columns_detailed(self):
        """Test get_evaluation_columns with detailed=True."""
        cols = DeletionPredictionColumns.get_evaluation_columns(detailed=True)
        expected = {
            "is_deleted_soon",
            "global_block_id",
            "revision",
            "function_name",
            "file_path",
            "lifetime_revisions",
            "lifetime_days",
        }
        assert cols == expected
