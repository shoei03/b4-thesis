"""Tests for visualize command."""

from click.testing import CliRunner
import pandas as pd
import pytest

from b4_thesis.commands.visualize import visualize


class TestVisualizeGeneral:
    """Tests for general visualize command."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def sample_csv(self, tmp_path):
        """Create sample CSV file."""
        csv_file = tmp_path / "data.csv"
        df = pd.DataFrame(
            {
                "x": [1, 2, 3, 4, 5],
                "y": [10, 20, 30, 40, 50],
                "category": ["A", "B", "A", "B", "A"],
            }
        )
        df.to_csv(csv_file, index=False)
        return csv_file

    def test_visualize_general_scatter(self, runner, sample_csv, tmp_path):
        """Test general visualize command with scatter plot."""
        output_file = tmp_path / "plot.png"
        result = runner.invoke(
            visualize,
            [
                "general",
                str(sample_csv),
                "-o",
                str(output_file),
                "-t",
                "scatter",
                "--x-column",
                "x",
                "--y-column",
                "y",
            ],
        )

        assert result.exit_code == 0
        assert output_file.exists()
        assert "Visualization saved" in result.output

    def test_visualize_general_histogram(self, runner, sample_csv, tmp_path):
        """Test general visualize command with histogram."""
        output_file = tmp_path / "plot.png"
        result = runner.invoke(
            visualize,
            [
                "general",
                str(sample_csv),
                "-o",
                str(output_file),
                "-t",
                "histogram",
                "--x-column",
                "x",
            ],
        )

        assert result.exit_code == 0
        assert output_file.exists()

    def test_visualize_general_missing_columns(self, runner, sample_csv, tmp_path):
        """Test with missing required columns."""
        output_file = tmp_path / "plot.png"
        result = runner.invoke(
            visualize,
            ["general", str(sample_csv), "-o", str(output_file), "-t", "scatter"],
        )

        assert result.exit_code == 0
        assert "--x-column and --y-column required" in result.output


class TestVisualizeMethods:
    """Tests for method tracking visualize command."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def method_tracking_csv(self, tmp_path):
        """Create sample method tracking CSV."""
        csv_file = tmp_path / "method_tracking.csv"
        df = pd.DataFrame(
            {
                "block_id": ["m1", "m2", "m1", "m3", "m2"],
                "revision": ["r1", "r1", "r2", "r2", "r2"],
                "state": ["added", "added", "survived", "added", "survived"],
                "state_detail": [
                    "added_to_group",
                    "added_isolated",
                    "survived_unchanged",
                    "added_to_group",
                    "survived_modified",
                ],
                "clone_count": [2, 0, 2, 3, 1],
                "lifetime_days": [10, 5, 10, 15, 5],
                "lifetime_revisions": [2, 1, 2, 3, 1],
            }
        )
        df.to_csv(csv_file, index=False)
        return csv_file

    def test_visualize_methods_dashboard(self, runner, method_tracking_csv, tmp_path):
        """Test method tracking dashboard creation."""
        output_dir = tmp_path / "plots"
        result = runner.invoke(
            visualize,
            ["methods", str(method_tracking_csv), "-o", str(output_dir), "-t", "dashboard"],
        )

        assert result.exit_code == 0
        assert output_dir.exists()
        assert "Dashboard created" in result.output

        # Check that plots were created
        assert (output_dir / "state_distribution.png").exists()
        assert (output_dir / "lifetime_days_distribution.png").exists()

    def test_visualize_methods_state(self, runner, method_tracking_csv, tmp_path):
        """Test method state distribution plot."""
        output_dir = tmp_path / "plots"
        result = runner.invoke(
            visualize,
            ["methods", str(method_tracking_csv), "-o", str(output_dir), "-t", "state"],
        )

        assert result.exit_code == 0
        assert (output_dir / "state_distribution.png").exists()
        assert "State distribution saved" in result.output

    def test_visualize_methods_lifetime(self, runner, method_tracking_csv, tmp_path):
        """Test method lifetime distribution plot."""
        output_dir = tmp_path / "plots"
        result = runner.invoke(
            visualize,
            ["methods", str(method_tracking_csv), "-o", str(output_dir), "-t", "lifetime"],
        )

        assert result.exit_code == 0
        assert (output_dir / "lifetime_distribution.png").exists()

    def test_visualize_methods_timeline(self, runner, method_tracking_csv, tmp_path):
        """Test method timeline plot."""
        output_dir = tmp_path / "plots"
        result = runner.invoke(
            visualize,
            ["methods", str(method_tracking_csv), "-o", str(output_dir), "-t", "timeline"],
        )

        assert result.exit_code == 0
        assert (output_dir / "method_count_timeline.png").exists()


class TestVisualizeGroups:
    """Tests for group tracking visualize command."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def group_tracking_csv(self, tmp_path):
        """Create sample group tracking CSV."""
        csv_file = tmp_path / "group_tracking.csv"
        df = pd.DataFrame(
            {
                "group_id": ["g1", "g2", "g1", "g3"],
                "revision": ["r1", "r1", "r2", "r2"],
                "state": ["born", "born", "continued", "born"],
                "member_count": [3, 5, 4, 2],
                "member_added": [0, 0, 1, 0],
                "member_removed": [0, 0, 0, 0],
                "lifetime_days": [10, 20, 10, 5],
                "lifetime_revisions": [2, 3, 2, 1],
            }
        )
        df.to_csv(csv_file, index=False)
        return csv_file

    def test_visualize_groups_dashboard(self, runner, group_tracking_csv, tmp_path):
        """Test group tracking dashboard creation."""
        output_dir = tmp_path / "plots"
        result = runner.invoke(
            visualize,
            ["groups", str(group_tracking_csv), "-o", str(output_dir), "-t", "dashboard"],
        )

        assert result.exit_code == 0
        assert output_dir.exists()
        assert "Dashboard created" in result.output

        # Check that plots were created
        assert (output_dir / "state_distribution.png").exists()
        assert (output_dir / "group_size_distribution.png").exists()

    def test_visualize_groups_state(self, runner, group_tracking_csv, tmp_path):
        """Test group state distribution plot."""
        output_dir = tmp_path / "plots"
        result = runner.invoke(
            visualize,
            ["groups", str(group_tracking_csv), "-o", str(output_dir), "-t", "state"],
        )

        assert result.exit_code == 0
        assert (output_dir / "state_distribution.png").exists()

    def test_visualize_groups_size(self, runner, group_tracking_csv, tmp_path):
        """Test group size distribution plot."""
        output_dir = tmp_path / "plots"
        result = runner.invoke(
            visualize,
            ["groups", str(group_tracking_csv), "-o", str(output_dir), "-t", "size"],
        )

        assert result.exit_code == 0
        assert (output_dir / "group_size_distribution.png").exists()

    def test_visualize_groups_timeline(self, runner, group_tracking_csv, tmp_path):
        """Test group timeline plot."""
        output_dir = tmp_path / "plots"
        result = runner.invoke(
            visualize,
            ["groups", str(group_tracking_csv), "-o", str(output_dir), "-t", "timeline"],
        )

        assert result.exit_code == 0
        assert (output_dir / "group_count_timeline.png").exists()

    def test_visualize_groups_members(self, runner, group_tracking_csv, tmp_path):
        """Test group member changes plot."""
        output_dir = tmp_path / "plots"
        result = runner.invoke(
            visualize,
            ["groups", str(group_tracking_csv), "-o", str(output_dir), "-t", "members"],
        )

        assert result.exit_code == 0
        assert (output_dir / "member_changes.png").exists()
