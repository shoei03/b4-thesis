from datetime import datetime
from pathlib import Path

import click
from rich.console import Console

from b4_thesis.analysis.clone_group_tracker import CloneGroupTracker
from b4_thesis.analysis.method_tracker import MethodTracker

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
@optimization_options
@click.option(
    "--max-workers",
    type=click.IntRange(1),
    help="Maximum number of worker processes (default: number of CPU cores)",
)
@click.option(
    "--parallel",
    "-p",
    is_flag=True,
    help="Enable parallel processing for similarity calculation",
)
@click.option(
    "--similarity",
    type=click.IntRange(0, 100),
    default=70,
    help="Similarity threshold for method matching (0-100, default: 70)",
)
@common_tracking_options
def methods(
    input: str,
    output: str,
    start_date: datetime | None,
    end_date: datetime | None,
    similarity: int,
    verbose: bool,
    parallel: bool,
    max_workers: int | None,
    use_lsh: bool,
    lsh_threshold: float,
    lsh_num_perm: int,
    top_k: int,
    use_optimized_similarity: bool,
    progressive_thresholds: str | None,
    optimize: bool,
) -> None:
    """Track method evolution across revisions."""
    # Apply optimization defaults
    use_lsh, use_optimized_similarity, progressive_thresholds = _apply_optimization_defaults(
        optimize, use_lsh, use_optimized_similarity, progressive_thresholds
    )

    # Parse progressive thresholds
    try:
        parsed_progressive_thresholds = _parse_progressive_thresholds(progressive_thresholds)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

    try:
        # Initialize tracker
        tracker = MethodTracker(
            input,
            similarity_threshold=similarity,
            use_lsh=use_lsh,
            lsh_threshold=lsh_threshold,
            lsh_num_perm=lsh_num_perm,
            top_k=top_k,
            use_optimized_similarity=use_optimized_similarity,
            progressive_thresholds=parsed_progressive_thresholds,
        )

        # Track methods
        with console.status("Tracking methods..."):
            df = tracker.track(
                start_date=start_date,
                end_date=end_date,
                parallel=parallel,
                max_workers=max_workers,
            )

        output_file = Path(output) / "method_tracking.csv"
        df.to_csv(output_file, index=False)

        console.print("[green]✓[/green] Method tracking complete!")
        console.print(f"[green]Results saved to:[/green] {output_file} row:{df.shape[0]}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            console.print_exception()
        raise click.Abort()


@track.command()
@optimization_options
@click.option(
    "--overlap",
    type=click.FloatRange(0.0, 1.0),
    default=0.5,
    help="Overlap threshold for group matching (0.0-1.0, default: 0.5)",
)
@click.option(
    "--similarity",
    type=click.IntRange(0, 100),
    default=70,
    help="Similarity threshold for group detection (0-100, default: 70)",
)
@common_tracking_options
def groups(
    input: str,
    output: str,
    start_date: datetime | None,
    end_date: datetime | None,
    similarity: int,
    overlap: float,
    verbose: bool,
    use_lsh: bool,
    lsh_threshold: float,
    lsh_num_perm: int,
    top_k: int,
    use_optimized_similarity: bool,
    progressive_thresholds: str | None,
    optimize: bool,
) -> None:
    """Track clone group evolution across revisions."""
    # Apply optimization defaults
    use_lsh, use_optimized_similarity, progressive_thresholds = _apply_optimization_defaults(
        optimize, use_lsh, use_optimized_similarity, progressive_thresholds
    )

    # Parse progressive thresholds
    try:
        parsed_progressive_thresholds = _parse_progressive_thresholds(progressive_thresholds)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

    try:
        # Initialize tracker
        tracker = CloneGroupTracker(
            input,
            similarity_threshold=similarity,
            overlap_threshold=overlap,
            use_lsh=use_lsh,
            lsh_threshold=lsh_threshold,
            lsh_num_perm=lsh_num_perm,
            top_k=top_k,
            use_optimized_similarity=use_optimized_similarity,
            progressive_thresholds=parsed_progressive_thresholds,
        )

        # Track groups
        with console.status("Tracking clone groups..."):
            group_df, membership_df = tracker.track(start_date=start_date, end_date=end_date)

        group_file = output / "group_tracking.csv"
        membership_file = output / "group_membership.csv"
        group_df.to_csv(group_file, index=False)
        membership_df.to_csv(membership_file, index=False)

        console.print("[green]✓[/green] Group tracking complete!")
        console.print("[green]Results saved to:[/green]")
        console.print(f"  - {group_file}")
        console.print(f"  - {membership_file}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            console.print_exception()
        raise click.Abort()
