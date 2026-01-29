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

            print(
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
        print(f"Processing revision pair: {prev_rev.timestamp} -> {curr_rev.timestamp}")

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
    print(df.groupby(["is_sig_matched", "is_sig_deleted", "is_sig_added"]).size())


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
        [df["is_matched"], df["is_deleted"], df["has_clone"]],
    )

    result.to_csv(output, index=True)
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
    default="./output/versions/nil/7_track_deletion_status.csv",
    help="Input file containing tracked methods data",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    default="./output/versions/nil/9_track_avg_similarity.csv",
    help="Output file for CSV data",
)
def track_avg_similarity(
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
            .mean()
            .rename("avg_similarity")
        )
        hash_2_sim = (
            clone_pairs.groupby(ColumnNames.TOKEN_HASH_2.value)["similarity"]
            .mean()
            .rename("avg_similarity")
        )

        avg_sim = pd.concat([hash_1_sim, hash_2_sim]).groupby(level=0).mean().round(1)

        df = df.merge(
            avg_sim, left_on=ColumnNames.PREV_TOKEN_HASH.value, right_index=True, how="outer"
        )
        output_df = pd.concat([output_df, df], ignore_index=True)

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(output_path, index=False)
    console.print(f"[green]Results saved to:[/green] {output_path}")


@nil.command()
def sim_count():
    df = pd.read_csv("./output/versions/nil/9_track_avg_similarity.csv")
    high_sim_df = df[df["avg_similarity"] >= 90]
    low_sim_df = df[(df["avg_similarity"] < 90) & (df["avg_similarity"] >= 70)]

    print(pd.crosstab(high_sim_df[ColumnNames.PREV_REVISION_ID.value], [high_sim_df["is_matched"]]))

    print(pd.crosstab(low_sim_df[ColumnNames.PREV_REVISION_ID.value], [low_sim_df["is_matched"]]))


@nil.command()
@click.option(
    "--input-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    default="./output/versions/nil/9_track_avg_similarity.csv",
    help="Input file containing tracked methods data",
)
@click.option(
    "--output-csv",
    type=click.Path(file_okay=True, dir_okay=False),
    default="./output/versions/nil/10_deletion_survival.csv",
    help="Input file containing tracked methods data",
)
@click.option(
    "--output-plot",
    type=click.Path(file_okay=True, dir_okay=False),
    default="./output/versions/nil/10_deletion_survival.png",
    help="Output file for the plot",
)
def deletion_survival(
    input_file: str,
    output_csv: str,
    output_plot: str,
) -> None:
    """Track avg_similarity evolution per method_id for different deletion types."""
    cols = [
        ColumnNames.PREV_REVISION_ID.value,
        "is_deleted",
        "is_partial_deleted",
        "is_all_deleted",
        "is_merge",
        "is_matched",
        "avg_similarity",
        "method_id",
    ]
    df = pd.read_csv(input_file, usecols=cols)

    # 各method_idの最新行で3分類: "Merged" / "Deleted" / "Matched"
    latest = (
        df.sort_values(ColumnNames.PREV_REVISION_ID.value, ascending=False)
        .groupby("method_id")
        .first()
    )
    latest["survival_group"] = None
    latest.loc[latest["is_matched"], "survival_group"] = "Matched"
    latest.loc[latest["is_deleted"], "survival_group"] = "Deleted"
    latest.loc[latest["is_merge"], "survival_group"] = "Merged"

    group_map = latest["survival_group"].dropna()
    df["survival_group"] = df["method_id"].map(group_map)
    df = df[df["survival_group"].notna()]

    # 各method_idごとに相対時間を計算（最新=0）
    df = df.sort_values(["method_id", ColumnNames.PREV_REVISION_ID.value])
    df["relative_time"] = (
        (
            df.groupby("method_id").cumcount()
            - df.groupby("method_id")["method_id"].transform("count")
            + 1
        )
        .fillna(0)
        .astype(int)
    )
    df.to_csv(output_csv, index=False)
    console.print(f"[green]Data with survival groups saved to:[/green] {output_csv}")

    # プロット設定（論文用）
    plt.rcParams.update(
        {
            "font.size": 12,
            "axes.titlesize": 14,
            "axes.labelsize": 12,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.fontsize": 11,
            "figure.dpi": 300,
        }
    )

    colors = {"Matched": "#1f77b4", "Merged": "#ff7f0e", "Deleted": "#d62728"}

    plot_df = df[df["avg_similarity"].notna()]

    # サンプル数の集計
    count_df = plot_df.groupby(["relative_time", "survival_group"]).size().reset_index(name="count")

    fig, axes = plt.subplots(2, 1, figsize=(12, 10), height_ratios=[3, 2], sharex=True)

    # 上段: 箱ひげ図
    time_values = sorted(plot_df["relative_time"].unique())
    sns.boxplot(
        data=plot_df,
        x="relative_time",
        y="avg_similarity",
        hue="survival_group",
        palette=colors,
        linewidth=1.2,
        fliersize=3,
        order=time_values,
        ax=axes[0],
    )
    axes[0].set_title("Clone Similarity", fontweight="bold", pad=15)
    axes[0].set_xlabel("")
    axes[0].set_ylabel("Average Similarity (%)", labelpad=10)
    axes[0].grid(True, alpha=0.3, linestyle="--")
    axes[0].legend(loc="upper left", frameon=True, fancybox=True, shadow=True)

    # 下段: サンプル数の折れ線グラフ（boxplotと同じカテゴリカル位置を使用）
    time_to_pos = {t: i for i, t in enumerate(time_values)}
    for group, color in colors.items():
        group_data = count_df[count_df["survival_group"] == group].sort_values("relative_time")
        positions = [time_to_pos[t] for t in group_data["relative_time"]]
        axes[1].plot(
            positions,
            group_data["count"].values,
            marker="o",
            markersize=4,
            color=color,
            label=group,
            linewidth=1.5,
        )
    axes[1].set_title("Sample Count", fontweight="bold", pad=15)
    axes[1].set_xlabel("Relative Time (0 = latest)", labelpad=10)
    axes[1].set_ylabel("Count", labelpad=10)
    axes[1].grid(True, alpha=0.3, linestyle="--")
    axes[1].legend(loc="upper left", frameon=True, fancybox=True, shadow=True)

    plt.tight_layout()
    plt.savefig(output_plot, dpi=300, bbox_inches="tight", facecolor="white", edgecolor="none")
    plt.close()
    console.print(f"[green]Plot saved to:[/green] {output_plot}")


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
