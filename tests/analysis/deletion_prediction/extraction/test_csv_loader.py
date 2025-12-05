"""Tests for CsvDataLoader."""

from pathlib import Path

import pandas as pd
import pytest

from b4_thesis.analysis.deletion_prediction.extraction import CsvDataLoader, CsvLoadResult


class TestCsvDataLoader:
    """Tests for CsvDataLoader class."""

    @pytest.fixture
    def csv_loader(self):
        """Create CsvDataLoader instance."""
        return CsvDataLoader()

    @pytest.fixture
    def valid_csv_data(self):
        """Create valid CSV data."""
        return pd.DataFrame(
            {
                "global_block_id": ["block1", "block2", "block3", "block4"],
                "revision": ["rev1", "rev1", "rev2", "rev2"],
                "function_name": ["foo", "bar", "foo", "baz"],
                "file_path": ["a.py", "b.py", "a.py", "c.py"],
                "start_line": [1, 10, 1, 20],
                "end_line": [5, 15, 6, 25],
                "loc": [4, 5, 5, 5],
                "state": ["added", "modified", "survived", "deleted"],
            }
        )

    @pytest.fixture
    def tmp_csv(self, tmp_path, valid_csv_data):
        """Create temporary CSV file."""
        csv_path = tmp_path / "test.csv"
        valid_csv_data.to_csv(csv_path, index=False)
        return csv_path

    def test_load_and_validate_success(self, csv_loader, tmp_csv):
        """Test successful CSV loading and validation."""
        result = csv_loader.load_and_validate(tmp_csv)

        assert isinstance(result, CsvLoadResult)
        assert result.original_count == 4
        assert result.deleted_count == 1
        assert result.filtered_count == 3
        assert len(result.df) == 3
        assert "deleted" not in result.df["state"].values

    def test_load_file_not_found(self, csv_loader, tmp_path):
        """Test FileNotFoundError when CSV file doesn't exist."""
        non_existent_path = tmp_path / "non_existent.csv"

        with pytest.raises(FileNotFoundError, match="CSV file not found"):
            csv_loader.load_and_validate(non_existent_path)

    def test_load_missing_required_columns(self, csv_loader, tmp_path):
        """Test ValueError when required columns are missing."""
        # Create CSV missing 'loc' column
        incomplete_data = pd.DataFrame(
            {
                "global_block_id": ["block1"],
                "revision": ["rev1"],
                "function_name": ["foo"],
                "file_path": ["a.py"],
                "start_line": [1],
                "end_line": [5],
                # Missing 'loc' and 'state'
            }
        )
        csv_path = tmp_path / "incomplete.csv"
        incomplete_data.to_csv(csv_path, index=False)

        with pytest.raises(ValueError, match="CSV missing required columns"):
            csv_loader.load_and_validate(csv_path)

    def test_filter_deleted_methods(self, csv_loader, tmp_csv):
        """Test that deleted methods are filtered out."""
        result = csv_loader.load_and_validate(tmp_csv)

        # Original has 4 methods, 1 deleted
        assert result.original_count == 4
        assert result.deleted_count == 1
        assert result.filtered_count == 3

        # Verify deleted method is not in result
        assert "deleted" not in result.df["state"].values
        assert "baz" not in result.df["function_name"].values

    def test_all_deleted_scenario(self, csv_loader, tmp_path):
        """Test ValueError when all methods are deleted."""
        all_deleted_data = pd.DataFrame(
            {
                "global_block_id": ["block1", "block2"],
                "revision": ["rev1", "rev1"],
                "function_name": ["foo", "bar"],
                "file_path": ["a.py", "b.py"],
                "start_line": [1, 10],
                "end_line": [5, 15],
                "loc": [4, 5],
                "state": ["deleted", "deleted"],
            }
        )
        csv_path = tmp_path / "all_deleted.csv"
        all_deleted_data.to_csv(csv_path, index=False)

        with pytest.raises(ValueError, match="No methods to process after filtering"):
            csv_loader.load_and_validate(csv_path)

    def test_no_deleted_scenario(self, csv_loader, tmp_path):
        """Test when there are no deleted methods."""
        no_deleted_data = pd.DataFrame(
            {
                "global_block_id": ["block1", "block2", "block3"],
                "revision": ["rev1", "rev1", "rev2"],
                "function_name": ["foo", "bar", "foo"],
                "file_path": ["a.py", "b.py", "a.py"],
                "start_line": [1, 10, 1],
                "end_line": [5, 15, 6],
                "loc": [4, 5, 5],
                "state": ["added", "modified", "survived"],
            }
        )
        csv_path = tmp_path / "no_deleted.csv"
        no_deleted_data.to_csv(csv_path, index=False)

        result = csv_loader.load_and_validate(csv_path)

        assert result.original_count == 3
        assert result.deleted_count == 0
        assert result.filtered_count == 3
        assert len(result.df) == 3

    def test_empty_csv(self, csv_loader, tmp_path):
        """Test ValueError when CSV is empty."""
        empty_data = pd.DataFrame(
            {
                "global_block_id": [],
                "revision": [],
                "function_name": [],
                "file_path": [],
                "start_line": [],
                "end_line": [],
                "loc": [],
                "state": [],
            }
        )
        csv_path = tmp_path / "empty.csv"
        empty_data.to_csv(csv_path, index=False)

        with pytest.raises(ValueError, match="No methods to process after filtering"):
            csv_loader.load_and_validate(csv_path)

    def test_required_columns_constant(self):
        """Test that REQUIRED_COLUMNS contains expected columns."""
        expected_columns = {
            "global_block_id",
            "revision",
            "function_name",
            "file_path",
            "start_line",
            "end_line",
            "loc",
            "state",
        }
        assert CsvDataLoader.REQUIRED_COLUMNS == expected_columns

    def test_result_dataframe_is_copy(self, csv_loader, tmp_csv):
        """Test that returned DataFrame is a copy, not a view."""
        result = csv_loader.load_and_validate(tmp_csv)

        # Modify result DataFrame
        result.df.loc[0, "function_name"] = "modified"

        # Load again and verify original data is unchanged
        result2 = csv_loader.load_and_validate(tmp_csv)
        assert result2.df.loc[0, "function_name"] != "modified"
