"""Tests for LabelGenerator."""

import pandas as pd
import pytest

from b4_thesis.analysis.deletion_prediction.label_generator import LabelGenerator


class TestLabelGenerator:
    """Test cases for LabelGenerator with lookahead_window=1 (legacy behavior)."""

    @pytest.fixture
    def generator(self):
        """Create LabelGenerator instance with lookahead_window=1."""
        return LabelGenerator(lookahead_window=1)

    def test_generate_labels_basic(self, generator):
        """Test basic label generation."""
        # id1 exists in rev1, deleted in rev2
        # id2 exists in both rev1 and rev2 (survives)
        df = pd.DataFrame(
            {
                "global_block_id": ["id1", "id2", "id2"],
                "revision": ["rev1", "rev1", "rev2"],
                "state": ["added", "added", "modified"],
            }
        )
        deleted_df = pd.DataFrame(
            {
                "global_block_id": ["id1"],
                "revision": ["rev2"],
                "state": ["deleted"],
            }
        )

        labels = generator.generate_labels(df, deleted_df)

        assert len(labels) == 3
        assert labels.iloc[0]  # id1 deleted in next revision
        assert not labels.iloc[1]  # id2 survives in next revision
        assert not labels.iloc[2]  # id2 in last revision

    def test_generate_labels_all_survive(self, generator):
        """Test label generation when all methods survive."""
        # id1 exists in all revisions (survives throughout)
        df = pd.DataFrame(
            {
                "global_block_id": ["id1", "id1", "id1"],
                "revision": ["rev1", "rev2", "rev3"],
                "state": ["added", "modified", "modified"],
            }
        )
        # No deleted records
        deleted_df = pd.DataFrame(
            {"global_block_id": [], "revision": [], "state": []}
        )

        labels = generator.generate_labels(df, deleted_df)

        assert len(labels) == 3
        assert all(label is False for label in labels)

    def test_generate_labels_immediate_deletion(self, generator):
        """Test label generation when method is added then deleted."""
        # id1 exists only in rev1 (deleted in rev2)
        df = pd.DataFrame(
            {
                "global_block_id": ["id1"],
                "revision": ["rev1"],
                "state": ["added"],
            }
        )
        deleted_df = pd.DataFrame(
            {
                "global_block_id": ["id1"],
                "revision": ["rev2"],
                "state": ["deleted"],
            }
        )

        labels = generator.generate_labels(df, deleted_df)

        assert len(labels) == 1
        assert labels.iloc[0]  # Deleted in next revision

    def test_generate_labels_missing_columns(self, generator):
        """Test error handling for missing required columns."""
        # Missing revision and state columns
        df = pd.DataFrame({"global_block_id": ["id1"]})
        deleted_df = pd.DataFrame(
            {"global_block_id": [], "revision": [], "state": []}
        )

        with pytest.raises(ValueError, match="missing required columns"):
            generator.generate_labels(df, deleted_df)

    def test_generate_labels_multiple_blocks(self, generator):
        """Test label generation with multiple independent blocks."""
        # id1: exists only in rev1 (deleted in rev2)
        # id2: exists in rev1 and rev2 (survives)
        # id3: exists only in rev1 (deleted in rev2)
        df = pd.DataFrame(
            {
                "global_block_id": ["id1", "id2", "id2", "id3"],
                "revision": ["rev1", "rev1", "rev2", "rev1"],
                "state": ["added", "added", "modified", "added"],
            }
        )
        deleted_df = pd.DataFrame(
            {
                "global_block_id": ["id1", "id3"],
                "revision": ["rev2", "rev2"],
                "state": ["deleted", "deleted"],
            }
        )

        labels = generator.generate_labels(df, deleted_df)

        assert len(labels) == 4
        assert labels.iloc[0]  # id1 deleted in rev2
        assert not labels.iloc[1]  # id2 survives to rev2
        assert not labels.iloc[2]  # id2 in last revision
        assert labels.iloc[3]  # id3 deleted in rev2

    def test_generate_labels_preserves_order(self, generator):
        """Test that labels are aligned with original DataFrame order."""
        # Create DataFrame with non-sorted order
        # id1 exists only in rev1 (deleted in rev2)
        # id2 exists in rev1 and rev2 (survives)
        df = pd.DataFrame(
            {
                "global_block_id": ["id2", "id1", "id2"],
                "revision": ["rev1", "rev1", "rev2"],
                "state": ["added", "added", "modified"],
            }
        )
        deleted_df = pd.DataFrame(
            {
                "global_block_id": ["id1"],
                "revision": ["rev2"],
                "state": ["deleted"],
            }
        )

        labels = generator.generate_labels(df, deleted_df)

        # Check that labels are correctly aligned with original rows
        assert len(labels) == 3
        # id2/rev1 should be False (survives to rev2)
        assert not labels.iloc[0]
        # id1/rev1 should be True (deleted in rev2)
        assert labels.iloc[1]
        # id2/rev2 should be False (last revision)
        assert not labels.iloc[2]


class TestLabelGeneratorWithLookahead:
    """Test cases for LabelGenerator with various lookahead windows."""

    def test_lookahead_default_value(self):
        """Test that default lookahead_window is 5."""
        generator = LabelGenerator()
        assert generator.lookahead_window == 5

    def test_lookahead_invalid_value(self):
        """Test error handling for invalid lookahead_window values."""
        with pytest.raises(ValueError, match="lookahead_window must be >= 1"):
            LabelGenerator(lookahead_window=0)

        with pytest.raises(ValueError, match="lookahead_window must be >= 1"):
            LabelGenerator(lookahead_window=-1)

    def test_lookahead_window_2(self):
        """Test deletion detection within 2 revisions."""
        # id1: exists in rev1 only, deleted in rev2
        # id2: exists in rev1 and rev2, deleted in rev3
        # id3: exists in all revisions (survives)
        df = pd.DataFrame(
            {
                "global_block_id": ["id1", "id2", "id2", "id3", "id3", "id3"],
                "revision": ["rev1", "rev1", "rev2", "rev1", "rev2", "rev3"],
                "state": ["added", "added", "modified", "added", "modified", "modified"],
            }
        )
        deleted_df = pd.DataFrame(
            {
                "global_block_id": ["id1", "id2"],
                "revision": ["rev2", "rev3"],
                "state": ["deleted", "deleted"],
            }
        )

        generator = LabelGenerator(lookahead_window=2)
        labels = generator.generate_labels(df, deleted_df)

        assert len(labels) == 6
        # id1/rev1: deleted in rev2 (within window) -> True
        assert labels.iloc[0]
        # id2/rev1: survives to rev2, deleted in rev3 (within window) -> True
        assert labels.iloc[1]
        # id2/rev2: deleted in rev3 (only 1 future revision to check) -> True
        assert labels.iloc[2]
        # id3/rev1: survives (no deletion in rev2 or rev3) -> False
        assert not labels.iloc[3]
        # id3/rev2: survives to rev3 -> False
        assert not labels.iloc[4]
        # id3/rev3: last revision -> False
        assert not labels.iloc[5]

    def test_lookahead_window_3(self):
        """Test deletion detection within 3 revisions."""
        # id1: exists in rev1, rev2, deleted in rev3
        # id2: exists in all revisions (rev1, rev2, rev3)
        df = pd.DataFrame(
            {
                "global_block_id": ["id1", "id1", "id2", "id2", "id2"],
                "revision": ["rev1", "rev2", "rev1", "rev2", "rev3"],
                "state": ["added", "modified", "added", "modified", "modified"],
            }
        )
        deleted_df = pd.DataFrame(
            {
                "global_block_id": ["id1"],
                "revision": ["rev3"],
                "state": ["deleted"],
            }
        )

        generator = LabelGenerator(lookahead_window=3)
        labels = generator.generate_labels(df, deleted_df)

        assert len(labels) == 5
        # id1/rev1: deleted in rev3 (within window of 3) -> True
        assert labels.iloc[0]
        # id1/rev2: deleted in rev3 (only 1 future revision to check) -> True
        assert labels.iloc[1]
        # id2/rev1: survives to rev2 and rev3 -> False
        assert not labels.iloc[2]
        # id2/rev2: survives to rev3 -> False
        assert not labels.iloc[3]
        # id2/rev3: last revision -> False
        assert not labels.iloc[4]

    def test_survives_lookahead(self):
        """Test that methods surviving all lookahead revisions are labeled False."""
        # id1 exists in all 6 revisions (survives throughout)
        df = pd.DataFrame(
            {
                "global_block_id": ["id1"] * 6,
                "revision": ["rev1", "rev2", "rev3", "rev4", "rev5", "rev6"],
                "state": ["added"] + ["modified"] * 5,
            }
        )
        # No deletions
        deleted_df = pd.DataFrame(
            {"global_block_id": [], "revision": [], "state": []}
        )

        generator = LabelGenerator(lookahead_window=5)
        labels = generator.generate_labels(df, deleted_df)

        # All should be False (survives in all future revisions within lookahead)
        assert len(labels) == 6
        assert all(label is False for label in labels)

    def test_lookahead_exceeds_available_revisions(self):
        """Test edge case where lookahead exceeds available future revisions."""
        # Only 3 revisions total, but lookahead=10
        # id1: exists in rev1, deleted in rev2
        # id2: exists in rev1, rev2, deleted in rev3
        # id3: exists in all revisions
        df = pd.DataFrame(
            {
                "global_block_id": ["id1", "id2", "id2", "id3", "id3", "id3"],
                "revision": ["rev1", "rev1", "rev2", "rev1", "rev2", "rev3"],
                "state": ["added", "added", "modified", "added", "modified", "modified"],
            }
        )
        deleted_df = pd.DataFrame(
            {
                "global_block_id": ["id1", "id2"],
                "revision": ["rev2", "rev3"],
                "state": ["deleted", "deleted"],
            }
        )

        generator = LabelGenerator(lookahead_window=10)
        labels = generator.generate_labels(df, deleted_df)

        assert len(labels) == 6
        # id1/rev1: deleted in rev2 (within window) -> True
        assert labels.iloc[0]
        # id2/rev1: deleted in rev3 (within window) -> True
        assert labels.iloc[1]
        # id2/rev2: deleted in rev3 (checks up to rev3) -> True
        assert labels.iloc[2]
        # id3/rev1: survives (no deletion) -> False
        assert not labels.iloc[3]
        # id3/rev2: survives to rev3 -> False
        assert not labels.iloc[4]
        # id3/rev3: last revision -> False
        assert not labels.iloc[5]

    def test_column_name_is_deleted_soon(self):
        """Test that output column name is 'is_deleted_soon'."""
        df = pd.DataFrame(
            {
                "global_block_id": ["id1", "id2"],
                "revision": ["rev1", "rev1"],
                "state": ["added", "added"],
            }
        )
        deleted_df = pd.DataFrame(
            {"global_block_id": [], "revision": [], "state": []}
        )

        generator = LabelGenerator(lookahead_window=5)
        labels = generator.generate_labels(df, deleted_df)

        assert labels.name == "is_deleted_soon"

    def test_lookahead_1_behaves_like_legacy(self):
        """Test that lookahead_window=1 matches legacy behavior."""
        # id1: deleted in next revision
        # id2: survives to next revision
        df = pd.DataFrame(
            {
                "global_block_id": ["id1", "id2", "id2"],
                "revision": ["rev1", "rev1", "rev2"],
                "state": ["added", "added", "modified"],
            }
        )
        deleted_df = pd.DataFrame(
            {
                "global_block_id": ["id1"],
                "revision": ["rev2"],
                "state": ["deleted"],
            }
        )

        generator_old = LabelGenerator(lookahead_window=1)
        labels_old = generator_old.generate_labels(df, deleted_df)

        # Verify legacy behavior
        assert labels_old.iloc[0]  # id1 deleted
        assert not labels_old.iloc[1]  # id2 survives
        assert not labels_old.iloc[2]  # last revision

        # Column name should still be is_deleted_soon even with lookahead=1
        assert labels_old.name == "is_deleted_soon"
