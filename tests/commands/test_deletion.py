"""Tests for deletion command."""

from click.testing import CliRunner
import pandas as pd
import pytest

from b4_thesis.cli import main
from b4_thesis.commands.predict import _create_composite_group_column


class TestCreateCompositeGroupColumn:
    """Test suite for _create_composite_group_column helper function."""

    @pytest.fixture
    def sample_df(self):
        """Create a sample DataFrame with rev_status and state columns."""
        return pd.DataFrame(
            {
                "rule_test": [True, False, True, False, True, False, True, False],
                "is_deleted_soon": [True, False, True, False, True, False, True, False],
                "rev_status": [
                    "no_deleted",
                    "no_deleted",
                    "all_deleted",
                    "all_deleted",
                    "partial_deleted",
                    "partial_deleted",
                    "partial_deleted",
                    "partial_deleted",
                ],
                "state": [
                    "survived",
                    "added",
                    "deleted",
                    "deleted",
                    "deleted",
                    "survived",
                    "added",
                    None,  # NaN value
                ],
                "global_block_id": ["gb1", "gb2", "gb3", "gb4", "gb5", "gb6", "gb7", "gb8"],
                "revision": ["r1"] * 8,
                "function_name": ["f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8"],
                "file_path": ["a.py"] * 8,
                "lifetime_revisions": [1] * 8,
                "lifetime_days": [1] * 8,
            }
        )

    def test_basic_composite_column_creation(self, sample_df):
        """Test basic composite column creation."""
        result_df, col_name = _create_composite_group_column(
            sample_df, group_by="rev_status", split_partial_by="state"
        )

        # Verify column name
        assert col_name == "_composite_rev_status_state"
        assert col_name in result_df.columns

        # Verify no_deleted rows remain unchanged
        assert result_df.loc[0, col_name] == "no_deleted"
        assert result_df.loc[1, col_name] == "no_deleted"

        # Verify all_deleted rows remain unchanged
        assert result_df.loc[2, col_name] == "all_deleted"
        assert result_df.loc[3, col_name] == "all_deleted"

        # Verify partial_deleted subdivision
        assert result_df.loc[4, col_name] == "partial_deleted_deleted"  # state=deleted
        assert result_df.loc[5, col_name] == "partial_deleted_survived"  # state=survived
        assert (
            result_df.loc[6, col_name] == "partial_deleted_survived"
        )  # state=added (treated as survived)
        assert result_df.loc[7, col_name] == "partial_deleted_other"  # state=NaN

    def test_correct_subdivision_of_partial_deleted(self, sample_df):
        """Test that partial_deleted is correctly split by state."""
        result_df, col_name = _create_composite_group_column(
            sample_df, group_by="rev_status", split_partial_by="state"
        )

        # Count composite groups
        value_counts = result_df[col_name].value_counts()

        assert "partial_deleted_deleted" in value_counts.index
        assert "partial_deleted_survived" in value_counts.index
        assert value_counts["partial_deleted_deleted"] == 1  # One deleted
        assert value_counts["partial_deleted_survived"] == 2  # One survived + one added

    def test_added_treated_as_survived(self, sample_df):
        """Test that state=added is treated the same as state=survived."""
        result_df, col_name = _create_composite_group_column(
            sample_df, group_by="rev_status", split_partial_by="state"
        )

        # Row 6 has state=added, should be partial_deleted_survived
        assert result_df.loc[6, col_name] == "partial_deleted_survived"

    def test_missing_group_by_column(self, sample_df):
        """Test error when group_by column doesn't exist."""
        with pytest.raises(ValueError, match="Group-by column 'nonexistent' not found"):
            _create_composite_group_column(
                sample_df, group_by="nonexistent", split_partial_by="state"
            )

    def test_missing_split_column(self, sample_df):
        """Test error when split column doesn't exist."""
        with pytest.raises(ValueError, match="Split column 'nonexistent' not found"):
            _create_composite_group_column(
                sample_df, group_by="rev_status", split_partial_by="nonexistent"
            )

    def test_nan_values_in_split_column(self, sample_df):
        """Test handling of NaN values in split column."""
        result_df, col_name = _create_composite_group_column(
            sample_df, group_by="rev_status", split_partial_by="state"
        )

        # Row 7 has state=NaN, should be partial_deleted_other
        assert result_df.loc[7, col_name] == "partial_deleted_other"

    def test_no_partial_deleted_rows(self):
        """Test behavior when there are no partial_deleted rows."""
        df = pd.DataFrame(
            {
                "rev_status": ["no_deleted", "all_deleted", "no_deleted"],
                "state": ["survived", "deleted", "added"],
                "rule_test": [True, False, True],
                "is_deleted_soon": [False, True, False],
                "global_block_id": ["gb1", "gb2", "gb3"],
                "revision": ["r1"] * 3,
                "function_name": ["f1", "f2", "f3"],
                "file_path": ["a.py"] * 3,
                "lifetime_revisions": [1] * 3,
                "lifetime_days": [1] * 3,
            }
        )

        result_df, col_name = _create_composite_group_column(
            df, group_by="rev_status", split_partial_by="state"
        )

        # Should not have any partial_deleted groups
        assert "partial_deleted_deleted" not in result_df[col_name].values
        assert "partial_deleted_survived" not in result_df[col_name].values

        # Should have unchanged values
        assert "no_deleted" in result_df[col_name].values
        assert "all_deleted" in result_df[col_name].values

    def test_all_partial_deleted_rows(self):
        """Test behavior when all rows are partial_deleted."""
        df = pd.DataFrame(
            {
                "rev_status": ["partial_deleted"] * 4,
                "state": ["deleted", "survived", "added", "deleted"],
                "rule_test": [True, False, True, False],
                "is_deleted_soon": [True, False, False, True],
                "global_block_id": ["gb1", "gb2", "gb3", "gb4"],
                "revision": ["r1"] * 4,
                "function_name": ["f1", "f2", "f3", "f4"],
                "file_path": ["a.py"] * 4,
                "lifetime_revisions": [1] * 4,
                "lifetime_days": [1] * 4,
            }
        )

        result_df, col_name = _create_composite_group_column(
            df, group_by="rev_status", split_partial_by="state"
        )

        # Count groups
        value_counts = result_df[col_name].value_counts()

        # Should only have partial_deleted groups
        assert "partial_deleted_deleted" in value_counts.index
        assert "partial_deleted_survived" in value_counts.index
        assert "no_deleted" not in value_counts.index
        assert "all_deleted" not in value_counts.index

        # Check counts
        assert value_counts["partial_deleted_deleted"] == 2  # Two deleted
        assert value_counts["partial_deleted_survived"] == 2  # One survived + one added

    def test_dataframe_copy(self, sample_df):
        """Test that the function creates a copy and doesn't modify the original."""
        original_columns = set(sample_df.columns)

        result_df, col_name = _create_composite_group_column(
            sample_df, group_by="rev_status", split_partial_by="state"
        )

        # Original should be unchanged
        assert set(sample_df.columns) == original_columns
        assert col_name not in sample_df.columns

        # Result should have the new column
        assert col_name in result_df.columns


class TestDeletionEvaluateComposite:
    """Integration tests for composite grouping in deletion evaluate command."""

    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()

    @pytest.fixture
    def sample_features_csv(self, tmp_path):
        """Create a sample features CSV with rev_status and state columns."""
        data = {
            "rule_test": [True, True, False, False, True, False, True, False, True, False],
            "is_deleted_soon": [
                True,
                False,
                True,
                False,
                True,
                False,
                True,
                False,
                True,
                False,
            ],
            "rev_status": [
                "no_deleted",
                "no_deleted",
                "all_deleted",
                "all_deleted",
                "partial_deleted",
                "partial_deleted",
                "partial_deleted",
                "partial_deleted",
                "partial_deleted",
                "partial_deleted",
            ],
            "state": [
                "survived",
                "added",
                "deleted",
                "deleted",
                "deleted",
                "deleted",
                "survived",
                "survived",
                "added",
                "added",
            ],
            "global_block_id": [f"gb{i}" for i in range(10)],
            "revision": ["r1"] * 10,
            "function_name": [f"f{i}" for i in range(10)],
            "file_path": ["a.py"] * 10,
            "lifetime_revisions": [1] * 10,
            "lifetime_days": [1] * 10,
        }
        df = pd.DataFrame(data)

        csv_file = tmp_path / "features.csv"
        df.to_csv(csv_file, index=False)
        return csv_file

    def test_basic_composite_grouping(self, runner, sample_features_csv, tmp_path):
        """Test basic composite grouping with --split-partial-by."""
        output_file = tmp_path / "composite_report.json"

        result = runner.invoke(
            main,
            [
                "deletion",
                "evaluate",
                str(sample_features_csv),
                "--output",
                str(output_file),
                "--format",
                "json",
                "--group-by",
                "rev_status",
                "--split-partial-by",
                "state",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert output_file.exists()

        # Verify output contains composite groups
        import json

        with open(output_file) as f:
            results = json.load(f)

        # Should have one result for the test rule
        assert len(results) > 0
        result_data = results[0]

        # Check that composite groups are present
        groups = result_data["groups"]
        assert "no_deleted" in groups
        assert "all_deleted" in groups
        assert "partial_deleted_deleted" in groups
        assert "partial_deleted_survived" in groups

    def test_split_without_group_by_warning(self, runner, sample_features_csv, tmp_path):
        """Test warning when using --split-partial-by without --group-by."""
        output_file = tmp_path / "report.json"

        result = runner.invoke(
            main,
            [
                "deletion",
                "evaluate",
                str(sample_features_csv),
                "--output",
                str(output_file),
                "--format",
                "json",
                "--split-partial-by",
                "state",
            ],
        )

        # Should still succeed but with a warning
        assert result.exit_code == 0
        assert "Warning" in result.output
        assert "--split-partial-by requires --group-by" in result.output

    def test_split_with_wrong_group_by_warning(self, runner, sample_features_csv, tmp_path):
        """Test warning when using --split-partial-by with wrong --group-by value."""
        output_file = tmp_path / "report.json"

        result = runner.invoke(
            main,
            [
                "deletion",
                "evaluate",
                str(sample_features_csv),
                "--output",
                str(output_file),
                "--format",
                "json",
                "--group-by",
                "state",  # Wrong column
                "--split-partial-by",
                "rev_status",
            ],
        )

        # Should still succeed but with a warning
        assert result.exit_code == 0
        assert "Warning" in result.output
        assert "only supports --group-by rev_status" in result.output

    def test_json_output_format_with_composite_groups(self, runner, sample_features_csv, tmp_path):
        """Test JSON output format displays composite group names correctly."""
        output_file = tmp_path / "composite_report.json"

        result = runner.invoke(
            main,
            [
                "deletion",
                "evaluate",
                str(sample_features_csv),
                "--output",
                str(output_file),
                "--format",
                "json",
                "--group-by",
                "rev_status",
                "--split-partial-by",
                "state",
            ],
        )

        assert result.exit_code == 0
        assert output_file.exists()

        import json

        with open(output_file) as f:
            results = json.load(f)

        # Verify structure
        assert isinstance(results, list)
        assert len(results) > 0

        for result_data in results:
            assert "rule_name" in result_data
            assert "group_by_column" in result_data
            assert "groups" in result_data
            assert result_data["group_by_column"] == "_composite_rev_status_state"

    def test_csv_output_format_with_composite_groups(self, runner, sample_features_csv, tmp_path):
        """Test CSV output format contains composite group names."""
        output_file = tmp_path / "composite_metrics.csv"

        result = runner.invoke(
            main,
            [
                "deletion",
                "evaluate",
                str(sample_features_csv),
                "--output",
                str(output_file),
                "--format",
                "csv",
                "--group-by",
                "rev_status",
                "--split-partial-by",
                "state",
            ],
        )

        assert result.exit_code == 0
        assert output_file.exists()

        # Read CSV and verify composite group names
        import pandas as pd

        df = pd.read_csv(output_file)

        assert "group_value" in df.columns
        group_values = df["group_value"].unique()

        # Should contain composite group names
        assert any("partial_deleted_deleted" in str(gv) for gv in group_values)
        assert any("partial_deleted_survived" in str(gv) for gv in group_values)

    def test_table_output_with_composite_groups(self, runner, sample_features_csv, tmp_path):
        """Test table output displays composite group names."""
        output_file = tmp_path / "composite_report.json"

        result = runner.invoke(
            main,
            [
                "deletion",
                "evaluate",
                str(sample_features_csv),
                "--output",
                str(output_file),
                "--format",
                "table",
                "--group-by",
                "rev_status",
                "--split-partial-by",
                "state",
            ],
        )

        assert result.exit_code == 0
        assert "partial_deleted_deleted" in result.output
        assert "partial_deleted_survived" in result.output
