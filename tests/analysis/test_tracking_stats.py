"""Tests for tracking statistics calculator."""

import pandas as pd
import pytest

from b4_thesis.analysis.tracking_stats import (
    GroupTrackingStats,
    MethodTrackingStats,
    calculate_group_stats,
    calculate_method_stats,
    get_lifetime_distribution,
    get_revision_timeline,
    get_state_distribution,
)


class TestMethodTrackingStats:
    """Tests for method tracking statistics."""

    @pytest.fixture
    def sample_method_df(self):
        """Sample method tracking DataFrame."""
        return pd.DataFrame(
            {
                "method_id": ["m1", "m2", "m1", "m3", "m2"],
                "revision": ["r1", "r1", "r2", "r2", "r2"],
                "state": ["added", "added", "survived", "added", "survived"],
                "detailed_state": [
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

    def test_calculate_method_stats(self, sample_method_df):
        """Test calculating method statistics."""
        stats = calculate_method_stats(sample_method_df)

        assert isinstance(stats, MethodTrackingStats)
        assert stats.total_methods == 5
        assert stats.total_revisions == 2
        assert stats.unique_methods == 3

        # State counts
        assert stats.state_counts["added"] == 3
        assert stats.state_counts["survived"] == 2

        # Clone statistics
        assert stats.methods_in_clones == 4
        assert stats.avg_clone_count == 1.6
        assert stats.max_clone_count == 3

    def test_calculate_method_stats_lifetime(self, sample_method_df):
        """Test lifetime statistics calculation."""
        stats = calculate_method_stats(sample_method_df)

        # Unique methods: m1 (10 days, 2 rev), m2 (5 days, 1 rev), m3 (15 days, 3 rev)
        assert stats.avg_lifetime_days == 10.0
        assert stats.max_lifetime_days == 15
        assert stats.median_lifetime_days == 10.0
        assert stats.avg_lifetime_revisions == 2.0
        assert stats.max_lifetime_revisions == 3

    def test_calculate_method_stats_per_revision(self, sample_method_df):
        """Test per-revision statistics."""
        stats = calculate_method_stats(sample_method_df)

        # r1: 2 methods, r2: 3 methods
        assert stats.avg_methods_per_revision == 2.5
        assert stats.max_methods_per_revision == 3
        assert stats.min_methods_per_revision == 2

    def test_calculate_method_stats_empty_df(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        with pytest.raises(ValueError, match="DataFrame is empty"):
            calculate_method_stats(df)

    def test_calculate_method_stats_missing_columns(self):
        """Test with missing columns."""
        df = pd.DataFrame({"method_id": ["m1"], "revision": ["r1"]})
        with pytest.raises(ValueError, match="Missing required columns"):
            calculate_method_stats(df)


class TestGroupTrackingStats:
    """Tests for group tracking statistics."""

    @pytest.fixture
    def sample_group_df(self):
        """Sample group tracking DataFrame."""
        return pd.DataFrame(
            {
                "group_id": ["g1", "g2", "g1", "g3"],
                "revision": ["r1", "r1", "r2", "r2"],
                "state": ["born", "born", "continued", "born"],
                "member_count": [3, 5, 4, 2],
                "members_added": [0, 0, 1, 0],
                "members_removed": [0, 0, 0, 0],
                "lifetime_days": [10, 20, 10, 5],
                "lifetime_revisions": [2, 3, 2, 1],
            }
        )

    def test_calculate_group_stats(self, sample_group_df):
        """Test calculating group statistics."""
        stats = calculate_group_stats(sample_group_df)

        assert isinstance(stats, GroupTrackingStats)
        assert stats.total_groups == 4
        assert stats.total_revisions == 2
        assert stats.unique_groups == 3

        # State counts
        assert stats.state_counts["born"] == 3
        assert stats.state_counts["continued"] == 1

    def test_calculate_group_stats_size(self, sample_group_df):
        """Test group size statistics."""
        stats = calculate_group_stats(sample_group_df)

        assert stats.avg_group_size == 3.5
        assert stats.max_group_size == 5
        assert stats.min_group_size == 2
        assert stats.median_group_size == 3.5

    def test_calculate_group_stats_member_changes(self, sample_group_df):
        """Test member change statistics."""
        stats = calculate_group_stats(sample_group_df)

        assert stats.avg_members_added == 0.25
        assert stats.avg_members_removed == 0.0
        assert stats.max_members_added == 1
        assert stats.max_members_removed == 0

    def test_calculate_group_stats_lifetime(self, sample_group_df):
        """Test lifetime statistics."""
        stats = calculate_group_stats(sample_group_df)

        # Unique groups: g1 (10 days, 2 rev), g2 (20 days, 3 rev), g3 (5 days, 1 rev)
        assert stats.avg_lifetime_days == pytest.approx(11.67, abs=0.1)
        assert stats.max_lifetime_days == 20
        assert stats.median_lifetime_days == 10.0
        assert stats.avg_lifetime_revisions == 2.0
        assert stats.max_lifetime_revisions == 3

    def test_calculate_group_stats_empty_df(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        with pytest.raises(ValueError, match="DataFrame is empty"):
            calculate_group_stats(df)

    def test_calculate_group_stats_missing_columns(self):
        """Test with missing columns."""
        df = pd.DataFrame({"group_id": ["g1"], "revision": ["r1"]})
        with pytest.raises(ValueError, match="Missing required columns"):
            calculate_group_stats(df)


class TestStateDistribution:
    """Tests for state distribution."""

    def test_get_state_distribution(self):
        """Test state distribution calculation."""
        df = pd.DataFrame(
            {
                "state": ["added", "added", "survived", "deleted", "added"],
            }
        )

        dist = get_state_distribution(df)

        assert len(dist) == 3
        assert dist[dist["state"] == "added"]["count"].values[0] == 3
        assert dist[dist["state"] == "added"]["percentage"].values[0] == 60.0
        assert dist[dist["state"] == "survived"]["count"].values[0] == 1
        assert dist[dist["state"] == "survived"]["percentage"].values[0] == 20.0

    def test_get_state_distribution_empty(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        dist = get_state_distribution(df)

        assert len(dist) == 0
        assert list(dist.columns) == ["state", "count", "percentage"]

    def test_get_state_distribution_custom_column(self):
        """Test with custom column name."""
        df = pd.DataFrame(
            {
                "detailed_state": ["added_to_group", "added_isolated", "added_to_group"],
            }
        )

        dist = get_state_distribution(df, state_col="detailed_state")

        assert len(dist) == 2
        assert dist[dist["state"] == "added_to_group"]["count"].values[0] == 2


class TestLifetimeDistribution:
    """Tests for lifetime distribution."""

    def test_get_lifetime_distribution(self):
        """Test lifetime distribution."""
        df = pd.DataFrame(
            {
                "method_id": ["m1", "m2", "m3", "m4", "m5"],
                "lifetime_days": [5, 10, 15, 20, 25],
            }
        )

        dist = get_lifetime_distribution(df, bins=5)

        assert len(dist) == 5
        assert "bin" in dist.columns
        assert "count" in dist.columns

    def test_get_lifetime_distribution_duplicates(self):
        """Test with duplicate method IDs."""
        df = pd.DataFrame(
            {
                "method_id": ["m1", "m1", "m2", "m2"],
                "lifetime_days": [10, 10, 20, 20],
            }
        )

        dist = get_lifetime_distribution(df, bins=2)

        # Should use unique methods only
        assert dist["count"].sum() == 2

    def test_get_lifetime_distribution_empty(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        dist = get_lifetime_distribution(df)

        assert len(dist) == 0
        assert list(dist.columns) == ["bin", "count"]

    def test_get_lifetime_distribution_revisions(self):
        """Test with lifetime_revisions column."""
        df = pd.DataFrame(
            {
                "method_id": ["m1", "m2", "m3"],
                "lifetime_revisions": [1, 2, 3],
            }
        )

        dist = get_lifetime_distribution(df, column="lifetime_revisions", bins=3)

        assert len(dist) == 3


class TestRevisionTimeline:
    """Tests for revision timeline."""

    def test_get_revision_timeline_count(self):
        """Test revision timeline with count metric."""
        df = pd.DataFrame(
            {
                "revision": ["r1", "r1", "r2", "r2", "r2"],
                "method_id": ["m1", "m2", "m3", "m4", "m5"],
            }
        )

        timeline = get_revision_timeline(df, metric="count")

        assert len(timeline) == 2
        assert timeline[timeline["revision"] == "r1"]["count"].values[0] == 2
        assert timeline[timeline["revision"] == "r2"]["count"].values[0] == 3

    def test_get_revision_timeline_avg_clone_count(self):
        """Test revision timeline with avg_clone_count metric."""
        df = pd.DataFrame(
            {
                "revision": ["r1", "r1", "r2", "r2"],
                "clone_count": [2, 4, 1, 3],
            }
        )

        timeline = get_revision_timeline(df, metric="avg_clone_count")

        assert len(timeline) == 2
        assert timeline[timeline["revision"] == "r1"]["avg_clone_count"].values[0] == 3.0
        assert timeline[timeline["revision"] == "r2"]["avg_clone_count"].values[0] == 2.0

    def test_get_revision_timeline_avg_group_size(self):
        """Test revision timeline with avg_group_size metric."""
        df = pd.DataFrame(
            {
                "revision": ["r1", "r1", "r2"],
                "member_count": [3, 5, 4],
            }
        )

        timeline = get_revision_timeline(df, metric="avg_group_size")

        assert len(timeline) == 2
        assert timeline[timeline["revision"] == "r1"]["avg_group_size"].values[0] == 4.0

    def test_get_revision_timeline_empty(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        timeline = get_revision_timeline(df)

        assert len(timeline) == 0

    def test_get_revision_timeline_invalid_metric(self):
        """Test with invalid metric."""
        df = pd.DataFrame({"revision": ["r1"]})
        with pytest.raises(ValueError, match="Unknown metric"):
            get_revision_timeline(df, metric="invalid")
