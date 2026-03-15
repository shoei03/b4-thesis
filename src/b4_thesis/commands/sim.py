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
