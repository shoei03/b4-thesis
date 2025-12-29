"""Tests for RuleApplicator."""

from unittest.mock import MagicMock

import pytest

from b4_thesis.analysis.deletion_prediction.extraction import (
    RuleApplicationResult,
    RuleApplicator,
)
from b4_thesis.analysis.deletion_prediction.rule_base import CodeSnippet, DeletionRule
import pandas as pd


class TestRuleApplicator:
    """Tests for RuleApplicator class."""

    @pytest.fixture
    def rule_applicator(self):
        """Create RuleApplicator instance."""
        return RuleApplicator()

    @pytest.fixture
    def sample_df(self):
        """Create sample DataFrame with code column."""
        return pd.DataFrame(
            {
                "global_block_id": ["block1", "block2"],
                "revision": ["rev1", "rev1"],
                "function_name": ["foo", "bar"],
                "file_path": ["a.py", "b.py"],
                "start_line": [1, 10],
                "end_line": [5, 15],
                "loc": [4, 5],
                "state": ["added", "modified"],
                "code": ["def foo(): pass", "def bar(): return 42"],
                "github_url": [
                    "https://github.com/repo/blob/rev1/a.py#L1-L5",
                    "https://github.com/repo/blob/rev1/b.py#L10-L15",
                ],
            }
        )

    @pytest.fixture
    def mock_rule(self):
        """Create mock rule that always returns True."""
        rule = MagicMock(spec=DeletionRule)
        rule.rule_name = "test_rule"
        rule.apply.return_value = True
        return rule

    @pytest.fixture
    def mock_rule_false(self):
        """Create mock rule that always returns False."""
        rule = MagicMock(spec=DeletionRule)
        rule.rule_name = "false_rule"
        rule.apply.return_value = False
        return rule

    def test_init(self):
        """Test RuleApplicator initialization."""
        applicator = RuleApplicator()
        assert applicator is not None

    def test_apply_rules_single_rule(self, rule_applicator, sample_df, mock_rule):
        """Test applying a single rule."""
        result = rule_applicator.apply_rules(sample_df, [mock_rule])

        assert isinstance(result, RuleApplicationResult)
        assert result.rules_applied == 1
        assert result.errors_count == 0
        assert len(result.df) == 2
        assert "rule_test_rule" in result.df.columns
        assert result.df["rule_test_rule"].tolist() == [True, True]

    def test_apply_rules_multiple_rules(
        self, rule_applicator, sample_df, mock_rule, mock_rule_false
    ):
        """Test applying multiple rules."""
        result = rule_applicator.apply_rules(sample_df, [mock_rule, mock_rule_false])

        assert isinstance(result, RuleApplicationResult)
        assert result.rules_applied == 2
        assert result.errors_count == 0
        assert "rule_test_rule" in result.df.columns
        assert "rule_false_rule" in result.df.columns
        assert result.df["rule_test_rule"].tolist() == [True, True]
        assert result.df["rule_false_rule"].tolist() == [False, False]

    def test_apply_rules_empty_rule_list(self, rule_applicator, sample_df):
        """Test applying empty rule list."""
        result = rule_applicator.apply_rules(sample_df, [])

        assert isinstance(result, RuleApplicationResult)
        assert result.rules_applied == 0
        assert result.errors_count == 0
        assert len(result.df) == 2
        # Verify no new columns added
        assert "rule_" not in " ".join(result.df.columns)

    def test_apply_rules_error_handling(self, rule_applicator, sample_df, capsys):
        """Test error handling when rule throws exception."""
        # Create rule that raises exception
        failing_rule = MagicMock(spec=DeletionRule)
        failing_rule.rule_name = "failing_rule"
        failing_rule.apply.side_effect = ValueError("Test error")

        result = rule_applicator.apply_rules(sample_df, [failing_rule])

        assert isinstance(result, RuleApplicationResult)
        assert result.rules_applied == 1
        assert result.errors_count == 2  # 2 methods, both fail
        assert "rule_failing_rule" in result.df.columns
        # When rule fails, it should return False
        assert result.df["rule_failing_rule"].tolist() == [False, False]

        # Verify warning message was printed
        captured = capsys.readouterr()
        assert "Warning: Rule failing_rule failed" in captured.out
        assert "Test error" in captured.out

    def test_apply_rules_partial_failure(self, rule_applicator, sample_df, capsys):
        """Test when rule fails for some methods but not all."""
        # Create rule that fails for first method only
        partial_fail_rule = MagicMock(spec=DeletionRule)
        partial_fail_rule.rule_name = "partial_fail"
        partial_fail_rule.apply.side_effect = [ValueError("Error"), True]

        result = rule_applicator.apply_rules(sample_df, [partial_fail_rule])

        assert result.rules_applied == 1
        assert result.errors_count == 1  # Only 1 failure
        assert result.df["rule_partial_fail"].tolist() == [False, True]

    def test_create_code_snippet(self, rule_applicator, sample_df):
        """Test CodeSnippet creation from DataFrame row."""
        row = sample_df.itertuples().__next__()
        snippet = rule_applicator._create_code_snippet(row)

        assert isinstance(snippet, CodeSnippet)
        assert snippet.code == "def foo(): pass"
        assert snippet.function_name == "foo"
        assert snippet.file_path == "a.py"
        assert snippet.start_line == 1
        assert snippet.end_line == 5
        assert snippet.revision == "rev1"
        assert snippet.loc == 4
        assert snippet.global_block_id == "block1"

    def test_rule_column_naming(self, rule_applicator, sample_df):
        """Test that rule columns are named correctly."""
        rule1 = MagicMock(spec=DeletionRule)
        rule1.rule_name = "my_rule"
        rule1.apply.return_value = True

        rule2 = MagicMock(spec=DeletionRule)
        rule2.rule_name = "another_rule"
        rule2.apply.return_value = False

        result = rule_applicator.apply_rules(sample_df, [rule1, rule2])

        assert "rule_my_rule" in result.df.columns
        assert "rule_another_rule" in result.df.columns

    def test_rule_apply_receives_code_snippet(self, rule_applicator, sample_df, mock_rule):
        """Test that rule.apply receives CodeSnippet object."""
        rule_applicator.apply_rules(sample_df, [mock_rule])

        # Verify rule.apply was called 2 times (once per method)
        assert mock_rule.apply.call_count == 2

        # Verify it received CodeSnippet objects
        for call in mock_rule.apply.call_args_list:
            arg = call[0][0]
            assert isinstance(arg, CodeSnippet)

    def test_dataframe_not_modified_in_place(self, rule_applicator, sample_df, mock_rule):
        """Test that original DataFrame columns are preserved."""
        original_columns = list(sample_df.columns)
        result = rule_applicator.apply_rules(sample_df, [mock_rule])

        # Original DataFrame should have new column added
        assert "rule_test_rule" in sample_df.columns

        # Result DataFrame should also have the new column
        assert "rule_test_rule" in result.df.columns

        # All original columns should still be present
        for col in original_columns:
            assert col in result.df.columns

    def test_single_method_dataframe(self, rule_applicator, mock_rule):
        """Test applying rules to single-method DataFrame."""
        single_df = pd.DataFrame(
            {
                "global_block_id": ["block1"],
                "revision": ["rev1"],
                "function_name": ["foo"],
                "file_path": ["a.py"],
                "start_line": [1],
                "end_line": [5],
                "loc": [4],
                "state": ["added"],
                "code": ["def foo(): pass"],
                "github_url": ["https://github.com/repo/blob/rev1/a.py#L1-L5"],
            }
        )

        result = rule_applicator.apply_rules(single_df, [mock_rule])

        assert result.rules_applied == 1
        assert result.errors_count == 0
        assert len(result.df) == 1
        assert result.df["rule_test_rule"].iloc[0] == True

    def test_rule_results_order(self, rule_applicator, sample_df):
        """Test that rule results match DataFrame row order."""
        # Create rule that returns different values based on function name
        conditional_rule = MagicMock(spec=DeletionRule)
        conditional_rule.rule_name = "conditional"

        def conditional_apply(snippet):
            return snippet.function_name == "foo"

        conditional_rule.apply.side_effect = conditional_apply

        result = rule_applicator.apply_rules(sample_df, [conditional_rule])

        assert result.df["rule_conditional"].tolist() == [True, False]
        # Verify order matches function names
        assert result.df["function_name"].tolist() == ["foo", "bar"]
