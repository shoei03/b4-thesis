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
        df = pd.DataFrame(
            {
                "global_block_id": ["id1", "id1", "id2", "id2"],
                "revision": ["rev1", "rev2", "rev1", "rev2"],
                "state": ["survived", "deleted", "survived", "survived"],
            }
        )

        labels = generator.generate_labels(df)

        assert len(labels) == 4
        assert labels.iloc[0]  # id1 deleted in next revision
        assert not labels.iloc[1]  # id1 last revision
        assert not labels.iloc[2]  # id2 survives in next revision
        assert not labels.iloc[3]  # id2 last revision

    def test_generate_labels_all_survive(self, generator):
        """Test label generation when all methods survive."""
        df = pd.DataFrame(
            {
                "global_block_id": ["id1", "id1", "id1"],
                "revision": ["rev1", "rev2", "rev3"],
                "state": ["survived", "survived", "survived"],
            }
        )

        labels = generator.generate_labels(df)

        assert len(labels) == 3
        assert all(label is False for label in labels)

    def test_generate_labels_immediate_deletion(self, generator):
        """Test label generation when method is added then deleted."""
        df = pd.DataFrame(
            {
                "global_block_id": ["id1", "id1"],
                "revision": ["rev1", "rev2"],
                "state": ["added", "deleted"],
            }
        )

        labels = generator.generate_labels(df)

        assert len(labels) == 2
        assert labels.iloc[0]  # Deleted in next revision
        assert not labels.iloc[1]  # Last revision

    def test_generate_labels_missing_columns(self, generator):
        """Test error handling for missing required columns."""
        df = pd.DataFrame({"global_block_id": ["id1"], "revision": ["rev1"]})

        with pytest.raises(ValueError, match="Missing required columns"):
            generator.generate_labels(df)

    def test_generate_labels_multiple_blocks(self, generator):
        """Test label generation with multiple independent blocks."""
        df = pd.DataFrame(
            {
                "global_block_id": ["id1", "id1", "id2", "id2", "id3", "id3"],
                "revision": ["rev1", "rev2", "rev1", "rev2", "rev1", "rev2"],
                "state": [
                    "survived",
                    "deleted",
                    "survived",
                    "survived",
                    "added",
                    "deleted",
                ],
            }
        )

        labels = generator.generate_labels(df)

        assert len(labels) == 6
        assert labels.iloc[0]  # id1 deleted next
        assert not labels.iloc[1]  # id1 last
        assert not labels.iloc[2]  # id2 survives next
        assert not labels.iloc[3]  # id2 last
        assert labels.iloc[4]  # id3 deleted next
        assert not labels.iloc[5]  # id3 last

    def test_generate_labels_preserves_order(self, generator):
        """Test that labels are aligned with original DataFrame order."""
        # Create DataFrame with non-sorted order
        df = pd.DataFrame(
            {
                "global_block_id": ["id2", "id1", "id2", "id1"],
                "revision": ["rev1", "rev1", "rev2", "rev2"],
                "state": ["survived", "survived", "survived", "deleted"],
            }
        )

        labels = generator.generate_labels(df)

        # Check that labels are correctly aligned with original rows
        assert len(labels) == 4
        # id2/rev1 should be False (survives to rev2)
        assert not labels.iloc[0]
        # id1/rev1 should be True (deleted in rev2)
        assert labels.iloc[1]
        # id2/rev2 should be False (last revision)
        assert not labels.iloc[2]
        # id1/rev2 should be False (last revision)
        assert not labels.iloc[3]
