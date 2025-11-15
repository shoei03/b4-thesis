"""Constants for method matching configuration.

This module defines default values and thresholds used throughout
the method matching process to improve maintainability and configurability.
"""


class FilterThresholds:
    """Thresholds for pre-filtering during similarity matching."""

    # Maximum allowed length difference ratio between token sequences (30%)
    MAX_LENGTH_DIFF_RATIO = 0.3

    # Minimum required Jaccard similarity for candidate pairs (30%)
    MIN_JACCARD_SIMILARITY = 0.3


class CacheConfig:
    """Configuration for caching mechanisms."""

    # Maximum size of LRU cache for similarity calculations
    SIMILARITY_CACHE_SIZE = 10000


class ParallelConfig:
    """Configuration for parallel processing."""

    # Number of unmatched pairs above which parallel processing is auto-enabled
    AUTO_PARALLEL_THRESHOLD = 100000


class MatchingDefaults:
    """Default values for matching parameters."""

    # Default minimum similarity score (0-100) for fuzzy matching
    SIMILARITY_THRESHOLD = 70

    # Default LSH similarity threshold (0.0-1.0)
    LSH_THRESHOLD = 0.7

    # Default number of LSH permutations
    LSH_NUM_PERM = 128

    # Default number of top candidates to consider per source block
    TOP_K_CANDIDATES = 20
