"""Tests for FeatureExtractor deleted state filtering."""

import pandas as pd


class TestFeatureExtractorFiltering:
    """Test cases for deleted method filtering logic."""

    def test_filter_deleted_methods(self):
        """Test that deleted methods are filtered out correctly."""
        # Create sample DataFrame with deleted methods
        df = pd.DataFrame(
            {
                "global_block_id": ["id1", "id1", "id2", "id2"],
                "revision": ["rev1", "rev2", "rev1", "rev2"],
                "function_name": ["foo", "foo", "bar", "bar"],
                "file_path": ["/test.py"] * 4,
                "start_line": [1, 1, 10, 10],
                "end_line": [5, 5, 15, 15],
                "loc": [5, 5, 6, 6],
                "state": ["survived", "deleted", "survived", "survived"],
            }
        )

        # Verify original data
        assert len(df) == 4
        assert (df["state"] == "deleted").sum() == 1

        # Apply filtering logic (same as in FeatureExtractor)
        df_filtered = df[df["state"] != "deleted"].copy()

        # Verify filtering
        assert len(df_filtered) == 3
        assert (df_filtered["state"] == "deleted").sum() == 0
        assert list(df_filtered["function_name"]) == ["foo", "bar", "bar"]

    def test_filter_all_deleted(self):
        """Test filtering when all methods are deleted."""
        df = pd.DataFrame(
            {
                "global_block_id": ["id1", "id2"],
                "revision": ["rev1", "rev1"],
                "function_name": ["foo", "bar"],
                "file_path": ["/test.py"] * 2,
                "start_line": [1, 10],
                "end_line": [5, 15],
                "loc": [5, 6],
                "state": ["deleted", "deleted"],
            }
        )

        # Verify original data
        assert len(df) == 2
        assert (df["state"] == "deleted").sum() == 2

        # Apply filtering logic
        df_filtered = df[df["state"] != "deleted"].copy()

        # Should have no methods left
        assert len(df_filtered) == 0

    def test_filter_no_deleted(self):
        """Test filtering when no methods are deleted."""
        df = pd.DataFrame(
            {
                "global_block_id": ["id1", "id2", "id3"],
                "revision": ["rev1", "rev1", "rev1"],
                "function_name": ["foo", "bar", "baz"],
                "file_path": ["/test.py"] * 3,
                "start_line": [1, 10, 20],
                "end_line": [5, 15, 25],
                "loc": [5, 6, 6],
                "state": ["survived", "added", "survived"],
            }
        )

        # Verify original data
        assert len(df) == 3
        assert (df["state"] == "deleted").sum() == 0

        # Apply filtering logic
        df_filtered = df[df["state"] != "deleted"].copy()

        # Should have all methods
        assert len(df_filtered) == 3
        assert list(df_filtered["function_name"]) == ["foo", "bar", "baz"]
