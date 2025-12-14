"""Code quality-based deletion prediction rules.

Note: ShortMethodRule and EmptyMethodRule have been migrated to YAML configuration.
Only custom rules that require complex logic are kept here.
"""

from b4_thesis.rules.base import CodeSnippet, DeletionRule


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
