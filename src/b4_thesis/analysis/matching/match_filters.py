"""Filtering and pre-processing utilities for method matching.

This module provides helper functions for filtering candidate matches:
- Length-based filtering
- Jaccard similarity filtering
- Cached similarity calculation
- Parallel processing helpers
"""

from functools import lru_cache

from b4_thesis.analysis.matching.matching_constants import CacheConfig, FilterThresholds
from b4_thesis.analysis.similarity import (
    calculate_similarity,
    calculate_similarity_optimized,
    parse_token_sequence,
)


def _should_skip_by_length(
    token_seq_1: str,
    token_seq_2: str,
    max_diff_ratio: float = FilterThresholds.MAX_LENGTH_DIFF_RATIO,
) -> bool:
    """Check if two sequences should be skipped based on length difference.

    Args:
        token_seq_1: First token sequence string
        token_seq_2: Second token sequence string
        max_diff_ratio: Maximum allowed length difference ratio

    Returns:
        True if length difference is too large and should skip, False otherwise.
    """
    try:
        tokens_1 = parse_token_sequence(token_seq_1)
        tokens_2 = parse_token_sequence(token_seq_2)
    except ValueError:
        # Invalid sequences should be skipped
        return True

    len_1, len_2 = len(tokens_1), len(tokens_2)
    if len_1 == 0 or len_2 == 0:
        return True

    # Calculate length difference ratio
    max_len = max(len_1, len_2)
    min_len = min(len_1, len_2)
    diff_ratio = (max_len - min_len) / max_len

    return diff_ratio > max_diff_ratio


def _calculate_jaccard(token_seq_1: str, token_seq_2: str) -> float:
    """Calculate Jaccard similarity between two token sequences.

    Args:
        token_seq_1: First token sequence string
        token_seq_2: Second token sequence string

    Returns:
        Jaccard similarity (0.0-1.0)
    """
    try:
        tokens_1 = parse_token_sequence(token_seq_1)
        tokens_2 = parse_token_sequence(token_seq_2)
    except ValueError:
        return 0.0

    set_1 = set(tokens_1)
    set_2 = set(tokens_2)

    if not set_1 or not set_2:
        return 0.0

    intersection = len(set_1 & set_2)
    union = len(set_1 | set_2)

    if union == 0:
        return 0.0

    return intersection / union


def _should_skip_by_jaccard(
    token_seq_1: str,
    token_seq_2: str,
    min_jaccard: float = FilterThresholds.MIN_JACCARD_SIMILARITY,
) -> bool:
    """Check if two sequences should be skipped based on Jaccard similarity.

    Args:
        token_seq_1: First token sequence string
        token_seq_2: Second token sequence string
        min_jaccard: Minimum required Jaccard similarity

    Returns:
        True if Jaccard similarity is too low and should skip, False otherwise.
    """
    jaccard = _calculate_jaccard(token_seq_1, token_seq_2)
    return jaccard < min_jaccard


@lru_cache(maxsize=CacheConfig.SIMILARITY_CACHE_SIZE)
def _cached_similarity(
    token_seq_1: str, token_seq_2: str, use_optimized: bool = False
) -> int | None:
    """Calculate similarity with LRU caching.

    Args:
        token_seq_1: First token sequence string
        token_seq_2: Second token sequence string
        use_optimized: If True, use optimized similarity (Phase 5.3.2)

    Returns:
        Similarity score (0-100), or None if below threshold (optimized mode only)

    Raises:
        ValueError: If token sequences are invalid.
    """
    # Sort sequences to ensure cache hits for bidirectional matching
    seq_a, seq_b = sorted([token_seq_1, token_seq_2])

    if use_optimized:
        return calculate_similarity_optimized(seq_a, seq_b)
    else:
        return calculate_similarity(seq_a, seq_b)


def _compute_similarity_for_pair(
    args: tuple[str, str, str, str, int],
) -> tuple[str, str, int] | None:
    """Compute similarity for a source-target pair (helper for parallel processing).

    Args:
        args: Tuple of (block_id_source, token_seq_source, block_id_target,
              token_seq_target, similarity_threshold)

    Returns:
        Tuple of (block_id_source, block_id_target, similarity) if similarity >= threshold,
        None otherwise.
    """
    block_id_source, token_seq_source, block_id_target, token_seq_target, threshold = args

    # Phase 5.3.1 optimization: Pre-filters
    if _should_skip_by_length(token_seq_source, token_seq_target):
        return None

    if _should_skip_by_jaccard(token_seq_source, token_seq_target):
        return None

    try:
        # Use cached similarity calculation
        similarity = _cached_similarity(token_seq_source, token_seq_target)
    except ValueError:
        # Skip if token sequences are invalid
        return None

    if similarity >= threshold:
        return (block_id_source, block_id_target, similarity)
    return None
