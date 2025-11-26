"""Track command for method and clone group evolution tracking.

This module provides commands for tracking evolution of methods and clone groups
across software revisions. It includes:

Commands:
    - track methods: Track individual method evolution
    - track groups: Track clone group evolution

Helper Functions:
    - _setup_paths(): Setup and validate input/output paths
    - _parse_progressive_thresholds(): Parse and validate progressive thresholds
    - _apply_optimization_defaults(): Apply optimization defaults
    - _log_basic_config(): Log basic configuration
    - _log_optimization_settings(): Log optimization settings
    - _build_status_message(): Build status message for tracking progress

Decorators:
    - common_tracking_options: Common CLI options (input, output, dates, etc.)
    - optimization_options: Optimization-related CLI options (LSH, banded LCS, etc.)
"""

from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from b4_thesis.analysis.clone_group_tracker import CloneGroupTracker
from b4_thesis.analysis.method_tracker import MethodTracker

console = Console()


# Helper functions for configuration and path management


def _setup_paths(input_path: str, output_path: str) -> tuple[Path, Path]:
    """Setup and validate input/output paths.

    Args:
        input_path: Input directory path
        output_path: Output directory path

    Returns:
        Tuple of (data_path, output_path) as Path objects
    """
    data_path = Path(input_path)
    output_path_obj = Path(output_path)
    output_path_obj.mkdir(parents=True, exist_ok=True)
    return data_path, output_path_obj


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


# Helper functions for logging


def _log_basic_config(
    verbose: bool,
    similarity: int,
    output_path: Path,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    overlap: float | None = None,
    parallel: bool = False,
    max_workers: int | None = None,
    optimize: bool = False,
) -> None:
    """Log basic configuration if verbose mode is enabled.

    Args:
        verbose: Whether verbose mode is enabled
        similarity: Similarity threshold
        output_path: Output directory path
        start_date: Start date filter (optional)
        end_date: End date filter (optional)
        overlap: Overlap threshold for groups (optional)
        parallel: Whether parallel processing is enabled (optional)
        max_workers: Number of worker processes (optional)
        optimize: Whether optimization mode is enabled (optional)
    """
    if not verbose:
        return

    console.print(f"[dim]Similarity threshold: {similarity}[/dim]")
    if overlap is not None:
        console.print(f"[dim]Overlap threshold: {overlap}[/dim]")
    console.print(f"[dim]Output directory: {output_path}[/dim]")
    if start_date:
        console.print(f"[dim]Start date: {start_date.strftime('%Y-%m-%d')}[/dim]")
    if end_date:
        console.print(f"[dim]End date: {end_date.strftime('%Y-%m-%d')}[/dim]")
    if parallel:
        workers = max_workers if max_workers else "auto (CPU cores)"
        console.print(f"[dim]Parallel processing: enabled (workers: {workers})[/dim]")
    if optimize:
        console.print("[dim]Optimization mode: enabled (all Phase 5.3 optimizations)[/dim]")


def _log_optimization_settings(
    verbose: bool,
    use_lsh: bool,
    lsh_threshold: float,
    lsh_num_perm: int,
    top_k: int,
    use_optimized_similarity: bool,
    parsed_progressive_thresholds: list[int] | None,
) -> None:
    """Log optimization settings if verbose mode is enabled.

    Args:
        verbose: Whether verbose mode is enabled
        use_lsh: Whether LSH indexing is enabled
        lsh_threshold: LSH similarity threshold
        lsh_num_perm: Number of LSH permutations
        top_k: Number of top candidates
        use_optimized_similarity: Whether optimized similarity is enabled
        parsed_progressive_thresholds: Parsed progressive thresholds
    """
    if not verbose:
        return

    if use_lsh:
        console.print(
            f"[dim]LSH indexing: enabled "
            f"(threshold={lsh_threshold}, num_perm={lsh_num_perm}, top_k={top_k})[/dim]"
        )
    if use_optimized_similarity:
        console.print("[dim]Optimized similarity: enabled (banded LCS)[/dim]")
    if parsed_progressive_thresholds:
        console.print(f"[dim]Progressive thresholds: {parsed_progressive_thresholds}[/dim]")


def _build_status_message(entity_type: str, optimized: bool, parallel: bool = False) -> str:
    """Build status message for tracking progress.

    Args:
        entity_type: Type of entity being tracked ("methods" or "clone groups")
        optimized: Whether optimization is enabled
        parallel: Whether parallel processing is enabled

    Returns:
        Formatted status message
    """
    parts = [f"[bold green]Analyzing {entity_type}"]
    if optimized:
        parts.append(" (optimized)")
    if parallel:
        parts.append(" (parallel)")
    parts.append("...")
    return "".join(parts)


# Common option decorators


def common_tracking_options(f):
    """Apply common tracking options to a command.

    Adds: --input, --output, --start-date, --end-date, --summary, --verbose
    """
    f = click.option("--verbose", "-v", is_flag=True, help="Verbose output")(f)
    f = click.option(
        "--summary",
        "-s",
        is_flag=True,
        help="Display summary statistics",
    )(f)
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
    summary: bool,
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
    """Track method evolution across revisions.

    Analyzes method evolution by tracking individual methods across revisions,
    identifying state transitions (new, modified, deleted, unchanged), and
    detecting clone relationships.

    Args:
        input: Input directory containing revision subdirectories
        output: Output directory for CSV files
        start_date: Start date for filtering revisions (optional)
        end_date: End date for filtering revisions (optional)
        similarity: Similarity threshold for method matching (0-100)
        summary: Whether to display summary statistics
        verbose: Enable verbose output
        parallel: Enable parallel processing for similarity calculation
        max_workers: Maximum number of worker processes (optional)
        use_lsh: Enable LSH indexing for candidate filtering
        lsh_threshold: LSH similarity threshold (0.0-1.0)
        lsh_num_perm: Number of LSH permutations (32-256)
        top_k: Number of top candidates per source block
        use_optimized_similarity: Use optimized similarity with banded LCS
        progressive_thresholds: Progressive thresholds (comma-separated)
        optimize: Enable all optimizations with recommended defaults

    Outputs:
        - method_tracking.csv: Method tracking results with state classification
          Columns: revision, block_id, file_path, method_name, state,
                   clone_count, matched_to, similarity_score, etc.
    """
    # Setup paths
    data_path, output_path = _setup_paths(input, output)
    console.print(f"[bold blue]Tracking methods:[/bold blue] {data_path}")

    # Apply optimization defaults
    use_lsh, use_optimized_similarity, progressive_thresholds = _apply_optimization_defaults(
        optimize, use_lsh, use_optimized_similarity, progressive_thresholds
    )

    # Log basic configuration
    _log_basic_config(
        verbose,
        similarity,
        output_path,
        start_date,
        end_date,
        parallel=parallel,
        max_workers=max_workers,
        optimize=optimize,
    )

    # Parse progressive thresholds
    try:
        parsed_progressive_thresholds = _parse_progressive_thresholds(progressive_thresholds)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

    # Display optimization settings
    _log_optimization_settings(
        verbose,
        use_lsh,
        lsh_threshold,
        lsh_num_perm,
        top_k,
        use_optimized_similarity,
        parsed_progressive_thresholds,
    )

    try:
        # Initialize tracker
        tracker = MethodTracker(
            data_path,
            similarity_threshold=similarity,
            use_lsh=use_lsh,
            lsh_threshold=lsh_threshold,
            lsh_num_perm=lsh_num_perm,
            top_k=top_k,
            use_optimized_similarity=use_optimized_similarity,
            progressive_thresholds=parsed_progressive_thresholds,
        )

        # Track methods
        status_msg = _build_status_message("methods", use_lsh or use_optimized_similarity, parallel)
        with console.status(status_msg):
            df = tracker.track(
                start_date=start_date,
                end_date=end_date,
                parallel=parallel,
                max_workers=max_workers,
            )

        # Check if any data was found
        if len(df) == 0:
            console.print("[yellow]No revisions found in the specified date range.[/yellow]")
            console.print("[yellow]0 revisions processed, 0 methods tracked.[/yellow]")
            return

        # Save results
        output_file = output_path / "method_tracking.csv"
        df.to_csv(output_file, index=False)

        console.print("[green]✓[/green] Method tracking complete!")
        console.print(f"[green]Results saved to:[/green] {output_file}")

        # Display summary if requested
        if summary:
            _display_method_summary(df)

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
    summary: bool,
    verbose: bool,
    use_lsh: bool,
    lsh_threshold: float,
    lsh_num_perm: int,
    top_k: int,
    use_optimized_similarity: bool,
    progressive_thresholds: str | None,
    optimize: bool,
) -> None:
    """Track clone group evolution across revisions.

    Analyzes clone group evolution by tracking groups of similar methods across
    revisions, identifying state transitions (new, modified, deleted, unchanged),
    and recording membership changes.

    Args:
        input: Input directory containing revision subdirectories
        output: Output directory for CSV files
        start_date: Start date for filtering revisions (optional)
        end_date: End date for filtering revisions (optional)
        similarity: Similarity threshold for group detection (0-100)
        overlap: Overlap threshold for group matching (0.0-1.0)
        summary: Whether to display summary statistics
        verbose: Enable verbose output
        use_lsh: Enable LSH indexing for method matching
        lsh_threshold: LSH similarity threshold (0.0-1.0)
        lsh_num_perm: Number of LSH permutations (32-256)
        top_k: Number of top candidates
        use_optimized_similarity: Use optimized similarity with banded LCS
        progressive_thresholds: Progressive thresholds (comma-separated)
        optimize: Enable all optimizations with recommended defaults

    Outputs:
        - group_tracking.csv: Group tracking results with state classification
          Columns: group_id, revision, state, member_count, matched_to, etc.
        - group_membership.csv: Group membership snapshots for each revision
          Columns: group_id, revision, block_id, file_path, method_name, etc.
    """
    # Setup paths
    data_path, output_path = _setup_paths(input, output)
    console.print(f"[bold blue]Tracking clone groups:[/bold blue] {data_path}")

    # Apply optimization defaults
    use_lsh, use_optimized_similarity, progressive_thresholds = _apply_optimization_defaults(
        optimize, use_lsh, use_optimized_similarity, progressive_thresholds
    )

    # Log basic configuration
    _log_basic_config(
        verbose,
        similarity,
        output_path,
        start_date,
        end_date,
        overlap=overlap,
        optimize=optimize,
    )

    # Parse progressive thresholds
    try:
        parsed_progressive_thresholds = _parse_progressive_thresholds(progressive_thresholds)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

    # Display optimization settings
    _log_optimization_settings(
        verbose,
        use_lsh,
        lsh_threshold,
        lsh_num_perm,
        top_k,
        use_optimized_similarity,
        parsed_progressive_thresholds,
    )

    try:
        # Initialize tracker
        tracker = CloneGroupTracker(
            data_path,
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
        status_msg = _build_status_message("clone groups", use_lsh or use_optimized_similarity)
        with console.status(status_msg):
            group_df, membership_df = tracker.track(start_date=start_date, end_date=end_date)

        # Check if any data was found
        if len(group_df) == 0:
            console.print("[yellow]No revisions found in the specified date range.[/yellow]")
            console.print("[yellow]0 revisions processed, 0 groups tracked.[/yellow]")
            return

        # Save results
        group_file = output_path / "group_tracking.csv"
        membership_file = output_path / "group_membership.csv"
        group_df.to_csv(group_file, index=False)
        membership_df.to_csv(membership_file, index=False)

        console.print("[green]✓[/green] Group tracking complete!")
        console.print("[green]Results saved to:[/green]")
        console.print(f"  - {group_file}")
        console.print(f"  - {membership_file}")

        # Display summary if requested
        if summary:
            _display_group_summary(group_df)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            console.print_exception()
        raise click.Abort()


def _display_method_summary(df):
    """Display summary statistics for method tracking."""
    table = Table(title="Method Tracking Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green", justify="right")

    total_methods = len(df)
    revisions = df["revision"].nunique()

    # State counts
    state_counts = df["state"].value_counts().to_dict()

    table.add_row("Total methods tracked", str(total_methods))
    table.add_row("Total revisions", str(revisions))
    table.add_row("", "")  # Empty row

    for state, count in sorted(state_counts.items()):
        table.add_row(f"  {state.capitalize()}", str(count))

    # Clone statistics
    clone_methods = len(df[df["clone_count"] > 0])
    if clone_methods > 0:
        table.add_row("", "")  # Empty row
        table.add_row("Methods in clone groups", str(clone_methods))

    console.print(table)


def _display_group_summary(df):
    """Display summary statistics for group tracking."""
    table = Table(title="Clone Group Tracking Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green", justify="right")

    total_groups = len(df)
    revisions = df["revision"].nunique()

    # State counts
    state_counts = df["state"].value_counts().to_dict()

    table.add_row("Total groups tracked", str(total_groups))
    table.add_row("Total revisions", str(revisions))
    table.add_row("", "")  # Empty row

    for state, count in sorted(state_counts.items()):
        table.add_row(f"  {state.capitalize()}", str(count))

    # Group size statistics
    avg_size = df["member_count"].mean()
    max_size = df["member_count"].max()
    table.add_row("", "")  # Empty row
    table.add_row("Average group size", f"{avg_size:.1f}")
    table.add_row("Maximum group size", str(max_size))

    console.print(table)
