"""Tests for code quality rules."""

import pytest

from b4_thesis.analysis.deletion_prediction.rule_base import CodeSnippet
from b4_thesis.analysis.deletion_prediction.rules.code_quality import (
    EmptyMethodRule,
    ShortMethodRule,
    SingleReturnRule,
)


class TestShortMethodRule:
    """Test cases for ShortMethodRule."""

    @pytest.fixture
    def rule(self):
        """Create ShortMethodRule instance."""
        return ShortMethodRule(threshold=3)

    def test_short_method_detected(self, rule):
        """Test detection of short method."""
        snippet = CodeSnippet(
            code='''def foo():
    """Docstring."""
    x = 1
    return x''',
            function_name="foo",
            file_path="test.py",
            start_line=1,
            end_line=4,
            revision="rev1",
            loc=4,
        )

        assert rule.apply(snippet) is True

    def test_long_method_not_detected(self, rule):
        """Test that long method is not detected."""
        snippet = CodeSnippet(
            code='''def foo():
    """Docstring."""
    x = 1
    y = 2
    z = 3
    w = 4
    return x + y + z + w''',
            function_name="foo",
            file_path="test.py",
            start_line=1,
            end_line=8,
            revision="rev1",
            loc=8,
        )

        assert rule.apply(snippet) is False

    def test_comments_excluded(self, rule):
        """Test that comments are excluded from line count."""
        snippet = CodeSnippet(
            code='''def foo():
    # Comment 1
    # Comment 2
    x = 1
    # Comment 3
    return x''',
            function_name="foo",
            file_path="test.py",
            start_line=1,
            end_line=6,
            revision="rev1",
            loc=6,
        )

        # Only 2 effective lines (x = 1, return x)
        assert rule.apply(snippet) is True


class TestEmptyMethodRule:
    """Test cases for EmptyMethodRule."""

    @pytest.fixture
    def rule(self):
        """Create EmptyMethodRule instance."""
        return EmptyMethodRule()

    def test_empty_with_pass(self, rule):
        """Test detection of method with only pass."""
        snippet = CodeSnippet(
            code='''def foo():
    """Docstring."""
    pass''',
            function_name="foo",
            file_path="test.py",
            start_line=1,
            end_line=3,
            revision="rev1",
            loc=3,
        )

        assert rule.apply(snippet) is True

    def test_empty_with_ellipsis(self, rule):
        """Test detection of method with only ellipsis."""
        snippet = CodeSnippet(
            code='''def foo():
    """Docstring."""
    ...''',
            function_name="foo",
            file_path="test.py",
            start_line=1,
            end_line=3,
            revision="rev1",
            loc=3,
        )

        assert rule.apply(snippet) is True

    def test_empty_with_return_none(self, rule):
        """Test detection of method with only return None."""
        snippet = CodeSnippet(
            code='''def foo():
    return None''',
            function_name="foo",
            file_path="test.py",
            start_line=1,
            end_line=2,
            revision="rev1",
            loc=2,
        )

        assert rule.apply(snippet) is True

    def test_non_empty_method(self, rule):
        """Test that non-empty method is not detected."""
        snippet = CodeSnippet(
            code='''def foo():
    x = 1
    return x''',
            function_name="foo",
            file_path="test.py",
            start_line=1,
            end_line=3,
            revision="rev1",
            loc=3,
        )

        assert rule.apply(snippet) is False


class TestSingleReturnRule:
    """Test cases for SingleReturnRule."""

    @pytest.fixture
    def rule(self):
        """Create SingleReturnRule instance."""
        return SingleReturnRule()

    def test_single_return_detected(self, rule):
        """Test detection of method with only return statement."""
        snippet = CodeSnippet(
            code='''def foo():
    """Docstring."""
    return 42''',
            function_name="foo",
            file_path="test.py",
            start_line=1,
            end_line=3,
            revision="rev1",
            loc=3,
        )

        assert rule.apply(snippet) is True

    def test_multiple_statements_not_detected(self, rule):
        """Test that method with multiple statements is not detected."""
        snippet = CodeSnippet(
            code='''def foo():
    x = 1
    return x''',
            function_name="foo",
            file_path="test.py",
            start_line=1,
            end_line=3,
            revision="rev1",
            loc=3,
        )

        assert rule.apply(snippet) is False

    def test_no_return_not_detected(self, rule):
        """Test that method without return is not detected."""
        snippet = CodeSnippet(
            code='''def foo():
    pass''',
            function_name="foo",
            file_path="test.py",
            start_line=1,
            end_line=2,
            revision="rev1",
            loc=2,
        )

        assert rule.apply(snippet) is False
