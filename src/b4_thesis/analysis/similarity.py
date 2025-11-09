"""Similarity calculation functions for code clone detection.

This module provides functions to calculate similarity between token sequences
using N-gram and LCS (Longest Common Subsequence) approaches.
"""

import numpy as np


def parse_token_sequence(token_seq: str) -> list[int]:
    """Parse token sequence from string format to list of integers.

    Args:
        token_seq: Token sequence string (e.g., "[123;456;789]")

    Returns:
        List of token integers.

    Raises:
        ValueError: If the token sequence format is invalid or empty.
    """
    if not token_seq:
        raise ValueError("Token sequence cannot be empty")

    # Check for proper bracket format
    if not token_seq.startswith("[") or not token_seq.endswith("]"):
        raise ValueError(f"Invalid token sequence format: {token_seq}")

    # Extract content between brackets
    content = token_seq[1:-1].strip()

    if not content:
        raise ValueError("Token sequence cannot be empty")

    # Split by semicolon and convert to integers
    try:
        tokens = [int(token.strip()) for token in content.split(";")]
        return tokens
    except ValueError as e:
        raise ValueError(f"Invalid token format in sequence: {token_seq}") from e


def calculate_ngram_similarity(tokens_1: list[int], tokens_2: list[int]) -> int:
    """Calculate N-gram based similarity between two token sequences.

    Uses bi-gram (2-gram) with Dice coefficient for similarity calculation.

    Args:
        tokens_1: First token sequence.
        tokens_2: Second token sequence.

    Returns:
        Similarity score (0-100).
    """
    if not tokens_1 or not tokens_2:
        return 0

    # Handle single token case
    if len(tokens_1) == 1 and len(tokens_2) == 1:
        return 100 if tokens_1[0] == tokens_2[0] else 0

    # Generate bi-grams (pairs of consecutive tokens)
    def get_bigrams(tokens: list[int]) -> set[tuple[int, int]]:
        if len(tokens) < 2:
            # For single token, create a special bi-gram with itself
            return {(tokens[0], tokens[0])} if tokens else set()
        return {(tokens[i], tokens[i + 1]) for i in range(len(tokens) - 1)}

    bigrams_1 = get_bigrams(tokens_1)
    bigrams_2 = get_bigrams(tokens_2)

    # Calculate Dice coefficient: 2 * |A ∩ B| / (|A| + |B|)
    intersection = len(bigrams_1 & bigrams_2)
    total = len(bigrams_1) + len(bigrams_2)

    if total == 0:
        return 0

    similarity = (2.0 * intersection / total) * 100
    return int(round(similarity))


def calculate_ngram_similarity_vectorized(tokens_1: list[int], tokens_2: list[int]) -> int:
    """Calculate N-gram similarity using NumPy vectorization.

    This is a vectorized version of calculate_ngram_similarity that uses NumPy
    for potentially faster computation on larger sequences.

    Args:
        tokens_1: First token sequence.
        tokens_2: Second token sequence.

    Returns:
        Similarity score (0-100).
    """
    if not tokens_1 or not tokens_2:
        return 0

    # Handle single token case
    if len(tokens_1) == 1 and len(tokens_2) == 1:
        return 100 if tokens_1[0] == tokens_2[0] else 0

    # Generate bi-grams using NumPy views
    def get_bigrams_vectorized(tokens: list[int]) -> np.ndarray:
        if len(tokens) < 2:
            # For single token, create a special bi-gram with itself
            if tokens:
                return np.array([[tokens[0], tokens[0]]], dtype=np.int32)
            return np.array([], dtype=np.int32).reshape(0, 2)

        arr = np.array(tokens, dtype=np.int32)
        # Create a view of bi-grams: [[t[0], t[1]], [t[1], t[2]], ...]
        bigrams = np.column_stack([arr[:-1], arr[1:]])
        return bigrams

    bigrams_1 = get_bigrams_vectorized(tokens_1)
    bigrams_2 = get_bigrams_vectorized(tokens_2)

    if len(bigrams_1) == 0 or len(bigrams_2) == 0:
        return 0

    # Convert to structured arrays for efficient set operations
    # This allows us to treat each bi-gram as a single comparable unit
    dt = np.dtype([("a", np.int32), ("b", np.int32)])
    bigrams_1_struct = np.array([tuple(b) for b in bigrams_1], dtype=dt)
    bigrams_2_struct = np.array([tuple(b) for b in bigrams_2], dtype=dt)

    # Calculate intersection using numpy
    intersection_count = len(np.intersect1d(bigrams_1_struct, bigrams_2_struct))
    total = len(bigrams_1_struct) + len(bigrams_2_struct)

    if total == 0:
        return 0

    similarity = (2.0 * intersection_count / total) * 100
    return int(round(similarity))


def calculate_lcs_similarity(tokens_1: list[int], tokens_2: list[int]) -> int:
    """Calculate LCS (Longest Common Subsequence) based similarity.

    Uses dynamic programming to find the longest common subsequence and
    calculates similarity based on the LCS length.

    Args:
        tokens_1: First token sequence.
        tokens_2: Second token sequence.

    Returns:
        Similarity score (0-100).
    """
    if not tokens_1 or not tokens_2:
        return 0

    len1, len2 = len(tokens_1), len(tokens_2)

    # Dynamic programming table for LCS
    dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]

    # Fill the DP table
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            if tokens_1[i - 1] == tokens_2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    lcs_length = dp[len1][len2]

    # Calculate similarity as LCS length / max length
    max_length = max(len1, len2)
    similarity = (lcs_length / max_length) * 100

    return int(round(similarity))


def calculate_lcs_similarity_banded(
    tokens_1: list[int],
    tokens_2: list[int],
    threshold: int = 70,
    band_width: int | None = None,
) -> int | None:
    """Calculate LCS similarity with early termination and banded DP.

    This is an optimized version of LCS that:
    1. Terminates early if theoretical maximum similarity < threshold
    2. Uses banded dynamic programming to reduce computation
    3. Monitors progress and exits early if similarity becomes impossible

    Args:
        tokens_1: First token sequence.
        tokens_2: Second token sequence.
        threshold: Minimum similarity threshold (0-100). Returns None if below.
        band_width: Width of the diagonal band for DP. If None, auto-calculated
                   based on length difference.

    Returns:
        Similarity score (0-100) if >= threshold, None otherwise.
    """
    if not tokens_1 or not tokens_2:
        return None

    len1, len2 = len(tokens_1), len(tokens_2)

    # Early termination: Check theoretical maximum similarity
    max_possible_lcs = min(len1, len2)
    max_length = max(len1, len2)
    max_possible_similarity = (max_possible_lcs / max_length) * 100

    if max_possible_similarity < threshold:
        return None

    # Auto-calculate band width if not provided
    if band_width is None:
        # Band width should cover the length difference plus some margin
        band_width = abs(len1 - len2) + max(10, int(0.1 * max(len1, len2)))

    # Banded dynamic programming
    dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    max_lcs_so_far = 0

    for i in range(1, len1 + 1):
        # Calculate band boundaries
        j_start = max(1, i - band_width)
        j_end = min(len2 + 1, i + band_width + 1)

        max_in_row = 0

        for j in range(j_start, j_end):
            if tokens_1[i - 1] == tokens_2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                # Only look at cells within the band
                prev_i = dp[i - 1][j] if j < j_end else 0
                prev_j = dp[i][j - 1] if j > j_start else 0
                dp[i][j] = max(prev_i, prev_j)

            max_in_row = max(max_in_row, dp[i][j])

        max_lcs_so_far = max(max_lcs_so_far, max_in_row)

        # Early termination: Check if we can still reach threshold
        # Optimistically assume we can match all remaining tokens
        if i > band_width:
            remaining_rows = len1 - i
            optimistic_lcs = max_lcs_so_far + min(remaining_rows, len2)
            optimistic_similarity = (optimistic_lcs / max_length) * 100

            # Add margin (0.8) to avoid premature termination near threshold
            if optimistic_similarity < threshold * 0.8:
                return None

    lcs_length = dp[len1][len2]

    # Calculate final similarity
    similarity = (lcs_length / max_length) * 100
    similarity_int = int(round(similarity))

    if similarity_int < threshold:
        return None

    return similarity_int


def calculate_similarity(token_seq_1: str, token_seq_2: str, ngram_threshold: int = 70) -> int:
    """Calculate similarity between two token sequences.

    2-phase approach:
    1. Calculate N-gram similarity
    2. If N-gram >= ngram_threshold, return N-gram similarity (skip LCS for efficiency)
    3. If N-gram < ngram_threshold, calculate and return LCS similarity

    Args:
        token_seq_1: Token sequence string (e.g., "[123;456;789]")
        token_seq_2: Token sequence string
        ngram_threshold: Threshold for skipping LCS calculation (default: 70).
                        If N-gram similarity >= threshold, LCS is skipped.

    Returns:
        Similarity score (0-100)

    Raises:
        ValueError: If token sequences are invalid or empty.
    """
    # Parse token sequences
    tokens_1 = parse_token_sequence(token_seq_1)
    tokens_2 = parse_token_sequence(token_seq_2)

    # Phase 1: Calculate N-gram similarity
    ngram_sim = calculate_ngram_similarity(tokens_1, tokens_2)

    # Phase 2: If N-gram >= threshold, skip LCS (optimization)
    if ngram_sim >= ngram_threshold:
        return ngram_sim

    # N-gram < threshold, calculate LCS similarity
    lcs_sim = calculate_lcs_similarity(tokens_1, tokens_2)
    return lcs_sim


def calculate_similarity_optimized(
    token_seq_1: str,
    token_seq_2: str,
    ngram_threshold: int = 70,
    use_banded_lcs: bool = True,
) -> int | None:
    """Calculate similarity with Phase 5.3.2 optimizations.

    Enhanced 2-phase approach with early termination:
    1. Calculate N-gram similarity
    2. If N-gram >= ngram_threshold, return N-gram similarity
    3. If N-gram < ngram_threshold, calculate LCS with early termination

    Args:
        token_seq_1: Token sequence string (e.g., "[123;456;789]")
        token_seq_2: Token sequence string
        ngram_threshold: Threshold for skipping LCS calculation (default: 70).
        use_banded_lcs: If True, use banded LCS with early termination (default: True).

    Returns:
        Similarity score (0-100) if >= ngram_threshold, None otherwise.

    Raises:
        ValueError: If token sequences are invalid or empty.
    """
    # Parse token sequences
    tokens_1 = parse_token_sequence(token_seq_1)
    tokens_2 = parse_token_sequence(token_seq_2)

    # Phase 1: Calculate N-gram similarity
    ngram_sim = calculate_ngram_similarity(tokens_1, tokens_2)

    # Phase 2: If N-gram >= threshold, skip LCS (optimization)
    if ngram_sim >= ngram_threshold:
        return ngram_sim

    # N-gram < threshold, calculate LCS similarity with optimizations
    if use_banded_lcs:
        # Use banded LCS with early termination
        lcs_sim = calculate_lcs_similarity_banded(tokens_1, tokens_2, ngram_threshold)
    else:
        # Use standard LCS
        lcs_sim = calculate_lcs_similarity(tokens_1, tokens_2)
        if lcs_sim < ngram_threshold:
            return None

    return lcs_sim
