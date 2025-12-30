from pathlib import Path

import click
from rich.console import Console

from b4_thesis.const.column import ColumnNames
from b4_thesis.core.track.method import MethodTracker
import pandas as pd

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
