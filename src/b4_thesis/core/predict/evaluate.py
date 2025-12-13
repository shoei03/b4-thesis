from pathlib import Path

import pandas as pd


def evaluate(
    feature_csv: Path,
    target_csv: Path,
    output: Path,
):
    feature_df = pd.read_csv(feature_csv)
    target_df = pd.read_csv(target_csv)

    merged_df = feature_df.merge(
        target_df,
        on=["global_block_id", "revision"],
        how="inner",
    )

    # Extract all rule_* columns
    rule_columns = [col for col in merged_df.columns if col.startswith("rule_")]

    # Create predict_class: True if ANY rule is True, else False
    merged_df["predict_class"] = merged_df[rule_columns].any(axis=1)

    merged_df.to_csv(output, index=False)
    print(f"Evaluation results saved to {output}")
