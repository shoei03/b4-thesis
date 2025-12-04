"""Tests for API usage pattern rules."""

import pytest

from b4_thesis.analysis.deletion_prediction.rule_base import CodeSnippet
from b4_thesis.analysis.deletion_prediction.rules.api_usage import (
    UsesAssertWarnRule,
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
        assert "select()" in rule.description or "select" in rule.description
        assert "loc" in rule.description
        assert "assert" in rule.description.lower() or "warn" in rule.description.lower()

    def test_all_three_detected(self, rule):
        """Test detection when all three patterns are used."""
        snippet = CodeSnippet(
            code='''def test_complex_operation(df):
    """Use select, loc, and assert_warn."""
    with tm.assert_produces_warning(FutureWarning):
        filtered = df.select(lambda x: x > 0)
        return filtered.loc[0:10]''',
            function_name="test_complex_operation",
            file_path="test.py",
            start_line=1,
            end_line=5,
            revision="rev1",
            loc=5,
        )

        assert rule.apply(snippet) is True

    def test_all_three_in_complex_test(self, rule):
        """Test detection with all three patterns in a test method."""
        snippet = CodeSnippet(
            code="""def test_pandas_operation():
    assert_warns(DeprecationWarning, old_func)
    result = df.select(cols).loc[df['x'] > 5]
    return result""",
            function_name="test_pandas_operation",
            file_path="test.py",
            start_line=1,
            end_line=4,
            revision="rev1",
            loc=4,
        )

        assert rule.apply(snippet) is True

    def test_only_select_and_loc_not_detected(self, rule):
        """Test that only .select() and .loc without assert_warn is not detected."""
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

        assert rule.apply(snippet) is False

    def test_only_select_and_assert_warn_not_detected(self, rule):
        """Test that only .select() and assert_warn without .loc is not detected."""
        snippet = CodeSnippet(
            code="""def test_select(df):
    with tm.assert_produces_warning(FutureWarning):
        return df.select(lambda x: x > 0)""",
            function_name="test_select",
            file_path="test.py",
            start_line=1,
            end_line=3,
            revision="rev1",
            loc=3,
        )

        assert rule.apply(snippet) is False

    def test_only_loc_and_assert_warn_not_detected(self, rule):
        """Test that only .loc and assert_warn without .select is not detected."""
        snippet = CodeSnippet(
            code="""def test_loc(df):
    assert_warns(UserWarning, func)
    return df.loc[0]""",
            function_name="test_loc",
            file_path="test.py",
            start_line=1,
            end_line=3,
            revision="rev1",
            loc=3,
        )

        assert rule.apply(snippet) is False

    def test_only_one_pattern_not_detected(self, rule):
        """Test that only one pattern is not detected."""
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

    def test_no_patterns_not_detected(self, rule):
        """Test that methods with no patterns are not detected."""
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


class TestUsesAssertWarnRule:
    """Test cases for UsesAssertWarnRule."""

    @pytest.fixture
    def rule(self):
        """Create UsesAssertWarnRule instance."""
        return UsesAssertWarnRule()

    def test_rule_name(self, rule):
        """Test rule name."""
        assert rule.rule_name == "uses_assert_warn"

    def test_rule_description(self, rule):
        """Test rule description."""
        assert "assert" in rule.description.lower()
        assert "warn" in rule.description.lower()

    def test_assert_produces_warning_detected(self, rule):
        """Test detection of tm.assert_produces_warning() usage."""
        snippet = CodeSnippet(
            code='''def test_warning():
    """Test that warning is produced."""
    with tm.assert_produces_warning(FutureWarning):
        deprecated_function()''',
            function_name="test_warning",
            file_path="test.py",
            start_line=1,
            end_line=4,
            revision="rev1",
            loc=4,
        )

        assert rule.apply(snippet) is True

    def test_assert_warns_detected(self, rule):
        """Test detection of assert_warns() usage."""
        snippet = CodeSnippet(
            code="""def test_deprecation():
    assert_warns(DeprecationWarning, old_api)""",
            function_name="test_deprecation",
            file_path="test.py",
            start_line=1,
            end_line=2,
            revision="rev1",
            loc=2,
        )

        assert rule.apply(snippet) is True

    def test_assert_something_warning_detected(self, rule):
        """Test detection of various assert_*_warn* patterns."""
        snippet = CodeSnippet(
            code="""def validate():
    result = assert_no_warnings_occurred()
    return result""",
            function_name="validate",
            file_path="test.py",
            start_line=1,
            end_line=3,
            revision="rev1",
            loc=3,
        )

        assert rule.apply(snippet) is True

    def test_with_whitespace(self, rule):
        """Test detection with various whitespace."""
        snippet = CodeSnippet(
            code="""def check_warning():
    tm.assert_produces_warning  (  RuntimeWarning  )""",
            function_name="check_warning",
            file_path="test.py",
            start_line=1,
            end_line=2,
            revision="rev1",
            loc=2,
        )

        assert rule.apply(snippet) is True

    def test_qualified_name_detected(self, rule):
        """Test detection with qualified names."""
        snippet = CodeSnippet(
            code="""def test_pandas_warning():
    pd.testing.assert_produces_warning(UserWarning)""",
            function_name="test_pandas_warning",
            file_path="test.py",
            start_line=1,
            end_line=2,
            revision="rev1",
            loc=2,
        )

        assert rule.apply(snippet) is True

    def test_no_assert_warn_not_detected(self, rule):
        """Test that methods without assert_*warn* are not detected."""
        snippet = CodeSnippet(
            code='''def process_data(df):
    """Process dataframe."""
    return df.dropna()''',
            function_name="process_data",
            file_path="test.py",
            start_line=1,
            end_line=3,
            revision="rev1",
            loc=3,
        )

        assert rule.apply(snippet) is False

    def test_assert_without_warn_not_detected(self, rule):
        """Test that assert without warn is not detected."""
        snippet = CodeSnippet(
            code="""def test_equality():
    assert_equal(a, b)""",
            function_name="test_equality",
            file_path="test.py",
            start_line=1,
            end_line=2,
            revision="rev1",
            loc=2,
        )

        assert rule.apply(snippet) is False

    def test_warn_without_assert_not_detected(self, rule):
        """Test that warn without assert is not detected."""
        snippet = CodeSnippet(
            code="""def emit_warning():
    warnings.warn("This is deprecated", DeprecationWarning)""",
            function_name="emit_warning",
            file_path="test.py",
            start_line=1,
            end_line=2,
            revision="rev1",
            loc=2,
        )

        assert rule.apply(snippet) is False

    def test_assert_warn_in_comment_detected(self, rule):
        """Test that assert_*warn* in comments is detected (expected behavior)."""
        snippet = CodeSnippet(
            code="""def process():
    # Use tm.assert_produces_warning() for testing
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
