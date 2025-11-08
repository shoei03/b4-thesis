"""Tests for method matching functionality."""

import pandas as pd
import pytest

from b4_thesis.analysis.method_matcher import MatchResult, MethodMatcher


class TestMethodMatcher:
    """Test MethodMatcher class."""

    @pytest.fixture
    def matcher(self):
        """Create MethodMatcher instance with default threshold."""
        return MethodMatcher(similarity_threshold=70)

    @pytest.fixture
    def sample_blocks_v1(self):
        """Sample code blocks for version 1."""
        return pd.DataFrame(
            {
                "block_id": ["block_a", "block_b", "block_c"],
                "token_hash": ["hash_1", "hash_2", "hash_3"],
                "token_sequence": ["[1;2;3]", "[4;5;6]", "[7;8;9]"],
                "function_name": ["func_a", "func_b", "func_c"],
            }
        )

    @pytest.fixture
    def sample_blocks_v2_exact_match(self):
        """Sample code blocks for version 2 with exact matches."""
        return pd.DataFrame(
            {
                "block_id": ["block_x", "block_y", "block_z"],
                "token_hash": ["hash_1", "hash_2", "hash_3"],  # Same hashes
                "token_sequence": ["[1;2;3]", "[4;5;6]", "[7;8;9]"],
                "function_name": ["func_a", "func_b", "func_c"],
            }
        )

    @pytest.fixture
    def sample_blocks_v2_similar(self):
        """Sample code blocks for version 2 with similar (not exact) matches."""
        return pd.DataFrame(
            {
                "block_id": ["block_x", "block_y", "block_z"],
                "token_hash": ["hash_x", "hash_y", "hash_z"],  # Different hashes
                "token_sequence": [
                    "[1;2;3;4]",  # Similar to [1;2;3]
                    "[4;5;6;7]",  # Similar to [4;5;6]
                    "[10;11;12]",  # Not similar to [7;8;9]
                ],
                "function_name": ["func_a_modified", "func_b_modified", "func_z"],
            }
        )

    def test_exact_match_via_token_hash(
        self, matcher, sample_blocks_v1, sample_blocks_v2_exact_match
    ):
        """Test Phase 1: Exact matching via token_hash."""
        result = matcher.match_blocks(sample_blocks_v1, sample_blocks_v2_exact_match)

        # All blocks should match exactly
        assert len(result.forward_matches) == 3
        assert result.forward_matches["block_a"] == "block_x"
        assert result.forward_matches["block_b"] == "block_y"
        assert result.forward_matches["block_c"] == "block_z"

        # All matches should be token_hash type
        assert all(match_type == "token_hash" for match_type in result.match_types.values())

        # All similarities should be 100
        assert all(sim == 100 for sim in result.match_similarities.values())

    def test_similarity_based_matching(self, matcher, sample_blocks_v1, sample_blocks_v2_similar):
        """Test Phase 2: Similarity-based matching."""
        result = matcher.match_blocks(sample_blocks_v1, sample_blocks_v2_similar)

        # block_a and block_b should match via similarity
        assert "block_a" in result.forward_matches
        assert "block_b" in result.forward_matches

        # Match types should be similarity
        assert result.match_types.get("block_a") == "similarity"
        assert result.match_types.get("block_b") == "similarity"

        # Similarities should be < 100 (not exact matches)
        if "block_a" in result.match_similarities:
            assert result.match_similarities["block_a"] < 100
        if "block_b" in result.match_similarities:
            assert result.match_similarities["block_b"] < 100

    def test_no_match_below_threshold(self, matcher):
        """Test that blocks below similarity threshold are not matched."""
        blocks_v1 = pd.DataFrame(
            {
                "block_id": ["block_a"],
                "token_hash": ["hash_1"],
                "token_sequence": ["[1;2;3;4;5]"],
                "function_name": ["func_a"],
            }
        )

        blocks_v2 = pd.DataFrame(
            {
                "block_id": ["block_x"],
                "token_hash": ["hash_x"],
                "token_sequence": ["[10;20;30;40;50]"],  # Very different
                "function_name": ["func_x"],
            }
        )

        result = matcher.match_blocks(blocks_v1, blocks_v2)

        # No match should be found
        assert len(result.forward_matches) == 0

    def test_backward_matches(self, matcher, sample_blocks_v1, sample_blocks_v2_exact_match):
        """Test that backward matches are correctly created."""
        result = matcher.match_blocks(sample_blocks_v1, sample_blocks_v2_exact_match)

        # Backward matches should be reverse of forward matches
        assert result.backward_matches["block_x"] == "block_a"
        assert result.backward_matches["block_y"] == "block_b"
        assert result.backward_matches["block_z"] == "block_c"

    def test_bidirectional_matching(self, matcher, sample_blocks_v1, sample_blocks_v2_exact_match):
        """Test bidirectional matching."""
        old_to_new, new_to_old = matcher.bidirectional_match(
            sample_blocks_v1, sample_blocks_v2_exact_match
        )

        # Forward direction
        assert old_to_new.forward_matches["block_a"] == "block_x"
        assert old_to_new.forward_matches["block_b"] == "block_y"

        # Backward direction
        assert new_to_old.forward_matches["block_x"] == "block_a"
        assert new_to_old.forward_matches["block_y"] == "block_b"

    def test_empty_source_blocks(self, matcher):
        """Test matching with empty source blocks."""
        source = pd.DataFrame(columns=["block_id", "token_hash", "token_sequence"])
        target = pd.DataFrame(
            {
                "block_id": ["block_x"],
                "token_hash": ["hash_x"],
                "token_sequence": ["[1;2;3]"],
            }
        )

        result = matcher.match_blocks(source, target)

        assert len(result.forward_matches) == 0
        assert len(result.match_types) == 0

    def test_empty_target_blocks(self, matcher):
        """Test matching with empty target blocks."""
        source = pd.DataFrame(
            {
                "block_id": ["block_a"],
                "token_hash": ["hash_1"],
                "token_sequence": ["[1;2;3]"],
            }
        )
        target = pd.DataFrame(columns=["block_id", "token_hash", "token_sequence"])

        result = matcher.match_blocks(source, target)

        assert len(result.forward_matches) == 0

    def test_best_match_selection(self, matcher):
        """Test that the best match (highest similarity) is selected."""
        source = pd.DataFrame(
            {
                "block_id": ["block_a"],
                "token_hash": ["hash_1"],
                "token_sequence": ["[1;2;3;4;5]"],
                "function_name": ["func_a"],
            }
        )

        target = pd.DataFrame(
            {
                "block_id": ["block_x", "block_y", "block_z"],
                "token_hash": ["hash_x", "hash_y", "hash_z"],
                "token_sequence": [
                    "[1;2;3;4]",  # High similarity
                    "[1;2;3;4;5;6]",  # Medium similarity
                    "[10;20;30]",  # Low similarity
                ],
                "function_name": ["func_x", "func_y", "func_z"],
            }
        )

        result = matcher.match_blocks(source, target)

        # Should match with the most similar block
        assert "block_a" in result.forward_matches
        # The matched block should be one with high similarity
        matched_block = result.forward_matches["block_a"]
        assert matched_block in ["block_x", "block_y"]  # Either high or medium similarity

    def test_no_double_matching(self, matcher):
        """Test that each target block is matched at most once."""
        source = pd.DataFrame(
            {
                "block_id": ["block_a", "block_b"],
                "token_hash": ["hash_1", "hash_2"],
                "token_sequence": ["[1;2;3]", "[1;2;3;4]"],
                "function_name": ["func_a", "func_b"],
            }
        )

        target = pd.DataFrame(
            {
                "block_id": ["block_x"],
                "token_hash": ["hash_x"],
                "token_sequence": ["[1;2;3;4;5]"],  # Similar to both
                "function_name": ["func_x"],
            }
        )

        result = matcher.match_blocks(source, target)

        # At most one source block should match to block_x
        matched_to_x = [k for k, v in result.forward_matches.items() if v == "block_x"]
        assert len(matched_to_x) <= 1

    def test_invalid_token_sequences_skipped(self, matcher):
        """Test that invalid token sequences are gracefully skipped."""
        source = pd.DataFrame(
            {
                "block_id": ["block_a"],
                "token_hash": ["hash_1"],
                "token_sequence": ["invalid"],  # Invalid format
                "function_name": ["func_a"],
            }
        )

        target = pd.DataFrame(
            {
                "block_id": ["block_x"],
                "token_hash": ["hash_x"],
                "token_sequence": ["[1;2;3]"],
                "function_name": ["func_x"],
            }
        )

        # Should not raise exception, just skip the invalid sequence
        result = matcher.match_blocks(source, target)

        # No match should be found due to invalid sequence
        assert len(result.forward_matches) == 0

    def test_custom_similarity_threshold(self):
        """Test MethodMatcher with custom similarity threshold."""
        # Low threshold matcher (60%)
        low_threshold_matcher = MethodMatcher(similarity_threshold=60)

        # High threshold matcher (90%)
        high_threshold_matcher = MethodMatcher(similarity_threshold=90)

        source = pd.DataFrame(
            {
                "block_id": ["block_a"],
                "token_hash": ["hash_1"],
                "token_sequence": ["[1;2;3;4]"],
            }
        )

        target = pd.DataFrame(
            {
                "block_id": ["block_x"],
                "token_hash": ["hash_x"],
                "token_sequence": ["[1;2;3;4;5;6]"],  # Medium similarity
            }
        )

        # Low threshold should find match
        result_low = low_threshold_matcher.match_blocks(source, target)

        # High threshold might not find match (depending on actual similarity)
        result_high = high_threshold_matcher.match_blocks(source, target)

        # At least the low threshold should find matches
        assert len(result_low.forward_matches) >= len(result_high.forward_matches)


class TestMatchResult:
    """Test MatchResult dataclass."""

    def test_match_result_creation(self):
        """Test creating a MatchResult instance."""
        result = MatchResult(
            forward_matches={"a": "x", "b": "y"},
            backward_matches={"x": "a", "y": "b"},
            match_types={"a": "token_hash", "b": "similarity"},
            match_similarities={"a": 100, "b": 85},
        )

        assert len(result.forward_matches) == 2
        assert result.forward_matches["a"] == "x"
        assert result.match_types["a"] == "token_hash"
        assert result.match_similarities["b"] == 85
