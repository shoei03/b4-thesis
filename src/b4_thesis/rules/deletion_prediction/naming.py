"""Naming convention-based deletion prediction rules.

Note: DeprecatedNamingRule and TemporaryNamingRule have been migrated to YAML configuration.
Only custom rules that require complex logic are kept here.
"""

from b4_thesis.rules.base import CodeSnippet, DeletionRule


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
