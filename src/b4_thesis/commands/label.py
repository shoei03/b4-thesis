from pathlib import Path

import click
import pandas as pd
from rich.console import Console

from b4_thesis.core.track.cross_revision_matcher import CrossRevisionMatcher
from b4_thesis.const.column import ColumnNames
from b4_thesis.utils.revision_manager import RevisionManager
from b4_thesis.utils.sig_match import apply_signature_matching, pre_process, validate_counts

console = Console()


@click.group()
def label():
    """Track method evolution across revisions."""
    pass


@label.command()
@click.option(
    "--input",
    "-i",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    required=True,
    default="./data/versions",
    help="Input directory containing revision subdirectories",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    required=False,
    default="./output/versions/labels/intermediate/signature_match_labels.csv",
    help="Output CSV for signature-based label candidates",
)
def track_sig(
    input: str,
    output: str,
) -> None:
    """Track method evolution across revisions based on signature."""
    df = pd.DataFrame()

    revision_manager = RevisionManager()
    revisions = revision_manager.get_revisions(Path(input))

    for prev_rev, curr_rev in zip(revisions[:-1], revisions[1:]):
        console.print(f"Processing revision pair: {prev_rev.timestamp} -> {curr_rev.timestamp}")

        prev_code_blocks = revision_manager.load_code_blocks(prev_rev)
        curr_code_blocks = revision_manager.load_code_blocks(curr_rev)

        prev_code_blocks, curr_code_blocks = pre_process(prev_code_blocks, curr_code_blocks)

        matched_df = apply_signature_matching(prev_code_blocks, curr_code_blocks)

        df = pd.concat([df, matched_df], ignore_index=True)

        validate_counts(prev_code_blocks, matched_df, prev_rev.timestamp)

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    console.print(f"[green]Results saved to:[/green] {output_path}")


@label.command()
@click.option(
    "--similarity",
    type=click.FloatRange(0.0, 1.0),
    default=0.7,
    help="LCS similarity threshold for method matching (0.0-1.0, default: 0.7)",
)
@click.option(
    "--n-gram-size",
    type=click.IntRange(1),
    default=5,
    help="Size of N-grams for indexing (default: 5)",
)
@click.option(
    "--filter-threshold",
    type=click.FloatRange(0.0, 1.0),
    default=0.1,
    help="N-gram overlap threshold for filtration (0.0-1.0, default: 0.1)",
)
@click.option(
    "--input",
    "-i",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    required=True,
    default="./data/versions",
    help="Input directory containing revision subdirectories",
)
@click.option(
    "--output",
    "-o",
    default="./output/versions/labels/intermediate/similarity_match_labels.csv",
    type=click.Path(file_okay=True, dir_okay=False),
    required=True,
    help="Output CSV for similarity-based label candidates",
)
def track_sim(
    input: str,
    output: str,
    similarity: float,
    n_gram_size: int,
    filter_threshold: float,
) -> None:
    """Track method evolution across revisions based on similarity."""
    revision_manager = RevisionManager()
    cross_revision_matcher = CrossRevisionMatcher(
        n_gram_size=n_gram_size,
        filter_threshold=filter_threshold,
        verify_threshold=similarity,
    )

    revisions = revision_manager.get_revisions(Path(input))

    all_results: list[dict] = []

    for prev_revision, curr_revision in zip(revisions[:-1], revisions[1:]):
        console.print(f"Revision {prev_revision.timestamp} -> {curr_revision.timestamp}")

        prev_code_blocks = revision_manager.load_code_blocks(prev_revision)
        curr_code_blocks = revision_manager.load_code_blocks(curr_revision)

        # Use NIL-based cross-revision matching
        match_results = cross_revision_matcher.match_revisions_with_changes(
            prev_code_blocks, curr_code_blocks
        )

        all_results.extend(match_results)

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(all_results).to_csv(output_path, index=False)

    console.print(f"[green]Results saved to:[/green] {output_path}")


@label.command()
@click.option(
    "--input-sim",
    "-i",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    required=False,
    default="./output/versions/labels/intermediate/similarity_match_labels.csv",
    help="Input CSV containing similarity-based label candidates",
)
@click.option(
    "--input-sig",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    required=False,
    default="./output/versions/labels/intermediate/signature_match_labels.csv",
    help="Input CSV containing signature-based label candidates",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    required=False,
    default="./output/versions/labels/final/method_transition_labels.csv",
    help="Output CSV for merged method-transition labels",
)
def track_sim_sig(
    input_sim: str,
    input_sig: str,
    output: str,
):
    """Evaluate false positives in method tracking results."""

    merge_cols = [
        ColumnNames.PREV_REVISION_ID.value,
        ColumnNames.PREV_TOKEN_HASH.value,
        ColumnNames.PREV_FILE_PATH.value,
        ColumnNames.PREV_METHOD_NAME.value,
        ColumnNames.PREV_RETURN_TYPE.value,
        ColumnNames.PREV_PARAMETERS.value,
    ]

    df_sim = pd.read_csv(
        input_sim,
        usecols=merge_cols
        + [
            ColumnNames.CURR_REVISION_ID.value,
            ColumnNames.CURR_FILE_PATH.value,
            ColumnNames.CURR_METHOD_NAME.value,
            ColumnNames.CURR_RETURN_TYPE.value,
            ColumnNames.CURR_PARAMETERS.value,
            "similarity",
            "is_sim_matched",
            "is_sim_deleted",
            "is_sim_added",
        ],
        dtype={
            **{col: "string" for col in merge_cols},
            ColumnNames.CURR_FILE_PATH.value: "string",
            ColumnNames.CURR_METHOD_NAME.value: "string",
            ColumnNames.CURR_RETURN_TYPE.value: "string",
            ColumnNames.CURR_PARAMETERS.value: "string",
            "similarity": "float64",
            "is_sim_matched": "boolean",
            "is_sim_deleted": "boolean",
            "is_sim_added": "boolean",
        },
        low_memory=False,
    )

    df_sig = pd.read_csv(
        input_sig,
        usecols=merge_cols + ["is_sig_matched", "is_sig_deleted", "is_sig_added"],
        dtype={
            **{col: "string" for col in merge_cols},
            "is_sig_matched": "boolean",
            "is_sig_deleted": "boolean",
            "is_sig_added": "boolean",
        },
    )

    console.print(f"df_sim: {len(df_sim)}")
    console.print(f"df_sig: {len(df_sig)}")

    df_sig_sorted = df_sig.sort_values(by="is_sig_matched", ascending=True)

    sig_dict = {}
    for _, row in df_sig_sorted.iterrows():
        key = "|".join(str(row[col]) for col in merge_cols)
        sig_dict[key] = (row["is_sig_matched"], row["is_sig_deleted"], row["is_sig_added"])

    console.print(f"sig_dict size: {len(sig_dict)}")

    keys = df_sim[merge_cols].astype(str).agg("|".join, axis=1)

    sig_info = keys.map(sig_dict)
    df_sim["is_sig_matched"] = sig_info.apply(lambda x: x[0] if x is not None else False)
    df_sim["is_sig_deleted"] = sig_info.apply(lambda x: x[1] if x is not None else False)
    df_sim["is_sig_added"] = sig_info.apply(lambda x: x[2] if x is not None else False)

    df_result = (
        df_sim.sort_values(by=["is_sig_matched", "similarity"], ascending=[False, False])
        .drop_duplicates(subset=merge_cols, keep="first")
        .copy()
    )

    console.print(f"After dropping duplicates df_sim: {len(df_result)}")

    # Calculate final flags
    df_result["is_matched"] = df_result["is_sig_matched"] | df_result["is_sim_matched"]
    df_result["is_deleted"] = df_result["is_sig_deleted"] & df_result["is_sim_deleted"]
    df_result["is_added"] = ~df_result["is_matched"] & ~df_result["is_deleted"]

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_result.to_csv(output_path, index=False)
    console.print(f"[green]Results saved to:[/green] {output_path}")
