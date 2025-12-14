"""Rule applicator for deletion prediction feature extraction."""

import numpy as np
import pandas as pd
from tqdm import tqdm

from b4_thesis.rules.base import CodeSnippet, DeletionRule


class RuleApplicator:
    def apply_rules(self, df: pd.DataFrame, rules: list[DeletionRule]) -> pd.DataFrame:
        """Apply rules to methods in DataFrame.

        Args:
            df: DataFrame with 'code' column and method metadata
            rules: List of DeletionRule instances to apply

        Returns:
            DataFrame with rule_* columns added
        """
        snippets = self._create_snippets(df)

        for rule in tqdm(rules, desc="Applying rules"):
            df[f"rule_{rule.rule_name}"] = self._apply_rule(rule, snippets)

        return df

    def _apply_rule(self, rule: DeletionRule, snippets: list[CodeSnippet]) -> np.ndarray:
        """Apply a single rule to all snippets."""
        results = np.empty(len(snippets), dtype=bool)

        for i, snippet in enumerate(snippets):
            try:
                results[i] = rule.apply(snippet)
            except Exception as e:
                print(f"Warning: Rule {rule.rule_name} failed on {snippet.function_name}: {e}")
                results[i] = False

        return results

    def _create_snippets(self, df: pd.DataFrame) -> list[CodeSnippet]:
        """Create CodeSnippet objects from DataFrame."""
        cols = {col: df[col].values for col in df.columns}

        return [
            CodeSnippet(
                code=cols["code"][i],
                function_name=cols["function_name"][i],
                file_path=cols["file_path"][i],
                start_line=cols["start_line"][i],
                end_line=cols["end_line"][i],
                revision=cols["revision"][i],
                loc=cols["loc"][i],
                global_block_id=cols["global_block_id"][i],
            )
            for i in range(len(df))
        ]
