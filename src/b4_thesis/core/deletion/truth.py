from pathlib import Path

import pandas as pd

from b4_thesis.analysis.deletion_prediction.label_generator import LabelGenerator


def deletion_truth(input: Path, output: Path, lookahead_window: int):
    method_lineage_df = pd.read_csv(
        input,
        usecols=[
            "global_block_id",
            "revision",
            "state",
            "rev_status",
        ],
    )

    label_generator = LabelGenerator(lookahead_window=lookahead_window)
    labeled_df = label_generator.generate_labels(method_lineage_df)

    output.parent.mkdir(parents=True, exist_ok=True)
    labeled_df.to_csv(
        output,
        index=False,
        columns=[
            "global_block_id",
            "revision",
            "state_with_clone",
            "is_deleted_soon",
        ],
    )
