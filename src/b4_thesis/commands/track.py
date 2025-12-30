from pathlib import Path

import click
from rich.console import Console

from b4_thesis.const.column import ColumnNames
from b4_thesis.core.track.merge_splits import MergeSplitsTracker
from b4_thesis.core.track.method import MethodTracker
import pandas as pd

console = Console()


def _parse_progressive_thresholds(thresholds_str: str | None) -> list[int] | None:
    """Parse and validate progressive thresholds.

    Args:
        thresholds_str: Comma-separated threshold values (e.g., "90,80,70")

    Returns:
        Sorted list of threshold values (high to low), or None if not provided

    Raises:
        ValueError: If thresholds are invalid
    """
    if not thresholds_str:
        return None

    try:
        parsed = [int(t.strip()) for t in thresholds_str.split(",")]
    except ValueError as e:
        raise ValueError("Progressive thresholds must be comma-separated integers") from e

    # Validate range
    invalid = [t for t in parsed if not 0 <= t <= 100]
    if invalid:
        raise ValueError(f"Progressive thresholds must be between 0 and 100, got: {invalid}")

    # Sort in descending order (high to low)
    return sorted(parsed, reverse=True)


def _apply_optimization_defaults(
    optimize: bool,
    use_lsh: bool,
    use_optimized_similarity: bool,
    progressive_thresholds: str | None,
) -> tuple[bool, bool, str]:
    """Apply optimization defaults if --optimize flag is set.

    Args:
        optimize: Whether --optimize flag is set
        use_lsh: Current use_lsh value
        use_optimized_similarity: Current use_optimized_similarity value
        progressive_thresholds: Current progressive_thresholds value

    Returns:
        Tuple of (use_lsh, use_optimized_similarity, progressive_thresholds)
    """
    if not optimize:
        return use_lsh, use_optimized_similarity, progressive_thresholds or ""

    return (
        True,  # use_lsh
        True,  # use_optimized_similarity
        progressive_thresholds or "90,80,70",
    )


# Common option decorators
def common_tracking_options(f):
    """Apply common tracking options to a command.

    Adds: --input, --output, --start-date, --end-date, --summary, --verbose
    """
    f = click.option(
        "--end-date",
        type=click.DateTime(formats=["%Y-%m-%d"]),
        help="End date for filtering revisions (YYYY-MM-DD)",
    )(f)
    f = click.option(
        "--start-date",
        type=click.DateTime(formats=["%Y-%m-%d"]),
        help="Start date for filtering revisions (YYYY-MM-DD)",
    )(f)
    f = click.option(
        "--output",
        "-o",
        type=click.Path(file_okay=False, dir_okay=True),
        required=True,
        help="Output directory for CSV files",
    )(f)
    f = click.option(
        "--input",
        "-i",
        type=click.Path(exists=True, file_okay=False, dir_okay=True),
        required=True,
        help="Input directory containing revision subdirectories",
    )(f)
    return f


def optimization_options(f):
    """Apply optimization-related options to a command.

    Adds: --use-lsh, --lsh-threshold, --lsh-num-perm, --top-k,
          --use-optimized-similarity, --progressive-thresholds, --optimize
    """
    f = click.option(
        "--optimize",
        is_flag=True,
        help="Enable all optimizations with recommended defaults",
    )(f)
    f = click.option(
        "--progressive-thresholds",
        type=str,
        default=None,
        help='Progressive thresholds as comma-separated values (e.g., "90,80,70")',
    )(f)
    f = click.option(
        "--use-optimized-similarity",
        is_flag=True,
        help="Use optimized similarity with banded LCS (Phase 5.3.2 optimization)",
    )(f)
    f = click.option(
        "--top-k",
        type=click.IntRange(1),
        default=20,
        help="Number of top candidates per source block (default: 20)",
    )(f)
    f = click.option(
        "--lsh-num-perm",
        type=click.IntRange(32, 256),
        default=128,
        help="Number of LSH permutations (32-256, default: 128)",
    )(f)
    f = click.option(
        "--lsh-threshold",
        type=click.FloatRange(0.0, 1.0),
        default=0.7,
        help="LSH similarity threshold (0.0-1.0, default: 0.7)",
    )(f)
    f = click.option(
        "--use-lsh",
        is_flag=True,
        help="Enable LSH indexing for candidate filtering (Phase 5.3.2 optimization)",
    )(f)
    return f


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
    "--input-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    required=True,
    default="./output/methods_tracking.csv",
    help="Input CSV file with method tracking results",
)
@click.option(
    "--output-file",
    type=click.Path(file_okay=True, dir_okay=False),
    required=True,
    default="./output/versions/method_tracking_merge_splits.csv",
    help="Output CSV file for merged code blocks",
)
@click.option(
    "--verify-threshold",
    type=click.FloatRange(0.0, 1.0),
    default=0.7,
    help="Verification threshold for merging splits (0.0-1.0, default: 0.7)",
)
def merge_splits(input_file: str, output_file: str, verify_threshold: float) -> None:
    """Merge split code blocks across revisions."""
    method_tracking_df = pd.read_csv(input_file)

    # Filter to only matched rows for merge/split detection
    # (deleted and added rows don't participate in merge/split analysis)
    matched_df = method_tracking_df[method_tracking_df[ColumnNames.IS_MATCHED.value]]

    merger = MergeSplitsTracker()
    merged_df = merger.merge_splits(matched_df, verify_threshold)

    merged_df.to_csv(output_file, index=False)
    console.print(f"[green]Results saved to:[/green] {output_file} rows:{len(merged_df)}")
