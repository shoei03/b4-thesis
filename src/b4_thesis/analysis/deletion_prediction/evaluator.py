"""Evaluation engine for deletion prediction rules."""

from dataclasses import dataclass

import pandas as pd
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score


@dataclass
class RuleEvaluation:
    """Evaluation results for a single deletion prediction rule.

    Attributes:
        rule_name: Name of the rule
        tp: True positives (correctly predicted deletions)
        fp: False positives (incorrectly predicted deletions)
        fn: False negatives (missed deletions)
        tn: True negatives (correctly predicted survivals)
        precision: TP / (TP + FP) - how many predicted deletions were correct
        recall: TP / (TP + FN) - how many actual deletions were caught
        f1: Harmonic mean of precision and recall
    """

    rule_name: str
    tp: int
    fp: int
    fn: int
    tn: int
    precision: float
    recall: float
    f1: float

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with all evaluation metrics
        """
        return {
            "rule_name": self.rule_name,
            "TP": self.tp,
            "FP": self.fp,
            "FN": self.fn,
            "TN": self.tn,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
        }


class Evaluator:
    """Evaluate deletion prediction rules.

    Calculates Precision, Recall, F1, and confusion matrix for each rule
    by comparing rule predictions against ground truth labels.
    """

    def evaluate(self, features_df: pd.DataFrame) -> list[RuleEvaluation]:
        """Evaluate all rules in the features DataFrame.

        Args:
            features_df: DataFrame with rule_XXX columns and is_deleted_next column

        Returns:
            List of RuleEvaluation objects, one per rule

        Raises:
            ValueError: If is_deleted_next column is missing
            ValueError: If no rule columns found
        """
        # Validate ground truth column
        if "is_deleted_next" not in features_df.columns:
            raise ValueError("Missing 'is_deleted_next' column in features DataFrame")

        # Find all rule columns
        rule_columns = [col for col in features_df.columns if col.startswith("rule_")]
        if not rule_columns:
            raise ValueError("No rule columns found (columns starting with 'rule_')")

        # Get ground truth
        ground_truth = features_df["is_deleted_next"]

        # Evaluate each rule
        results = []
        for rule_col in rule_columns:
            predictions = features_df[rule_col]
            rule_name = rule_col.replace("rule_", "")

            # Calculate metrics
            precision = precision_score(ground_truth, predictions, zero_division=0)
            recall = recall_score(ground_truth, predictions, zero_division=0)
            f1 = f1_score(ground_truth, predictions, zero_division=0)

            # Calculate confusion matrix
            tn, fp, fn, tp = confusion_matrix(ground_truth, predictions).ravel()

            results.append(
                RuleEvaluation(
                    rule_name=rule_name,
                    tp=int(tp),
                    fp=int(fp),
                    fn=int(fn),
                    tn=int(tn),
                    precision=float(precision),
                    recall=float(recall),
                    f1=float(f1),
                )
            )

        return results

    def print_summary(self, results: list[RuleEvaluation]) -> None:
        """Print evaluation summary to console.

        Args:
            results: List of RuleEvaluation objects
        """
        print("\n" + "=" * 80)
        print("Deletion Prediction Rule Evaluation Summary")
        print("=" * 80)

        for result in results:
            print(f"\nRule: {result.rule_name}")
            print(f"  TP: {result.tp:6d}  FP: {result.fp:6d}")
            print(f"  FN: {result.fn:6d}  TN: {result.tn:6d}")
            print(
                f"  Precision: {result.precision:.4f}  "
                f"Recall: {result.recall:.4f}  "
                f"F1: {result.f1:.4f}"
            )

        print("\n" + "=" * 80)
