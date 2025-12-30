from pathlib import Path

import click
from rich.console import Console

from b4_thesis.const.column import ColumnNames
from b4_thesis.core.track.method import MethodTracker

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
