from pathlib import Path
import json

import click
from rich.console import Console

from b4_thesis.const.column import ColumnNames
from b4_thesis.core.track.method import MethodTracker
from b4_thesis.utils.revision_manager import RevisionManager
import pandas as pd
import numpy as np

console = Console()


@click.group()
def track():
    """Track method and clone group evolution across revisions.

    This command group provides subcommands for tracking:
    - methods: Track individual method evolution
    - groups: Track clone group evolution
    """
    pass


@track.command()
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
    help="Input directory containing revision subdirectories",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=False, dir_okay=True),
    required=True,
    help="Output directory for CSV files",
)
def methods(
    input: str,
    output: str,
    similarity: float,
    n_gram_size: int,
    filter_threshold: float,
) -> None:
    """Track method evolution across revisions."""
    try:
        method_tracker = MethodTracker()
        result_df = method_tracker.track(
            Path(input),
            similarity_threshold=similarity,
            n_gram_size=n_gram_size,
            filter_threshold=filter_threshold,
        )

        # Define sort keys for consistent ordering
        sort_keys = [
            ColumnNames.PREV_REVISION_ID.value,
            ColumnNames.CURR_REVISION_ID.value,
            ColumnNames.PREV_TOKEN_HASH.value,
            ColumnNames.CURR_TOKEN_HASH.value,
            ColumnNames.PREV_FILE_PATH.value,
            ColumnNames.CURR_FILE_PATH.value,
            ColumnNames.PREV_START_LINE.value,
            ColumnNames.CURR_START_LINE.value,
        ]

        existing_keys = [k for k in sort_keys if k in result_df.columns]
        if existing_keys:
            result_df = result_df.sort_values(by=existing_keys)

        output_path = Path(output)
        output_path.mkdir(parents=True, exist_ok=True)

        file_path = output_path / "methods_tracking_with_merge_splits.csv"
        result_df.to_csv(file_path, index=False)

        console.print(f"[green]Results saved to:[/green] {file_path}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@track.command()
@click.option(
    "--input",
    "-i",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    required=True,
    default="./output/versions/methods_tracking_with_merge_splits.csv",
    help="Input file containing tracked methods data",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    required=False,
    default="./output/versions/methods_classified.csv",
    help="Output file for classified results",
)
def classify(
    input: str,
    output: str,
) -> None:
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
        ],
    )

    prev_col = ColumnNames.PREV_REVISION_ID.value
    curr_col = ColumnNames.CURR_REVISION_ID.value

    # ステップ1: 両方存在する行でグループを作成
    both_exist_mask = df[prev_col].notna() & df[curr_col].notna()
    df_both = df[both_exist_mask].copy()
    df_nan = df[~both_exist_mask].copy()

    # 両方存在する組み合わせのユニークなペアを取得
    unique_pairs = df_both[[prev_col, curr_col]].drop_duplicates()

    # グループキーを作成（タプルの文字列表現）
    df_both["group_key"] = df_both[prev_col].astype(str) + "___" + df_both[curr_col].astype(str)

    # ステップ2: NaNを含む行を既存グループにマッピング
    # PREVまたはCURRが既存ペアに一致するかチェック
    prev_to_group = {}
    curr_to_group = {}

    for _, row in unique_pairs.iterrows():
        group_key = str(row[prev_col]) + "___" + str(row[curr_col])
        prev_val = row[prev_col]
        curr_val = row[curr_col]

        # 同じPREVまたはCURRを持つグループをマッピング
        if prev_val not in prev_to_group:
            prev_to_group[prev_val] = group_key
        if curr_val not in curr_to_group:
            curr_to_group[curr_val] = group_key

    # NaN行にグループキーを割り当て
    def assign_group(row):
        prev_val = row[prev_col]
        curr_val = row[curr_col]

        # PREVが存在する場合
        if pd.notna(prev_val) and prev_val in prev_to_group:
            return prev_to_group[prev_val]
        # CURRが存在する場合
        if pd.notna(curr_val) and curr_val in curr_to_group:
            return curr_to_group[curr_val]
        # どちらも既存グループに該当しない場合
        if pd.notna(prev_val):
            return str(prev_val) + "___nan"
        if pd.notna(curr_val):
            return "nan___" + str(curr_val)
        return "nan___nan"

    df_nan["group_key"] = df_nan.apply(assign_group, axis=1)

    # 結合
    df_result = pd.concat([df_both, df_nan], ignore_index=True)

    # グループ化して集計
    result = df_result.groupby("group_key").sum()[
        [
            ColumnNames.IS_MATCHED.value,
            ColumnNames.IS_DELETED.value,
            ColumnNames.IS_ADDED.value,
            ColumnNames.IS_SPLIT.value,
            ColumnNames.IS_MERGED.value,
            ColumnNames.IS_MODIFIED.value,
        ]
    ]

    # CSVとして保存（インデックス（group_key）も含める）
    result.to_csv(output)


@track.command()
@click.option(
    "--input",
    "-i",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    required=True,
    default="./output/versions/methods_tracking_with_merge_splits.csv",
    help="Input file containing tracked methods data",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    required=False,
    default="./output/versions/tmp.json",
    help="Output file for classified results",
)
def stats(input: str, output: str) -> None:
    """Display statistics of method tracking results."""
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
            f"Processing revision pair: {unique_revisions[i]} -> {unique_revisions[i + 1]} -> {unique_revisions[i + 2]} "
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


@track.command()
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
    default="./output/versions/methods_tracking_with_merge_splits.csv",
    help="Input file containing tracked methods data",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    required=True,
    default="./output/versions/clones/methods_with_clone_flag.csv",
    help="Output file for CSV data",
)
def clones(
    input: str,
    input_file: str,
    output: str,
) -> None:
    """Track clone group evolution across revisions."""
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

    df["has_clone"] = False
    for rev_id, hashes in rev_clone_hashes.items():
        mask = df[prev_rev_col] == rev_id
        matched = df.loc[mask, prev_hash_col].isin(hashes)
        df.loc[mask, "has_clone"] = matched

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    console.print(f"[green]Results saved to:[/green] {output_path}")
