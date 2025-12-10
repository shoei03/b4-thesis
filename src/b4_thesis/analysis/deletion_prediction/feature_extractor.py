"""Feature extraction engine for deletion prediction."""

import pandas as pd
from rich.console import Console

from b4_thesis.analysis.deletion_prediction.extraction import (
    RuleApplicator,
)
from b4_thesis.analysis.deletion_prediction.rules import get_all_rules, get_rules_by_name

console = Console()


class FeatureExtractor:
    """Extract deletion prediction features from method lineage CSV.

    This class coordinates:
    1. CSV loading and validation (CsvDataLoader)
    2. Code snippet extraction (SnippetLoader)
    3. Rule application (RuleApplicator)
    4. Label generation (LabelGenerator)
    """

    def __init__(
        self
    ):
        """Initialize FeatureExtractor.

        Args:
            repo_path: Path to git repository
            base_path_prefix: Prefix to remove from file paths in CSV
            github_base_url: GitHub base URL for permalink generation
            lookahead_window: Number of future revisions to check for deletion
                             (default: 5)
        """
        self.rule_applicator = RuleApplicator()

    def apply_rules(
        self,
        df: pd.DataFrame,
        rule_names: list[str] | None = None,
    ) -> pd.DataFrame:
        """Apply deletion prediction rules to DataFrame.

        Args:
            df: DataFrame with code snippets
            rule_names: List of rule names to apply (None = all rules)

        Returns:
            DataFrame with rule_XXX columns added
        """
        rules = get_all_rules() if rule_names is None else get_rules_by_name(rule_names)

        console.print(f"  Applying {len(rules)} deletion prediction rules...")
        rule_result = self.rule_applicator.apply_rules(df, rules)

        return rule_result.df
