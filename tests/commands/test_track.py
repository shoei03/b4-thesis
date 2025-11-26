"""Tests for track CLI commands."""

from pathlib import Path
import shutil

from click.testing import CliRunner
import pandas as pd
import pytest

from b4_thesis.commands.track import (
    _apply_optimization_defaults,
    _build_status_message,
    _parse_progressive_thresholds,
    _setup_paths,
    track,
)


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
            ["methods", "--input", str(sample_data_dir), "--output", str(temp_output_dir)],
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
            [
                "methods",
                "--input",
                str(sample_data_dir),
                "--output",
                str(temp_output_dir),
                "--summary",
            ],
        )

        assert result.exit_code == 0
        assert "Summary" in result.output or "Total methods" in result.output

    def test_track_methods_with_date_range(self, runner, sample_data_dir, temp_output_dir):
        """Test method tracking with date range filtering."""
        result = runner.invoke(
            track,
            [
                "methods",
                "--input",
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
            ["methods", "--input", "/nonexistent/path", "--output", str(temp_output_dir)],
        )

        assert result.exit_code != 0


class TestTrackGroups:
    """Tests for 'track groups' command."""

    def test_track_groups_basic(self, runner, sample_data_dir, temp_output_dir):
        """Test basic group tracking."""
        result = runner.invoke(
            track,
            ["groups", "--input", str(sample_data_dir), "--output", str(temp_output_dir)],
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
            [
                "groups",
                "--input",
                str(sample_data_dir),
                "--output",
                str(temp_output_dir),
                "--summary",
            ],
        )

        assert result.exit_code == 0
        assert "Summary" in result.output or "Total groups" in result.output

    def test_track_groups_with_similarity_threshold(self, runner, sample_data_dir, temp_output_dir):
        """Test group tracking with custom similarity threshold."""
        result = runner.invoke(
            track,
            [
                "groups",
                "--input",
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
                "--input",
                str(sample_data_dir),
                "--output",
                str(temp_output_dir),
                "--overlap",
                "0.6",
            ],
        )

        assert result.exit_code == 0


class TestTrackCommandGroup:
    """Tests for track command group."""

    def test_track_help(self, runner):
        """Test track command help."""
        result = runner.invoke(track, ["--help"])

        assert result.exit_code == 0
        assert "methods" in result.output
        assert "groups" in result.output

    def test_track_methods_help(self, runner):
        """Test track methods help."""
        result = runner.invoke(track, ["methods", "--help"])

        assert result.exit_code == 0
        assert "--input" in result.output.lower()

    def test_track_groups_help(self, runner):
        """Test track groups help."""
        result = runner.invoke(track, ["groups", "--help"])

        assert result.exit_code == 0
        assert "--input" in result.output.lower()


class TestTrackErrorHandling:
    """Tests for error handling."""

    def test_empty_data_directory(self, runner, tmp_path):
        """Test with empty data directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = runner.invoke(
            track,
            ["methods", "--input", str(empty_dir), "--output", str(output_dir)],
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
                "--input",
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
                "--input",
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
                "--input",
                str(sample_data_dir),
                "--output",
                str(temp_output_dir),
                "--overlap",
                "1.5",
            ],
        )

        assert result.exit_code != 0


class TestHelperFunctions:
    """Tests for helper functions in track module."""

    def test_setup_paths_creates_output_directory(self, tmp_path):
        """Test _setup_paths creates output directory if it doesn't exist."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()

        data_path, output_path = _setup_paths(str(input_dir), str(output_dir))

        assert data_path == input_dir
        assert output_path == output_dir
        assert output_dir.exists()

    def test_setup_paths_with_existing_output(self, tmp_path):
        """Test _setup_paths works with existing output directory."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        data_path, output_path = _setup_paths(str(input_dir), str(output_dir))

        assert data_path == input_dir
        assert output_path == output_dir
        assert output_dir.exists()

    def test_parse_progressive_thresholds_valid(self):
        """Test _parse_progressive_thresholds with valid input."""
        result = _parse_progressive_thresholds("90,80,70")
        assert result == [90, 80, 70]

    def test_parse_progressive_thresholds_unsorted(self):
        """Test _parse_progressive_thresholds sorts in descending order."""
        result = _parse_progressive_thresholds("70,90,80")
        assert result == [90, 80, 70]

    def test_parse_progressive_thresholds_with_spaces(self):
        """Test _parse_progressive_thresholds handles spaces."""
        result = _parse_progressive_thresholds(" 90 , 80 , 70 ")
        assert result == [90, 80, 70]

    def test_parse_progressive_thresholds_none(self):
        """Test _parse_progressive_thresholds with None input."""
        result = _parse_progressive_thresholds(None)
        assert result is None

    def test_parse_progressive_thresholds_empty_string(self):
        """Test _parse_progressive_thresholds with empty string."""
        result = _parse_progressive_thresholds("")
        assert result is None

    def test_parse_progressive_thresholds_invalid_format(self):
        """Test _parse_progressive_thresholds with invalid format."""
        with pytest.raises(ValueError, match="comma-separated integers"):
            _parse_progressive_thresholds("90,abc,70")

    def test_parse_progressive_thresholds_out_of_range(self):
        """Test _parse_progressive_thresholds with out of range values."""
        with pytest.raises(ValueError, match="must be between 0 and 100"):
            _parse_progressive_thresholds("90,150,70")

        with pytest.raises(ValueError, match="must be between 0 and 100"):
            _parse_progressive_thresholds("90,-10,70")

    def test_apply_optimization_defaults_optimize_false(self):
        """Test _apply_optimization_defaults when optimize is False."""
        use_lsh, use_opt_sim, thresholds = _apply_optimization_defaults(False, False, False, None)
        assert use_lsh is False
        assert use_opt_sim is False
        assert thresholds == ""

    def test_apply_optimization_defaults_optimize_true(self):
        """Test _apply_optimization_defaults when optimize is True."""
        use_lsh, use_opt_sim, thresholds = _apply_optimization_defaults(True, False, False, None)
        assert use_lsh is True
        assert use_opt_sim is True
        assert thresholds == "90,80,70"

    def test_apply_optimization_defaults_with_custom_thresholds(self):
        """Test _apply_optimization_defaults with custom thresholds."""
        use_lsh, use_opt_sim, thresholds = _apply_optimization_defaults(
            True, False, False, "95,85,75"
        )
        assert use_lsh is True
        assert use_opt_sim is True
        assert thresholds == "95,85,75"

    def test_build_status_message_basic(self):
        """Test _build_status_message with basic parameters."""
        msg = _build_status_message("methods", False, False)
        assert msg == "[bold green]Analyzing methods..."

    def test_build_status_message_optimized(self):
        """Test _build_status_message with optimized flag."""
        msg = _build_status_message("methods", True, False)
        assert msg == "[bold green]Analyzing methods (optimized)..."

    def test_build_status_message_parallel(self):
        """Test _build_status_message with parallel flag."""
        msg = _build_status_message("methods", False, True)
        assert msg == "[bold green]Analyzing methods (parallel)..."

    def test_build_status_message_optimized_and_parallel(self):
        """Test _build_status_message with both flags."""
        msg = _build_status_message("methods", True, True)
        assert msg == "[bold green]Analyzing methods (optimized) (parallel)..."

    def test_build_status_message_clone_groups(self):
        """Test _build_status_message with clone groups."""
        msg = _build_status_message("clone groups", True, False)
        assert msg == "[bold green]Analyzing clone groups (optimized)..."
