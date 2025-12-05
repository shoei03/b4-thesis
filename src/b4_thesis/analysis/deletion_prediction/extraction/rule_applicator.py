"""Rule applicator for deletion prediction feature extraction."""

import pandas as pd
from tqdm import tqdm

from b4_thesis.analysis.deletion_prediction.extraction.result_types import (
    RuleApplicationResult,
)
from b4_thesis.analysis.deletion_prediction.rule_base import CodeSnippet, DeletionRule


class RuleApplicator:
    """Apply deletion prediction rules to code snippets.

    This component handles:
    - Creating CodeSnippet objects from DataFrame
    - Applying rules with error handling
    - Adding rule columns to DataFrame
    """

    def apply_rules(
        self,
        df: pd.DataFrame,
        rules: list[DeletionRule],
    ) -> RuleApplicationResult:
        """Apply rules to methods in DataFrame.

        Args:
            df: DataFrame with 'code' column and method metadata
            rules: List of DeletionRule instances to apply

        Returns:
            RuleApplicationResult with DataFrame containing rule_* columns
        """
        # Create CodeSnippet objects from DataFrame
        code_snippets = [self._create_code_snippet(row) for row in df.itertuples()]

        # Apply rules
        errors_count = 0
        for rule in tqdm(rules, desc="Applying rules"):
            rule_results = []
            for snippet in code_snippets:
                try:
                    result = rule.apply(snippet)
                    rule_results.append(result)
                except Exception as e:
                    # If rule application fails, assume False (no deletion sign)
                    print(
                        f"Warning: Rule {rule.rule_name} failed on "
                        f"{snippet.function_name} (revision {snippet.revision}): {e}"
                    )
                    rule_results.append(False)
                    errors_count += 1

            df[f"rule_{rule.rule_name}"] = rule_results

        return RuleApplicationResult(
            df=df,
            rules_applied=len(rules),
            errors_count=errors_count,
        )

    def _create_code_snippet(self, row) -> CodeSnippet:
        """Create CodeSnippet from DataFrame row.

        Args:
            row: DataFrame row (itertuples result)

        Returns:
            CodeSnippet instance
        """
        return CodeSnippet(
            code=row.code,
            function_name=row.function_name,
            file_path=row.file_path,
            start_line=row.start_line,
            end_line=row.end_line,
            revision=row.revision,
            loc=row.loc,
            global_block_id=row.global_block_id,
        )
