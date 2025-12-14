"""Code quality-based deletion prediction rules."""

from b4_thesis.rules.base import CodeSnippet, DeletionRule


class ShortMethodRule(DeletionRule):
    """Detect methods that are too short (potentially trivial).

    Short methods (3 or fewer effective lines) are often trivial wrappers
    or delegators that might be candidates for deletion or inlining.
    """

    def __init__(self, threshold: int = 3):
        """Initialize ShortMethodRule.

        Args:
            threshold: Maximum number of effective lines (default: 3)
        """
        self.threshold = threshold

    @property
    def rule_name(self) -> str:
        """Return rule name."""
        return "short_method"

    @property
    def description(self) -> str:
        """Return rule description."""
        return f"Method has {self.threshold} or fewer effective lines of code"

    def apply(self, snippet: CodeSnippet) -> bool:
        """Check if method is too short.

        Counts effective lines excluding:
        - Empty lines
        - Comment lines (starting with #)
        - Docstring lines

        Args:
            snippet: Code snippet to analyze

        Returns:
            True if method has threshold or fewer effective lines
        """
        lines = snippet.code.split("\n")

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

        return effective_lines <= self.threshold


class EmptyMethodRule(DeletionRule):
    """Detect methods with empty or trivial implementations.

    Empty methods often contain only:
    - pass statement
    - ... (Ellipsis)
    - return/return None
    """

    @property
    def rule_name(self) -> str:
        """Return rule name."""
        return "empty_method"

    @property
    def description(self) -> str:
        """Return rule description."""
        return "Method body is empty or contains only pass/... statements"

    def apply(self, snippet: CodeSnippet) -> bool:
        """Check if method is empty or trivial.

        Args:
            snippet: Code snippet to analyze

        Returns:
            True if method body is empty or trivial
        """
        lines = snippet.code.split("\n")

        # Remove function definition and docstring
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

        # Check if body is empty or trivial
        if not body_lines:
            return True

        # Check for trivial statements only
        trivial_statements = {"pass", "...", "return", "return None"}
        return all(line in trivial_statements for line in body_lines)


class SingleReturnRule(DeletionRule):
    """Detect methods that only return a single value or expression.

    Methods containing only a single return statement are often simple
    wrappers or getters that might be candidates for deletion or inlining.
    """

    @property
    def rule_name(self) -> str:
        """Return rule name."""
        return "single_return"

    @property
    def description(self) -> str:
        """Return rule description."""
        return "Method contains only a single return statement"

    def apply(self, snippet: CodeSnippet) -> bool:
        """Check if method only contains a single return statement.

        Args:
            snippet: Code snippet to analyze

        Returns:
            True if method body contains only a single return statement
        """
        lines = snippet.code.split("\n")

        # Extract body lines (exclude def, docstring, comments, empty)
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

        # Check if there's exactly one line and it's a return statement
        if len(body_lines) != 1:
            return False

        return body_lines[0].startswith("return")
