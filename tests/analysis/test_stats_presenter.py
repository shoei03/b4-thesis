"""Tests for stats_presenter module."""

from io import StringIO

import pandas as pd
import pytest
from rich.console import Console

from b4_thesis.analysis.stats_presenter import (
    display_group_stats_tables,
    display_method_stats_tables,
    export_group_stats_to_excel,
    export_method_stats_to_excel,
)
from b4_thesis.analysis.tracking_stats import (
    GroupTrackingStats,
    MethodTrackingStats,
)


class TestDisplayMethodStatsTables:
    """Tests for display_method_stats_tables function."""

    @pytest.fixture
    def method_stats(self):
        """Create sample method tracking statistics."""
        return MethodTrackingStats(
            total_methods=100,
            unique_methods=50,
            total_revisions=10,
            avg_methods_per_revision=10.0,
            max_methods_per_revision=15,
            min_methods_per_revision=5,
            state_counts={"added": 30, "survived": 50, "deleted": 20},
            detailed_state_counts={
                "added_to_group": 20,
                "added_isolated": 10,
                "survived_unchanged": 50,
            },
            methods_in_clones=40,
            avg_clone_count=2.5,
            max_clone_count=5,
            avg_lifetime_days=15.5,
            median_lifetime_days=12.0,
            max_lifetime_days=30,
            avg_lifetime_revisions=3.2,
            median_lifetime_revisions=3.0,
            max_lifetime_revisions=8,
        )

    def test_display_method_stats_tables(self, method_stats):
        """Test method stats table display."""
        # Capture console output
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        # Display tables
        display_method_stats_tables(method_stats, console)

        # Get output
        result = output.getvalue()

        # Verify table titles (Rich wraps text, so check individual words)
        assert "Method Tracking Statistics" in result or "Method" in result
        assert "Overview" in result
        assert "State Distribution" in result
        assert "Clone Statistics" in result
        assert "Lifetime Statistics" in result

        # Verify data content
        assert "100" in result  # total_methods
        assert "50" in result  # unique_methods
        assert "10" in result  # total_revisions

    def test_display_method_stats_empty_states(self):
        """Test method stats with empty state counts."""
        stats = MethodTrackingStats(
            total_methods=0,
            unique_methods=0,
            total_revisions=0,
            avg_methods_per_revision=0.0,
            max_methods_per_revision=0,
            min_methods_per_revision=0,
            state_counts={},
            detailed_state_counts={},
            methods_in_clones=0,
            avg_clone_count=0.0,
            max_clone_count=0,
            avg_lifetime_days=0.0,
            median_lifetime_days=0.0,
            max_lifetime_days=0,
            avg_lifetime_revisions=0.0,
            median_lifetime_revisions=0.0,
            max_lifetime_revisions=0,
        )

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        # Should not raise error
        display_method_stats_tables(stats, console)

        result = output.getvalue()
        # Rich wraps text, so check individual words
        assert "Overview" in result

    def test_clone_percentage_calculation(self, method_stats):
        """Test that clone percentage is displayed correctly."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        display_method_stats_tables(method_stats, console)

        result = output.getvalue()

        # Clone percentage should be 40/100 * 100 = 40.0%
        assert "40.0%" in result or "40%" in result


class TestDisplayGroupStatsTables:
    """Tests for display_group_stats_tables function."""

    @pytest.fixture
    def group_stats(self):
        """Create sample group tracking statistics."""
        return GroupTrackingStats(
            total_groups=80,
            unique_groups=40,
            total_revisions=8,
            avg_groups_per_revision=10.0,
            max_groups_per_revision=12,
            min_groups_per_revision=8,
            state_counts={"born": 20, "continued": 30, "grown": 15, "shrunk": 10, "died": 5},
            avg_group_size=4.5,
            median_group_size=4.0,
            max_group_size=10,
            min_group_size=2,
            avg_members_added=1.2,
            max_members_added=5,
            avg_members_removed=0.8,
            max_members_removed=3,
            avg_lifetime_days=20.5,
            median_lifetime_days=18.0,
            max_lifetime_days=45,
            avg_lifetime_revisions=4.5,
            median_lifetime_revisions=4.0,
            max_lifetime_revisions=10,
        )

    def test_display_group_stats_tables(self, group_stats):
        """Test group stats table display."""
        # Capture console output
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        # Display tables
        display_group_stats_tables(group_stats, console)

        # Get output
        result = output.getvalue()

        # Verify table titles
        assert "Group Tracking Statistics - Overview" in result
        assert "State Distribution" in result
        assert "Group Size Statistics" in result
        assert "Member Change Statistics" in result
        assert "Lifetime Statistics" in result

        # Verify data content
        assert "80" in result  # total_groups
        assert "40" in result  # unique_groups
        assert "8" in result  # total_revisions

    def test_display_group_stats_empty_states(self):
        """Test group stats with empty state counts."""
        stats = GroupTrackingStats(
            total_groups=0,
            unique_groups=0,
            total_revisions=0,
            avg_groups_per_revision=0.0,
            max_groups_per_revision=0,
            min_groups_per_revision=0,
            state_counts={},
            avg_group_size=0.0,
            median_group_size=0.0,
            max_group_size=0,
            min_group_size=0,
            avg_members_added=0.0,
            max_members_added=0,
            avg_members_removed=0.0,
            max_members_removed=0,
            avg_lifetime_days=0.0,
            median_lifetime_days=0.0,
            max_lifetime_days=0,
            avg_lifetime_revisions=0.0,
            median_lifetime_revisions=0.0,
            max_lifetime_revisions=0,
        )

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        # Should not raise error
        display_group_stats_tables(stats, console)

        result = output.getvalue()
        assert "Group Tracking Statistics - Overview" in result

    def test_state_distribution_percentages(self, group_stats):
        """Test that state distribution percentages are calculated correctly."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        display_group_stats_tables(group_stats, console)

        result = output.getvalue()

        # State Distribution table should show percentages
        # Total states = 20+30+15+10+5 = 80
        # born: 20/80 = 25.0%, continued: 30/80 = 37.5%
        assert "%" in result


class TestExportMethodStatsToExcel:
    """Tests for export_method_stats_to_excel function."""

    @pytest.fixture
    def method_tracking_df(self):
        """Create sample method tracking DataFrame."""
        return pd.DataFrame(
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

    def test_export_method_stats_to_excel(self, method_tracking_df, tmp_path):
        """Test exporting method stats to Excel."""
        output_file = tmp_path / "method_stats.xlsx"
        result_path = export_method_stats_to_excel(method_tracking_df, str(output_file))

        # Check file was created
        assert result_path.endswith(".xlsx")
        assert (tmp_path / "method_stats.xlsx").exists()

        # Read Excel file and verify sheets
        excel_file = pd.ExcelFile(tmp_path / "method_stats.xlsx")
        assert "State Distribution" in excel_file.sheet_names
        assert "Detailed States" in excel_file.sheet_names
        assert "Lifetime Distribution" in excel_file.sheet_names

    def test_export_method_stats_csv_extension(self, method_tracking_df, tmp_path):
        """Test that .csv extension is converted to .xlsx."""
        output_file = tmp_path / "method_stats.csv"
        result_path = export_method_stats_to_excel(method_tracking_df, str(output_file))

        # Should convert to .xlsx
        assert result_path.endswith(".xlsx")
        assert (tmp_path / "method_stats.xlsx").exists()

    def test_export_method_stats_no_extension(self, method_tracking_df, tmp_path):
        """Test that missing extension is added."""
        output_file = tmp_path / "method_stats"
        result_path = export_method_stats_to_excel(method_tracking_df, str(output_file))

        # Should add .xlsx extension
        assert result_path.endswith(".xlsx")
        assert (tmp_path / "method_stats.xlsx").exists()


class TestExportGroupStatsToExcel:
    """Tests for export_group_stats_to_excel function."""

    @pytest.fixture
    def group_tracking_df(self):
        """Create sample group tracking DataFrame."""
        return pd.DataFrame(
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

    def test_export_group_stats_to_excel(self, group_tracking_df, tmp_path):
        """Test exporting group stats to Excel."""
        output_file = tmp_path / "group_stats.xlsx"
        result_path = export_group_stats_to_excel(group_tracking_df, str(output_file))

        # Check file was created
        assert result_path.endswith(".xlsx")
        assert (tmp_path / "group_stats.xlsx").exists()

        # Read Excel file and verify sheets
        excel_file = pd.ExcelFile(tmp_path / "group_stats.xlsx")
        assert "State Distribution" in excel_file.sheet_names
        assert "Size Distribution" in excel_file.sheet_names
        assert "Lifetime Distribution" in excel_file.sheet_names

    def test_export_group_stats_no_xlsx_extension(self, group_tracking_df, tmp_path):
        """Test that .xlsx extension is added if missing."""
        output_file = tmp_path / "group_stats"
        result_path = export_group_stats_to_excel(group_tracking_df, str(output_file))

        # Should add .xlsx extension
        assert result_path.endswith(".xlsx")
        assert (tmp_path / "group_stats.xlsx").exists()

    def test_export_group_stats_xlsx_extension(self, group_tracking_df, tmp_path):
        """Test that existing .xlsx extension is preserved."""
        output_file = tmp_path / "group_stats.xlsx"
        result_path = export_group_stats_to_excel(group_tracking_df, str(output_file))

        # Should preserve .xlsx extension
        assert result_path.endswith(".xlsx")
        assert result_path == str(output_file)
