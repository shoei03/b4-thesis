"""Naming convention-based deletion prediction rules."""

import re

from b4_thesis.rules.base import CodeSnippet, DeletionRule


class DeprecatedNamingRule(DeletionRule):
    """Detect methods with deprecated naming patterns.

    Methods with names containing 'deprecated', 'old', 'legacy', 'obsolete'
    are likely candidates for deletion.
    """

    def __init__(self):
        """Initialize DeprecatedNamingRule."""
        self.patterns = [
            r"\bdeprecated\b",
            r"\bold[_-]",
            r"[_-]old\b",
            r"\blegacy\b",
            r"\bobsolete\b",
        ]
        self.regex = re.compile("|".join(self.patterns), re.IGNORECASE)

    @property
    def rule_name(self) -> str:
        """Return rule name."""
        return "deprecated_naming"

    @property
    def description(self) -> str:
        """Return rule description."""
        return "Method name contains 'deprecated', 'old', 'legacy', or 'obsolete'"

    def apply(self, snippet: CodeSnippet) -> bool:
        """Check if method name suggests deprecation.

        Args:
            snippet: Code snippet to analyze

        Returns:
            True if method name contains deprecated patterns
        """
        # Extract method name (remove class prefix if present)
        method_name = snippet.function_name
        if "." in method_name:
            method_name = method_name.split(".")[-1]

        return bool(self.regex.search(method_name))


class TemporaryNamingRule(DeletionRule):
    """Detect methods with temporary naming patterns.

    Methods with names containing 'tmp', 'temp', 'test', 'debug', 'hack'
    are likely temporary and candidates for deletion.
    """

    def __init__(self):
        """Initialize TemporaryNamingRule."""
        self.patterns = [
            r"\btmp[_-]",
            r"[_-]tmp\b",
            r"\btemp[_-]",
            r"[_-]temp\b",
            r"\bdebug[_-]",
            r"[_-]debug\b",
            r"\bhack\b",
            r"\bfixme\b",
            r"\bcompat\b",
            r"\bcompatibility\b",
            r"\bbackward[_-]?compat(?:ibility)?\b",
            r"\bbackward[_-]?compatible\b",
            r"\bback_?compat\b",
            r"\bretrocompat\b",
        ]
        self.regex = re.compile("|".join(self.patterns), re.IGNORECASE)

    @property
    def rule_name(self) -> str:
        """Return rule name."""
        return "temporary_naming"

    @property
    def description(self) -> str:
        """Return rule description."""
        return "Method name contains 'tmp', 'temp', 'test', 'debug', or 'hack'"

    def apply(self, snippet: CodeSnippet) -> bool:
        """Check if method name suggests temporary nature.

        Args:
            snippet: Code snippet to analyze

        Returns:
            True if method name contains temporary patterns
        """
        # Extract method name (remove class prefix if present)
        method_name = snippet.function_name
        if "." in method_name:
            method_name = method_name.split(".")[-1]

        return bool(self.regex.search(method_name))


class PrivateUnusedRule(DeletionRule):
    """Detect private methods that might be unused.

    Methods starting with underscore (private) are internal implementation
    details that might be unused and candidates for deletion.

    Note: This rule cannot determine actual usage, so it only checks naming.
    It's a weak signal on its own.
    """

    @property
    def rule_name(self) -> str:
        """Return rule name."""
        return "private_unused"

    @property
    def description(self) -> str:
        """Return rule description."""
        return "Method is private (starts with underscore)"

    def apply(self, snippet: CodeSnippet) -> bool:
        """Check if method is private (starts with underscore).

        Args:
            snippet: Code snippet to analyze

        Returns:
            True if method name starts with underscore
        """
        # Extract method name (remove class prefix if present)
        method_name = snippet.function_name
        if "." in method_name:
            method_name = method_name.split(".")[-1]

        # Check if starts with single underscore (but not double underscore)
        return method_name.startswith("_") and not method_name.startswith("__")
