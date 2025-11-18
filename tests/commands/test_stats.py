"""Tests for stats command."""

from click.testing import CliRunner
import pandas as pd
import pytest

from b4_thesis.commands.stats import stats


class TestStatsGeneral:
    """Tests for general stats command."""

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
                "value1": [1, 2, 3, 4, 5],
                "value2": [10, 20, 30, 40, 50],
                "category": ["A", "B", "A", "B", "A"],
            }
        )
        df.to_csv(csv_file, index=False)
        return csv_file

    def test_stats_general(self, runner, sample_csv):
        """Test general stats command."""
        result = runner.invoke(stats, ["general", str(sample_csv)])

        assert result.exit_code == 0
        assert "Computing statistics" in result.output
        assert "Statistical Summary" in result.output
        assert "Statistics computed!" in result.output

    def test_stats_general_with_column(self, runner, sample_csv):
        """Test general stats with specific column."""
        result = runner.invoke(stats, ["general", str(sample_csv), "--column", "value1"])

        assert result.exit_code == 0
        assert "value1" in result.output or "MEAN" in result.output

    def test_stats_general_with_metrics(self, runner, sample_csv):
        """Test general stats with specific metrics."""
        result = runner.invoke(stats, ["general", str(sample_csv), "-m", "mean", "-m", "max"])

        assert result.exit_code == 0
        assert "MEAN" in result.output or "MAX" in result.output

    def test_stats_general_nonexistent_file(self, runner):
        """Test with nonexistent file."""
        result = runner.invoke(stats, ["general", "nonexistent.csv"])

        assert result.exit_code != 0

    def test_stats_general_nonexistent_column(self, runner, sample_csv):
        """Test with nonexistent column."""
        result = runner.invoke(stats, ["general", str(sample_csv), "--column", "nonexistent"])

        assert result.exit_code == 0
        assert "not found" in result.output


class TestStatsMethods:
    """Tests for method tracking stats command."""

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

    def test_stats_methods(self, runner, method_tracking_csv):
        """Test method tracking stats command."""
        result = runner.invoke(stats, ["methods", str(method_tracking_csv)])

        assert result.exit_code == 0
        assert "Analyzing method tracking results" in result.output
        assert "Method Tracking Statistics" in result.output
        assert "Overview" in result.output
        assert "State Distribution" in result.output
        assert "Clone Statistics" in result.output
        assert "Lifetime Statistics" in result.output
        assert "Method statistics computed!" in result.output

    def test_stats_methods_with_output(self, runner, method_tracking_csv, tmp_path):
        """Test method tracking stats with output file."""
        output_file = tmp_path / "stats.xlsx"
        result = runner.invoke(stats, ["methods", str(method_tracking_csv), "-o", str(output_file)])

        assert result.exit_code == 0
        assert output_file.exists()
        assert "Detailed statistics saved" in result.output

    def test_stats_methods_missing_columns(self, runner, tmp_path):
        """Test with missing required columns."""
        csv_file = tmp_path / "invalid.csv"
        df = pd.DataFrame({"block_id": ["m1"], "revision": ["r1"]})
        df.to_csv(csv_file, index=False)

        result = runner.invoke(stats, ["methods", str(csv_file)])

        assert result.exit_code != 0


class TestStatsGroups:
    """Tests for group tracking stats command."""

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

    def test_stats_groups(self, runner, group_tracking_csv):
        """Test group tracking stats command."""
        result = runner.invoke(stats, ["groups", str(group_tracking_csv)])

        assert result.exit_code == 0
        assert "Analyzing group tracking results" in result.output
        assert "Group Tracking Statistics - Overview" in result.output
        assert "State Distribution" in result.output
        assert "Group Size Statistics" in result.output
        assert "Member Change Statistics" in result.output
        assert "Lifetime Statistics" in result.output
        assert "Group statistics computed!" in result.output

    def test_stats_groups_with_output(self, runner, group_tracking_csv, tmp_path):
        """Test group tracking stats with output file."""
        output_file = tmp_path / "stats.xlsx"
        result = runner.invoke(stats, ["groups", str(group_tracking_csv), "-o", str(output_file)])

        assert result.exit_code == 0
        assert output_file.exists()
        assert "Detailed statistics saved" in result.output

    def test_stats_groups_missing_columns(self, runner, tmp_path):
        """Test with missing required columns."""
        csv_file = tmp_path / "invalid.csv"
        df = pd.DataFrame({"group_id": ["g1"], "revision": ["r1"]})
        df.to_csv(csv_file, index=False)

        result = runner.invoke(stats, ["groups", str(csv_file)])

        assert result.exit_code != 0
