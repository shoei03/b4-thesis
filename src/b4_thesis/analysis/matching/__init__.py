"""Method matching module for tracking code blocks across revisions.

This module provides method matching functionality with performance optimizations.
Main entry point is the MethodMatcher class.

Public API:
    - MethodMatcher: Main class for matching methods between revisions
    - MatchResult: Result data structure containing match information
    - MatchContext: Internal context for matching state (advanced usage)
"""

from b4_thesis.analysis.matching.match_types import MatchContext, MatchResult
from b4_thesis.analysis.matching.matching_constants import MatchingDefaults
from b4_thesis.analysis.matching.method_matcher import MethodMatcher

__all__ = [
    "MethodMatcher",
    "MatchResult",
    "MatchContext",
    "MatchingDefaults",
]
