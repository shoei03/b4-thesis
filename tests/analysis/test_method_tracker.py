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
        assert pd.isna(
            block_c_deleted.iloc[0]["matched_block_id"]
        ), "Deleted block should have no match"

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

        valid_match_types = ["token_hash", "similarity", "none", None]
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


class TestMethodTrackerLineage:
    """Test lineage format conversion functionality."""

    @pytest.fixture
    def sample_revisions_dir(self):
        """Path to sample revisions fixture directory."""
        return Path(__file__).parent.parent / "fixtures" / "sample_revisions"

    @pytest.fixture
    def tracker(self, sample_revisions_dir):
        """Create MethodTracker instance."""
        return MethodTracker(data_dir=sample_revisions_dir, similarity_threshold=70)

    def test_to_lineage_format_columns(self, tracker):
        """Test that lineage format has correct columns (16 total)."""
        tracker.track()
        lineage_df = tracker.to_lineage_format()

        # Should have 16 columns (17 - block_id - matched_block_id + global_block_id)
        assert len(lineage_df.columns) == 16

        # Should have global_block_id
        assert "global_block_id" in lineage_df.columns

        # Should NOT have block_id or matched_block_id
        assert "block_id" not in lineage_df.columns
        assert "matched_block_id" not in lineage_df.columns

        # Should have all other columns
        required_columns = [
            "global_block_id",
            "revision",
            "function_name",
            "file_path",
            "start_line",
            "end_line",
            "loc",
            "state",
            "state_detail",
            "match_type",
            "match_similarity",
            "clone_count",
            "clone_group_id",
            "clone_group_size",
            "lifetime_revisions",
            "lifetime_days",
        ]
        for col in required_columns:
            assert col in lineage_df.columns, f"Missing column: {col}"

    def test_global_block_id_consistency(self, tracker):
        """Test that same lineage has same global_block_id across revisions."""
        # Track first two revisions (block_a -> block_a2)
        tracker.track(
            start_date=datetime(2025, 1, 1, 10, 0, 0), end_date=datetime(2025, 1, 1, 11, 0, 0)
        )
        lineage_df = tracker.to_lineage_format()

        # Get block_a from rev1 and block_a2 from rev2 (they should match)
        rev1_blocks = lineage_df[lineage_df["revision"] == "20250101_100000_hash1"]
        rev2_blocks = lineage_df[lineage_df["revision"] == "20250101_110000_hash2"]

        # Find survived block in rev2
        survived = rev2_blocks[rev2_blocks["state"] == "survived"]

        if len(survived) > 0:
            # Get first survived block's global_block_id
            survived_global_id = survived.iloc[0]["global_block_id"]

            # Check if this global_block_id exists in rev1
            rev1_matching = rev1_blocks[rev1_blocks["global_block_id"] == survived_global_id]
            assert (
                len(rev1_matching) > 0
            ), "Survived block should have same global_block_id as predecessor"

    def test_global_block_id_first_revision(self, tracker):
        """Test that first revision's global_block_id equals original block_id."""
        tracking_df = tracker.track(
            start_date=datetime(2025, 1, 1, 10, 0, 0), end_date=datetime(2025, 1, 1, 10, 30, 0)
        )
        lineage_df = tracker.to_lineage_format()

        # In first revision, global_block_id should equal block_id
        first_rev_tracking = tracking_df[tracking_df["revision"] == "20250101_100000_hash1"]
        first_rev_lineage = lineage_df[lineage_df["revision"] == "20250101_100000_hash1"]

        for idx, tracking_row in first_rev_tracking.iterrows():
            block_id = tracking_row["block_id"]
            func_name = tracking_row["function_name"]
            lineage_row = first_rev_lineage[first_rev_lineage["function_name"] == func_name]
            if len(lineage_row) > 0:
                assert lineage_row.iloc[0]["global_block_id"] == block_id

    def test_global_block_id_survived_method(self, tracker):
        """Test that survived methods inherit global_block_id."""
        tracking_df = tracker.track(
            start_date=datetime(2025, 1, 1, 10, 0, 0), end_date=datetime(2025, 1, 1, 11, 0, 0)
        )
        lineage_df = tracker.to_lineage_format()

        # Find a survived block in rev2
        rev2_tracking = tracking_df[tracking_df["revision"] == "20250101_110000_hash2"]
        survived = rev2_tracking[rev2_tracking["state"] == "survived"]

        if len(survived) > 0:
            survived_row = survived.iloc[0]
            matched_block_id = survived_row["matched_block_id"]

            # Get global_block_id of the matched block in rev1
            rev1_tracking = tracking_df[
                (tracking_df["revision"] == "20250101_100000_hash1")
                & (tracking_df["block_id"] == matched_block_id)
            ]

            if len(rev1_tracking) > 0:
                # Get global_block_id from lineage format
                rev1_lineage = lineage_df[
                    (lineage_df["revision"] == "20250101_100000_hash1")
                    & (lineage_df["function_name"] == rev1_tracking.iloc[0]["function_name"])
                ]
                rev2_lineage = lineage_df[
                    (lineage_df["revision"] == "20250101_110000_hash2")
                    & (lineage_df["function_name"] == survived_row["function_name"])
                ]

                if len(rev1_lineage) > 0 and len(rev2_lineage) > 0:
                    rev1_global = rev1_lineage.iloc[0]["global_block_id"]
                    rev2_global = rev2_lineage.iloc[0]["global_block_id"]
                    assert rev1_global == rev2_global

    def test_global_block_id_added_method(self, tracker):
        """Test that newly added methods get new global_block_id."""
        tracking_df = tracker.track(
            start_date=datetime(2025, 1, 1, 10, 0, 0), end_date=datetime(2025, 1, 1, 11, 0, 0)
        )
        lineage_df = tracker.to_lineage_format()

        # Find added blocks in rev2
        rev2_tracking = tracking_df[tracking_df["revision"] == "20250101_110000_hash2"]
        added = rev2_tracking[rev2_tracking["state"] == "added"]

        if len(added) > 0:
            # Get their global_block_ids from lineage format
            for _, added_row in added.iterrows():
                lineage_row = lineage_df[
                    (lineage_df["revision"] == "20250101_110000_hash2")
                    & (lineage_df["function_name"] == added_row["function_name"])
                ]
                assert len(lineage_row) > 0
                # For added methods, global_block_id should be set (not None)
                assert lineage_row.iloc[0]["global_block_id"] is not None

    def test_global_block_id_deleted_method(self, tracker):
        """Test that deleted methods retain their global_block_id in lineage format."""
        tracking_df = tracker.track(
            start_date=datetime(2025, 1, 1, 10, 0, 0), end_date=datetime(2025, 1, 1, 11, 0, 0)
        )
        lineage_df = tracker.to_lineage_format()

        # Find deleted blocks in rev2 (block_c should be deleted)
        rev2_tracking = tracking_df[tracking_df["revision"] == "20250101_110000_hash2"]
        deleted = rev2_tracking[rev2_tracking["state"] == "deleted"]

        assert len(deleted) > 0, "Expected to find deleted methods"

        # Verify block_c is deleted and has a global_block_id
        block_c_deleted = deleted[deleted["block_id"] == "block_c"]
        assert len(block_c_deleted) == 1, "block_c should be deleted"

        # Check lineage format for block_c in rev2
        rev2_lineage = lineage_df[lineage_df["revision"] == "20250101_110000_hash2"]
        block_c_lineage = rev2_lineage[rev2_lineage["function_name"] == "compute"]

        assert len(block_c_lineage) == 1, "block_c should appear in lineage format"
        assert (
            block_c_lineage.iloc[0]["global_block_id"] == "block_c"
        ), "Deleted method should retain its original global_block_id"

        # Verify that block_c in rev1 has the same global_block_id
        rev1_lineage = lineage_df[lineage_df["revision"] == "20250101_100000_hash1"]
        block_c_rev1 = rev1_lineage[rev1_lineage["function_name"] == "compute"]
        assert len(block_c_rev1) == 1
        assert (
            block_c_rev1.iloc[0]["global_block_id"] == block_c_lineage.iloc[0]["global_block_id"]
        ), "Same method should have same global_block_id across revisions"

    def test_lineage_format_no_matched_block_id(self, tracker):
        """Test that lineage format does not contain matched_block_id column."""
        tracker.track()
        lineage_df = tracker.to_lineage_format()

        assert "matched_block_id" not in lineage_df.columns

    def test_tracking_format_unchanged(self, tracker):
        """Test that tracking format has 17 columns with block_id and matched_block_id."""
        tracker.track()
        tracking_df = tracker.to_tracking_format()

        # Should have 17 columns
        assert len(tracking_df.columns) == 17

        # Should have block_id and matched_block_id
        assert "block_id" in tracking_df.columns
        assert "matched_block_id" in tracking_df.columns

        # Should NOT have global_block_id
        assert "global_block_id" not in tracking_df.columns

    def test_to_lineage_format_before_track(self, tracker):
        """Test that calling to_lineage_format() before track() raises error."""
        error_msg = "Must call track\\(\\) before to_lineage_format\\(\\)"
        with pytest.raises(RuntimeError, match=error_msg):
            tracker.to_lineage_format()

    def test_to_tracking_format_before_track(self, tracker):
        """Test that calling to_tracking_format() before track() raises error."""
        error_msg = "Must call track\\(\\) before to_tracking_format\\(\\)"
        with pytest.raises(RuntimeError, match=error_msg):
            tracker.to_tracking_format()
