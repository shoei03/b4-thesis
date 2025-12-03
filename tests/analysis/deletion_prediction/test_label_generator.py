"""Tests for LabelGenerator."""

import pandas as pd
import pytest

from b4_thesis.analysis.deletion_prediction.label_generator import LabelGenerator


class TestLabelGenerator:
    """Test cases for LabelGenerator."""

    @pytest.fixture
    def generator(self):
        """Create LabelGenerator instance."""
        return LabelGenerator()

    def test_generate_labels_basic(self, generator):
        """Test basic label generation."""
        # id1 exists only in rev1 (deleted in rev2)
        # id2 exists in both rev1 and rev2 (survives)
        df = pd.DataFrame(
            {
                "global_block_id": ["id1", "id2", "id2"],
                "revision": ["rev1", "rev1", "rev2"],
            }
        )

        labels = generator.generate_labels(df)

        assert len(labels) == 3
        assert labels.iloc[0]  # id1 deleted in next revision (not in rev2)
        assert not labels.iloc[1]  # id2 survives in next revision (exists in rev2)
        assert not labels.iloc[2]  # id2 in last revision

    def test_generate_labels_all_survive(self, generator):
        """Test label generation when all methods survive."""
        # id1 exists in all revisions (survives throughout)
        df = pd.DataFrame(
            {
                "global_block_id": ["id1", "id1", "id1"],
                "revision": ["rev1", "rev2", "rev3"],
            }
        )

        labels = generator.generate_labels(df)

        assert len(labels) == 3
        assert all(label is False for label in labels)

    def test_generate_labels_immediate_deletion(self, generator):
        """Test label generation when method is added then deleted."""
        # id1 exists only in rev1 (deleted before rev2)
        df = pd.DataFrame(
            {
                "global_block_id": ["id1"],
                "revision": ["rev1"],
            }
        )

        labels = generator.generate_labels(df)

        assert len(labels) == 1
        assert not labels.iloc[0]  # Last revision (cannot determine if deleted)

    def test_generate_labels_missing_columns(self, generator):
        """Test error handling for missing required columns."""
        # Missing revision column
        df = pd.DataFrame({"global_block_id": ["id1"]})

        with pytest.raises(ValueError, match="Missing required columns"):
            generator.generate_labels(df)

    def test_generate_labels_multiple_blocks(self, generator):
        """Test label generation with multiple independent blocks."""
        # id1: exists only in rev1 (deleted)
        # id2: exists in rev1 and rev2 (survives)
        # id3: exists only in rev1 (deleted)
        df = pd.DataFrame(
            {
                "global_block_id": ["id1", "id2", "id2", "id3"],
                "revision": ["rev1", "rev1", "rev2", "rev1"],
            }
        )

        labels = generator.generate_labels(df)

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
            }
        )

        labels = generator.generate_labels(df)

        # Check that labels are correctly aligned with original rows
        assert len(labels) == 3
        # id2/rev1 should be False (survives to rev2)
        assert not labels.iloc[0]
        # id1/rev1 should be True (deleted in rev2)
        assert labels.iloc[1]
        # id2/rev2 should be False (last revision)
        assert not labels.iloc[2]
