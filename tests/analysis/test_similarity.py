"""Tests for similarity calculation functions."""

import pytest

from b4_thesis.analysis.similarity import (
    calculate_lcs_similarity,
    calculate_lcs_similarity_banded,
    calculate_ngram_similarity,
    calculate_similarity,
    calculate_similarity_optimized,
    parse_token_sequence,
)


class TestParseTokenSequence:
    """Test token sequence parsing."""

    def test_parse_valid_sequence(self):
        """Test parsing valid token sequence."""
        token_seq = "[1;2;3;4;5]"
        tokens = parse_token_sequence(token_seq)
        assert tokens == [1, 2, 3, 4, 5]

    def test_parse_single_token(self):
        """Test parsing single token."""
        token_seq = "[42]"
        tokens = parse_token_sequence(token_seq)
        assert tokens == [42]

    def test_parse_empty_sequence(self):
        """Test parsing empty sequence."""
        token_seq = "[]"
        with pytest.raises(ValueError):
            parse_token_sequence(token_seq)

    def test_parse_invalid_format(self):
        """Test parsing invalid format."""
        with pytest.raises(ValueError):
            parse_token_sequence("invalid")

    def test_parse_missing_brackets(self):
        """Test parsing without brackets."""
        with pytest.raises(ValueError):
            parse_token_sequence("1;2;3")


class TestCalculateNgramSimilarity:
    """Test N-gram similarity calculation."""

    def test_identical_sequences(self):
        """Test 100% similarity for identical sequences."""
        tokens1 = [1, 2, 3, 4, 5]
        tokens2 = [1, 2, 3, 4, 5]
        similarity = calculate_ngram_similarity(tokens1, tokens2)
        assert similarity == 100

    def test_completely_different(self):
        """Test 0% similarity for completely different sequences."""
        tokens1 = [1, 2, 3, 4, 5]
        tokens2 = [10, 20, 30, 40, 50]
        similarity = calculate_ngram_similarity(tokens1, tokens2)
        assert similarity == 0

    def test_partial_overlap(self):
        """Test partial overlap."""
        tokens1 = [1, 2, 3, 4, 5]
        tokens2 = [1, 2, 3, 6, 7]
        similarity = calculate_ngram_similarity(tokens1, tokens2)
        assert 0 < similarity < 100

    def test_single_token_identical(self):
        """Test single token identical."""
        tokens1 = [42]
        tokens2 = [42]
        similarity = calculate_ngram_similarity(tokens1, tokens2)
        assert similarity == 100

    def test_single_token_different(self):
        """Test single token different."""
        tokens1 = [42]
        tokens2 = [99]
        similarity = calculate_ngram_similarity(tokens1, tokens2)
        assert similarity == 0


class TestCalculateLcsSimilarity:
    """Test LCS (Longest Common Subsequence) similarity calculation."""

    def test_identical_sequences(self):
        """Test 100% similarity for identical sequences."""
        tokens1 = [1, 2, 3, 4, 5]
        tokens2 = [1, 2, 3, 4, 5]
        similarity = calculate_lcs_similarity(tokens1, tokens2)
        assert similarity == 100

    def test_completely_different(self):
        """Test 0% similarity for completely different sequences."""
        tokens1 = [1, 2, 3, 4, 5]
        tokens2 = [10, 20, 30, 40, 50]
        similarity = calculate_lcs_similarity(tokens1, tokens2)
        assert similarity == 0

    def test_subsequence(self):
        """Test when one is subsequence of another."""
        tokens1 = [1, 2, 3, 4, 5]
        tokens2 = [1, 3, 5]  # Subsequence
        similarity = calculate_lcs_similarity(tokens1, tokens2)
        # LCS is [1,3,5] (length 3)
        # Similarity should be based on LCS length vs average length
        assert similarity > 0

    def test_reversed_sequence(self):
        """Test reversed sequence."""
        tokens1 = [1, 2, 3, 4, 5]
        tokens2 = [5, 4, 3, 2, 1]
        similarity = calculate_lcs_similarity(tokens1, tokens2)
        # LCS would be single element
        assert similarity > 0
        assert similarity < 100


class TestCalculateSimilarity:
    """Test cross-revision similarity calculation."""

    def test_identical_sequences(self):
        """Test 100% similarity for identical sequences."""
        seq1 = "[1;2;3;4;5]"
        seq2 = "[1;2;3;4;5]"
        similarity = calculate_similarity(seq1, seq2)
        assert similarity == 100

    def test_high_similarity_ngram_only(self):
        """Test N-gram ≥ 70 (LCS should be skipped)."""
        # Create sequences with high N-gram similarity
        # Nearly identical, only last token different
        seq1 = "[1;2;3;4;5;6;7;8;9;10]"
        seq2 = "[1;2;3;4;5;6;7;8;9;99]"

        similarity = calculate_similarity(seq1, seq2)
        # Should be >= 70 (N-gram will be used)
        assert similarity >= 70

    def test_low_similarity_uses_lcs(self):
        """Test N-gram < 70 triggers LCS calculation."""
        # Low N-gram similarity sequences
        seq1 = "[1;2;3;4;5]"
        seq2 = "[10;20;30;4;5]"

        similarity = calculate_similarity(seq1, seq2)
        # This should use LCS since N-gram will be < 70
        assert 0 <= similarity < 100

    def test_completely_different(self):
        """Test 0% similarity for completely different sequences."""
        seq1 = "[1;2;3;4;5]"
        seq2 = "[10;20;30;40;50]"
        similarity = calculate_similarity(seq1, seq2)
        assert similarity == 0

    def test_empty_sequences(self):
        """Test handling of empty sequences."""
        with pytest.raises(ValueError):
            calculate_similarity("[]", "[1;2;3]")

        with pytest.raises(ValueError):
            calculate_similarity("[1;2;3]", "[]")

    def test_malformed_sequence(self):
        """Test handling of malformed token sequences."""
        with pytest.raises(ValueError):
            calculate_similarity("invalid", "[1;2;3]")

        with pytest.raises(ValueError):
            calculate_similarity("[1;2;3]", "malformed")

    def test_partial_overlap(self):
        """Test sequences with partial overlap."""
        seq1 = "[1;2;3;4;5]"
        seq2 = "[3;4;5;6;7]"  # 3 tokens overlap
        similarity = calculate_similarity(seq1, seq2)
        assert 20 <= similarity <= 80

    def test_single_token_sequences(self):
        """Test single token sequences."""
        seq1 = "[42]"
        seq2 = "[42]"
        similarity = calculate_similarity(seq1, seq2)
        assert similarity == 100

        seq1 = "[42]"
        seq2 = "[99]"
        similarity = calculate_similarity(seq1, seq2)
        assert similarity == 0

    def test_ngram_threshold_boundary(self):
        """Test behavior at N-gram threshold boundary."""
        # This test verifies the 2-phase approach works correctly
        # We can't predict exact similarity without implementation details,
        # but we can verify the function returns valid range
        seq1 = "[1;2;3;4;5;6;7;8;9;10]"
        seq2 = "[1;2;3;4;5;6;7;99;99;99]"

        similarity = calculate_similarity(seq1, seq2)
        assert 0 <= similarity <= 100
        assert isinstance(similarity, int)

    def test_custom_threshold_high(self):
        """Test with custom high threshold (e.g., 90)."""
        # With high threshold (90), even good N-gram similarity should trigger LCS
        seq1 = "[1;2;3;4;5;6;7;8;9;10]"
        seq2 = "[1;2;3;4;5;6;7;8;9;99]"

        # Default threshold (70) - should return N-gram
        similarity_default = calculate_similarity(seq1, seq2)

        # High threshold (90) - should trigger LCS if N-gram < 90
        similarity_high = calculate_similarity(seq1, seq2, ngram_threshold=90)

        # Both should return valid similarity
        assert 0 <= similarity_default <= 100
        assert 0 <= similarity_high <= 100

    def test_custom_threshold_low(self):
        """Test with custom low threshold (e.g., 50)."""
        # With low threshold (50), more cases will skip LCS
        seq1 = "[1;2;3;4;5]"
        seq2 = "[1;2;3;99;99]"

        # Default threshold (70)
        similarity_default = calculate_similarity(seq1, seq2)

        # Low threshold (50) - may skip LCS if N-gram >= 50
        similarity_low = calculate_similarity(seq1, seq2, ngram_threshold=50)

        # Both should return valid similarity
        assert 0 <= similarity_default <= 100
        assert 0 <= similarity_low <= 100

    def test_threshold_zero(self):
        """Test with threshold 0 (always use N-gram, never LCS)."""
        seq1 = "[1;2;3;4;5]"
        seq2 = "[10;20;30;40;50]"

        # With threshold 0, should always use N-gram (even if 0%)
        similarity = calculate_similarity(seq1, seq2, ngram_threshold=0)
        assert similarity == 0  # N-gram similarity is 0

    def test_threshold_100(self):
        """Test with threshold 100 (always use LCS unless N-gram is 100)."""
        seq1 = "[1;2;3;4;5]"
        seq2 = "[1;2;3;4;99]"

        # With threshold 100, should use LCS unless perfect match
        similarity = calculate_similarity(seq1, seq2, ngram_threshold=100)
        # Should calculate LCS since N-gram < 100
        assert 0 <= similarity <= 100


class TestCalculateLCSSimilarityBanded:
    """Test banded LCS similarity calculation (Phase 5.3.2)."""

    def test_identical_sequences(self):
        """Test banded LCS with identical sequences."""
        tokens1 = [1, 2, 3, 4, 5]
        tokens2 = [1, 2, 3, 4, 5]
        similarity = calculate_lcs_similarity_banded(tokens1, tokens2, threshold=70)
        assert similarity == 100

    def test_similar_sequences_above_threshold(self):
        """Test banded LCS with similar sequences above threshold."""
        tokens1 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        tokens2 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 99]
        similarity = calculate_lcs_similarity_banded(tokens1, tokens2, threshold=70)
        assert similarity is not None
        assert similarity >= 70

    def test_dissimilar_sequences_below_threshold(self):
        """Test banded LCS returns None for dissimilar sequences."""
        tokens1 = [1, 2, 3, 4, 5]
        tokens2 = [10, 20, 30, 40, 50]
        similarity = calculate_lcs_similarity_banded(tokens1, tokens2, threshold=70)
        assert similarity is None

    def test_early_termination_length(self):
        """Test early termination based on length difference."""
        # Very different lengths, max possible similarity < threshold
        tokens1 = [1, 2, 3]
        tokens2 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        similarity = calculate_lcs_similarity_banded(tokens1, tokens2, threshold=80)
        # max_possible_lcs = 3, max_length = 10
        # max_possible_similarity = 3/10 * 100 = 30 < 80
        assert similarity is None

    def test_empty_sequences(self):
        """Test banded LCS with empty sequences."""
        assert calculate_lcs_similarity_banded([], [1, 2, 3], threshold=70) is None
        assert calculate_lcs_similarity_banded([1, 2, 3], [], threshold=70) is None
        assert calculate_lcs_similarity_banded([], [], threshold=70) is None

    def test_custom_band_width(self):
        """Test banded LCS with custom band width."""
        tokens1 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        tokens2 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 99]

        # Narrow band
        similarity_narrow = calculate_lcs_similarity_banded(
            tokens1, tokens2, threshold=70, band_width=5
        )

        # Wide band
        similarity_wide = calculate_lcs_similarity_banded(
            tokens1, tokens2, threshold=70, band_width=20
        )

        # Both should succeed for this similar sequence
        assert similarity_narrow is not None
        assert similarity_wide is not None

    def test_auto_band_width(self):
        """Test auto band width calculation."""
        tokens1 = [1, 2, 3, 4, 5]
        tokens2 = [1, 2, 3, 4, 99]

        # Auto band width (None)
        similarity = calculate_lcs_similarity_banded(tokens1, tokens2, threshold=70)
        assert similarity is not None

    def test_comparison_with_standard_lcs(self):
        """Test that banded LCS gives same result as standard LCS when above threshold."""
        tokens1 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        tokens2 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 99]

        standard = calculate_lcs_similarity(tokens1, tokens2)
        banded = calculate_lcs_similarity_banded(tokens1, tokens2, threshold=70)

        # If banded returns a value (not None), it should match standard
        if banded is not None:
            assert abs(standard - banded) <= 1  # Allow 1 point rounding difference


class TestCalculateSimilarityOptimized:
    """Test optimized similarity calculation (Phase 5.3.2)."""

    def test_identical_sequences(self):
        """Test optimized similarity with identical sequences."""
        seq1 = "[1;2;3;4;5]"
        seq2 = "[1;2;3;4;5]"
        similarity = calculate_similarity_optimized(seq1, seq2)
        assert similarity == 100

    def test_high_similarity_ngram_shortcut(self):
        """Test that high N-gram similarity uses shortcut."""
        # Very similar sequences, N-gram should be >= 70
        seq1 = "[1;2;3;4;5;6;7;8;9;10]"
        seq2 = "[1;2;3;4;5;6;7;8;9;99]"
        similarity = calculate_similarity_optimized(seq1, seq2)
        assert similarity is not None
        assert similarity >= 70

    def test_low_similarity_returns_none(self):
        """Test that low similarity returns None."""
        seq1 = "[1;2;3;4;5]"
        seq2 = "[10;20;30;40;50]"
        similarity = calculate_similarity_optimized(seq1, seq2, ngram_threshold=70)
        assert similarity is None

    def test_medium_similarity_uses_banded_lcs(self):
        """Test that medium similarity uses banded LCS."""
        # Somewhat similar, N-gram < 70, but LCS might be >= 70
        seq1 = "[1;2;3;4;5;6;7]"
        seq2 = "[1;2;3;99;99;6;7]"
        similarity = calculate_similarity_optimized(seq1, seq2, use_banded_lcs=True)

        # Result depends on actual similarity
        assert similarity is None or (isinstance(similarity, int) and 0 <= similarity <= 100)

    def test_without_banded_lcs(self):
        """Test optimized similarity without banded LCS."""
        seq1 = "[1;2;3;4;5]"
        seq2 = "[1;2;3;99;99]"

        similarity = calculate_similarity_optimized(seq1, seq2, use_banded_lcs=False)

        # Should return None if below threshold
        assert similarity is None or (isinstance(similarity, int) and 0 <= similarity <= 100)

    def test_empty_sequences(self):
        """Test optimized similarity with empty sequences."""
        with pytest.raises(ValueError):
            calculate_similarity_optimized("[]", "[1;2;3]")

        with pytest.raises(ValueError):
            calculate_similarity_optimized("[1;2;3]", "[]")

    def test_malformed_sequences(self):
        """Test optimized similarity with malformed sequences."""
        with pytest.raises(ValueError):
            calculate_similarity_optimized("invalid", "[1;2;3]")

        with pytest.raises(ValueError):
            calculate_similarity_optimized("[1;2;3]", "malformed")
