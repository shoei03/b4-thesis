"""Tests for label command."""

from click.testing import CliRunner
import pandas as pd
import pytest

from b4_thesis.cli import main


class TestLabelRevisions:
    """Test suite for label revisions command."""

    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()

    @pytest.fixture
    def sample_lineage_csv(self, tmp_path):
        """Create a sample method_lineage.csv for testing."""
        data = {
            "global_block_id": ["gb1", "gb2", "gb3", "gb4", "gb5", "gb6", "gb7"],
            "clone_group_id": ["g1", "g1", "g1", "g2", "g2", "g3", "g3"],
            "revision": ["r1", "r1", "r1", "r1", "r1", "r2", "r2"],
            "state": [
                "survived",
                "survived",
                "deleted",  # g1@r1: partial_deleted
                "deleted",
                "deleted",  # g2@r1: all_deleted
                "survived",
                "added",  # g3@r2: no_deleted
            ],
            "function_name": ["f1", "f2", "f3", "f4", "f5", "f6", "f7"],
            "file_path": ["a.py", "b.py", "c.py", "d.py", "e.py", "f.py", "g.py"],
            "start_line": [1, 10, 20, 30, 40, 50, 60],
            "end_line": [5, 15, 25, 35, 45, 55, 65],
        }
        df = pd.DataFrame(data)

        csv_file = tmp_path / "method_lineage.csv"
        df.to_csv(csv_file, index=False)
        return csv_file

    def test_label_revisions_basic(self, runner, sample_lineage_csv, tmp_path):
        """Test label revisions command with basic options."""
        output_file = tmp_path / "labeled.csv"

        result = runner.invoke(
            main,
            [
                "label",
                "revisions",
                str(sample_lineage_csv),
                "-o",
                str(output_file),
            ],
        )

        assert result.exit_code == 0
        assert output_file.exists()

        # Verify output format
        df = pd.read_csv(output_file)
        assert "rev_status" in df.columns
        assert len(df) == 7

    def test_label_revisions_correct_labels(self, runner, sample_lineage_csv, tmp_path):
        """Test that correct labels are assigned."""
        output_file = tmp_path / "labeled.csv"

        result = runner.invoke(
            main,
            [
                "label",
                "revisions",
                str(sample_lineage_csv),
                "-o",
                str(output_file),
            ],
        )

        assert result.exit_code == 0

        df = pd.read_csv(output_file)

        # g1@r1: partial_deleted
        g1_r1 = df[(df["clone_group_id"] == "g1") & (df["revision"] == "r1")]
        assert (g1_r1["rev_status"] == "partial_deleted").all()

        # g2@r1: all_deleted
        g2_r1 = df[(df["clone_group_id"] == "g2") & (df["revision"] == "r1")]
        assert (g2_r1["rev_status"] == "all_deleted").all()

        # g3@r2: no_deleted
        g3_r2 = df[(df["clone_group_id"] == "g3") & (df["revision"] == "r2")]
        assert (g3_r2["rev_status"] == "no_deleted").all()

    def test_label_revisions_default_output(self, runner, sample_lineage_csv):
        """Test default output path."""
        result = runner.invoke(
            main,
            [
                "label",
                "revisions",
                str(sample_lineage_csv),
            ],
        )

        assert result.exit_code == 0

        # Check default output path
        expected_output = sample_lineage_csv.parent / "method_lineage_labeled.csv"
        assert expected_output.exists()

    def test_label_revisions_with_summary(self, runner, sample_lineage_csv, tmp_path):
        """Test label revisions command with --summary option."""
        output_file = tmp_path / "labeled.csv"

        result = runner.invoke(
            main,
            [
                "label",
                "revisions",
                str(sample_lineage_csv),
                "-o",
                str(output_file),
                "--summary",
            ],
        )

        assert result.exit_code == 0
        # Summary should be in output
        assert "Clone Group Status by Revision" in result.output or "total" in result.output.lower()

    def test_label_revisions_with_verbose(self, runner, sample_lineage_csv, tmp_path):
        """Test label revisions command with --verbose option."""
        output_file = tmp_path / "labeled.csv"

        result = runner.invoke(
            main,
            [
                "label",
                "revisions",
                str(sample_lineage_csv),
                "-o",
                str(output_file),
                "-v",
            ],
        )

        assert result.exit_code == 0
        # Should show more details
        assert "Total records" in result.output

    def test_label_revisions_missing_columns(self, runner, tmp_path):
        """Test error handling for missing required columns."""
        # Create CSV without 'state' column
        data = {
            "clone_group_id": ["g1"],
            "revision": ["r1"],
            "function_name": ["f1"],
        }
        df = pd.DataFrame(data)
        csv_file = tmp_path / "invalid.csv"
        df.to_csv(csv_file, index=False)

        result = runner.invoke(
            main,
            [
                "label",
                "revisions",
                str(csv_file),
            ],
        )

        assert result.exit_code != 0
        assert "Missing required columns" in result.output or "Error" in result.output

    def test_label_revisions_nonexistent_file(self, runner, tmp_path):
        """Test error handling for nonexistent file."""
        result = runner.invoke(
            main,
            [
                "label",
                "revisions",
                str(tmp_path / "nonexistent.csv"),
            ],
        )

        assert result.exit_code != 0

    def test_label_revisions_preserves_columns(self, runner, sample_lineage_csv, tmp_path):
        """Test that all original columns are preserved."""
        output_file = tmp_path / "labeled.csv"

        result = runner.invoke(
            main,
            [
                "label",
                "revisions",
                str(sample_lineage_csv),
                "-o",
                str(output_file),
            ],
        )

        assert result.exit_code == 0

        original_df = pd.read_csv(sample_lineage_csv)
        labeled_df = pd.read_csv(output_file)

        # All original columns should be present
        for col in original_df.columns:
            assert col in labeled_df.columns

        # Plus new rev_status column
        assert "rev_status" in labeled_df.columns


class TestLabelFilter:
    """Test suite for label filter command."""

    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()

    @pytest.fixture
    def sample_labeled_csv(self, tmp_path):
        """Create a sample labeled CSV for testing."""
        data = {
            "global_block_id": ["gb1", "gb2", "gb3", "gb4", "gb5"],
            "clone_group_id": ["g1", "g1", "g2", "g2", "g3"],
            "revision": ["r1", "r1", "r1", "r1", "r2"],
            "state": ["survived", "deleted", "deleted", "deleted", "survived"],
            "rev_status": [
                "partial_deleted",
                "partial_deleted",
                "all_deleted",
                "all_deleted",
                "no_deleted",
            ],
            "function_name": ["f1", "f2", "f3", "f4", "f5"],
        }
        df = pd.DataFrame(data)

        csv_file = tmp_path / "labeled.csv"
        df.to_csv(csv_file, index=False)
        return csv_file

    def test_filter_basic(self, runner, sample_labeled_csv, tmp_path):
        """Test filter command with basic options."""
        output_file = tmp_path / "filtered.csv"

        result = runner.invoke(
            main,
            [
                "label",
                "filter",
                str(sample_labeled_csv),
                "-o",
                str(output_file),
            ],
        )

        assert result.exit_code == 0
        assert output_file.exists()

    def test_filter_correct_rows(self, runner, sample_labeled_csv, tmp_path):
        """Test that only partial_deleted rows are extracted."""
        output_file = tmp_path / "filtered.csv"

        result = runner.invoke(
            main,
            [
                "label",
                "filter",
                str(sample_labeled_csv),
                "-o",
                str(output_file),
            ],
        )

        assert result.exit_code == 0

        df = pd.read_csv(output_file)
        assert len(df) == 2  # Only gb1 and gb2
        assert (df["rev_status"] == "partial_deleted").all()

    def test_filter_custom_status(self, runner, sample_labeled_csv, tmp_path):
        """Test filtering by different status value."""
        output_file = tmp_path / "filtered.csv"

        result = runner.invoke(
            main,
            [
                "label",
                "filter",
                str(sample_labeled_csv),
                "-o",
                str(output_file),
                "--status",
                "all_deleted",
            ],
        )

        assert result.exit_code == 0

        df = pd.read_csv(output_file)
        assert len(df) == 2  # gb3 and gb4
        assert (df["rev_status"] == "all_deleted").all()

    def test_filter_default_output(self, runner, sample_labeled_csv, tmp_path):
        """Test default output path."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Copy sample CSV to isolated filesystem
            from pathlib import Path
            import shutil

            test_csv = Path("labeled.csv")
            shutil.copy(sample_labeled_csv, test_csv)

            result = runner.invoke(
                main,
                [
                    "label",
                    "filter",
                    str(test_csv),
                ],
            )

            assert result.exit_code == 0
            assert "output/partial_deleted.csv" in result.output

            # Verify file was created in isolated filesystem
            assert Path("output/partial_deleted.csv").exists()

    def test_filter_with_verbose(self, runner, sample_labeled_csv, tmp_path):
        """Test filter command with --verbose option."""
        output_file = tmp_path / "filtered.csv"

        result = runner.invoke(
            main,
            [
                "label",
                "filter",
                str(sample_labeled_csv),
                "-o",
                str(output_file),
                "-v",
            ],
        )

        assert result.exit_code == 0
        assert "Total records" in result.output
        assert "Target status" in result.output
        assert "Previous revision rows" in result.output
        assert "Total filtered" in result.output

    def test_filter_missing_rev_status(self, runner, tmp_path):
        """Test error handling for missing rev_status column."""
        data = {
            "clone_group_id": ["g1"],
            "revision": ["r1"],
            "state": ["survived"],
        }
        df = pd.DataFrame(data)
        csv_file = tmp_path / "no_status.csv"
        df.to_csv(csv_file, index=False)

        result = runner.invoke(
            main,
            [
                "label",
                "filter",
                str(csv_file),
            ],
        )

        assert result.exit_code != 0
        assert "rev_status" in result.output

    def test_filter_preserves_columns(self, runner, sample_labeled_csv, tmp_path):
        """Test that all columns are preserved in output."""
        output_file = tmp_path / "filtered.csv"

        result = runner.invoke(
            main,
            [
                "label",
                "filter",
                str(sample_labeled_csv),
                "-o",
                str(output_file),
            ],
        )

        assert result.exit_code == 0

        original_df = pd.read_csv(sample_labeled_csv)
        filtered_df = pd.read_csv(output_file)

        # All columns should be present
        for col in original_df.columns:
            assert col in filtered_df.columns

    def test_filter_with_previous_revision(self, runner, tmp_path):
        """Test that filter includes previous revision rows."""
        # Create test data with multiple revisions
        data = {
            "global_block_id": ["gb1", "gb1", "gb2", "gb3", "gb3"],
            "clone_group_id": ["g1", "g1", "g2", "g3", "g3"],
            "revision": ["r0", "r1", "r1", "r0", "r1"],
            "state": ["survived", "deleted", "deleted", "survived", "survived"],
            "rev_status": [
                "no_deleted",  # g1@r0: gb1
                "partial_deleted",  # g1@r1: gb1 (target - should include r0's gb1)
                "partial_deleted",  # g2@r1: gb2 (target - no previous revision)
                "no_deleted",  # g3@r0: gb3
                "no_deleted",  # g3@r1: gb3 (not target)
            ],
            "function_name": ["f1", "f1", "f2", "f3", "f3"],
        }
        df = pd.DataFrame(data)

        csv_file = tmp_path / "test_data.csv"
        df.to_csv(csv_file, index=False)

        output_file = tmp_path / "filtered.csv"

        result = runner.invoke(
            main,
            [
                "label",
                "filter",
                str(csv_file),
                "-o",
                str(output_file),
                "--status",
                "partial_deleted",
            ],
        )

        assert result.exit_code == 0

        filtered_df = pd.read_csv(output_file)

        # Should include:
        # - gb1@r1 (partial_deleted)
        # - gb1@r0 (previous revision of gb1)
        # - gb2@r1 (partial_deleted, no previous)
        assert len(filtered_df) == 3

        # Verify gb1@r0 is included (previous revision)
        gb1_r0 = filtered_df[
            (filtered_df["global_block_id"] == "gb1") & (filtered_df["revision"] == "r0")
        ]
        assert len(gb1_r0) == 1

        # Verify gb1@r1 is included (target)
        gb1_r1 = filtered_df[
            (filtered_df["global_block_id"] == "gb1") & (filtered_df["revision"] == "r1")
        ]
        assert len(gb1_r1) == 1

        # Verify gb2@r1 is included (target, no previous)
        gb2_r1 = filtered_df[
            (filtered_df["global_block_id"] == "gb2") & (filtered_df["revision"] == "r1")
        ]
        assert len(gb2_r1) == 1

        # Verify gb3 rows are NOT included
        gb3_rows = filtered_df[filtered_df["global_block_id"] == "gb3"]
        assert len(gb3_rows) == 0

        # Verify original order is maintained (sorted by index)
        assert filtered_df.index.is_monotonic_increasing

    def test_filter_with_previous_revision_verbose(self, runner, tmp_path):
        """Test filter with previous revision in verbose mode."""
        data = {
            "global_block_id": ["gb1", "gb1"],
            "clone_group_id": ["g1", "g1"],
            "revision": ["r0", "r1"],
            "state": ["survived", "deleted"],
            "rev_status": ["no_deleted", "partial_deleted"],
            "function_name": ["f1", "f1"],
        }
        df = pd.DataFrame(data)

        csv_file = tmp_path / "test_data.csv"
        df.to_csv(csv_file, index=False)

        output_file = tmp_path / "filtered.csv"

        result = runner.invoke(
            main,
            [
                "label",
                "filter",
                str(csv_file),
                "-o",
                str(output_file),
                "-v",
            ],
        )

        assert result.exit_code == 0

        # Verbose output should show breakdown
        assert "Target status" in result.output
        assert "Previous revision" in result.output
        assert "Total" in result.output
