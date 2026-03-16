import click
from rich.console import Console

from b4_thesis.const.column import ColumnNames
from b4_thesis.utils.revision_manager import RevisionManager
import pandas as pd

from pathlib import Path

console = Console()


@click.group()
def sim():
    pass


def _add_similarity_column(clone_pairs: pd.DataFrame) -> pd.DataFrame:
    """Add a unified similarity column to clone_pairs DataFrame."""
    clone_pairs["similarity"] = clone_pairs[ColumnNames.VERIFY_SIMILARITY.value].fillna(
        clone_pairs[ColumnNames.NGRAM_OVERLAP.value]
    )
    return clone_pairs


@sim.command()
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
    default="./output/versions/labels/final/method_identity_tracking.csv",
    help="Input CSV containing method identity tracking labels",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    default="./output/versions/features/method_similarity_features.csv",
    help="Output CSV for method-level similarity features",
)
def apply_median_similarity(
    input: str,
    input_file: str,
    output: str,
) -> None:
    """Apply median similarity for each method across revisions."""
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
            avg_sim, left_on=ColumnNames.PREV_TOKEN_HASH.value, right_index=True, how="left"
        )
        output_df = pd.concat([output_df, df], ignore_index=True)

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(output_path, index=False)
    console.print(f"[green]Results saved to:[/green] {output_path}")


@sim.command()
@click.option(
    "--input-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    default="./output/versions/features/method_similarity_features.csv",
    help="Input CSV containing method-level similarity features",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    required=True,
    default="./output/versions/analysis/deletion_by_clone_summary.csv",
    help="Output CSV for deletion/absorption summary by clone presence",
)
def by_clone(
    input_file: str,
    output: str,
):
    df = pd.read_csv(input_file)

    df["has_clone"] = df["median_similarity"] >= 70

    # ブール型に変換（文字列として読み込まれている場合に対応）
    df["is_matched"] = df["is_matched"].astype(bool)
    df["is_absorbed"] = df["is_absorbed"].astype(bool)
    df["is_deleted"] = df["is_deleted"].astype(bool)

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

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=True)
    console.print(f"[green]Results saved to:[/green] {output_path}")


@sim.command()
@click.option(
    "--input-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    default="./output/versions/features/method_similarity_features.csv",
    help="Input CSV containing method-level similarity features",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    required=True,
    default="./output/versions/analysis/deletion_by_similarity_band_summary.csv",
    help="Output CSV for deletion/absorption summary by similarity band",
)
def by_sim(
    input_file: str,
    output: str,
):
    df = pd.read_csv(input_file)

    df = df.sort_values("prev_revision_id")
    df["has_clone"] = df["median_similarity"] >= 70
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

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=True)
    console.print(f"[green]Results saved to:[/green] {output_path}")
