from pathlib import Path

import pandas as pd

from b4_thesis.analysis.code_extractor import ExtractRequest, GitCodeExtractor


def extract_snippets(
    input_csv: Path,
    repo: Path,
    output: Path,
    base_prefix: str,
):
    method_lineage_df = pd.read_csv(
        input_csv,
        usecols=[
            "global_block_id",
            "function_name",
            "file_path",
            "revision",
            "start_line",
            "end_line",
            "state",
        ],
    )

    non_deleted_df = method_lineage_df[method_lineage_df["state"] != "deleted"]

    requests = [
        ExtractRequest(
            function_name=row.function_name,
            file_path=row.file_path,
            revision=row.revision,
            start_line=row.start_line,
            end_line=row.end_line,
            global_block_id=row.global_block_id,
        )
        for row in non_deleted_df.itertuples()
    ]

    code_extractor = GitCodeExtractor(
        repo_path=repo,
        base_path_prefix=base_prefix,
    )
    code_snippets_raw = code_extractor.batch_extract(requests)

    snippets_df = pd.DataFrame(
        {
            "global_block_id": non_deleted_df["global_block_id"].values,
            "revision": non_deleted_df["revision"].values,
            "code": [snippet.code for snippet in code_snippets_raw],
        }
    )

    snippets_df.to_csv(output, index=False)
