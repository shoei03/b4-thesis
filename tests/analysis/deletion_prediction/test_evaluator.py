"""Tests for Evaluator."""

import pandas as pd
import pytest

from b4_thesis.analysis.deletion_prediction.evaluator import (
    DetailedRuleEvaluation,
    Evaluator,
    MethodClassification,
    RuleEvaluation,
)


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
                "is_deleted_soon": [True, True, False, False],
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
                "is_deleted_soon": [True, True, False, False],
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
                "is_deleted_soon": [True, True, False, False, False],
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

        with pytest.raises(ValueError, match="Missing 'is_deleted_soon' column"):
            evaluator.evaluate(df)

    def test_evaluate_no_rules(self, evaluator):
        """Test error handling when no rule columns exist."""
        df = pd.DataFrame({"is_deleted_soon": [True, False, True, False]})

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

    def test_evaluate_detailed_mode(self, evaluator):
        """Test detailed evaluation mode with per-method classifications."""
        df = pd.DataFrame(
            {
                "rule_test": [True, True, False, False],
                "is_deleted_soon": [True, False, True, False],
                "global_block_id": ["id1", "id2", "id3", "id4"],
                "revision": [
                    "20210101_120000_abc",
                    "20210102_130000_def",
                    "20210103_140000_ghi",
                    "20210104_150000_jkl",
                ],
                "function_name": ["func1", "func2", "func3", "func4"],
                "file_path": ["file1.py", "file2.py", "file3.py", "file4.py"],
                "lifetime_revisions": [5, 3, 10, 2],
                "lifetime_days": [14, 7, 30, 5],
            }
        )

        results = evaluator.evaluate(df, detailed=True)

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, DetailedRuleEvaluation)
        assert result.rule_name == "test"
        assert result.tp == 1  # id1: predicted=True, actual=True
        assert result.fp == 1  # id2: predicted=True, actual=False
        assert result.fn == 1  # id3: predicted=False, actual=True
        assert result.tn == 1  # id4: predicted=False, actual=False

        # Check classifications
        assert result.classifications is not None
        assert len(result.classifications) == 4

        # Verify classification types
        tp_methods = result.get_tp_methods()
        fp_methods = result.get_fp_methods()
        fn_methods = result.get_fn_methods()
        tn_methods = result.get_tn_methods()

        assert len(tp_methods) == 1
        assert len(fp_methods) == 1
        assert len(fn_methods) == 1
        assert len(tn_methods) == 1

        # Check TP method details
        assert tp_methods[0].global_block_id == "id1"
        assert tp_methods[0].function_name == "func1"
        assert tp_methods[0].classification == "TP"
        assert tp_methods[0].predicted is True
        assert tp_methods[0].actual is True
        assert tp_methods[0].lifetime_revisions == 5
        assert tp_methods[0].lifetime_days == 14

    def test_evaluate_detailed_missing_columns(self, evaluator):
        """Test error handling when detailed mode is missing required columns."""
        df = pd.DataFrame(
            {
                "rule_test": [True, False],
                "is_deleted_soon": [True, False],
                # Missing: global_block_id, revision, etc.
            }
        )

        with pytest.raises(ValueError, match="Missing columns required for detailed mode"):
            evaluator.evaluate(df, detailed=True)

    def test_method_classification_to_dict(self):
        """Test MethodClassification.to_dict() method."""
        classification = MethodClassification(
            global_block_id="test_id",
            revision="20210101_120000_abc",
            function_name="test_func",
            file_path="test/file.py",
            classification="TP",
            predicted=True,
            actual=True,
            lifetime_revisions=5,
            lifetime_days=14,
        )

        result_dict = classification.to_dict()

        assert result_dict["global_block_id"] == "test_id"
        assert result_dict["revision"] == "20210101_120000_abc"
        assert result_dict["function_name"] == "test_func"
        assert result_dict["file_path"] == "test/file.py"
        assert result_dict["classification"] == "TP"
        assert result_dict["predicted"] is True
        assert result_dict["actual"] is True
        assert result_dict["lifetime_revisions"] == 5
        assert result_dict["lifetime_days"] == 14

    def test_export_classifications_csv(self, evaluator, tmp_path):
        """Test exporting classifications to CSV files."""
        df = pd.DataFrame(
            {
                "rule_test1": [True, False, True, False],
                "rule_test2": [False, True, False, True],
                "is_deleted_soon": [True, False, False, True],
                "global_block_id": ["id1", "id2", "id3", "id4"],
                "revision": ["r1", "r2", "r3", "r4"],
                "function_name": ["f1", "f2", "f3", "f4"],
                "file_path": ["p1", "p2", "p3", "p4"],
                "lifetime_revisions": [1, 2, 3, 4],
                "lifetime_days": [5, 6, 7, 8],
            }
        )

        results = evaluator.evaluate(df, detailed=True)
        output_dir = tmp_path / "classifications"
        created_files = evaluator.export_classifications_csv(results, output_dir)

        # Check that files were created
        assert len(created_files) == 2
        assert output_dir.exists()

        # Check test1 classifications
        test1_csv = output_dir / "test1_classifications.csv"
        assert test1_csv.exists()
        test1_df = pd.read_csv(test1_csv)
        assert len(test1_df) == 4
        assert "classification" in test1_df.columns
        assert "global_block_id" in test1_df.columns

    def test_export_classifications_csv_with_filter(self, evaluator, tmp_path):
        """Test exporting filtered classifications to CSV."""
        df = pd.DataFrame(
            {
                "rule_test": [True, True, False, False],
                "is_deleted_soon": [True, False, True, False],
                "global_block_id": ["id1", "id2", "id3", "id4"],
                "revision": ["r1", "r2", "r3", "r4"],
                "function_name": ["f1", "f2", "f3", "f4"],
                "file_path": ["p1", "p2", "p3", "p4"],
                "lifetime_revisions": [1, 2, 3, 4],
                "lifetime_days": [5, 6, 7, 8],
            }
        )

        results = evaluator.evaluate(df, detailed=True)
        output_dir = tmp_path / "classifications"

        # Export only FP classifications
        created_files = evaluator.export_classifications_csv(
            results, output_dir, classification_filter="FP"
        )

        # Check that FP file was created
        assert len(created_files) == 1
        fp_csv = output_dir / "test_FP.csv"
        assert fp_csv.exists()
        fp_df = pd.read_csv(fp_csv)
        assert len(fp_df) == 1  # Only one FP method
        assert fp_df.iloc[0]["classification"] == "FP"
        assert fp_df.iloc[0]["global_block_id"] == "id2"

    def test_export_classifications_csv_invalid_results(self, evaluator, tmp_path):
        """Test error handling when exporting non-detailed results."""
        df = pd.DataFrame(
            {
                "rule_test": [True, False],
                "is_deleted_soon": [True, False],
            }
        )

        # Get non-detailed results
        results = evaluator.evaluate(df, detailed=False)
        output_dir = tmp_path / "classifications"

        with pytest.raises(
            ValueError, match="export_classifications_csv requires DetailedRuleEvaluation"
        ):
            evaluator.export_classifications_csv(results, output_dir)

    def test_evaluate_combined_or_logic(self, evaluator):
        """Test combined evaluation with OR logic."""
        df = pd.DataFrame(
            {
                "rule_a": [True, False, False, False],
                "rule_b": [False, True, False, False],
                "is_deleted_soon": [True, True, False, False],
            }
        )

        result = evaluator.evaluate_combined(df)

        # Combined: [True, True, False, False] (OR of rule_a and rule_b)
        # Ground truth: [True, True, False, False]
        assert result.rule_name == "combined_all_rules"
        assert result.tp == 2  # Both deletions caught by combined rules
        assert result.fp == 0
        assert result.fn == 0
        assert result.tn == 2
        assert result.precision == 1.0
        assert result.recall == 1.0
        assert result.f1 == 1.0

    def test_evaluate_combined_detailed_mode(self, evaluator):
        """Test combined evaluation with detailed mode."""
        df = pd.DataFrame(
            {
                "rule_a": [True, False, False, False],
                "rule_b": [False, True, False, False],
                "is_deleted_soon": [True, False, True, False],
                "global_block_id": ["id1", "id2", "id3", "id4"],
                "revision": ["r1", "r2", "r3", "r4"],
                "function_name": ["f1", "f2", "f3", "f4"],
                "file_path": ["p1", "p2", "p3", "p4"],
                "lifetime_revisions": [1, 2, 3, 4],
                "lifetime_days": [5, 6, 7, 8],
            }
        )

        result = evaluator.evaluate_combined(df, detailed=True)

        assert isinstance(result, DetailedRuleEvaluation)
        assert result.rule_name == "combined_all_rules"
        # Combined predictions: [True, True, False, False]
        # Ground truth:         [True, False, True, False]
        assert result.tp == 1  # id1: predicted=True, actual=True
        assert result.fp == 1  # id2: predicted=True, actual=False
        assert result.fn == 1  # id3: predicted=False, actual=True
        assert result.tn == 1  # id4: predicted=False, actual=False

        # Check classifications
        assert result.classifications is not None
        assert len(result.classifications) == 4

    def test_evaluate_with_include_combined(self, evaluator):
        """Test evaluate() with include_combined=True."""
        df = pd.DataFrame(
            {
                "rule_a": [True, False, False, False],
                "rule_b": [False, True, False, False],
                "is_deleted_soon": [True, True, False, False],
            }
        )

        # Without combined
        results_without = evaluator.evaluate(df, include_combined=False)
        assert len(results_without) == 2
        assert all(r.rule_name in ["a", "b"] for r in results_without)

        # With combined
        results_with = evaluator.evaluate(df, include_combined=True)
        assert len(results_with) == 3
        assert results_with[-1].rule_name == "combined_all_rules"
        # Combined should have perfect scores in this case
        combined = results_with[-1]
        assert combined.tp == 2
        assert combined.fp == 0
        assert combined.fn == 0
        assert combined.tn == 2

    def test_evaluate_combined_missing_ground_truth(self, evaluator):
        """Test error handling when ground truth column is missing."""
        df = pd.DataFrame({"rule_test": [True, False, True, False]})

        with pytest.raises(ValueError, match="Missing 'is_deleted_soon' column"):
            evaluator.evaluate_combined(df)

    def test_evaluate_combined_no_rules(self, evaluator):
        """Test error handling when no rule columns exist."""
        df = pd.DataFrame({"is_deleted_soon": [True, False, True, False]})

        with pytest.raises(ValueError, match="No rule columns found"):
            evaluator.evaluate_combined(df)
