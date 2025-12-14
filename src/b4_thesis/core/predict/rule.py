from pathlib import Path

import pandas as pd

from b4_thesis.rules.applicator import RuleApplicator
from b4_thesis.rules.deletion_prediction.registry import get_rules


def rule(input_snippets: Path, input_metadata: Path, output: Path, rules: str | None):
    snippets_df = pd.read_csv(input_snippets)
    metadata_df = pd.read_csv(input_metadata)

    merged_df = snippets_df.merge(
        metadata_df,
        on=["global_block_id", "revision"],
        how="inner",
    )

    rule_applicator = RuleApplicator()
    rule_result_df = rule_applicator.apply_rules(merged_df, get_rules(rules))

    rule_result_df = rule_result_df.drop(
        columns=["function_name", "file_path", "start_line", "end_line", "loc", "code"]
    )
    rule_result_df = rule_result_df.sort_values(by=["global_block_id", "revision"]).reset_index(
        drop=True
    )
    rule_result_df.to_csv(output, index=False)
    print(f"Rule results saved to {output}")
