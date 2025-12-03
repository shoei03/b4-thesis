"""API usage pattern-based deletion prediction rules.

This module contains rules for detecting specific pandas API usage patterns
such as .select() and .loc[] that might indicate methods at risk of deletion.
"""

import re

from b4_thesis.analysis.deletion_prediction.rule_base import CodeSnippet, DeletionRule


class UsesSelectRule(DeletionRule):
    """Detect methods using pandas .select() API.

    The .select() method was used in older pandas versions for column selection
    and filtering. Methods using this API might be candidates for refactoring
    or deletion as pandas evolves.
    """

    def __init__(self):
        """Initialize UsesSelectRule."""
        # Match .select( with optional whitespace
        self.pattern = re.compile(r"\.select\s*\(")

    @property
    def rule_name(self) -> str:
        """Return rule name."""
        return "uses_select"

    @property
    def description(self) -> str:
        """Return rule description."""
        return "Method uses pandas .select() API"

    def apply(self, snippet: CodeSnippet) -> bool:
        """Check if method uses .select() API.

        Args:
            snippet: Code snippet to analyze

        Returns:
            True if .select() usage detected
        """
        return bool(self.pattern.search(snippet.code))


class UsesLocRule(DeletionRule):
    """Detect methods using pandas .loc[] indexer.

    The .loc[] indexer is used for label-based indexing in pandas.
    Methods using this API are tracked to understand usage patterns
    and potential refactoring opportunities.
    """

    def __init__(self):
        """Initialize UsesLocRule."""
        # Match .loc[ with optional whitespace
        self.pattern = re.compile(r"\.loc\s*\[")

    @property
    def rule_name(self) -> str:
        """Return rule name."""
        return "uses_loc"

    @property
    def description(self) -> str:
        """Return rule description."""
        return "Method uses pandas .loc[] indexer"

    def apply(self, snippet: CodeSnippet) -> bool:
        """Check if method uses .loc[] indexer.

        Args:
            snippet: Code snippet to analyze

        Returns:
            True if .loc[] usage detected
        """
        return bool(self.pattern.search(snippet.code))


class UsesBothSelectLocRule(DeletionRule):
    """Detect methods using both .select() and .loc[] APIs.

    Methods that use both .select() and .loc[] might indicate complex
    data manipulation logic that could be candidates for refactoring.
    """

    def __init__(self):
        """Initialize UsesBothSelectLocRule."""
        # Match both .select( and .loc[ patterns
        self.select_pattern = re.compile(r"\.select\s*\(")
        self.loc_pattern = re.compile(r"\.loc\s*\[")

    @property
    def rule_name(self) -> str:
        """Return rule name."""
        return "uses_both_select_loc"

    @property
    def description(self) -> str:
        """Return rule description."""
        return "Method uses both .select() and .loc[] APIs"

    def apply(self, snippet: CodeSnippet) -> bool:
        """Check if method uses both .select() and .loc[].

        Args:
            snippet: Code snippet to analyze

        Returns:
            True if both .select() and .loc[] usage detected
        """
        has_select = bool(self.select_pattern.search(snippet.code))
        has_loc = bool(self.loc_pattern.search(snippet.code))
        return has_select and has_loc
