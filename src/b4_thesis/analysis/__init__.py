"""Analysis modules for code clone detection and tracking.

This package provides core analysis functionality including:
- Similarity calculation (N-gram and LCS)
- Union-Find data structure for group detection
"""

from b4_thesis.analysis.similarity import (
    calculate_lcs_similarity,
    calculate_ngram_similarity,
    calculate_similarity,
    parse_token_sequence,
)
from b4_thesis.analysis.union_find import UnionFind

__all__ = [
    "UnionFind",
    "calculate_similarity",
    "calculate_ngram_similarity",
    "calculate_lcs_similarity",
    "parse_token_sequence",
]
