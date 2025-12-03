"""Tests for API usage pattern rules."""

import pytest

from b4_thesis.analysis.deletion_prediction.rule_base import CodeSnippet
from b4_thesis.analysis.deletion_prediction.rules.api_usage import (
    UsesBothSelectLocRule,
    UsesLocRule,
    UsesSelectRule,
)


class TestUsesSelectRule:
    """Test cases for UsesSelectRule."""

    @pytest.fixture
    def rule(self):
        """Create UsesSelectRule instance."""
        return UsesSelectRule()

    def test_rule_name(self, rule):
        """Test rule name."""
        assert rule.rule_name == "uses_select"

    def test_rule_description(self, rule):
        """Test rule description."""
        assert "select()" in rule.description

    def test_select_detected(self, rule):
        """Test detection of .select() usage."""
        snippet = CodeSnippet(
            code='''def filter_data(df):
    """Filter data using select."""
    return df.select(lambda x: x > 0)''',
            function_name="filter_data",
            file_path="test.py",
            start_line=1,
            end_line=3,
            revision="rev1",
            loc=3,
        )

        assert rule.apply(snippet) is True

    def test_select_with_whitespace(self, rule):
        """Test detection with various whitespace."""
        snippet = CodeSnippet(
            code="""def get_columns(df):
    return df.select  (  col1  )""",
            function_name="get_columns",
            file_path="test.py",
            start_line=1,
            end_line=2,
            revision="rev1",
            loc=2,
        )

        assert rule.apply(snippet) is True

    def test_no_select_not_detected(self, rule):
        """Test that methods without .select() are not detected."""
        snippet = CodeSnippet(
            code='''def add_numbers(a, b):
    """Simple function."""
    return a + b''',
            function_name="add_numbers",
            file_path="test.py",
            start_line=1,
            end_line=3,
            revision="rev1",
            loc=3,
        )

        assert rule.apply(snippet) is False

    def test_select_in_comment_detected(self, rule):
        """Test that .select() in comments is detected (expected behavior)."""
        snippet = CodeSnippet(
            code="""def process():
    # Use df.select() for filtering
    pass""",
            function_name="process",
            file_path="test.py",
            start_line=1,
            end_line=3,
            revision="rev1",
            loc=3,
        )

        # This is expected - we accept some false positives for simplicity
        assert rule.apply(snippet) is True


class TestUsesLocRule:
    """Test cases for UsesLocRule."""

    @pytest.fixture
    def rule(self):
        """Create UsesLocRule instance."""
        return UsesLocRule()

    def test_rule_name(self, rule):
        """Test rule name."""
        assert rule.rule_name == "uses_loc"

    def test_rule_description(self, rule):
        """Test rule description."""
        assert "loc[]" in rule.description or ".loc" in rule.description

    def test_loc_detected(self, rule):
        """Test detection of .loc[] usage."""
        snippet = CodeSnippet(
            code='''def get_row(df):
    """Get row using loc."""
    return df.loc[0]''',
            function_name="get_row",
            file_path="test.py",
            start_line=1,
            end_line=3,
            revision="rev1",
            loc=3,
        )

        assert rule.apply(snippet) is True

    def test_loc_with_slice(self, rule):
        """Test detection of .loc with slice."""
        snippet = CodeSnippet(
            code="""def subset_rows(df):
    return df.loc[1:5, 'col1':'col3']""",
            function_name="subset_rows",
            file_path="test.py",
            start_line=1,
            end_line=2,
            revision="rev1",
            loc=2,
        )

        assert rule.apply(snippet) is True

    def test_loc_with_boolean_indexing(self, rule):
        """Test detection of .loc with boolean indexing."""
        snippet = CodeSnippet(
            code="""def filter_rows(df):
    mask = df['value'] > 10
    return df.loc[mask]""",
            function_name="filter_rows",
            file_path="test.py",
            start_line=1,
            end_line=3,
            revision="rev1",
            loc=3,
        )

        assert rule.apply(snippet) is True

    def test_no_loc_not_detected(self, rule):
        """Test that methods without .loc are not detected."""
        snippet = CodeSnippet(
            code='''def calculate(x):
    """Simple calculation."""
    return x * 2''',
            function_name="calculate",
            file_path="test.py",
            start_line=1,
            end_line=3,
            revision="rev1",
            loc=3,
        )

        assert rule.apply(snippet) is False

    def test_iloc_not_detected(self, rule):
        """Test that .iloc is not detected (different API)."""
        snippet = CodeSnippet(
            code="""def get_first_row(df):
    return df.iloc[0]""",
            function_name="get_first_row",
            file_path="test.py",
            start_line=1,
            end_line=2,
            revision="rev1",
            loc=2,
        )

        assert rule.apply(snippet) is False


class TestUsesBothSelectLocRule:
    """Test cases for UsesBothSelectLocRule."""

    @pytest.fixture
    def rule(self):
        """Create UsesBothSelectLocRule instance."""
        return UsesBothSelectLocRule()

    def test_rule_name(self, rule):
        """Test rule name."""
        assert rule.rule_name == "uses_both_select_loc"

    def test_rule_description(self, rule):
        """Test rule description."""
        assert "both" in rule.description.lower()
        assert "select()" in rule.description or "select" in rule.description
        assert "loc" in rule.description

    def test_both_detected(self, rule):
        """Test detection when both .select() and .loc are used."""
        snippet = CodeSnippet(
            code='''def complex_operation(df):
    """Use both select and loc."""
    filtered = df.select(lambda x: x > 0)
    return filtered.loc[0:10]''',
            function_name="complex_operation",
            file_path="test.py",
            start_line=1,
            end_line=4,
            revision="rev1",
            loc=4,
        )

        assert rule.apply(snippet) is True

    def test_both_in_chain(self, rule):
        """Test detection when both are used in method chain."""
        snippet = CodeSnippet(
            code="""def chain_operation(df):
    return df.select(cols).loc[df['x'] > 5]""",
            function_name="chain_operation",
            file_path="test.py",
            start_line=1,
            end_line=2,
            revision="rev1",
            loc=2,
        )

        assert rule.apply(snippet) is True

    def test_only_select_not_detected(self, rule):
        """Test that only .select() is not detected."""
        snippet = CodeSnippet(
            code="""def use_select(df):
    return df.select(lambda x: x > 0)""",
            function_name="use_select",
            file_path="test.py",
            start_line=1,
            end_line=2,
            revision="rev1",
            loc=2,
        )

        assert rule.apply(snippet) is False

    def test_only_loc_not_detected(self, rule):
        """Test that only .loc is not detected."""
        snippet = CodeSnippet(
            code="""def use_loc(df):
    return df.loc[0]""",
            function_name="use_loc",
            file_path="test.py",
            start_line=1,
            end_line=2,
            revision="rev1",
            loc=2,
        )

        assert rule.apply(snippet) is False

    def test_neither_not_detected(self, rule):
        """Test that methods with neither API are not detected."""
        snippet = CodeSnippet(
            code="""def normal_operation(df):
    return df.head()""",
            function_name="normal_operation",
            file_path="test.py",
            start_line=1,
            end_line=2,
            revision="rev1",
            loc=2,
        )

        assert rule.apply(snippet) is False
