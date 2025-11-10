"""Tests for track CLI commands."""

from pathlib import Path
import shutil

from click.testing import CliRunner
import pandas as pd
import pytest

from b4_thesis.commands.track import track


@pytest.fixture
def runner():
    """Create CLI runner."""
    return CliRunner()


@pytest.fixture
def sample_data_dir():
    """Path to sample revision data."""
    return Path(__file__).parent.parent / "fixtures" / "sample_revisions"


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    yield output_dir
    # Cleanup
    if output_dir.exists():
        shutil.rmtree(output_dir)


class TestTrackMethods:
    """Tests for 'track methods' command."""

    def test_track_methods_basic(self, runner, sample_data_dir, temp_output_dir):
        """Test basic method tracking."""
        result = runner.invoke(
            track,
            ["methods", str(sample_data_dir), "--output", str(temp_output_dir)],
        )

        assert result.exit_code == 0
        assert "Method tracking complete" in result.output

        # Check output file exists
        output_file = temp_output_dir / "method_tracking.csv"
        assert output_file.exists()

        # Verify CSV content
        df = pd.read_csv(output_file)
        assert len(df) > 0
        assert "revision" in df.columns
        assert "block_id" in df.columns
        assert "state" in df.columns

    def test_track_methods_with_summary(self, runner, sample_data_dir, temp_output_dir):
        """Test method tracking with summary display."""
        result = runner.invoke(
            track,
            ["methods", str(sample_data_dir), "--output", str(temp_output_dir), "--summary"],
        )

        assert result.exit_code == 0
        assert "Summary" in result.output or "Total methods" in result.output

    def test_track_methods_with_date_range(self, runner, sample_data_dir, temp_output_dir):
        """Test method tracking with date range filtering."""
        result = runner.invoke(
            track,
            [
                "methods",
                str(sample_data_dir),
                "--output",
                str(temp_output_dir),
                "--start-date",
                "2025-01-01",
                "--end-date",
                "2025-01-02",
            ],
        )

        assert result.exit_code == 0

    def test_track_methods_invalid_data_dir(self, runner, temp_output_dir):
        """Test method tracking with invalid data directory."""
        result = runner.invoke(
            track,
            ["methods", "/nonexistent/path", "--output", str(temp_output_dir)],
        )

        assert result.exit_code != 0

    def test_track_methods_missing_output_dir(self, runner, sample_data_dir):
        """Test method tracking without output directory (default to current dir)."""
        result = runner.invoke(
            track,
            ["methods", str(sample_data_dir)],
        )

        assert result.exit_code == 0

    def test_track_methods_with_lineage_flag(self, runner, sample_data_dir, temp_output_dir):
        """Test method tracking with --lineage flag generates both CSV files."""
        result = runner.invoke(
            track,
            ["methods", str(sample_data_dir), "--output", str(temp_output_dir), "--lineage"],
        )

        assert result.exit_code == 0
        assert "Method tracking complete" in result.output
        assert "Lineage data" in result.output

        # Check both output files exist
        tracking_file = temp_output_dir / "method_tracking.csv"
        lineage_file = temp_output_dir / "method_lineage.csv"
        assert tracking_file.exists()
        assert lineage_file.exists()

        # Verify tracking CSV has block_id and matched_block_id
        tracking_df = pd.read_csv(tracking_file)
        assert "block_id" in tracking_df.columns
        assert "matched_block_id" in tracking_df.columns
        assert "global_block_id" not in tracking_df.columns

        # Verify lineage CSV has global_block_id but not block_id/matched_block_id
        lineage_df = pd.read_csv(lineage_file)
        assert "global_block_id" in lineage_df.columns
        assert "block_id" not in lineage_df.columns
        assert "matched_block_id" not in lineage_df.columns

        # Verify lineage CSV has 16 columns
        assert len(lineage_df.columns) == 16

        # Verify both have same number of rows
        assert len(tracking_df) == len(lineage_df)

    def test_track_methods_without_lineage_flag(self, runner, sample_data_dir, temp_output_dir):
        """Test that lineage CSV is not generated without --lineage flag."""
        result = runner.invoke(
            track,
            ["methods", str(sample_data_dir), "--output", str(temp_output_dir)],
        )

        assert result.exit_code == 0

        # Check only tracking file exists
        tracking_file = temp_output_dir / "method_tracking.csv"
        lineage_file = temp_output_dir / "method_lineage.csv"
        assert tracking_file.exists()
        assert not lineage_file.exists()


class TestTrackGroups:
    """Tests for 'track groups' command."""

    def test_track_groups_basic(self, runner, sample_data_dir, temp_output_dir):
        """Test basic group tracking."""
        result = runner.invoke(
            track,
            ["groups", str(sample_data_dir), "--output", str(temp_output_dir)],
        )

        assert result.exit_code == 0
        assert "Group tracking complete" in result.output

        # Check output files exist
        group_file = temp_output_dir / "group_tracking.csv"
        membership_file = temp_output_dir / "group_membership.csv"
        assert group_file.exists()
        assert membership_file.exists()

        # Verify CSV content
        df_groups = pd.read_csv(group_file)
        df_membership = pd.read_csv(membership_file)
        assert len(df_groups) > 0
        assert len(df_membership) > 0
        assert "group_id" in df_groups.columns
        assert "state" in df_groups.columns

    def test_track_groups_with_summary(self, runner, sample_data_dir, temp_output_dir):
        """Test group tracking with summary display."""
        result = runner.invoke(
            track,
            ["groups", str(sample_data_dir), "--output", str(temp_output_dir), "--summary"],
        )

        assert result.exit_code == 0
        assert "Summary" in result.output or "Total groups" in result.output

    def test_track_groups_with_similarity_threshold(self, runner, sample_data_dir, temp_output_dir):
        """Test group tracking with custom similarity threshold."""
        result = runner.invoke(
            track,
            [
                "groups",
                str(sample_data_dir),
                "--output",
                str(temp_output_dir),
                "--similarity",
                "80",
            ],
        )

        assert result.exit_code == 0

    def test_track_groups_with_overlap_threshold(self, runner, sample_data_dir, temp_output_dir):
        """Test group tracking with custom overlap threshold."""
        result = runner.invoke(
            track,
            [
                "groups",
                str(sample_data_dir),
                "--output",
                str(temp_output_dir),
                "--overlap",
                "0.6",
            ],
        )

        assert result.exit_code == 0


class TestTrackAll:
    """Tests for 'track all' command."""

    def test_track_all_basic(self, runner, sample_data_dir, temp_output_dir):
        """Test tracking both methods and groups."""
        result = runner.invoke(
            track,
            ["all", str(sample_data_dir), "--output", str(temp_output_dir)],
        )

        assert result.exit_code == 0
        assert "Method tracking complete" in result.output
        assert "Group tracking complete" in result.output

        # Check all output files exist
        method_file = temp_output_dir / "method_tracking.csv"
        group_file = temp_output_dir / "group_tracking.csv"
        membership_file = temp_output_dir / "group_membership.csv"
        assert method_file.exists()
        assert group_file.exists()
        assert membership_file.exists()

    def test_track_all_with_summary(self, runner, sample_data_dir, temp_output_dir):
        """Test tracking all with summary display."""
        result = runner.invoke(
            track,
            ["all", str(sample_data_dir), "--output", str(temp_output_dir), "--summary"],
        )

        assert result.exit_code == 0
        assert "Summary" in result.output or "Total" in result.output


class TestTrackCommandGroup:
    """Tests for track command group."""

    def test_track_help(self, runner):
        """Test track command help."""
        result = runner.invoke(track, ["--help"])

        assert result.exit_code == 0
        assert "methods" in result.output
        assert "groups" in result.output
        assert "all" in result.output

    def test_track_methods_help(self, runner):
        """Test track methods help."""
        result = runner.invoke(track, ["methods", "--help"])

        assert result.exit_code == 0
        assert "DATA_DIR" in result.output or "data-dir" in result.output.lower()

    def test_track_groups_help(self, runner):
        """Test track groups help."""
        result = runner.invoke(track, ["groups", "--help"])

        assert result.exit_code == 0
        assert "DATA_DIR" in result.output or "data-dir" in result.output.lower()

    def test_track_all_help(self, runner):
        """Test track all help."""
        result = runner.invoke(track, ["all", "--help"])

        assert result.exit_code == 0
        assert "DATA_DIR" in result.output or "data-dir" in result.output.lower()


class TestTrackErrorHandling:
    """Tests for error handling."""

    def test_empty_data_directory(self, runner, tmp_path):
        """Test with empty data directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = runner.invoke(
            track,
            ["methods", str(empty_dir)],
        )

        # Should handle gracefully (no revisions found)
        assert result.exit_code == 0
        assert "No revisions found" in result.output or "0 revisions" in result.output

    def test_invalid_date_format(self, runner, sample_data_dir, temp_output_dir):
        """Test with invalid date format."""
        result = runner.invoke(
            track,
            [
                "methods",
                str(sample_data_dir),
                "--output",
                str(temp_output_dir),
                "--start-date",
                "invalid-date",
            ],
        )

        assert result.exit_code != 0
        assert "Invalid" in result.output or "Error" in result.output

    def test_invalid_similarity_threshold(self, runner, sample_data_dir, temp_output_dir):
        """Test with invalid similarity threshold."""
        result = runner.invoke(
            track,
            [
                "groups",
                str(sample_data_dir),
                "--output",
                str(temp_output_dir),
                "--similarity",
                "150",
            ],
        )

        assert result.exit_code != 0

    def test_invalid_overlap_threshold(self, runner, sample_data_dir, temp_output_dir):
        """Test with invalid overlap threshold."""
        result = runner.invoke(
            track,
            [
                "groups",
                str(sample_data_dir),
                "--output",
                str(temp_output_dir),
                "--overlap",
                "1.5",
            ],
        )

        assert result.exit_code != 0
