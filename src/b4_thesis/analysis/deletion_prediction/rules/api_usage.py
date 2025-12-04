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
    """Detect methods using .select(), .loc[], and assert_*warn* APIs together.

    Methods that use all three patterns (.select(), .loc[], and assert_*warn*)
    might indicate complex test or data manipulation logic that could be
    candidates for refactoring or deletion.
    """

    def __init__(self):
        """Initialize UsesBothSelectLocRule."""
        # Match .select(, .loc[, and assert_*warn* patterns
        self.select_pattern = re.compile(r"\.select\s*\(")
        self.loc_pattern = re.compile(r"\.loc\s*\[")
        self.assert_warn_pattern = re.compile(r"[\w\.]*assert_.*warn[\w]*\s*\(")

    @property
    def rule_name(self) -> str:
        """Return rule name."""
        return "uses_both_select_loc"

    @property
    def description(self) -> str:
        """Return rule description."""
        return "Method uses .select(), .loc[], and assert_*warn* APIs together"

    def apply(self, snippet: CodeSnippet) -> bool:
        """Check if method uses .select(), .loc[], and assert_*warn* together.

        Args:
            snippet: Code snippet to analyze

        Returns:
            True if all three patterns (.select(), .loc[], assert_*warn*) are detected
        """
        has_select = bool(self.select_pattern.search(snippet.code))
        has_loc = bool(self.loc_pattern.search(snippet.code))
        has_assert_warn = bool(self.assert_warn_pattern.search(snippet.code))
        return has_select and has_loc and has_assert_warn


class UsesAssertWarnRule(DeletionRule):
    """Detect methods using assert and warning-related APIs.

    This rule detects usage of assertion and warning functions such as
    tm.assert_produces_warning() and similar testing utility methods.
    Methods using these APIs might be test utilities or validation code
    that could be refactored or removed.
    """

    def __init__(self):
        """Initialize UsesAssertWarnRule."""
        # Match patterns like tm.assert_produces_warning(, assert_something_warning(, etc.
        self.pattern = re.compile(r"[\w\.]*assert_.*warn[\w]*\s*\(")

    @property
    def rule_name(self) -> str:
        """Return rule name."""
        return "uses_assert_warn"

    @property
    def description(self) -> str:
        """Return rule description."""
        return "Method uses assert and warning-related APIs"

    def apply(self, snippet: CodeSnippet) -> bool:
        """Check if method uses assert and warning APIs.

        Args:
            snippet: Code snippet to analyze

        Returns:
            True if assert_*warn* usage detected
        """
        return bool(self.pattern.search(snippet.code))
