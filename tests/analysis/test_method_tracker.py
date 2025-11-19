"""Tests for MethodTracker."""

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from b4_thesis.analysis.method_tracker import MethodTracker, MethodTrackingResult
from b4_thesis.core.revision_manager import RevisionManager


class TestMethodTrackerBasic:
    """Test basic MethodTracker functionality."""

    @pytest.fixture
    def sample_revisions_dir(self):
        """Path to sample revisions fixture directory."""
        return Path(__file__).parent.parent / "fixtures" / "sample_revisions"

    @pytest.fixture
    def tracker(self, sample_revisions_dir):
        """Create MethodTracker instance."""
        return MethodTracker(data_dir=sample_revisions_dir, similarity_threshold=70)

    def test_initialization(self, sample_revisions_dir):
        """Test MethodTracker initialization."""
        tracker = MethodTracker(data_dir=sample_revisions_dir, similarity_threshold=70)
        assert tracker.data_dir == sample_revisions_dir
        assert tracker.similarity_threshold == 70
        assert isinstance(tracker.revision_manager, RevisionManager)

    def test_track_returns_dataframe(self, tracker):
        """Test that track() returns a DataFrame."""
        result = tracker.track()
        assert isinstance(result, pd.DataFrame)

    def test_track_has_required_columns(self, tracker):
        """Test that output DataFrame has all required columns."""
        result = tracker.track()
        required_columns = [
            "revision",
            "block_id",
            "function_name",
            "file_path",
            "start_line",
            "end_line",
            "loc",
            "state",
            "state_detail",
            "matched_block_id",
            "match_type",
            "match_similarity",
            "clone_count",
            "clone_group_id",
            "clone_group_size",
            "lifetime_revisions",
            "lifetime_days",
        ]
        for col in required_columns:
            assert col in result.columns, f"Missing column: {col}"

    def test_to_tracking_format_before_track(self, tracker):
        """Test that calling to_tracking_format() before track() raises error."""
        error_msg = "Must call track\\(\\) before to_tracking_format\\(\\)"
        with pytest.raises(RuntimeError, match=error_msg):
            tracker.to_tracking_format()


class TestMethodTrackerRevisionPair:
    """Test processing of revision pairs."""

    @pytest.fixture
    def sample_revisions_dir(self):
        """Path to sample revisions fixture directory."""
        return Path(__file__).parent.parent / "fixtures" / "sample_revisions"

    @pytest.fixture
    def tracker(self, sample_revisions_dir):
        """Create MethodTracker instance."""
        return MethodTracker(data_dir=sample_revisions_dir, similarity_threshold=70)

    def test_track_first_two_revisions(self, tracker):
        """Test tracking across first two revisions."""
        # Track only first two revisions
        result = tracker.track(
            start_date=datetime(2025, 1, 1, 10, 0, 0), end_date=datetime(2025, 1, 1, 11, 0, 0)
        )

        # Should have data for both revisions
        assert len(result) > 0
        revisions = result["revision"].unique()
        assert len(revisions) >= 1

    def test_survived_method_detected(self, tracker):
        """Test that survived methods are detected."""
        result = tracker.track(
            start_date=datetime(2025, 1, 1, 10, 0, 0), end_date=datetime(2025, 1, 1, 11, 0, 0)
        )

        # block_a should survive as block_a2
        rev2_blocks = result[result["revision"] == "20250101_110000_hash2"]
        survived = rev2_blocks[rev2_blocks["state"] == "survived"]
        assert len(survived) > 0

    def test_deleted_method_detected(self, tracker):
        """Test that deleted methods are detected."""
        result = tracker.track(
            start_date=datetime(2025, 1, 1, 10, 0, 0), end_date=datetime(2025, 1, 1, 11, 0, 0)
        )

        # block_c should be deleted in rev2 (appears in rev1, not in rev2)
        # Deleted methods appear in the new revision with state="deleted"
        rev2_blocks = result[result["revision"] == "20250101_110000_hash2"]
        deleted_blocks = rev2_blocks[rev2_blocks["state"] == "deleted"]

        # Should have at least one deleted block (block_c)
        assert len(deleted_blocks) > 0, "Expected to find deleted methods in rev2"

        # Verify block_c is marked as deleted
        block_c_deleted = deleted_blocks[deleted_blocks["block_id"] == "block_c"]
        assert len(block_c_deleted) == 1, "block_c should be marked as deleted"
        assert pd.isna(block_c_deleted.iloc[0]["matched_block_id"]), (
            "Deleted block should have no match"
        )

    def test_added_method_detected(self, tracker):
        """Test that added methods are detected."""
        result = tracker.track()

        # In rev1, all methods should be "added" (first revision)
        rev1_blocks = result[result["revision"] == "20250101_100000_hash1"]
        assert (rev1_blocks["state"] == "added").all()

        # In later revisions, check if there are any truly new methods
        # (methods not present in previous revisions)
        # Note: Current fixtures don't have new methods added after rev1,
        # but we can still verify the "added" state logic works
        all_added = result[result["state"] == "added"]
        assert len(all_added) >= 4  # At least rev1's 4 blocks


class TestMethodTrackerMultipleRevisions:
    """Test tracking across multiple revisions."""

    @pytest.fixture
    def sample_revisions_dir(self):
        """Path to sample revisions fixture directory."""
        return Path(__file__).parent.parent / "fixtures" / "sample_revisions"

    @pytest.fixture
    def tracker(self, sample_revisions_dir):
        """Create MethodTracker instance."""
        return MethodTracker(data_dir=sample_revisions_dir, similarity_threshold=70)

    def test_track_all_revisions(self, tracker):
        """Test tracking across all available revisions."""
        result = tracker.track()

        # Should have data for all revisions
        assert len(result) > 0
        revisions = result["revision"].unique()
        assert len(revisions) >= 3  # At least 3 revisions in fixtures

    def test_lifetime_calculation(self, tracker):
        """Test lifetime calculation across revisions."""
        result = tracker.track(
            start_date=datetime(2025, 1, 1, 10, 0, 0), end_date=datetime(2025, 1, 1, 12, 0, 0)
        )

        # block_a survives through rev1, rev2, rev3 (as block_a, block_a2, block_a3)
        # Find block_a in rev1
        rev1_blocks = result[result["revision"] == "20250101_100000_hash1"]
        block_a = rev1_blocks[rev1_blocks["block_id"] == "block_a"]

        if len(block_a) > 0:
            # Should have lifetime_revisions >= 1
            assert block_a.iloc[0]["lifetime_revisions"] >= 1

    def test_lifetime_days_calculation(self, tracker):
        """Test lifetime days calculation."""
        result = tracker.track(
            start_date=datetime(2025, 1, 1, 10, 0, 0), end_date=datetime(2025, 1, 1, 12, 0, 0)
        )

        # Lifetime days should be calculated between revisions
        # Rev1 to Rev3 is 2 hours = 0 days (same day)
        assert "lifetime_days" in result.columns
        # At least one block should have lifetime_days >= 0
        assert (result["lifetime_days"] >= 0).any()


class TestMethodTrackerCloneTracking:
    """Test clone group membership tracking."""

    @pytest.fixture
    def sample_revisions_dir(self):
        """Path to sample revisions fixture directory."""
        return Path(__file__).parent.parent / "fixtures" / "sample_revisions"

    @pytest.fixture
    def tracker(self, sample_revisions_dir):
        """Create MethodTracker instance."""
        return MethodTracker(data_dir=sample_revisions_dir, similarity_threshold=70)

    def test_clone_count_calculation(self, tracker):
        """Test clone count calculation."""
        result = tracker.track(
            start_date=datetime(2025, 1, 1, 10, 0, 0), end_date=datetime(2025, 1, 1, 11, 0, 0)
        )

        # In rev1, block_a and block_b are clones (similarity 75%)
        rev1_blocks = result[result["revision"] == "20250101_100000_hash1"]
        cloned_blocks = rev1_blocks[rev1_blocks["clone_count"] > 0]
        assert len(cloned_blocks) > 0

    def test_clone_group_id_assigned(self, tracker):
        """Test that clone_group_id is assigned to cloned methods."""
        result = tracker.track(
            start_date=datetime(2025, 1, 1, 10, 0, 0), end_date=datetime(2025, 1, 1, 11, 0, 0)
        )

        # Methods in clone groups should have clone_group_id
        cloned = result[result["clone_count"] > 0]
        if len(cloned) > 0:
            assert cloned["clone_group_id"].notna().all()

    def test_clone_group_size(self, tracker):
        """Test clone_group_size calculation."""
        result = tracker.track(
            start_date=datetime(2025, 1, 1, 10, 0, 0), end_date=datetime(2025, 1, 1, 11, 0, 0)
        )

        # Clone group size should match clone count + 1
        cloned = result[result["clone_count"] > 0]
        if len(cloned) > 0:
            assert (cloned["clone_group_size"] == cloned["clone_count"] + 1).all()


class TestMethodTrackerDataTypes:
    """Test data types and formats."""

    @pytest.fixture
    def sample_revisions_dir(self):
        """Path to sample revisions fixture directory."""
        return Path(__file__).parent.parent / "fixtures" / "sample_revisions"

    @pytest.fixture
    def tracker(self, sample_revisions_dir):
        """Create MethodTracker instance."""
        return MethodTracker(data_dir=sample_revisions_dir, similarity_threshold=70)

    def test_output_data_types(self, tracker):
        """Test that output DataFrame has correct data types."""
        result = tracker.track()

        # String columns
        assert result["revision"].dtype == "object"
        assert result["block_id"].dtype == "object"
        assert result["function_name"].dtype == "object"
        assert result["file_path"].dtype == "object"
        assert result["state"].dtype == "object"
        assert result["state_detail"].dtype == "object"

        # Integer columns
        assert pd.api.types.is_integer_dtype(result["start_line"])
        assert pd.api.types.is_integer_dtype(result["end_line"])
        assert pd.api.types.is_integer_dtype(result["loc"])
        assert pd.api.types.is_integer_dtype(result["clone_count"])
        assert pd.api.types.is_integer_dtype(result["clone_group_size"])
        assert pd.api.types.is_integer_dtype(result["lifetime_revisions"])
        assert pd.api.types.is_integer_dtype(result["lifetime_days"])

    def test_match_type_values(self, tracker):
        """Test that match_type contains valid values."""
        result = tracker.track()

        valid_match_types = [
            "name_based",
            "token_hash",
            "moved",
            "renamed",
            "moved_and_renamed",
            "similarity",
            "similarity_moved",
            "similarity_renamed",
            "similarity_moved_and_renamed",
            "none",
            None,
        ]
        # Allow NaN values which represent None
        assert (
            result["match_type"].isna().all() or result["match_type"].isin(valid_match_types).all()
        )

    def test_state_values(self, tracker):
        """Test that state contains valid values."""
        result = tracker.track()

        valid_states = ["deleted", "survived", "added"]
        assert result["state"].isin(valid_states).all()


class TestMethodTrackerEdgeCases:
    """Test edge cases."""

    @pytest.fixture
    def sample_revisions_dir(self):
        """Path to sample revisions fixture directory."""
        return Path(__file__).parent.parent / "fixtures" / "sample_revisions"

    def test_empty_date_range(self, sample_revisions_dir):
        """Test with date range that has no revisions."""
        tracker = MethodTracker(data_dir=sample_revisions_dir, similarity_threshold=70)
        result = tracker.track(
            start_date=datetime(2024, 1, 1, 0, 0, 0), end_date=datetime(2024, 1, 1, 23, 59, 59)
        )

        # Should return empty DataFrame with correct columns
        assert len(result) == 0
        assert isinstance(result, pd.DataFrame)

    def test_single_revision(self, sample_revisions_dir):
        """Test with only one revision (no pairs to compare)."""
        tracker = MethodTracker(data_dir=sample_revisions_dir, similarity_threshold=70)
        result = tracker.track(
            start_date=datetime(2025, 1, 1, 10, 0, 0), end_date=datetime(2025, 1, 1, 10, 0, 0)
        )

        # Should have data for first revision only, all as "added"
        if len(result) > 0:
            assert (result["state"] == "added").all()

    def test_high_similarity_threshold(self, sample_revisions_dir):
        """Test with very high similarity threshold."""
        tracker = MethodTracker(data_dir=sample_revisions_dir, similarity_threshold=95)
        result = tracker.track(
            start_date=datetime(2025, 1, 1, 10, 0, 0), end_date=datetime(2025, 1, 1, 11, 0, 0)
        )

        # Should still work, but fewer matches
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0


class TestMethodTrackingResultDataclass:
    """Test MethodTrackingResult dataclass."""

    def test_dataclass_creation(self):
        """Test creating MethodTrackingResult instance."""
        result = MethodTrackingResult(
            revision="20250101_100000_hash1",
            block_id="block_a",
            function_name="calculate",
            file_path="src/main.py",
            start_line=10,
            end_line=20,
            loc=11,
            state="survived",
            state_detail="survived_unchanged",
            matched_block_id="block_a2",
            match_type="token_hash",
            match_similarity=None,
            clone_count=1,
            clone_group_id="group_1",
            clone_group_size=2,
            lifetime_revisions=2,
            lifetime_days=0,
        )

        assert result.revision == "20250101_100000_hash1"
        assert result.block_id == "block_a"
        assert result.function_name == "calculate"
        assert result.state == "survived"
        assert result.lifetime_revisions == 2
