from pathlib import Path

import click
import pandas as pd
from rich.console import Console

from b4_thesis.const.column import ColumnNames
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
    default="./output/versions/nil/4_track_median_similarity.csv",
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
    default="./output/versions/nil/6_class_delete.csv",
    help="Output file for CSV data",
)
def class_delete(
    input_file: str,
    output: str,
):
    df = pd.read_csv(input_file)

    # ブール型に変換（文字列として読み込まれている場合に対応）
    df["is_matched"] = df["is_matched"].astype(bool)
    df["is_absorbed"] = df["is_absorbed"].astype(bool)
    df["is_deleted"] = df["is_deleted"].astype(bool)
    df["has_clone"] = df["has_clone"].astype(bool)

    # 状態を3分類: deleted, absorbed, survived
    df["status"] = "survived"
    df.loc[df["is_deleted"], "status"] = "deleted"
    df.loc[df["is_absorbed"], "status"] = "absorbed"

    result = pd.crosstab(
        df[ColumnNames.PREV_REVISION_ID.value],
        [df["status"], df["has_clone"]],
    )

    # クローン有無別の削除率（is_deleted）
    deleted_rate_by_clone = (
        df.groupby([ColumnNames.PREV_REVISION_ID.value, "has_clone"])["is_deleted"]
        .apply(lambda x: x.mean() * 100)
        .unstack(fill_value=0)
        .round(2)
    )

    # クローン有無別の吸収率（is_absorbed）
    absorbed_rate_by_clone = (
        df.groupby([ColumnNames.PREV_REVISION_ID.value, "has_clone"])["is_absorbed"]
        .apply(lambda x: x.mean() * 100)
        .unstack(fill_value=0)
        .round(2)
    )

    # カラムとして追加
    result[("clone_deleted_rate(%)", "")] = deleted_rate_by_clone.get(True, 0)
    result[("no_clone_deleted_rate(%)", "")] = deleted_rate_by_clone.get(False, 0)
    result[("clone_absorbed_rate(%)", "")] = absorbed_rate_by_clone.get(True, 0)
    result[("no_clone_absorbed_rate(%)", "")] = absorbed_rate_by_clone.get(False, 0)

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
    default="./output/versions/nil/5_has_clone.csv",
    help="Input file containing tracked methods data",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    required=True,
    default="./output/versions/nil/7_class_high_low_sim.csv",
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
            "is_absorbed",
            "has_clone",
        ],
        dtype={
            "is_matched": "boolean",
            "is_deleted": "boolean",
            "is_absorbed": "boolean",
            "has_clone": "boolean",
        },
        low_memory=False,
    )

    df = df.sort_values("prev_revision_id")
    df["high_sim"] = df["median_similarity"] >= 90
    df["low_sim"] = (df["median_similarity"] < 90) & (df["median_similarity"] >= 70)

    # 状態を3分類: deleted, absorbed, survived
    df["status"] = "survived"
    df.loc[df["is_deleted"], "status"] = "deleted"
    df.loc[df["is_absorbed"], "status"] = "absorbed"

    result = pd.crosstab(
        df[ColumnNames.PREV_REVISION_ID.value],
        [df["status"], df["high_sim"], df["low_sim"]],
    )

    # high_sim の削除率と吸収率を計算
    high_sim_deleted_rate = (
        df[df["high_sim"] & df["has_clone"]]
        .groupby(ColumnNames.PREV_REVISION_ID.value)["is_deleted"]
        .apply(lambda x: x.astype(float).mean() * 100)
        .round(2)
    )
    high_sim_absorbed_rate = (
        df[df["high_sim"] & df["has_clone"]]
        .groupby(ColumnNames.PREV_REVISION_ID.value)["is_absorbed"]
        .apply(lambda x: x.astype(float).mean() * 100)
        .round(2)
    )

    # low_sim の削除率と吸収率を計算
    low_sim_deleted_rate = (
        df[df["low_sim"] & df["has_clone"]]
        .groupby(ColumnNames.PREV_REVISION_ID.value)["is_deleted"]
        .apply(lambda x: x.astype(float).mean() * 100)
        .round(2)
    )
    low_sim_absorbed_rate = (
        df[df["low_sim"] & df["has_clone"]]
        .groupby(ColumnNames.PREV_REVISION_ID.value)["is_absorbed"]
        .apply(lambda x: x.astype(float).mean() * 100)
        .round(2)
    )

    # カラムとして追加（3レベルのマルチインデックスに対応）
    result[("high_sim_deleted_rate(%)", "", "")] = high_sim_deleted_rate
    result[("high_sim_absorbed_rate(%)", "", "")] = high_sim_absorbed_rate
    result[("low_sim_deleted_rate(%)", "", "")] = low_sim_deleted_rate
    result[("low_sim_absorbed_rate(%)", "", "")] = low_sim_absorbed_rate

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
