from pathlib import Path

import numpy as np
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

    merged_df = merged_df[merged_df["is_deleted_soon"] != "unknown"]

    # Extract all rule_* columns
    rule_columns = [col for col in merged_df.columns if col.startswith("rule_")]

    # Create predict_class: class_*_deleted if ANY rule is True, else class_*_survived
    merged_df["predict_class"] = np.where(
        merged_df[rule_columns].any(axis=1), "class_*_deleted", "class_*_survived"
    )

    # Evaluate prediction accuracy
    merged_df["is_correct"] = (
        (merged_df["predict_class"] == "class_*_deleted")
        & merged_df["is_deleted_soon"].str.contains("deleted")
    ) | (
        (merged_df["predict_class"] == "class_*_survived")
        & merged_df["is_deleted_soon"].str.contains("survived")
    )

    merged_df.to_csv(
        output,
        index=False,
        columns=[
            "global_block_id",
            "revision",
            "predict_class",
            "is_deleted_soon",
            "is_correct",
        ],
    )
    print(f"Evaluation results saved to {output}")
