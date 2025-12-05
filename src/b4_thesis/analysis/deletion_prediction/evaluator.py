"""Evaluation engine for deletion prediction rules."""

from dataclasses import dataclass
from pathlib import Path

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


@dataclass
class MethodClassification:
    """Classification result for a single method.

    Attributes:
        global_block_id: Unique identifier for the method
        revision: Revision timestamp
        function_name: Name of the method
        file_path: Full path to the file
        classification: Classification category (TP/FP/FN/TN)
        predicted: Rule prediction (True = predicts deletion)
        actual: Ground truth (True = actually deleted)
        lifetime_revisions: Number of revisions method appeared in
        lifetime_days: Number of days between first and last appearance
    """

    global_block_id: str
    revision: str
    function_name: str
    file_path: str
    classification: str  # "TP", "FP", "FN", "TN"
    predicted: bool
    actual: bool
    lifetime_revisions: int
    lifetime_days: int

    def to_dict(self) -> dict:
        """Convert to dictionary for CSV export.

        Returns:
            Dictionary with all classification data
        """
        return {
            "global_block_id": self.global_block_id,
            "revision": self.revision,
            "function_name": self.function_name,
            "file_path": self.file_path,
            "classification": self.classification,
            "predicted": self.predicted,
            "actual": self.actual,
            "lifetime_revisions": self.lifetime_revisions,
            "lifetime_days": self.lifetime_days,
        }


@dataclass
class DetailedRuleEvaluation(RuleEvaluation):
    """Extended evaluation with per-method classification.

    Attributes:
        Inherits all attributes from RuleEvaluation
        classifications: List of MethodClassification objects for each method
    """

    classifications: list[MethodClassification] | None = None

    def get_tp_methods(self) -> list[MethodClassification]:
        """Get methods classified as True Positives.

        Returns:
            List of MethodClassification objects with classification="TP"
        """
        if self.classifications is None:
            return []
        return [c for c in self.classifications if c.classification == "TP"]

    def get_fp_methods(self) -> list[MethodClassification]:
        """Get methods classified as False Positives.

        Returns:
            List of MethodClassification objects with classification="FP"
        """
        if self.classifications is None:
            return []
        return [c for c in self.classifications if c.classification == "FP"]

    def get_fn_methods(self) -> list[MethodClassification]:
        """Get methods classified as False Negatives.

        Returns:
            List of MethodClassification objects with classification="FN"
        """
        if self.classifications is None:
            return []
        return [c for c in self.classifications if c.classification == "FN"]

    def get_tn_methods(self) -> list[MethodClassification]:
        """Get methods classified as True Negatives.

        Returns:
            List of MethodClassification objects with classification="TN"
        """
        if self.classifications is None:
            return []
        return [c for c in self.classifications if c.classification == "TN"]


class Evaluator:
    """Evaluate deletion prediction rules.

    Calculates Precision, Recall, F1, and confusion matrix for each rule
    by comparing rule predictions against ground truth labels.
    """

    def _evaluate_predictions(
        self,
        features_df: pd.DataFrame,
        predictions: pd.Series,
        rule_name: str,
        detailed: bool,
    ) -> RuleEvaluation | DetailedRuleEvaluation:
        """Evaluate a single set of predictions against ground truth.

        Args:
            features_df: DataFrame with ground truth and metadata columns
            predictions: Boolean Series of predictions
            rule_name: Name for this rule/prediction set
            detailed: If True, include per-method classification details

        Returns:
            RuleEvaluation or DetailedRuleEvaluation object
        """
        ground_truth = features_df["is_deleted_soon"]

        # Calculate metrics
        precision = precision_score(ground_truth, predictions, zero_division=0)
        recall = recall_score(ground_truth, predictions, zero_division=0)
        f1 = f1_score(ground_truth, predictions, zero_division=0)

        # Calculate confusion matrix
        # Use labels=[False, True] to ensure 2x2 matrix even if one class is missing
        tn, fp, fn, tp = confusion_matrix(ground_truth, predictions, labels=[False, True]).ravel()

        if detailed:
            # Create MethodClassification objects for each method
            classifications = []
            for idx, row in features_df.iterrows():
                predicted = bool(
                    predictions.iloc[idx] if hasattr(predictions, "iloc") else predictions[idx]
                )
                actual = bool(row["is_deleted_soon"])

                # Determine classification
                if predicted and actual:
                    classification = "TP"
                elif predicted and not actual:
                    classification = "FP"
                elif not predicted and actual:
                    classification = "FN"
                else:
                    classification = "TN"

                classifications.append(
                    MethodClassification(
                        global_block_id=str(row["global_block_id"]),
                        revision=str(row["revision"]),
                        function_name=str(row["function_name"]),
                        file_path=str(row["file_path"]),
                        classification=classification,
                        predicted=predicted,
                        actual=actual,
                        lifetime_revisions=int(row["lifetime_revisions"]),
                        lifetime_days=int(row["lifetime_days"]),
                    )
                )

            return DetailedRuleEvaluation(
                rule_name=rule_name,
                tp=int(tp),
                fp=int(fp),
                fn=int(fn),
                tn=int(tn),
                precision=float(precision),
                recall=float(recall),
                f1=float(f1),
                classifications=classifications,
            )
        else:
            return RuleEvaluation(
                rule_name=rule_name,
                tp=int(tp),
                fp=int(fp),
                fn=int(fn),
                tn=int(tn),
                precision=float(precision),
                recall=float(recall),
                f1=float(f1),
            )

    def evaluate_combined(
        self, features_df: pd.DataFrame, detailed: bool = False
    ) -> RuleEvaluation | DetailedRuleEvaluation:
        """Evaluate all rules combined with OR logic.

        A method is predicted as deleted if ANY rule predicts deletion.

        Args:
            features_df: DataFrame with rule_XXX columns and is_deleted_soon column
            detailed: If True, include per-method classification details

        Returns:
            RuleEvaluation (or DetailedRuleEvaluation if detailed=True)
            with rule_name="combined_all_rules"

        Raises:
            ValueError: If is_deleted_soon column is missing
            ValueError: If no rule columns found
            ValueError: If detailed=True but required columns are missing
        """
        # Validate ground truth column
        if "is_deleted_soon" not in features_df.columns:
            raise ValueError("Missing 'is_deleted_soon' column in features DataFrame")

        # Find all rule columns
        rule_columns = [col for col in features_df.columns if col.startswith("rule_")]
        if not rule_columns:
            raise ValueError("No rule columns found (columns starting with 'rule_')")

        # Validate columns needed for detailed mode
        if detailed:
            required_cols = [
                "global_block_id",
                "revision",
                "function_name",
                "file_path",
                "lifetime_revisions",
                "lifetime_days",
            ]
            missing_cols = [col for col in required_cols if col not in features_df.columns]
            if missing_cols:
                raise ValueError(
                    f"Missing columns required for detailed mode: {', '.join(missing_cols)}"
                )

        # Combine all rules with OR logic (any rule predicts True → combined predicts True)
        combined_predictions = features_df[rule_columns].any(axis=1)

        return self._evaluate_predictions(
            features_df, combined_predictions, "combined_all_rules", detailed
        )

    def evaluate(
        self,
        features_df: pd.DataFrame,
        detailed: bool = False,
        include_combined: bool = False,
    ) -> list[RuleEvaluation] | list[DetailedRuleEvaluation]:
        """Evaluate all rules in the features DataFrame.

        Args:
            features_df: DataFrame with rule_XXX columns and is_deleted_soon column
            detailed: If True, include per-method classification details
            include_combined: If True, append combined evaluation (OR logic) to results

        Returns:
            List of RuleEvaluation objects (or DetailedRuleEvaluation if detailed=True)

        Raises:
            ValueError: If is_deleted_soon column is missing
            ValueError: If no rule columns found
            ValueError: If detailed=True but required columns are missing
        """
        # Validate ground truth column
        if "is_deleted_soon" not in features_df.columns:
            raise ValueError("Missing 'is_deleted_soon' column in features DataFrame")

        # Find all rule columns
        rule_columns = [col for col in features_df.columns if col.startswith("rule_")]
        if not rule_columns:
            raise ValueError("No rule columns found (columns starting with 'rule_')")

        # Validate columns needed for detailed mode
        if detailed:
            required_cols = [
                "global_block_id",
                "revision",
                "function_name",
                "file_path",
                "lifetime_revisions",
                "lifetime_days",
            ]
            missing_cols = [col for col in required_cols if col not in features_df.columns]
            if missing_cols:
                raise ValueError(
                    f"Missing columns required for detailed mode: {', '.join(missing_cols)}"
                )

        # Evaluate each rule
        results = []
        for rule_col in rule_columns:
            predictions = features_df[rule_col]
            rule_name = rule_col.replace("rule_", "")
            result = self._evaluate_predictions(features_df, predictions, rule_name, detailed)
            results.append(result)

        # Optionally add combined evaluation
        if include_combined:
            combined_result = self.evaluate_combined(features_df, detailed)
            results.append(combined_result)

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

    def export_classifications_csv(
        self,
        results: list[DetailedRuleEvaluation],
        output_dir: Path,
        classification_filter: str | None = None,
    ) -> list[Path]:
        """Export classification details to CSV files.

        Creates one CSV file per rule with method-level classification data.

        Args:
            results: List of DetailedRuleEvaluation objects with classifications
            output_dir: Directory to save CSV files
            classification_filter: Optional filter for classification type (TP/FP/FN/TN)

        Returns:
            List of Path objects for created CSV files

        Raises:
            ValueError: If results contain RuleEvaluation instead of DetailedRuleEvaluation
            ValueError: If output_dir doesn't exist or isn't a directory
        """
        # Validate output directory
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)
        if not output_dir.is_dir():
            raise ValueError(f"Output path is not a directory: {output_dir}")

        # Validate results have classifications
        for result in results:
            if not isinstance(result, DetailedRuleEvaluation):
                raise ValueError(
                    "export_classifications_csv requires DetailedRuleEvaluation objects. "
                    "Call evaluate() with detailed=True"
                )
            if result.classifications is None:
                raise ValueError(
                    f"Rule {result.rule_name} has no classifications. "
                    "Call evaluate() with detailed=True"
                )

        # Validate classification filter
        if classification_filter and classification_filter not in ["TP", "FP", "FN", "TN"]:
            raise ValueError(
                f"Invalid classification filter: {classification_filter}. "
                "Must be one of: TP, FP, FN, TN"
            )

        created_files = []
        for result in results:
            # Get classifications (optionally filtered)
            classifications = result.classifications
            if classification_filter:
                classifications = [
                    c for c in classifications if c.classification == classification_filter
                ]

            # Skip if no classifications after filtering
            if not classifications:
                continue

            # Convert to DataFrame
            data = [c.to_dict() for c in classifications]
            df = pd.DataFrame(data)

            # Generate filename
            filename_suffix = (
                f"_{classification_filter}" if classification_filter else "_classifications"
            )
            output_path = output_dir / f"{result.rule_name}{filename_suffix}.csv"

            # Export to CSV
            df.to_csv(output_path, index=False)
            created_files.append(output_path)

        return created_files
