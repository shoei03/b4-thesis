"""Analysis modules for code clone detection and tracking.

This package provides core analysis functionality including:
- Similarity calculation (N-gram and LCS)
- Union-Find data structure for group detection
- Method matching across revisions
- Clone group detection
"""

from b4_thesis.analysis.group_detector import CloneGroup, GroupDetector
from b4_thesis.analysis.matching import MatchResult, MethodMatcher
from b4_thesis.analysis.similarity import (
    calculate_lcs_similarity,
    calculate_ngram_similarity,
    calculate_similarity,
    parse_token_sequence,
)
from b4_thesis.analysis.union_find import UnionFind

# Backward compatibility: re-export from old locations
# This allows existing code to keep using:
#   from b4_thesis.analysis.method_matcher import MethodMatcher
# while new code can use:
#   from b4_thesis.analysis.matching import MethodMatcher
method_matcher = None  # Lazy import to avoid circular dependency

__all__ = [
    "UnionFind",
    "calculate_similarity",
    "calculate_ngram_similarity",
    "calculate_lcs_similarity",
    "parse_token_sequence",
    "MethodMatcher",
    "MatchResult",
    "GroupDetector",
    "CloneGroup",
]
