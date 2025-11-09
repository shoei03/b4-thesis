"""Tests for CloneGroupTracker."""

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from b4_thesis.analysis.clone_group_tracker import (
    CloneGroupTracker,
    GroupMembershipResult,
    GroupTrackingResult,
)
from b4_thesis.core.revision_manager import RevisionManager


class TestCloneGroupTrackerBasic:
    """Test basic CloneGroupTracker functionality."""

    @pytest.fixture
    def sample_revisions_dir(self):
        """Path to sample revisions fixture directory."""
        return Path(__file__).parent.parent / "fixtures" / "sample_revisions"

    @pytest.fixture
    def tracker(self, sample_revisions_dir):
        """Create CloneGroupTracker instance."""
        return CloneGroupTracker(
            data_dir=sample_revisions_dir, similarity_threshold=70, overlap_threshold=0.5
        )

    def test_initialization(self, sample_revisions_dir):
        """Test CloneGroupTracker initialization."""
        tracker = CloneGroupTracker(
            data_dir=sample_revisions_dir, similarity_threshold=70, overlap_threshold=0.5
        )
        assert tracker.data_dir == sample_revisions_dir
        assert tracker.similarity_threshold == 70
        assert tracker.overlap_threshold == 0.5
        assert isinstance(tracker.revision_manager, RevisionManager)

    def test_track_returns_two_dataframes(self, tracker):
        """Test that track() returns two DataFrames."""
        group_tracking, membership = tracker.track()
        assert isinstance(group_tracking, pd.DataFrame)
        assert isinstance(membership, pd.DataFrame)

    def test_group_tracking_has_required_columns(self, tracker):
        """Test that group_tracking DataFrame has all required columns."""
        group_tracking, _ = tracker.track()
        required_columns = [
            "revision",
            "group_id",
            "member_count",
            "avg_similarity",
            "min_similarity",
            "max_similarity",
            "density",
            "state",
            "matched_group_id",
            "overlap_ratio",
            "member_added",
            "member_removed",
            "lifetime_revisions",
            "lifetime_days",
        ]
        for col in required_columns:
            assert col in group_tracking.columns, f"Missing column: {col}"

    def test_membership_has_required_columns(self, tracker):
        """Test that membership DataFrame has all required columns."""
        _, membership = tracker.track()
        required_columns = [
            "revision",
            "group_id",
            "block_id",
            "function_name",
            "is_clone",
        ]
        for col in required_columns:
            assert col in membership.columns, f"Missing column: {col}"


class TestCloneGroupTrackerRevisionPair:
    """Test processing of revision pairs."""

    @pytest.fixture
    def sample_revisions_dir(self):
        """Path to sample revisions fixture directory."""
        return Path(__file__).parent.parent / "fixtures" / "sample_revisions"

    @pytest.fixture
    def tracker(self, sample_revisions_dir):
        """Create CloneGroupTracker instance."""
        return CloneGroupTracker(
            data_dir=sample_revisions_dir, similarity_threshold=70, overlap_threshold=0.5
        )

    def test_track_first_two_revisions(self, tracker):
        """Test tracking across first two revisions."""
        group_tracking, membership = tracker.track(
            start_date=datetime(2025, 1, 1, 10, 0, 0), end_date=datetime(2025, 1, 1, 11, 0, 0)
        )

        # Should have data for both revisions
        assert len(group_tracking) > 0
        revisions = group_tracking["revision"].unique()
        assert len(revisions) >= 1

    def test_group_state_detected(self, tracker):
        """Test that group states are detected correctly."""
        group_tracking, _ = tracker.track(
            start_date=datetime(2025, 1, 1, 10, 0, 0), end_date=datetime(2025, 1, 1, 11, 0, 0)
        )

        # Valid states (lowercase as per GroupState enum)
        valid_states = ["continued", "grown", "shrunk", "split", "merged", "dissolved", "born"]
        assert group_tracking["state"].isin(valid_states).all()

    def test_membership_tracking(self, tracker):
        """Test that membership is tracked correctly."""
        _, membership = tracker.track(
            start_date=datetime(2025, 1, 1, 10, 0, 0), end_date=datetime(2025, 1, 1, 11, 0, 0)
        )

        # Should have membership records
        assert len(membership) > 0
        # is_clone should be boolean
        assert membership["is_clone"].dtype == bool


class TestCloneGroupTrackerMultipleRevisions:
    """Test tracking across multiple revisions."""

    @pytest.fixture
    def sample_revisions_dir(self):
        """Path to sample revisions fixture directory."""
        return Path(__file__).parent.parent / "fixtures" / "sample_revisions"

    @pytest.fixture
    def tracker(self, sample_revisions_dir):
        """Create CloneGroupTracker instance."""
        return CloneGroupTracker(
            data_dir=sample_revisions_dir, similarity_threshold=70, overlap_threshold=0.5
        )

    def test_track_all_revisions(self, tracker):
        """Test tracking across all available revisions."""
        group_tracking, membership = tracker.track()

        # Should have data for all revisions
        assert len(group_tracking) > 0
        assert len(membership) > 0
        revisions = group_tracking["revision"].unique()
        assert len(revisions) >= 3  # At least 3 revisions in fixtures

    def test_lifetime_calculation(self, tracker):
        """Test lifetime calculation across revisions."""
        group_tracking, _ = tracker.track(
            start_date=datetime(2025, 1, 1, 10, 0, 0), end_date=datetime(2025, 1, 1, 12, 0, 0)
        )

        # Should have lifetime_revisions >= 1
        assert "lifetime_revisions" in group_tracking.columns
        assert (group_tracking["lifetime_revisions"] >= 1).all()

    def test_lifetime_days_calculation(self, tracker):
        """Test lifetime days calculation."""
        group_tracking, _ = tracker.track(
            start_date=datetime(2025, 1, 1, 10, 0, 0), end_date=datetime(2025, 1, 1, 12, 0, 0)
        )

        # Lifetime days should be calculated
        assert "lifetime_days" in group_tracking.columns
        assert (group_tracking["lifetime_days"] >= 0).all()


class TestCloneGroupTrackerMemberChanges:
    """Test member change tracking."""

    @pytest.fixture
    def sample_revisions_dir(self):
        """Path to sample revisions fixture directory."""
        return Path(__file__).parent.parent / "fixtures" / "sample_revisions"

    @pytest.fixture
    def tracker(self, sample_revisions_dir):
        """Create CloneGroupTracker instance."""
        return CloneGroupTracker(
            data_dir=sample_revisions_dir, similarity_threshold=70, overlap_threshold=0.5
        )

    def test_member_added_calculation(self, tracker):
        """Test member_added calculation."""
        group_tracking, _ = tracker.track(
            start_date=datetime(2025, 1, 1, 10, 0, 0), end_date=datetime(2025, 1, 1, 11, 0, 0)
        )

        # member_added should be >= 0
        assert "member_added" in group_tracking.columns
        assert (group_tracking["member_added"] >= 0).all()

    def test_member_removed_calculation(self, tracker):
        """Test member_removed calculation."""
        group_tracking, _ = tracker.track(
            start_date=datetime(2025, 1, 1, 10, 0, 0), end_date=datetime(2025, 1, 1, 11, 0, 0)
        )

        # member_removed should be >= 0
        assert "member_removed" in group_tracking.columns
        assert (group_tracking["member_removed"] >= 0).all()


class TestCloneGroupTrackerDataTypes:
    """Test data types and formats."""

    @pytest.fixture
    def sample_revisions_dir(self):
        """Path to sample revisions fixture directory."""
        return Path(__file__).parent.parent / "fixtures" / "sample_revisions"

    @pytest.fixture
    def tracker(self, sample_revisions_dir):
        """Create CloneGroupTracker instance."""
        return CloneGroupTracker(
            data_dir=sample_revisions_dir, similarity_threshold=70, overlap_threshold=0.5
        )

    def test_group_tracking_data_types(self, tracker):
        """Test that group_tracking DataFrame has correct data types."""
        group_tracking, _ = tracker.track()

        # String columns
        assert group_tracking["revision"].dtype == "object"
        assert group_tracking["group_id"].dtype == "object"
        assert group_tracking["state"].dtype == "object"

        # Integer columns
        assert pd.api.types.is_integer_dtype(group_tracking["member_count"])
        assert pd.api.types.is_integer_dtype(group_tracking["member_added"])
        assert pd.api.types.is_integer_dtype(group_tracking["member_removed"])
        assert pd.api.types.is_integer_dtype(group_tracking["lifetime_revisions"])
        assert pd.api.types.is_integer_dtype(group_tracking["lifetime_days"])

        # Float columns
        assert pd.api.types.is_float_dtype(group_tracking["density"])

    def test_membership_data_types(self, tracker):
        """Test that membership DataFrame has correct data types."""
        _, membership = tracker.track()

        # String columns
        assert membership["revision"].dtype == "object"
        assert membership["group_id"].dtype == "object"
        assert membership["block_id"].dtype == "object"
        assert membership["function_name"].dtype == "object"

        # Boolean column
        assert membership["is_clone"].dtype == bool


class TestCloneGroupTrackerEdgeCases:
    """Test edge cases."""

    @pytest.fixture
    def sample_revisions_dir(self):
        """Path to sample revisions fixture directory."""
        return Path(__file__).parent.parent / "fixtures" / "sample_revisions"

    def test_empty_date_range(self, sample_revisions_dir):
        """Test with date range that has no revisions."""
        tracker = CloneGroupTracker(
            data_dir=sample_revisions_dir, similarity_threshold=70, overlap_threshold=0.5
        )
        group_tracking, membership = tracker.track(
            start_date=datetime(2024, 1, 1, 0, 0, 0), end_date=datetime(2024, 1, 1, 23, 59, 59)
        )

        # Should return empty DataFrames with correct columns
        assert len(group_tracking) == 0
        assert len(membership) == 0
        assert isinstance(group_tracking, pd.DataFrame)
        assert isinstance(membership, pd.DataFrame)

    def test_single_revision(self, sample_revisions_dir):
        """Test with only one revision (no pairs to compare)."""
        tracker = CloneGroupTracker(
            data_dir=sample_revisions_dir, similarity_threshold=70, overlap_threshold=0.5
        )
        group_tracking, membership = tracker.track(
            start_date=datetime(2025, 1, 1, 10, 0, 0), end_date=datetime(2025, 1, 1, 10, 0, 0)
        )

        # Should have data for first revision only
        if len(group_tracking) > 0:
            assert (group_tracking["state"] == "born").all()

    def test_high_similarity_threshold(self, sample_revisions_dir):
        """Test with very high similarity threshold."""
        tracker = CloneGroupTracker(
            data_dir=sample_revisions_dir, similarity_threshold=95, overlap_threshold=0.5
        )
        group_tracking, membership = tracker.track(
            start_date=datetime(2025, 1, 1, 10, 0, 0), end_date=datetime(2025, 1, 1, 11, 0, 0)
        )

        # Should still work, but fewer groups
        assert isinstance(group_tracking, pd.DataFrame)
        assert isinstance(membership, pd.DataFrame)


class TestGroupTrackingResultDataclass:
    """Test GroupTrackingResult dataclass."""

    def test_dataclass_creation(self):
        """Test creating GroupTrackingResult instance."""
        result = GroupTrackingResult(
            revision="20250101_100000_hash1",
            group_id="group_1",
            member_count=2,
            avg_similarity=80.0,
            min_similarity=75,
            max_similarity=85,
            density=1.0,
            state="CONTINUED",
            matched_group_id="group_2",
            overlap_ratio=0.8,
            member_added=1,
            member_removed=0,
            lifetime_revisions=2,
            lifetime_days=0,
        )

        assert result.revision == "20250101_100000_hash1"
        assert result.group_id == "group_1"
        assert result.member_count == 2
        assert result.state == "CONTINUED"
        assert result.lifetime_revisions == 2


class TestGroupMembershipResultDataclass:
    """Test GroupMembershipResult dataclass."""

    def test_dataclass_creation(self):
        """Test creating GroupMembershipResult instance."""
        result = GroupMembershipResult(
            revision="20250101_100000_hash1",
            group_id="group_1",
            block_id="block_a",
            function_name="calculate",
            is_clone=True,
        )

        assert result.revision == "20250101_100000_hash1"
        assert result.group_id == "group_1"
        assert result.block_id == "block_a"
        assert result.function_name == "calculate"
        assert result.is_clone is True
