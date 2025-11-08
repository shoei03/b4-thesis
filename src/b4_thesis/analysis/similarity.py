"""Similarity calculation functions for code clone detection.

This module provides functions to calculate similarity between token sequences
using N-gram and LCS (Longest Common Subsequence) approaches.
"""


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
