"""Comment-based deletion prediction rules."""

import re

from b4_thesis.rules.base import CodeSnippet, DeletionRule


class TodoCommentRule(DeletionRule):
    """Detect methods with TODO/FIXME/HACK comments.

    Methods containing TODO, FIXME, or HACK comments might indicate
    incomplete implementation or known issues, making them candidates
    for deletion or refactoring.
    """

    def __init__(self):
        """Initialize TodoCommentRule."""
        # Match TODO, FIXME, HACK, XXX in comments
        self.patterns = [
            r"#.*\bTODO\b",
            r"#.*\bFIXME\b",
            r"#.*\bHACK\b",
            r"#.*\bXXX\b",
        ]
        self.regex = re.compile("|".join(self.patterns), re.IGNORECASE)

    @property
    def rule_name(self) -> str:
        """Return rule name."""
        return "has_todo"

    @property
    def description(self) -> str:
        """Return rule description."""
        return "Method contains TODO, FIXME, HACK, or XXX comments"

    def apply(self, snippet: CodeSnippet) -> bool:
        """Check if method contains TODO/FIXME/HACK comments.

        Args:
            snippet: Code snippet to analyze

        Returns:
            True if method contains TODO/FIXME/HACK comments
        """
        return bool(self.regex.search(snippet.code))


class DeprecatedAnnotationRule(DeletionRule):
    """Detect methods with @deprecated decorator or deprecation warnings.

    Methods explicitly marked as deprecated (via decorator or warning)
    are clear candidates for future deletion.
    """

    def __init__(self):
        """Initialize DeprecatedAnnotationRule."""
        # Match various deprecation patterns
        self.patterns = [
            r"@deprecated",
            r"@deprecate",
            r"warnings\.warn.*[Dd]eprecat",
            r"DeprecationWarning",
            r"FutureWarning",
            r"# *deprecated",
            r"# *DEPRECATED",
        ]
        self.regex = re.compile("|".join(self.patterns))

    @property
    def rule_name(self) -> str:
        """Return rule name."""
        return "has_deprecated"

    @property
    def description(self) -> str:
        """Return rule description."""
        return "Method has @deprecated decorator or deprecation warning"

    def apply(self, snippet: CodeSnippet) -> bool:
        """Check if method has deprecation markers.

        Args:
            snippet: Code snippet to analyze

        Returns:
            True if method has deprecation markers
        """
        return bool(self.regex.search(snippet.code))
