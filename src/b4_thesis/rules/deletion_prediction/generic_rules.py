"""Generic rule implementations that work from YAML configuration.

These classes provide reusable implementations for common rule patterns:
- Regex pattern matching on code or function names
- Threshold-based line counting
- Trivial statement detection
- Composite rules combining multiple patterns
"""

import re
from typing import Any

from b4_thesis.rules.base import CodeSnippet, DeletionRule


class RegexRule(DeletionRule):
    """Applies regex patterns to code content.

    This generic rule allows defining regex-based rules entirely in YAML
    configuration without writing Python code.
    """

    def __init__(
        self, name: str, description: str, patterns: list[str], flags: list[str] | None = None
    ):
        """Initialize RegexRule.

        Args:
            name: Rule name (e.g., "has_todo")
            description: Human-readable description
            patterns: List of regex patterns to match
            flags: Optional list of regex flags ("IGNORECASE", "MULTILINE", "DOTALL")
        """
        self._name = name
        self._description = description
        self.patterns = patterns

        # Parse and combine flags
        flag_int = self._parse_flags(flags or [])

        # Compile all patterns into single regex with OR logic
        combined_pattern = "|".join(f"({p})" for p in patterns)
        self.regex = re.compile(combined_pattern, flag_int)

    @property
    def rule_name(self) -> str:
        """Return rule name."""
        return self._name

    @property
    def description(self) -> str:
        """Return rule description."""
        return self._description

    def apply(self, snippet: CodeSnippet) -> bool:
        """Check if code matches any of the regex patterns.

        Args:
            snippet: Code snippet to analyze

        Returns:
            True if any pattern matches
        """
        return bool(self.regex.search(snippet.code))

    @staticmethod
    def _parse_flags(flags: list[str]) -> int:
        """Parse regex flag names to re module constants.

        Args:
            flags: List of flag names (e.g., ["IGNORECASE", "MULTILINE"])

        Returns:
            Combined regex flags as integer
        """
        flag_map = {
            "IGNORECASE": re.IGNORECASE,
            "I": re.IGNORECASE,
            "MULTILINE": re.MULTILINE,
            "M": re.MULTILINE,
            "DOTALL": re.DOTALL,
            "S": re.DOTALL,
        }

        result = 0
        for flag in flags:
            if flag in flag_map:
                result |= flag_map[flag]
            else:
                raise ValueError(f"Unknown regex flag: {flag}")

        return result


class RegexFunctionNameRule(DeletionRule):
    """Applies regex patterns to function names.

    This rule extracts the method name from the full function path
    (e.g., "DataFrame.method" -> "method") and applies regex matching.
    """

    def __init__(
        self, name: str, description: str, patterns: list[str], flags: list[str] | None = None
    ):
        """Initialize RegexFunctionNameRule.

        Args:
            name: Rule name (e.g., "deprecated_naming")
            description: Human-readable description
            patterns: List of regex patterns to match against function name
            flags: Optional list of regex flags
        """
        self._name = name
        self._description = description
        self.patterns = patterns

        # Parse and combine flags
        flag_int = RegexRule._parse_flags(flags or [])

        # Compile all patterns into single regex
        combined_pattern = "|".join(f"({p})" for p in patterns)
        self.regex = re.compile(combined_pattern, flag_int)

    @property
    def rule_name(self) -> str:
        """Return rule name."""
        return self._name

    @property
    def description(self) -> str:
        """Return rule description."""
        return self._description

    def apply(self, snippet: CodeSnippet) -> bool:
        """Check if function name matches any of the regex patterns.

        Args:
            snippet: Code snippet to analyze

        Returns:
            True if function name matches any pattern
        """
        # Extract method name (remove class prefix if present)
        method_name = snippet.function_name
        if "." in method_name:
            method_name = method_name.split(".")[-1]

        return bool(self.regex.search(method_name))


class ThresholdRule(DeletionRule):
    """Counts effective lines of code and compares to threshold.

    Effective lines exclude:
    - Empty lines
    - Comment lines (starting with #)
    - Docstring lines
    - Function definition line
    """

    def __init__(self, name: str, description: str, threshold: int):
        """Initialize ThresholdRule.

        Args:
            name: Rule name (e.g., "short_method")
            description: Human-readable description
            threshold: Maximum number of effective lines
        """
        self._name = name
        self._description = description
        self.threshold = threshold

    @property
    def rule_name(self) -> str:
        """Return rule name."""
        return self._name

    @property
    def description(self) -> str:
        """Return rule description."""
        return self._description

    def apply(self, snippet: CodeSnippet) -> bool:
        """Check if method has threshold or fewer effective lines.

        Args:
            snippet: Code snippet to analyze

        Returns:
            True if effective_lines <= threshold
        """
        effective_lines = self._count_effective_lines(snippet.code)
        return effective_lines <= self.threshold

    @staticmethod
    def _count_effective_lines(code: str) -> int:
        """Count effective lines of code.

        Excludes:
        - Empty lines
        - Comment lines (starting with #)
        - Docstring lines
        - Function definition line (first line starting with def or async def)

        Args:
            code: Source code to analyze

        Returns:
            Number of effective lines
        """
        lines = code.split("\n")

        # Remove function definition line (first line)
        if lines and (
            lines[0].strip().startswith("def ") or lines[0].strip().startswith("async def ")
        ):
            lines = lines[1:]

        # Count effective lines
        in_docstring = False
        docstring_delimiter = None
        effective_lines = 0

        for line in lines:
            stripped = line.strip()

            # Skip empty lines
            if not stripped:
                continue

            # Handle docstrings
            if stripped.startswith('"""') or stripped.startswith("'''"):
                delimiter = '"""' if stripped.startswith('"""') else "'''"
                if not in_docstring:
                    # Start of docstring
                    in_docstring = True
                    docstring_delimiter = delimiter
                    # Check if docstring ends on same line
                    if stripped.count(delimiter) >= 2:
                        in_docstring = False
                        docstring_delimiter = None
                    continue
                elif delimiter == docstring_delimiter:
                    # End of docstring
                    in_docstring = False
                    docstring_delimiter = None
                    continue

            # Skip lines inside docstring
            if in_docstring:
                continue

            # Skip comment lines
            if stripped.startswith("#"):
                continue

            # Count as effective line
            effective_lines += 1

        return effective_lines


class TrivialStatementsRule(DeletionRule):
    """Check if method body contains only trivial statements.

    A method is considered trivial if its body (after removing def, docstrings,
    comments, and empty lines) contains only specified trivial statements
    like "pass", "...", "return", "return None".
    """

    def __init__(self, name: str, description: str, trivial_statements: list[str]):
        """Initialize TrivialStatementsRule.

        Args:
            name: Rule name (e.g., "empty_method")
            description: Human-readable description
            trivial_statements: List of statements considered trivial
        """
        self._name = name
        self._description = description
        self.trivial_statements = set(trivial_statements)

    @property
    def rule_name(self) -> str:
        """Return rule name."""
        return self._name

    @property
    def description(self) -> str:
        """Return rule description."""
        return self._description

    def apply(self, snippet: CodeSnippet) -> bool:
        """Check if method body contains only trivial statements.

        Args:
            snippet: Code snippet to analyze

        Returns:
            True if body is empty or contains only trivial statements
        """
        body_lines = self._extract_body_lines(snippet.code)

        # Empty body is considered trivial
        if not body_lines:
            return True

        # Check if all body lines are trivial statements
        return all(line in self.trivial_statements for line in body_lines)

    @staticmethod
    def _extract_body_lines(code: str) -> list[str]:
        """Extract non-trivial body lines from code.

        Removes:
        - Function definition line
        - Docstrings
        - Comments
        - Empty lines

        Args:
            code: Source code to analyze

        Returns:
            List of stripped body lines
        """
        lines = code.split("\n")

        body_lines = []
        in_docstring = False
        docstring_delimiter = None
        skip_first_def = True

        for line in lines:
            stripped = line.strip()

            # Skip function definition
            if skip_first_def and (
                stripped.startswith("def ") or stripped.startswith("async def ")
            ):
                skip_first_def = False
                continue

            # Handle docstrings
            if stripped.startswith('"""') or stripped.startswith("'''"):
                delimiter = '"""' if stripped.startswith('"""') else "'''"
                if not in_docstring:
                    in_docstring = True
                    docstring_delimiter = delimiter
                    if stripped.count(delimiter) >= 2:
                        in_docstring = False
                        docstring_delimiter = None
                    continue
                elif delimiter == docstring_delimiter:
                    in_docstring = False
                    docstring_delimiter = None
                    continue

            if in_docstring:
                continue

            # Skip comments and empty lines
            if not stripped or stripped.startswith("#"):
                continue

            body_lines.append(stripped)

        return body_lines


class CompositeRule(DeletionRule):
    """Combine multiple regex patterns with AND/OR logic.

    This rule allows creating complex detection logic by combining
    multiple regex patterns. All patterns must match (AND) or any
    pattern can match (OR).
    """

    def __init__(
        self,
        name: str,
        description: str,
        operator: str,
        sub_patterns: list[dict[str, Any]],
    ):
        """Initialize CompositeRule.

        Args:
            name: Rule name (e.g., "uses_both_select_loc")
            description: Human-readable description
            operator: Combination operator ("AND" or "OR")
            sub_patterns: List of pattern dicts with "pattern" and optional "flags"

        Raises:
            ValueError: If operator is not "AND" or "OR"
        """
        self._name = name
        self._description = description
        self.operator = operator.upper()

        if self.operator not in ("AND", "OR"):
            raise ValueError(f"Unknown operator: {operator}. Must be AND or OR.")

        # Compile all sub-patterns
        self.patterns = []
        for p in sub_patterns:
            pattern_str = p["pattern"]
            flags = p.get("flags", [])
            flag_int = RegexRule._parse_flags(flags)
            compiled = re.compile(pattern_str, flag_int)
            self.patterns.append(compiled)

    @property
    def rule_name(self) -> str:
        """Return rule name."""
        return self._name

    @property
    def description(self) -> str:
        """Return rule description."""
        return self._description

    def apply(self, snippet: CodeSnippet) -> bool:
        """Check if code matches the composite pattern.

        Args:
            snippet: Code snippet to analyze

        Returns:
            True if operator logic is satisfied
                - AND: All patterns must match
                - OR: At least one pattern must match
        """
        matches = [bool(p.search(snippet.code)) for p in self.patterns]

        if self.operator == "AND":
            return all(matches)
        else:  # OR
            return any(matches)
