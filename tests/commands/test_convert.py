"""Tests for convert command."""

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest
from click.testing import CliRunner

from b4_thesis.cli import main


class TestConvertMethods:
    """Test suite for convert methods command."""

    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()

    @pytest.fixture
    def sample_tracking_csv(self, tmp_path):
        """Create a sample method_tracking.csv for testing."""
        # Create sample tracking data with matched_block_id relationships
        data = {
            "revision": [
                "20250101_100000_hash1",
                "20250101_100000_hash1",
                "20250101_110000_hash2",
                "20250101_110000_hash2",
                "20250101_120000_hash3",
            ],
            "block_id": ["block_a", "block_b", "block_a2", "block_c", "block_a3"],
            "matched_block_id": [None, None, "block_a", None, "block_a2"],
            "function_name": ["func_a", "func_b", "func_a", "func_c", "func_a"],
            "file_path": ["file1.py", "file2.py", "file1.py", "file3.py", "file1.py"],
            "start_line": [1, 10, 1, 20, 1],
            "end_line": [5, 15, 6, 25, 7],
            "loc": [5, 6, 6, 6, 7],
            "state": ["added", "added", "survived", "added", "survived"],
            "state_detail": [
                "clone_to_non_clone",
                "non_clone",
                "remained_non_clone",
                "non_clone",
                "remained_non_clone",
            ],
            "match_type": ["none", "none", "exact", "none", "exact"],
            "match_similarity": [None, None, 100.0, None, 100.0],
            "clone_count": [0, 0, 0, 0, 0],
            "clone_group_id": [None, None, None, None, None],
            "clone_group_size": [1, 1, 1, 1, 1],
            "lifetime_revisions": [1, 1, 2, 1, 3],
            "lifetime_days": [0, 0, 1, 0, 2],
        }
        df = pd.DataFrame(data)

        # Save to CSV
        csv_file = tmp_path / "method_tracking.csv"
        df.to_csv(csv_file, index=False)
        return csv_file

    def test_convert_methods_lineage(self, runner, sample_tracking_csv, tmp_path):
        """Test convert methods command with --lineage flag."""
        output_file = tmp_path / "method_lineage.csv"

        result = runner.invoke(
            main,
            [
                "convert",
                "methods",
                str(sample_tracking_csv),
                "--lineage",
                "-o",
                str(output_file),
            ],
        )

        assert result.exit_code == 0
        assert output_file.exists()

        # Verify output format
        df = pd.read_csv(output_file)

        # Should have 16 columns
        assert len(df.columns) == 16

        # Should have global_block_id
        assert "global_block_id" in df.columns

        # Should NOT have block_id or matched_block_id
        assert "block_id" not in df.columns
        assert "matched_block_id" not in df.columns

        # Should have correct number of rows
        assert len(df) == 5

    def test_convert_methods_global_block_id_consistency(
        self, runner, sample_tracking_csv, tmp_path
    ):
        """Test that same lineage has same global_block_id."""
        output_file = tmp_path / "method_lineage.csv"

        result = runner.invoke(
            main,
            [
                "convert",
                "methods",
                str(sample_tracking_csv),
                "--lineage",
                "-o",
                str(output_file),
            ],
        )

        assert result.exit_code == 0

        df = pd.read_csv(output_file)

        # func_a appears in 3 revisions (block_a -> block_a2 -> block_a3)
        # All should have same global_block_id
        func_a_rows = df[df["function_name"] == "func_a"]
        assert len(func_a_rows) == 3

        # Check all have same global_block_id
        global_ids = func_a_rows["global_block_id"].unique()
        assert len(global_ids) == 1, "All blocks in same lineage should have same global_block_id"

        # The global_block_id should be the earliest block_id
        assert global_ids[0] == "block_a"

    def test_convert_methods_different_lineages(self, runner, sample_tracking_csv, tmp_path):
        """Test that different lineages have different global_block_id."""
        output_file = tmp_path / "method_lineage.csv"

        result = runner.invoke(
            main,
            [
                "convert",
                "methods",
                str(sample_tracking_csv),
                "--lineage",
                "-o",
                str(output_file),
            ],
        )

        assert result.exit_code == 0

        df = pd.read_csv(output_file)

        # func_a and func_b are different lineages
        func_a_global_id = df[df["function_name"] == "func_a"].iloc[0]["global_block_id"]
        func_b_global_id = df[df["function_name"] == "func_b"].iloc[0]["global_block_id"]

        assert func_a_global_id != func_b_global_id

    def test_convert_methods_column_order(self, runner, sample_tracking_csv, tmp_path):
        """Test that columns are in correct order."""
        output_file = tmp_path / "method_lineage.csv"

        result = runner.invoke(
            main,
            [
                "convert",
                "methods",
                str(sample_tracking_csv),
                "--lineage",
                "-o",
                str(output_file),
            ],
        )

        assert result.exit_code == 0

        df = pd.read_csv(output_file)

        expected_columns = [
            "global_block_id",
            "revision",
            "function_name",
            "file_path",
            "start_line",
            "end_line",
            "loc",
            "state",
            "state_detail",
            "match_type",
            "match_similarity",
            "clone_count",
            "clone_group_id",
            "clone_group_size",
            "lifetime_revisions",
            "lifetime_days",
        ]

        assert list(df.columns) == expected_columns

    def test_convert_methods_without_lineage_flag(self, runner, sample_tracking_csv, tmp_path):
        """Test that command requires --lineage flag."""
        output_file = tmp_path / "method_lineage.csv"

        result = runner.invoke(
            main, ["convert", "methods", str(sample_tracking_csv), "-o", str(output_file)]
        )

        # Should fail without --lineage flag
        assert result.exit_code != 0
        assert "No conversion option specified" in result.output

    def test_convert_methods_missing_input_file(self, runner, tmp_path):
        """Test error handling for missing input file."""
        output_file = tmp_path / "method_lineage.csv"

        result = runner.invoke(
            main,
            [
                "convert",
                "methods",
                "nonexistent_file.csv",
                "--lineage",
                "-o",
                str(output_file),
            ],
        )

        assert result.exit_code != 0

    def test_convert_methods_invalid_csv_format(self, runner, tmp_path):
        """Test error handling for invalid CSV format."""
        # Create invalid CSV (missing required columns)
        invalid_csv = tmp_path / "invalid.csv"
        pd.DataFrame({"col1": [1, 2], "col2": [3, 4]}).to_csv(invalid_csv, index=False)

        output_file = tmp_path / "method_lineage.csv"

        result = runner.invoke(
            main,
            ["convert", "methods", str(invalid_csv), "--lineage", "-o", str(output_file)],
        )

        assert result.exit_code != 0
        assert "Missing required columns" in result.output

    def test_convert_methods_default_output(self, runner, sample_tracking_csv, tmp_path):
        """Test that default output filename is method_lineage.csv."""
        # Run from temp directory
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                main, ["convert", "methods", str(sample_tracking_csv), "--lineage"]
            )

            assert result.exit_code == 0
            assert Path("method_lineage.csv").exists()

    def test_convert_methods_preserves_data_integrity(
        self, runner, sample_tracking_csv, tmp_path
    ):
        """Test that conversion preserves all data from original tracking."""
        output_file = tmp_path / "method_lineage.csv"

        # Read original tracking data
        tracking_df = pd.read_csv(sample_tracking_csv)

        # Convert to lineage format
        result = runner.invoke(
            main,
            [
                "convert",
                "methods",
                str(sample_tracking_csv),
                "--lineage",
                "-o",
                str(output_file),
            ],
        )

        assert result.exit_code == 0

        lineage_df = pd.read_csv(output_file)

        # Should have same number of rows
        assert len(lineage_df) == len(tracking_df)

        # Check that function names are preserved
        assert set(lineage_df["function_name"]) == set(tracking_df["function_name"])

        # Check that states are preserved
        assert set(lineage_df["state"]) == set(tracking_df["state"])
