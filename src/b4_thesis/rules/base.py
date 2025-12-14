"""Base classes for deletion prediction rules."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class CodeSnippet:
    """Extracted code snippet with metadata.

    Attributes:
        code: Source code content
        function_name: Method signature (e.g., "DataFrame.set_axis")
        file_path: File path (relative or absolute)
        start_line: Starting line number (1-based)
        end_line: Ending line number (1-based, inclusive)
        revision: Revision identifier (timestamp format: YYYYMMDD_HHMMSS_<hash>)
        loc: Lines of code
        global_block_id: Optional unified ID tracking same method across revisions
    """

    code: str
    function_name: str
    file_path: str
    start_line: int
    end_line: int
    revision: str
    loc: int
    global_block_id: str | None = None


class DeletionRule(ABC):
    """Abstract base class for deletion prediction rules.

    Each rule detects a specific sign that a method might be deleted in the next revision.
    Subclasses must implement rule_name, description, and apply methods.

    Example:
        >>> class ShortMethodRule(DeletionRule):
        ...     @property
        ...     def rule_name(self) -> str:
        ...         return "short_method"
        ...
        ...     @property
        ...     def description(self) -> str:
        ...         return "Method has 3 or fewer lines"
        ...
        ...     def apply(self, snippet: CodeSnippet) -> bool:
        ...         return snippet.loc <= 3
    """

    @property
    @abstractmethod
    def rule_name(self) -> str:
        """Return unique rule identifier (e.g., "short_method").

        This name will be used as a column name in the output CSV with "rule_" prefix.
        Use snake_case and keep it concise.
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Return human-readable description of what this rule detects.

        Example: "Detects methods with 3 or fewer lines of code"
        """
        pass

    @abstractmethod
    def apply(self, snippet: CodeSnippet) -> bool:
        """Apply this rule to a code snippet.

        Args:
            snippet: Code snippet to analyze

        Returns:
            True if deletion sign detected (positive prediction),
            False otherwise (negative prediction)
        """
        pass

    def __repr__(self) -> str:
        """Return string representation."""
        return f"{self.__class__.__name__}(name='{self.rule_name}')"
