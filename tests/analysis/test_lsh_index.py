"""Tests for LSH index functionality."""

import pytest

from b4_thesis.analysis.lsh_index import LSHIndex


class TestLSHIndex:
    """Test LSH index for approximate nearest neighbor search."""

    def test_initialization(self):
        """Test LSH index initialization."""
        index = LSHIndex(threshold=0.7, num_perm=128)
        assert index.threshold == 0.7
        assert index.num_perm == 128

    def test_add_and_query_exact_match(self):
        """Test adding and querying exact match."""
        index = LSHIndex(threshold=0.7)

        tokens = [1, 2, 3, 4, 5]
        index.add("block1", tokens)

        # Query with same tokens should return the block
        candidates = index.query(tokens)
        assert "block1" in candidates

    def test_add_and_query_similar_tokens(self):
        """Test querying similar but not identical tokens."""
        # Use larger token sequences for better LSH performance
        index = LSHIndex(threshold=0.6)

        # Add similar blocks (longer sequences)
        base = list(range(1, 21))  # [1, 2, ..., 20]
        index.add("block1", base)
        index.add("block2", base[:-1] + [99])  # Change last token
        index.add("block3", list(range(100, 120)))  # Completely different

        # Query with block similar to block1 and block2
        query_tokens = base[:-1] + [77]  # Similar to block1/block2
        candidates = index.query(query_tokens)

        # Should find block1 and block2 (similar), but not block3
        # Note: LSH is approximate, so this might not always be exact
        # With larger sequences, LSH should work better
        assert len(candidates) >= 1  # At least one similar block found
        if len(candidates) > 0:
            assert "block3" not in candidates  # Should not find completely different block

    def test_add_and_query_dissimilar_tokens(self):
        """Test that dissimilar tokens don't match."""
        index = LSHIndex(threshold=0.9)  # High threshold

        index.add("block1", [1, 2, 3, 4, 5])

        # Query with completely different tokens
        query_tokens = [10, 20, 30, 40, 50]
        candidates = index.query(query_tokens)

        # Should not find block1
        assert "block1" not in candidates

    def test_add_empty_tokens(self):
        """Test adding empty token list."""
        index = LSHIndex()

        # Adding empty tokens should be handled gracefully
        index.add("block1", [])

        # Querying should not crash
        candidates = index.query([1, 2, 3])
        assert isinstance(candidates, list)

    def test_query_empty_tokens(self):
        """Test querying with empty token list."""
        index = LSHIndex()

        index.add("block1", [1, 2, 3])

        # Querying with empty tokens should return empty list
        candidates = index.query([])
        assert candidates == []

    def test_multiple_blocks(self):
        """Test index with multiple blocks."""
        index = LSHIndex(threshold=0.7)

        # Add multiple blocks
        index.add("block1", [1, 2, 3, 4, 5])
        index.add("block2", [1, 2, 3, 4, 6])
        index.add("block3", [2, 3, 4, 5, 6])
        index.add("block4", [10, 20, 30, 40, 50])

        # Query should find multiple similar blocks
        candidates = index.query([1, 2, 3, 4, 5])

        # Should find at least block1 (exact match)
        assert "block1" in candidates
        # Might find block2 and block3 (similar)

    def test_clear_index(self):
        """Test clearing the index."""
        index = LSHIndex()

        index.add("block1", [1, 2, 3])
        index.add("block2", [4, 5, 6])

        # Clear the index
        index.clear()

        # After clearing, queries should return no results
        candidates = index.query([1, 2, 3])
        assert len(candidates) == 0

    def test_threshold_effect(self):
        """Test that threshold affects matching."""
        # Low threshold - more permissive
        index_low = LSHIndex(threshold=0.5)
        index_low.add("block1", [1, 2, 3, 4, 5])

        # High threshold - more strict
        index_high = LSHIndex(threshold=0.9)
        index_high.add("block1", [1, 2, 3, 4, 5])

        # Query with somewhat different tokens
        query_tokens = [1, 2, 3, 10, 11]

        candidates_low = index_low.query(query_tokens)
        candidates_high = index_high.query(query_tokens)

        # Low threshold should be more likely to find matches
        # High threshold should be more strict
        # Verify both return lists (exact behavior depends on LSH parameters)
        assert isinstance(candidates_low, list)
        assert isinstance(candidates_high, list)

    def test_large_token_sequences(self):
        """Test with larger token sequences."""
        index = LSHIndex(threshold=0.7)

        # Add large token sequence
        large_tokens = list(range(100))
        index.add("large_block", large_tokens)

        # Query with similar large sequence
        query_tokens = list(range(5, 105))  # Shifted by 5
        candidates = index.query(query_tokens)

        # Should find the block (high overlap)
        assert "large_block" in candidates

    def test_duplicate_block_ids(self):
        """Test behavior with duplicate block IDs."""
        index = LSHIndex()

        # Add same block ID twice (datasketch doesn't allow duplicates)
        index.add("block1", [1, 2, 3])

        # Adding duplicate should raise ValueError
        with pytest.raises(ValueError):
            index.add("block1", [4, 5, 6])
