"""Tests for Evaluator."""

import pandas as pd
import pytest

from b4_thesis.analysis.deletion_prediction.evaluator import Evaluator, RuleEvaluation


class TestEvaluator:
    """Test cases for Evaluator."""

    @pytest.fixture
    def evaluator(self):
        """Create Evaluator instance."""
        return Evaluator()

    def test_evaluate_perfect_rule(self, evaluator):
        """Test evaluation of a perfect rule."""
        df = pd.DataFrame(
            {
                "rule_perfect": [True, True, False, False],
                "is_deleted_next": [True, True, False, False],
            }
        )

        results = evaluator.evaluate(df)

        assert len(results) == 1
        result = results[0]
        assert result.rule_name == "perfect"
        assert result.tp == 2
        assert result.fp == 0
        assert result.fn == 0
        assert result.tn == 2
        assert result.precision == 1.0
        assert result.recall == 1.0
        assert result.f1 == 1.0

    def test_evaluate_poor_rule(self, evaluator):
        """Test evaluation of a rule that always predicts negative."""
        df = pd.DataFrame(
            {
                "rule_always_false": [False, False, False, False],
                "is_deleted_next": [True, True, False, False],
            }
        )

        results = evaluator.evaluate(df)

        assert len(results) == 1
        result = results[0]
        assert result.rule_name == "always_false"
        assert result.tp == 0
        assert result.fp == 0
        assert result.fn == 2
        assert result.tn == 2
        assert result.precision == 0.0
        assert result.recall == 0.0
        assert result.f1 == 0.0

    def test_evaluate_multiple_rules(self, evaluator):
        """Test evaluation of multiple rules."""
        df = pd.DataFrame(
            {
                "rule_good": [True, True, False, False, True],
                "rule_bad": [False, False, True, True, False],
                "is_deleted_next": [True, True, False, False, False],
            }
        )

        results = evaluator.evaluate(df)

        assert len(results) == 2

        # Check good rule
        good_result = next(r for r in results if r.rule_name == "good")
        assert good_result.tp == 2  # Correctly predicted 2 deletions
        assert good_result.fp == 1  # Incorrectly predicted 1 deletion
        assert good_result.fn == 0  # Missed 0 deletions
        assert good_result.tn == 2  # Correctly predicted 2 survivals

        # Check bad rule (inverse predictions)
        bad_result = next(r for r in results if r.rule_name == "bad")
        assert bad_result.tp == 0
        assert bad_result.fp == 2
        assert bad_result.fn == 2
        assert bad_result.tn == 1

    def test_evaluate_missing_ground_truth(self, evaluator):
        """Test error handling when ground truth column is missing."""
        df = pd.DataFrame({"rule_test": [True, False, True, False]})

        with pytest.raises(ValueError, match="Missing 'is_deleted_next' column"):
            evaluator.evaluate(df)

    def test_evaluate_no_rules(self, evaluator):
        """Test error handling when no rule columns exist."""
        df = pd.DataFrame({"is_deleted_next": [True, False, True, False]})

        with pytest.raises(ValueError, match="No rule columns found"):
            evaluator.evaluate(df)

    def test_rule_evaluation_to_dict(self):
        """Test RuleEvaluation.to_dict() method."""
        result = RuleEvaluation(
            rule_name="test_rule",
            tp=10,
            fp=5,
            fn=3,
            tn=82,
            precision=0.6667,
            recall=0.7692,
            f1=0.7143,
        )

        result_dict = result.to_dict()

        assert result_dict["rule_name"] == "test_rule"
        assert result_dict["TP"] == 10
        assert result_dict["FP"] == 5
        assert result_dict["FN"] == 3
        assert result_dict["TN"] == 82
        assert result_dict["precision"] == 0.6667
        assert result_dict["recall"] == 0.7692
        assert result_dict["f1"] == 0.7143
