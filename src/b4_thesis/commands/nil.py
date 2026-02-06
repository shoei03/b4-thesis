import json
from pathlib import Path

import click
import matplotlib.pyplot as plt
import pandas as pd
from rich.console import Console
import seaborn as sns

from b4_thesis.const.column import ColumnNames
from b4_thesis.core.track.classify.merge_splits import merge_splits
from b4_thesis.core.track.cross_revision_matcher import CrossRevisionMatcher
from b4_thesis.core.track.union_find import UnionFind
from b4_thesis.utils.revision_manager import RevisionManager

console = Console()


@click.group()
def nil():
    """Track method and clone group evolution across revisions.

    This command group provides subcommands for tracking:
    - track: Track individual method evolution
    - groups: Track clone group evolution
    """
    pass


@nil.command()
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
    default="./output/versions/nil/1_sim_match.csv",
    type=click.Path(file_okay=True, dir_okay=False),
    required=True,
    help="Output directory for CSV files",
)
def track_sim(
    input: str,
    output: str,
    similarity: float,
    n_gram_size: int,
    filter_threshold: float,
) -> None:
    """Track method evolution across revisions."""
    revision_manager = RevisionManager()
    try:
        cross_revision_matcher = CrossRevisionMatcher(
            n_gram_size=n_gram_size,
            filter_threshold=filter_threshold,
            verify_threshold=similarity,
        )

        revisions = revision_manager.get_revisions(Path(input))

        # Collect all results
        all_results: list[dict] = []

        # Iterate through revision pairs
        for prev_revision, curr_revision in zip(revisions[:-1], revisions[1:]):
            prev_code_blocks = revision_manager.load_code_blocks(prev_revision)
            curr_code_blocks = revision_manager.load_code_blocks(curr_revision)

            prev_code_blocks[ColumnNames.REVISION_ID.value] = prev_revision.timestamp
            curr_code_blocks[ColumnNames.REVISION_ID.value] = curr_revision.timestamp

            # Convert DataFrames to list of dicts for NIL-based matching
            source_blocks = prev_code_blocks.to_dict("records")
            target_blocks = curr_code_blocks.to_dict("records")

            console.print(
                f"Revision {prev_revision.timestamp} -> {curr_revision.timestamp}: "
                f"{len(source_blocks)}×{len(target_blocks)} blocks to match"
            )

            # Use NIL-based cross-revision matching
            match_results = cross_revision_matcher.match_revisions_with_changes(
                source_blocks, target_blocks
            )

            # Accumulate results
            all_results.extend(match_results)

        pd.DataFrame(all_results).to_csv(output, index=False)

        console.print(f"[green]Results saved to:[/green] {output}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@nil.command()
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
    default="./output/versions/nil/2_sig_match.csv",
    help="Output file for classified results",
)
def track_sig(
    input: str,
    output: str,
) -> None:
    df = pd.DataFrame()

    revision_manager = RevisionManager()
    revisions = revision_manager.get_revisions(Path(input))

    for prev_rev, curr_rev in zip(revisions, revisions[1:]):
        console.print(f"Processing revision pair: {prev_rev.timestamp} -> {curr_rev.timestamp}")

        prev_code_blocks = revision_manager.load_code_blocks(prev_rev)
        curr_code_blocks = revision_manager.load_code_blocks(curr_rev)

        prev_code_blocks[ColumnNames.REVISION_ID.value] = prev_rev.timestamp
        curr_code_blocks[ColumnNames.REVISION_ID.value] = curr_rev.timestamp

        prev_code_blocks = prev_code_blocks[
            [
                ColumnNames.REVISION_ID.value,
                ColumnNames.TOKEN_HASH.value,
                ColumnNames.FILE_PATH.value,
                ColumnNames.METHOD_NAME.value,
                ColumnNames.RETURN_TYPE.value,
                ColumnNames.PARAMETERS.value,
            ]
        ]
        curr_code_blocks = curr_code_blocks[
            [
                ColumnNames.REVISION_ID.value,
                ColumnNames.TOKEN_HASH.value,
                ColumnNames.FILE_PATH.value,
                ColumnNames.METHOD_NAME.value,
                ColumnNames.RETURN_TYPE.value,
                ColumnNames.PARAMETERS.value,
            ]
        ]

        prev_code_blocks = prev_code_blocks.add_prefix("prev_")
        curr_code_blocks = curr_code_blocks.add_prefix("curr_")

        matched_df = prev_code_blocks.merge(
            curr_code_blocks,
            left_on=[
                ColumnNames.PREV_FILE_PATH.value,
                ColumnNames.PREV_METHOD_NAME.value,
                ColumnNames.PREV_RETURN_TYPE.value,
                ColumnNames.PREV_PARAMETERS.value,
            ],
            right_on=[
                ColumnNames.CURR_FILE_PATH.value,
                ColumnNames.CURR_METHOD_NAME.value,
                ColumnNames.CURR_RETURN_TYPE.value,
                ColumnNames.CURR_PARAMETERS.value,
            ],
            how="outer",
        )

        matched_df["is_sig_matched"] = (
            matched_df[ColumnNames.PREV_FILE_PATH.value].notnull()
            & matched_df[ColumnNames.CURR_FILE_PATH.value].notnull()
        )
        matched_df["is_sig_deleted"] = matched_df[ColumnNames.CURR_FILE_PATH.value].isnull()
        matched_df["is_sig_added"] = matched_df[ColumnNames.PREV_FILE_PATH.value].isnull()

        df = pd.concat([df, matched_df], ignore_index=True)

        if (
            len(prev_code_blocks)
            != matched_df["is_sig_matched"].sum() + matched_df["is_sig_deleted"].sum()
        ) or (
            len(curr_code_blocks)
            != matched_df["is_sig_matched"].sum() + matched_df["is_sig_added"].sum()
        ):
            console.print(
                f"[red]Mismatch in counts detected for revisions "
                f"{prev_rev.timestamp} -> {curr_rev.timestamp}[/red]"
            )

    df.to_csv(output, index=False)
    console.print(f"[green]Results saved to:[/green] {output}")
    console.print(df.groupby(["is_sig_matched", "is_sig_deleted", "is_sig_added"]).size())


@nil.command()
@click.option(
    "--input-sim",
    "-i",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    required=False,
    default="./output/versions/nil/1_sim_match.csv",
    help="Input file containing tracked methods data",
)
@click.option(
    "--input-sig",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    required=False,
    default="./output/versions/nil/2_sig_match.csv",
    help="Input file containing tracked methods data",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    required=False,
    default="./output/versions/nil/3_sim_sig_match.csv",
    help="Output file for classified results",
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

    df_result.to_csv(output, index=False)
    console.print(f"[green]Results saved to:[/green] {output}")


def _add_similarity_column(clone_pairs: pd.DataFrame) -> pd.DataFrame:
    """Add a unified similarity column to clone_pairs DataFrame."""
    clone_pairs["similarity"] = clone_pairs[ColumnNames.VERIFY_SIMILARITY.value].fillna(
        clone_pairs[ColumnNames.NGRAM_OVERLAP.value]
    )
    return clone_pairs


@nil.command()
@click.option(
    "--input",
    "-i",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    required=True,
    default="./data/versions",
    help="Input directory containing revision subdirectories",
)
@click.option(
    "--input-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    default="./output/versions/method_tracker/methods_tracked.csv",
    help="Input file containing tracked methods data",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    default="./output/versions/nil/4_track_median_similarity.csv",
    help="Output file for CSV data",
)
def track_median_similarity(
    input: str,
    input_file: str,
    output: str,
) -> None:
    all_df = pd.read_csv(input_file)
    revision_manager = RevisionManager()
    revisions = revision_manager.get_revisions(Path(input))

    output_df: pd.DataFrame = pd.DataFrame()
    for rev in revisions:
        clone_pairs = revision_manager.load_clone_pairs(rev)

        clone_pairs = _add_similarity_column(clone_pairs)
        df = all_df[all_df[ColumnNames.PREV_REVISION_ID.value] == str(rev.timestamp)].copy()

        hash_1_sim = (
            clone_pairs.groupby(ColumnNames.TOKEN_HASH_1.value)["similarity"]
            .median()
            .rename("median_similarity")
        )
        hash_2_sim = (
            clone_pairs.groupby(ColumnNames.TOKEN_HASH_2.value)["similarity"]
            .median()
            .rename("median_similarity")
        )

        avg_sim = pd.concat([hash_1_sim, hash_2_sim]).groupby(level=0).median().round(1)

        df = df.merge(
            avg_sim, left_on=ColumnNames.PREV_TOKEN_HASH.value, right_index=True, how="outer"
        )
        output_df = pd.concat([output_df, df], ignore_index=True)

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(output_path, index=False)
    console.print(f"[green]Results saved to:[/green] {output_path}")


@nil.command()
@click.option(
    "--input",
    "-i",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    required=False,
    default="./output/versions/nil/methods_tracking_by_nil.csv",
    help="Input file containing tracked methods data",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    required=False,
    default="./output/versions/nil/tmp.json",
    help="Output file for classified results",
)
def evaluate(input: str, output: str) -> None:
    """Evaluate false positives in method tracking results."""
    df = pd.read_csv(input, low_memory=False)

    # NaNを除外したユニークなリビジョン
    unique_revisions = df[ColumnNames.PREV_REVISION_ID.value].dropna().unique()
    unique_revisions = sorted(unique_revisions)

    prev_file_col = ColumnNames.PREV_FILE_PATH.value
    prev_method_col = ColumnNames.PREV_METHOD_NAME.value
    curr_file_col = ColumnNames.CURR_FILE_PATH.value
    curr_method_col = ColumnNames.CURR_METHOD_NAME.value

    # 各タイプごとに辞書を分ける
    deleted_false_positives = {}
    matched_false_positives = {}
    added_false_positives = {}

    # 全てのリビジョンペアに対して処理
    for i in range(len(unique_revisions) - 2):
        print(
            f"Processing revision pair: {unique_revisions[i]} -> "
            f"{unique_revisions[i + 1]} -> {unique_revisions[i + 2]} "
        )
        prev_rev = unique_revisions[i]
        curr_rev = unique_revisions[i + 1]
        next_rev = unique_revisions[i + 2]

        # フィルタリングでグループを取得
        is_matched_prev_df = df[
            (df[ColumnNames.PREV_REVISION_ID.value] == prev_rev)
            & (df[ColumnNames.CURR_REVISION_ID.value] == curr_rev)
        ]
        is_deleted_df = df[
            (df[ColumnNames.PREV_REVISION_ID.value] == prev_rev)
            & (df[ColumnNames.CURR_REVISION_ID.value].isna())
        ]
        is_added_df = df[
            (df[ColumnNames.PREV_REVISION_ID.value].isna())
            & (df[ColumnNames.CURR_REVISION_ID.value] == curr_rev)
        ]
        is_matched_next_df = df[
            (df[ColumnNames.PREV_REVISION_ID.value] == curr_rev)
            & (df[ColumnNames.CURR_REVISION_ID.value] == next_rev)
        ]

        # ===== is_deleted_dfとマッチするものを選ぶ処理 =====
        deleted_with_key = is_deleted_df[[prev_file_col, prev_method_col]].copy()
        deleted_with_key["del_idx"] = is_deleted_df.index

        # matchedとの結合
        matched_with_key = is_matched_next_df[[prev_file_col, prev_method_col]].copy()
        matched_with_key["matched_idx"] = is_matched_next_df.index
        matched_merge = deleted_with_key.merge(
            matched_with_key,
            on=[prev_file_col, prev_method_col],
            how="left",
        )

        # グループ化して辞書を構築
        matched_grouped = matched_merge.groupby("del_idx")["matched_idx"].apply(
            lambda x: x.dropna().astype(int).to_list()
        )

        # deleted用の辞書に追加
        for idx in is_deleted_df.index:
            deleted_false_positives[idx] = {
                "matched": matched_grouped.get(idx, []),
            }

        # ===== is_matched_dfとマッチするものを選ぶ処理 =====
        # matched_dfの両方のファイルパス・メソッド名を使用
        matched_prev_with_key = is_matched_prev_df[[prev_file_col, prev_method_col]].copy()
        matched_prev_with_key["matched_idx"] = is_matched_prev_df.index

        matched_next_with_key = is_matched_next_df[[curr_file_col, curr_method_col]].copy()
        matched_next_with_key["matched_idx"] = is_matched_next_df.index
        matched_prev_curr_merge = matched_prev_with_key.merge(
            matched_next_with_key,
            left_on=[prev_file_col, prev_method_col],
            right_on=[curr_file_col, curr_method_col],
            how="left",
            suffixes=("_prev", "_curr"),
        )

        # グループ化して辞書を構築
        matched_prev_corr_grouped = matched_prev_curr_merge.groupby("matched_idx_prev")[
            "matched_idx_curr"
        ].apply(lambda x: x.dropna().astype(int).to_list())

        # matched用の辞書に追加
        for idx in is_matched_prev_df.index:
            matched_false_positives[idx] = {
                "matched": matched_prev_corr_grouped.get(idx, []),
            }

        # ===== is_added_dfとマッチするものを選ぶ処理 =====
        added_curr_with_key = is_added_df[[curr_file_col, curr_method_col]].copy()
        added_curr_with_key["added_idx"] = is_added_df.index

        # matchedとの結合（prev側で照合）
        matched_with_key = is_matched_prev_df[[prev_file_col, prev_method_col]].copy()
        matched_with_key["matched_idx"] = is_matched_prev_df.index
        matched_merge = added_curr_with_key.merge(
            matched_with_key,
            left_on=[curr_file_col, curr_method_col],
            right_on=[prev_file_col, prev_method_col],
            how="left",
        )

        # グループ化して辞書を構築
        matched_grouped = matched_merge.groupby("added_idx")["matched_idx"].apply(
            lambda x: x.dropna().astype(int).to_list()
        )

        # added用の辞書に追加
        for idx in is_added_df.index:
            added_false_positives[idx] = {
                "matched": matched_grouped.get(idx, []),
            }

    # 辞書のキーをintからstrに変換（JSONシリアライズのため）
    output_data = {
        "deleted": {str(k): v for k, v in deleted_false_positives.items()},
        "matched": {str(k): v for k, v in matched_false_positives.items()},
        "added": {str(k): v for k, v in added_false_positives.items()},
    }

    # deleted内のmatchedとaddedを持つエントリの個数（空のリストは除外）
    count_deleted_with_matched = sum(1 for v in deleted_false_positives.values() if v["matched"])
    count_matched_with_matched = sum(1 for v in matched_false_positives.values() if v["matched"])
    count_added_with_matched = sum(1 for v in added_false_positives.values() if v["matched"])

    # JSONファイルに保存
    output_path = Path(output)
    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

    console.print(f"[green]False positives saved to:[/green] {output_path}")
    console.print(f"Total deleted entries: {len(deleted_false_positives)}")
    console.print(f"  - Entries with matched references: {count_deleted_with_matched}")
    console.print(f"Total matched entries: {len(matched_false_positives)}")
    console.print(f"  - Entries with matched references: {count_matched_with_matched}")
    console.print(f"Total added entries: {len(added_false_positives)}")
    console.print(f"  - Entries with matched references: {count_added_with_matched}")


@nil.command()
@click.option(
    "--input",
    "-i",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    required=True,
    default="./output/versions/nil/methods_tracking_by_nil.csv",
    help="Input file containing tracked methods data",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    required=False,
    default="./output/versions/nil/methods_tracking_with_merge_splits.csv",
    help="Output file for classified results",
)
@click.option(
    "--verify-threshold",
    type=click.FloatRange(0.0, 1.0),
    default=0.7,
    help="Threshold for verifying splits/merges (0.0-1.0, default: 0.7)",
)
def track_merge_splits(
    input: str,
    output: str,
    verify_threshold: float,
) -> None:
    """Classify tracked methods into categories including merges and splits."""
    df = pd.read_csv(input)

    merge_splits_df = merge_splits(df, verify_threshold=verify_threshold)

    merge_splits_df.to_csv(output, index=False)
    console.print(f"[green]Results with merge/split classification saved to:[/green] {output}")


@nil.command()
@click.option(
    "--input",
    "-i",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    required=True,
    default="./data/versions",
    help="Input directory containing revision subdirectories",
)
@click.option(
    "--input-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    default="./output/versions/nil/4_method_tracking.csv",
    help="Input file containing tracked methods data",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    required=True,
    default="./output/versions/nil/5_has_clone.csv",
    help="Output file for CSV data",
)
def track_clone(
    input: str,
    input_file: str,
    output: str,
) -> None:
    """Track clone presence in method tracking results."""
    df = pd.read_csv(input_file)
    revision_manager = RevisionManager()
    revisions = revision_manager.get_revisions(Path(input))

    rev_clone_hashes = {}
    for rev in revisions:
        clone_pairs = revision_manager.load_clone_pairs(rev)
        hashes = set(clone_pairs[ColumnNames.TOKEN_HASH_1.value]) | set(
            clone_pairs[ColumnNames.TOKEN_HASH_2.value]
        )
        rev_clone_hashes[str(rev.timestamp)] = hashes

    prev_rev_col = ColumnNames.PREV_REVISION_ID.value
    prev_hash_col = ColumnNames.PREV_TOKEN_HASH.value

    df[ColumnNames.HAS_CLONE.value] = False
    for rev_id, hashes in rev_clone_hashes.items():
        mask = df[prev_rev_col] == rev_id
        matched = df.loc[mask, prev_hash_col].isin(hashes)
        df.loc[mask, ColumnNames.HAS_CLONE.value] = matched

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    console.print(f"[green]Results saved to:[/green] {output_path}")

    console.print("\nOverall clone presence:")
    console.print(
        pd.crosstab(
            df[ColumnNames.PREV_REVISION_ID.value],
            [df[ColumnNames.HAS_CLONE.value], df["is_matched"], df["is_deleted"]],
        )
    )


@nil.command()
@click.option(
    "--input",
    "-i",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    required=True,
    default="./data/versions",
    help="Input directory containing revision subdirectories",
)
@click.option(
    "--input-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    default="./output/versions/nil/5_has_clone.csv",
    help="Input file containing tracked methods data",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    required=True,
    default="./output/versions/nil/6_clone_group.csv",
    help="Output file for CSV data",
)
def classify_clone(
    input_file: str,
    input: str,
    output: str,
):
    """Classify method tracking results based on clone presence."""
    df = pd.read_csv(input_file)

    revision_manager = RevisionManager()
    revisions = revision_manager.get_revisions(Path(input))

    uf = UnionFind()

    all_df = pd.DataFrame()
    for rev in revisions:
        clone_pairs = revision_manager.load_clone_pairs(rev)

        for _, row in clone_pairs.iterrows():
            uf.union(row[ColumnNames.TOKEN_HASH_1.value], row[ColumnNames.TOKEN_HASH_2.value])

        groups = {root: i for i, root in enumerate(set(uf.find(t) for t in uf.parent))}

        result_df = pd.DataFrame(
            [
                {
                    "prev_token_hash": t,
                    "prev_revision_id": str(rev.timestamp),
                    "group_id": int(groups[uf.find(t)]),
                }
                for t in uf.parent
            ]
        )

        all_df = pd.concat([all_df, result_df], ignore_index=True)

    all_df.sort_values([ColumnNames.PREV_REVISION_ID.value, "group_id"], inplace=True)

    merge_df = df.merge(
        all_df,
        on=[ColumnNames.PREV_REVISION_ID.value, ColumnNames.PREV_TOKEN_HASH.value],
        how="left",
    )

    merge_df.to_csv(output, index=False)
    console.print(f"[green]Results saved to:[/green] {output}")


@nil.command()
@click.option(
    "--input-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    default="./output/versions/nil/6_clone_group.csv",
    help="Input file containing tracked methods data",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    required=True,
    default="./output/versions/nil/7_track_deletion_status.csv",
    help="Output file for CSV data",
)
def track_deletion_status(
    input_file: str,
    output: str,
):
    df = pd.read_csv(input_file)
    df["is_all_deleted"] = False
    df["is_partial_deleted"] = False

    no_clone_df = df[~df["has_clone"]]
    has_clone_df = df[df["has_clone"]]

    revision_manager = RevisionManager()
    revisions = revision_manager.get_revisions(Path("./data/versions"))

    # 結果を格納するための新しいカラムを初期化
    has_clone_df = has_clone_df.copy()

    rev_dfs = pd.DataFrame()
    for rev in revisions:
        console.print(f"Processing revision: {rev.timestamp}")
        rev_df = has_clone_df[has_clone_df["prev_revision_id"] == str(rev.timestamp)]

        if len(rev_df) == 0:
            continue

        # group_idごとにis_deletedの状態を集計
        group_status = rev_df.groupby("group_id")["is_deleted"].agg(
            all_deleted="all", any_deleted="any"
        )

        # 全てTrue → is_all_deleted = True（is_deleted=Trueの行のみ）
        all_deleted_groups = group_status[group_status["all_deleted"]].index
        rev_df.loc[
            rev_df["group_id"].isin(all_deleted_groups) & rev_df["is_deleted"], "is_all_deleted"
        ] = True

        # 一部True、一部False → is_partial_deleted = True（is_deleted=Trueの行のみ）
        partial_deleted_groups = group_status[
            group_status["any_deleted"] & ~group_status["all_deleted"]
        ].index
        rev_df.loc[
            rev_df["group_id"].isin(partial_deleted_groups) & rev_df["is_deleted"],
            "is_partial_deleted",
        ] = True

        rev_dfs = pd.concat([rev_dfs, rev_df], ignore_index=True)

    # 結果を出力
    all_df = pd.concat([no_clone_df, rev_dfs], ignore_index=True)

    console.print(
        pd.crosstab(
            all_df[ColumnNames.PREV_REVISION_ID.value],
            [all_df["is_deleted"], all_df["is_all_deleted"], all_df["is_partial_deleted"]],
        )
    )
    all_df.to_csv(output, index=False)


@nil.command()
@click.option(
    "--input-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    default="./output/versions/nil/7_track_deletion_status.csv",
    help="Input file containing tracked methods data",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    required=True,
    default="./output/versions/nil/8_class_delete.csv",
    help="Output file for CSV data",
)
def class_delete(
    input_file: str,
    output: str,
):
    df = pd.read_csv(input_file)

    result = pd.crosstab(
        df[ColumnNames.PREV_REVISION_ID.value],
        [df["is_matched"], df["has_clone"]],
    )

    # クローン有無別の削除率
    deletion_by_clone = (
        df.groupby([ColumnNames.PREV_REVISION_ID.value, "has_clone"])["is_matched"]
        .apply(lambda x: (~x).mean() * 100)
        .unstack(fill_value=0)
        .round(2)
    )

    # カラムとして追加
    result[("clone_deletion_rate(%)", "")] = deletion_by_clone.get(True, 0)
    result[("no_clone_deletion_rate(%)", "")] = deletion_by_clone.get(False, 0)

    # 全リビジョンでの平均を計算
    avg_row = result.mean(numeric_only=True).round(2)
    avg_row.name = "Average"
    result = pd.concat([result, avg_row.to_frame().T])

    result.to_csv(output, index=True)
    console.print(f"[green]Results saved to:[/green] {output}")


@nil.command()
@click.option(
    "--input-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    default="./output/versions/nil/9_track_median_similarity.csv",
    help="Input file containing tracked methods data",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    required=True,
    default="./output/versions/nil/11_class_high_low_sim.csv",
    help="Output file for CSV data",
)
def class_high_low_sim(
    input_file: str,
    output: str,
):
    df = pd.read_csv(
        input_file,
        usecols=[
            ColumnNames.PREV_REVISION_ID.value,
            "median_similarity",
            "is_matched",
            "is_deleted",
            "has_clone",
        ],
        dtype={
            "is_matched": "boolean",
            "is_deleted": "boolean",
            "has_clone": "boolean",
        },
        low_memory=False,
    )

    df = df.sort_values("prev_revision_id")
    df["high_sim"] = df["median_similarity"] >= 90
    df["low_sim"] = (df["median_similarity"] < 90) & (df["median_similarity"] >= 70)

    result = pd.crosstab(
        df[ColumnNames.PREV_REVISION_ID.value],
        [df["is_matched"], df["high_sim"], df["low_sim"]],
    )

    # high_sim と low_sim 別の削除率を計算
    deletion_by_high_sim = (
        df[df["high_sim"] & df["has_clone"]]
        .groupby(ColumnNames.PREV_REVISION_ID.value)["is_deleted"]
        .apply(lambda x: x.astype(float).mean() * 100)
        .round(2)
    )
    deletion_by_low_sim = (
        df[df["low_sim"] & df["has_clone"]]
        .groupby(ColumnNames.PREV_REVISION_ID.value)["is_deleted"]
        .apply(lambda x: x.astype(float).mean() * 100)
        .round(2)
    )

    # カラムとして追加（3レベルのマルチインデックスに対応）
    result[("high_sim_deletion_rate(%)", "", "")] = deletion_by_high_sim
    result[("low_sim_deletion_rate(%)", "", "")] = deletion_by_low_sim

    avg_row = result.mean(numeric_only=True).round(2)
    avg_row.name = "Average"
    result = pd.concat([result, avg_row.to_frame().T])

    result.to_csv(output, index=True)
    console.print(f"[green]Results saved to:[/green] {output}")


@nil.command()
def sim_count():
    df = pd.read_csv("./output/versions/nil/9_track_median_similarity.csv")
    high_sim_df = df[df["median_similarity"] >= 90]
    low_sim_df = df[(df["median_similarity"] < 90) & (df["median_similarity"] >= 70)]

    print(pd.crosstab(high_sim_df[ColumnNames.PREV_REVISION_ID.value], [high_sim_df["is_matched"]]))

    print(pd.crosstab(low_sim_df[ColumnNames.PREV_REVISION_ID.value], [low_sim_df["is_matched"]]))


@nil.command()
@click.option(
    "--input-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    default="./output/versions/nil/9_track_median_similarity_max.csv",
    help="Input file containing tracked methods data",
)
@click.option(
    "--output-csv",
    type=click.Path(file_okay=True, dir_okay=False),
    default="./output/versions/nil/10_deletion_survival_max.csv",
    help="Output file for CSV data",
)
@click.option(
    "--output-boxplot-absorber",
    type=click.Path(file_okay=True, dir_okay=False),
    default="./output/versions/nil/10_deletion_survival_boxplot_max.pdf",
    help="Output file for the absorber group boxplot",
)
@click.option(
    "--output-boxplot-deletion",
    type=click.Path(file_okay=True, dir_okay=False),
    default="./output/versions/nil/10_deletion_survival_boxplot_max_deletion.pdf",
    help="Output file for the absorbed+deleted group boxplot",
)
@click.option(
    "--output-areaplot-absorber",
    type=click.Path(file_okay=True, dir_okay=False),
    default="./output/versions/nil/10_deletion_survival_areaplot_max_absorber.pdf",
    help="Output file for the absorber group area plot",
)
@click.option(
    "--output-areaplot-deletion",
    type=click.Path(file_okay=True, dir_okay=False),
    default="./output/versions/nil/10_deletion_survival_areaplot_max_deletion.pdf",
    help="Output file for the absorbed+deleted group stacked area plot",
)
def deletion_survival(
    input_file: str,
    output_csv: str,
    output_boxplot_absorber: str,
    output_boxplot_deletion: str,
    output_areaplot_absorber: str,
    output_areaplot_deletion: str,
) -> None:
    """Track median_similarity evolution per method_id for different deletion types."""
    cols = [
        ColumnNames.PREV_REVISION_ID.value,
        "is_deleted",
        # "is_partial_deleted",
        # "is_all_deleted",
        "is_absorbed",
        "is_absorber",
        "is_matched",
        "median_similarity",
        "method_id",
    ]
    df = pd.read_csv(input_file, usecols=cols)

    # 各method_idの最新行で4分類: "Matched" / "Absorber" / "Absorbed" / "Deleted"
    latest = (
        df.sort_values(ColumnNames.PREV_REVISION_ID.value, ascending=False)
        .groupby("method_id")
        .first()
    )
    latest["survival_group"] = None
    # 最終行の状態で分類
    latest.loc[latest["is_matched"], "survival_group"] = "Matched"
    latest.loc[latest["is_deleted"], "survival_group"] = "Deleted"
    latest.loc[latest["is_absorbed"], "survival_group"] = "Absorbed"
    # Absorber: 最終状態がMatchedかつ生存期間中にis_absorber=Trueを持つ
    absorber_any = df.groupby("method_id")["is_absorber"].any()
    absorber_ids = absorber_any[absorber_any].index
    latest.loc[
        (latest["survival_group"] == "Matched") & latest.index.isin(absorber_ids),
        "survival_group",
    ] = "Absorber"

    group_map = latest["survival_group"].dropna()
    df["survival_group"] = df["method_id"].map(group_map)
    df = df[df["survival_group"].notna()]

    # 各method_idごとに相対時間を計算
    df = df.sort_values(["method_id", ColumnNames.PREV_REVISION_ID.value])

    # デフォルト: 最新行=0、遡って-1, -2, ...
    df["relative_time"] = (
        (
            df.groupby("method_id").cumcount()
            - df.groupby("method_id")["method_id"].transform("count")
            + 1
        )
        .fillna(0)
        .astype(int)
    )

    # Absorberグループ: 最後のis_absorber=True行を基準(0)に再計算
    absorber_mask = df["survival_group"] == "Absorber"
    if absorber_mask.any():
        absorber_df = df.loc[absorber_mask].copy()
        absorber_df["_pos"] = absorber_df.groupby("method_id").cumcount()
        last_absorber_pos = (
            absorber_df[absorber_df["is_absorber"]].groupby("method_id")["_pos"].last()
        )
        absorber_df["_anchor"] = absorber_df["method_id"].map(last_absorber_pos)
        df.loc[absorber_mask, "relative_time"] = (
            absorber_df["_pos"] - absorber_df["_anchor"]
        ).astype(int)
    df.to_csv(output_csv, index=False)
    latest_df = df[df["relative_time"] == 0]
    console.print(latest_df.groupby(["survival_group"]).size())
    console.print(
        latest_df[latest_df["median_similarity"].notna()]
        .groupby(["survival_group"])["median_similarity"]
        .mean()
    )
    console.print(f"[green]Data with survival groups saved to:[/green] {output_csv}")

    # プロット設定（論文用、PDF出力対応）
    plt.rcParams.update(
        {
            "font.family": "Hiragino Sans",  # macOS用日本語フォント
            "font.size": 16,
            "axes.titlesize": 20,
            "axes.labelsize": 18,
            "xtick.labelsize": 14,
            "ytick.labelsize": 14,
            "legend.fontsize": 16,
            "figure.dpi": 300,
            "pdf.fonttype": 42,  # TrueTypeフォントを埋め込み（日本語対応）
            "ps.fonttype": 42,
        }
    )

    # 日本語ラベル用のマッピング
    label_map = {"Matched": "生存", "Absorber": "統合先", "Absorbed": "統合元", "Deleted": "削除"}
    df["survival_group_ja"] = df["survival_group"].map(label_map)

    colors = {"生存": "#1f77b4", "統合先": "#2ca02c", "統合元": "#ff7f0e", "削除": "#d62728"}

    plot_df = df[df["median_similarity"].notna()]

    # DataFrameを統合先群と統合元+削除群に分割
    absorber_df = plot_df[plot_df["survival_group_ja"] == "統合先"]
    deletion_df = plot_df[plot_df["survival_group_ja"].isin(["統合元", "削除"])]

    # 統合先用のtime_values（中央が0）
    absorber_time_values = sorted(absorber_df["relative_time"].unique())
    # 統合元+削除用のtime_values（右端が0、降順で並べる）
    deletion_time_values = sorted(deletion_df["relative_time"].unique())

    # サンプル数の集計
    count_df = (
        plot_df.groupby(["relative_time", "survival_group_ja"]).size().reset_index(name="count")
    )
    count_absorber = count_df[count_df["survival_group_ja"] == "統合先"]
    count_deletion = count_df[count_df["survival_group_ja"].isin(["統合元", "削除"])]

    # --- 箱ひげ図: 統合先群（中央が0） ---
    fig1, ax1 = plt.subplots(figsize=(12, 6))
    sns.boxplot(
        data=absorber_df,
        x="relative_time",
        y="median_similarity",
        color=colors["統合先"],
        linewidth=1.2,
        fliersize=3,
        order=absorber_time_values,
        ax=ax1,
    )
    ax1.set_xlabel("相対時間 (0 = 統合直前のバージョン)", labelpad=10)
    ax1.set_ylabel("類似度（中央値） (%)", labelpad=10)
    ax1.grid(True, alpha=0.3, linestyle="--")
    ax1.set_xlim(-0.5, len(absorber_time_values) - 0.5)
    # x軸ラベルは偶数（0含む）のみ表示（目盛り線は全値に残す）
    ax1.set_xticks(range(len(absorber_time_values)))
    ax1.set_xticklabels([str(t) if t % 2 == 0 else "" for t in absorber_time_values])

    plt.tight_layout()
    plt.savefig(
        output_boxplot_absorber, dpi=300, bbox_inches="tight", facecolor="white", edgecolor="none"
    )
    plt.close()
    console.print(f"[green]Boxplot (absorber) saved to:[/green] {output_boxplot_absorber}")

    # --- 箱ひげ図: 統合元+削除群（右端が0） ---
    fig2, ax2 = plt.subplots(figsize=(12, 6))
    sns.boxplot(
        data=deletion_df,
        x="relative_time",
        y="median_similarity",
        hue="survival_group_ja",
        palette={k: colors[k] for k in ["統合元", "削除"]},
        linewidth=1.2,
        fliersize=3,
        order=deletion_time_values,
        ax=ax2,
    )
    ax2.set_xlabel("相対時間 (0 = 削除または統合直前のバージョン)", labelpad=10)
    ax2.set_ylabel("類似度（中央値） (%)", labelpad=10)
    ax2.grid(True, alpha=0.3, linestyle="--")
    ax2.legend(loc="upper left", frameon=True, fancybox=True, shadow=True)
    ax2.set_xlim(-0.5, len(deletion_time_values) - 0.5)
    # x軸ラベルは偶数（0含む）のみ表示（目盛り線は全値に残す）
    ax2.set_xticks(range(len(deletion_time_values)))
    ax2.set_xticklabels([str(t) if t % 2 == 0 else "" for t in deletion_time_values])

    plt.tight_layout()
    plt.savefig(
        output_boxplot_deletion, dpi=300, bbox_inches="tight", facecolor="white", edgecolor="none"
    )
    plt.close()
    console.print(f"[green]Boxplot (deletion) saved to:[/green] {output_boxplot_deletion}")

    # --- 面グラフ用のデータ準備と縦軸の最大値計算 ---
    absorber_time_to_pos = {t: i for i, t in enumerate(absorber_time_values)}

    # 統合先群のカウントデータ
    absorber_count_data = count_absorber.sort_values("relative_time")
    absorber_count_by_time = (
        dict(zip(absorber_count_data["relative_time"], absorber_count_data["count"]))
        if not absorber_count_data.empty
        else {}
    )
    absorber_counts = [absorber_count_by_time.get(t, 0) for t in absorber_time_values]

    # 統合元+削除群のカウントデータ
    stacked_data = {}
    for group in ["統合元", "削除"]:
        group_data = count_deletion[count_deletion["survival_group_ja"] == group]
        count_by_time = dict(zip(group_data["relative_time"], group_data["count"]))
        stacked_data[group] = [count_by_time.get(t, 0) for t in deletion_time_values]

    # 両グラフの縦軸最大値を揃える
    max_absorber = max(absorber_counts) if absorber_counts else 0
    max_deletion = (
        max(a + b for a, b in zip(stacked_data["統合元"], stacked_data["削除"]))
        if stacked_data["統合元"]
        else 0
    )
    y_max = max(max_absorber, max_deletion) * 1.05  # 5%の余白

    # --- 面グラフ: 統合先群（中央が0） ---
    fig3, ax3 = plt.subplots(figsize=(12, 4))
    if absorber_counts:
        positions = list(range(len(absorber_time_values)))
        ax3.fill_between(
            positions,
            absorber_counts,
            color=colors["統合先"],
            alpha=0.7,
            label="統合先",
        )
        ax3.plot(positions, absorber_counts, color=colors["統合先"], linewidth=1.5)
    ax3.set_xlabel("相対時間 (0 = 統合直前のバージョン)", labelpad=10)
    ax3.set_ylabel("メソッド数", labelpad=10)
    ax3.grid(True, alpha=0.3, linestyle="--")
    ax3.legend(loc="upper left", frameon=True, fancybox=True, shadow=True)
    ax3.set_xticks(range(len(absorber_time_values)))
    # x軸ラベルは偶数（0含む）のみ表示（目盛り線は全値に残す）
    ax3.set_xticklabels([str(t) if t % 2 == 0 else "" for t in absorber_time_values])
    ax3.set_xlim(-0.5, len(absorber_time_values) - 0.5)
    ax3.set_ylim(0, y_max)

    plt.tight_layout()
    plt.savefig(
        output_areaplot_absorber, dpi=300, bbox_inches="tight", facecolor="white", edgecolor="none"
    )
    plt.close()
    console.print(f"[green]Area plot (absorber) saved to:[/green] {output_areaplot_absorber}")

    # --- 積み上げ面グラフ: 統合元+削除群（右端が0） ---
    fig4, ax4 = plt.subplots(figsize=(12, 4))

    positions = list(range(len(deletion_time_values)))
    ax4.stackplot(
        positions,
        stacked_data["統合元"],
        stacked_data["削除"],
        labels=["統合元", "削除"],
        colors=[colors["統合元"], colors["削除"]],
        alpha=0.7,
    )
    ax4.set_xlabel("相対時間 (0 = 統合または削除直前のバージョン)", labelpad=10)
    ax4.set_ylabel("メソッド数", labelpad=10)
    ax4.grid(True, alpha=0.3, linestyle="--")
    ax4.legend(loc="upper left", frameon=True, fancybox=True, shadow=True)
    ax4.set_xticks(positions)
    # x軸ラベルは偶数（0含む）のみ表示（目盛り線は全値に残す）
    ax4.set_xticklabels([str(t) if t % 2 == 0 else "" for t in deletion_time_values])
    ax4.set_xlim(-0.5, len(deletion_time_values) - 0.5)
    ax4.set_ylim(0, y_max)

    plt.tight_layout()
    plt.savefig(
        output_areaplot_deletion, dpi=300, bbox_inches="tight", facecolor="white", edgecolor="none"
    )
    plt.close()
    console.print(f"[green]Area plot (deletion) saved to:[/green] {output_areaplot_deletion}")


@nil.command()
@click.option(
    "--input",
    "-i",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    required=True,
    default="./output/versions/nil/methods_tracking_with_clone.csv",
    help="Input file containing tracked methods data",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    required=False,
    default="./output/versions/nil/methods_classified_count.csv",
    help="Output file for classified results",
)
def count_classified(
    input: str,
    output: str,
) -> None:
    """Count classified method tracking results by groups."""
    df = pd.read_csv(
        input,
        usecols=[
            ColumnNames.PREV_REVISION_ID.value,
            ColumnNames.CURR_REVISION_ID.value,
            ColumnNames.IS_MATCHED.value,
            ColumnNames.IS_DELETED.value,
            ColumnNames.IS_ADDED.value,
            ColumnNames.IS_SPLIT.value,
            ColumnNames.IS_MERGED.value,
            ColumnNames.IS_MODIFIED.value,
            ColumnNames.HAS_CLONE.value,
        ],
    )

    prev_col = ColumnNames.PREV_REVISION_ID.value
    curr_col = ColumnNames.CURR_REVISION_ID.value

    unique_revisions = df[prev_col].dropna().unique()
    unique_revisions = sorted(unique_revisions)

    all_results = []
    for i in range(len(unique_revisions) - 1):
        prev_rev = unique_revisions[i]
        curr_rev = unique_revisions[i + 1]

        is_matched_df = df[(df[prev_col] == prev_rev) & (df[curr_col] == curr_rev)]
        is_deleted_df = df[(df[prev_col] == prev_rev) & (df[curr_col].isna())]
        is_added_df = df[(df[prev_col].isna()) & (df[curr_col] == curr_rev)]

        rev_df = pd.concat([is_matched_df, is_deleted_df, is_added_df], join="outer")

        count_df = (
            rev_df.groupby(
                [
                    ColumnNames.IS_DELETED.value,
                    ColumnNames.IS_ADDED.value,
                    ColumnNames.IS_SPLIT.value,
                    ColumnNames.IS_MERGED.value,
                    ColumnNames.IS_MODIFIED.value,
                    ColumnNames.HAS_CLONE.value,
                ]
            )
            .size()
            .reset_index(name="count")
        )

        labels = [
            "added_no_clone",
            "deleted_no_clone",
            "deleted_with_clone",
            "split_no_clone",
            "split_with_clone",
            "merged_no_clone",
            "merged_with_clone",
            "modified_no_clone",
            "modified_with_clone",
        ]

        counts_dict = dict(zip(labels, count_df["count"].values))
        all_results.append(counts_dict)

    final_df = pd.DataFrame(all_results)

    final_df.to_csv(output, index=False)
    console.print(f"[green]Classified counts saved to:[/green] {output}")


@nil.command()
@click.option(
    "--input-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    default="./output/versions/nil/10_deletion_survival.csv",
    help="Input file from deletion_survival command",
)
@click.option(
    "--input-tracking",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    default="./output/versions/nil/9_track_median_similarity.csv",
    help="Full tracking data with method signatures",
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
    "--output-csv",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    default="./output/versions/nil/12_analyze_absorbed.csv",
    help="Output CSV with absorbed method analysis",
)
@click.option(
    "--output-histogram",
    type=click.Path(file_okay=True, dir_okay=False),
    default="./output/versions/nil/12_analyze_absorbed_histogram.png",
    help="Output histogram of lifetime distribution",
)
@click.option(
    "--output-revision-breakdown",
    type=click.Path(file_okay=True, dir_okay=False),
    default="./output/versions/nil/12_analyze_absorbed_breakdown.png",
    help="Output per-revision breakdown chart",
)
def analyze_absorbed(
    input_file: str,
    input_tracking: str,
    input: str,
    output_csv: str,
    output_histogram: str,
    output_revision_breakdown: str,
) -> None:
    """Analyze Absorbed methods: lifetime distribution and origin classification."""
    # Step 1: Load deletion_survival data and compute lifetime
    ds_cols = [
        ColumnNames.PREV_REVISION_ID.value,
        "method_id",
        "survival_group",
        "relative_time",
        "median_similarity",
    ]
    df_ds = pd.read_csv(input_file, usecols=ds_cols)

    lifetime = df_ds.groupby("method_id").size().rename("lifetime")

    # Step 2: Get method signatures from tracking data
    sig_cols = [
        "method_id",
        ColumnNames.PREV_REVISION_ID.value,
        ColumnNames.PREV_FILE_PATH.value,
        ColumnNames.PREV_METHOD_NAME.value,
        ColumnNames.PREV_RETURN_TYPE.value,
        ColumnNames.PREV_PARAMETERS.value,
    ]
    has_clone_col = ColumnNames.HAS_CLONE.value
    try:
        df_tracking = pd.read_csv(input_tracking, usecols=sig_cols + [has_clone_col])
    except ValueError:
        df_tracking = pd.read_csv(input_tracking, usecols=sig_cols)
        df_tracking[has_clone_col] = None

    # Get t=0 row for each Absorbed method
    absorbed_t0 = df_ds[(df_ds["survival_group"] == "Absorbed") & (df_ds["relative_time"] == 0)][
        ["method_id", ColumnNames.PREV_REVISION_ID.value, "median_similarity"]
    ].copy()

    absorbed_t0 = absorbed_t0.merge(lifetime.reset_index(), on="method_id")

    # Add signatures from tracking data (join on method_id + prev_revision_id)
    # Remove duplicates to prevent row explosion during merge
    df_tracking_dedup = df_tracking.drop_duplicates(
        subset=["method_id", ColumnNames.PREV_REVISION_ID.value], keep="first"
    )
    absorbed_t0 = absorbed_t0.merge(
        df_tracking_dedup,
        on=["method_id", ColumnNames.PREV_REVISION_ID.value],
        how="left",
    )

    # Step 3: Check prior revision existence for lifetime=1 methods
    revision_manager = RevisionManager()
    revisions = revision_manager.get_revisions(Path(input))

    prev_rev_lookup: dict = {}
    for i in range(1, len(revisions)):
        prev_rev_lookup[str(revisions[i].timestamp)] = revisions[i - 1]

    absorbed_t0["origin"] = "already_tracked"
    absorbed_t0.loc[absorbed_t0["lifetime"] == 1, "origin"] = "unknown"

    single_row = absorbed_t0[absorbed_t0["lifetime"] == 1]

    for rev_id, group in single_row.groupby(ColumnNames.PREV_REVISION_ID.value):
        if rev_id not in prev_rev_lookup:
            absorbed_t0.loc[group.index, "origin"] = "first_revision"
            continue

        prev_rev = prev_rev_lookup[rev_id]
        code_blocks = revision_manager.load_code_blocks(prev_rev)

        sig_set = set(
            zip(
                code_blocks[ColumnNames.FILE_PATH.value],
                code_blocks[ColumnNames.METHOD_NAME.value],
                code_blocks[ColumnNames.RETURN_TYPE.value],
                code_blocks[ColumnNames.PARAMETERS.value],
            )
        )

        for idx, row in group.iterrows():
            method_sig = (
                row[ColumnNames.PREV_FILE_PATH.value],
                row[ColumnNames.PREV_METHOD_NAME.value],
                row[ColumnNames.PREV_RETURN_TYPE.value],
                row[ColumnNames.PREV_PARAMETERS.value],
            )
            if method_sig in sig_set:
                absorbed_t0.loc[idx, "origin"] = "similarity_crossed"
            else:
                absorbed_t0.loc[idx, "origin"] = "newly_added"

    # Step 4: Print summary
    total = len(absorbed_t0)
    single_count = int((absorbed_t0["lifetime"] == 1).sum())
    multi_count = int((absorbed_t0["lifetime"] >= 2).sum())

    newly_added_count = int((absorbed_t0["origin"] == "newly_added").sum())
    sim_crossed_count = int((absorbed_t0["origin"] == "similarity_crossed").sum())
    first_rev_count = int((absorbed_t0["origin"] == "first_revision").sum())

    console.print("\n[bold]Absorbed Method Analysis[/bold]")
    console.print("=" * 40)
    console.print(f"Total Absorbed methods: {total:,}")
    console.print(f"  lifetime=1 (t=0 only): {single_count:,} ({single_count / total * 100:.1f}%)")
    console.print(
        f"    newly_added:        {newly_added_count:,} ({newly_added_count / total * 100:.1f}%)"
    )
    console.print(
        f"    similarity_crossed: {sim_crossed_count:,} ({sim_crossed_count / total * 100:.1f}%)"
    )
    console.print(
        f"    first_revision:     {first_rev_count:,} ({first_rev_count / total * 100:.1f}%)"
    )
    console.print(f"  lifetime>=2 (tracked): {multi_count:,} ({multi_count / total * 100:.1f}%)")
    if multi_count > 0:
        multi_lifetime = absorbed_t0[absorbed_t0["lifetime"] >= 2]["lifetime"]
        console.print(f"    Mean lifetime: {multi_lifetime.mean():.1f}")
        console.print(f"    Median lifetime: {multi_lifetime.median():.1f}")
    console.print(f"\nt=0 -> t=-1 drop: {single_count:,} methods")

    # # Step 5: Save CSV
    # output_path = Path(output_csv)
    # output_path.parent.mkdir(parents=True, exist_ok=True)

    # output_cols = [
    #     "method_id",
    #     "lifetime",
    #     "origin",
    #     ColumnNames.PREV_REVISION_ID.value,
    #     ColumnNames.PREV_FILE_PATH.value,
    #     ColumnNames.PREV_METHOD_NAME.value,
    #     "median_similarity",
    #     has_clone_col,
    # ]
    # absorbed_t0[output_cols].to_csv(output_path, index=False)
    # console.print(f"\n[green]Results saved to:[/green] {output_path}")

    # # Step 6: Visualizations
    # plt.rcParams.update(
    #     {
    #         "font.family": "Hiragino Sans",
    #         "font.size": 12,
    #         "axes.titlesize": 14,
    #         "axes.labelsize": 12,
    #         "xtick.labelsize": 10,
    #         "ytick.labelsize": 10,
    #         "legend.fontsize": 11,
    #         "figure.dpi": 300,
    #     }
    # )

    # colors = {
    #     "newly_added": "#2ca02c",
    #     "similarity_crossed": "#ff7f0e",
    #     "first_revision": "#9467bd",
    #     "already_tracked": "#1f77b4",
    # }
    # label_map = {
    #     "newly_added": "新規追加",
    #     "similarity_crossed": "類似度超過",
    #     "first_revision": "初回リビジョン",
    #     "already_tracked": "追跡済み",
    # }

    # # --- Histogram: lifetime distribution with origin breakdown ---
    # fig, ax = plt.subplots(figsize=(10, 6))
    # max_lifetime = int(absorbed_t0["lifetime"].max())

    # # Stacked histogram for lifetime=1 (by origin) and lifetime>=2 (already_tracked)
    # origin_order = ["newly_added", "similarity_crossed", "first_revision", "already_tracked"]
    # bottom = pd.Series(0, index=range(1, max_lifetime + 1))

    # for origin in origin_order:
    #     subset = absorbed_t0[absorbed_t0["origin"] == origin]
    #     if subset.empty:
    #         continue
    #     counts = subset["lifetime"].value_counts().reindex(range(1, max_lifetime + 1), fill_value=0)
    #     ax.bar(
    #         counts.index,
    #         counts.values,
    #         bottom=bottom.values,
    #         color=colors[origin],
    #         label=label_map[origin],
    #         edgecolor="white",
    #         linewidth=0.5,
    #     )
    #     bottom += counts

    # ax.set_xlabel("ライフタイム (リビジョンペア数)")
    # ax.set_ylabel("メソッド数")
    # ax.legend(loc="upper right", frameon=True, fancybox=True, shadow=True)
    # ax.set_xticks(range(1, max_lifetime + 1))
    # ax.grid(True, alpha=0.3, linestyle="--", axis="y")

    # plt.tight_layout()
    # Path(output_histogram).parent.mkdir(parents=True, exist_ok=True)
    # plt.savefig(output_histogram, dpi=300, bbox_inches="tight", facecolor="white", edgecolor="none")
    # plt.close()
    # console.print(f"[green]Histogram saved to:[/green] {output_histogram}")

    # # --- Per-revision breakdown stacked bar chart ---
    # rev_order = sorted(absorbed_t0[ColumnNames.PREV_REVISION_ID.value].dropna().unique())
    # rev_breakdown = pd.crosstab(
    #     absorbed_t0[ColumnNames.PREV_REVISION_ID.value],
    #     absorbed_t0["origin"],
    # ).reindex(index=rev_order, columns=origin_order, fill_value=0)

    # fig2, ax2 = plt.subplots(figsize=(14, 6))
    # bottom2 = pd.Series(0.0, index=rev_breakdown.index)

    # for origin in origin_order:
    #     if origin not in rev_breakdown.columns:
    #         continue
    #     vals = rev_breakdown[origin]
    #     ax2.bar(
    #         range(len(rev_order)),
    #         vals.values,
    #         bottom=bottom2.values,
    #         color=colors[origin],
    #         label=label_map[origin],
    #         edgecolor="white",
    #         linewidth=0.5,
    #     )
    #     bottom2 += vals

    # ax2.set_xlabel("リビジョン")
    # ax2.set_ylabel("Absorbed メソッド数")
    # ax2.set_xticks(range(len(rev_order)))
    # ax2.set_xticklabels([r[:10] for r in rev_order], rotation=45, ha="right", fontsize=8)
    # ax2.legend(loc="upper left", frameon=True, fancybox=True, shadow=True)
    # ax2.grid(True, alpha=0.3, linestyle="--", axis="y")

    # plt.tight_layout()
    # Path(output_revision_breakdown).parent.mkdir(parents=True, exist_ok=True)
    # plt.savefig(
    #     output_revision_breakdown,
    #     dpi=300,
    #     bbox_inches="tight",
    #     facecolor="white",
    #     edgecolor="none",
    # )
    # plt.close()
    # console.print(f"[green]Revision breakdown saved to:[/green] {output_revision_breakdown}")
