"""Track command for method and clone group evolution tracking."""

from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from b4_thesis.analysis.clone_group_tracker import CloneGroupTracker
from b4_thesis.analysis.method_tracker import MethodTracker

console = Console()


@click.group()
def track():
    """Track method and clone group evolution across revisions.

    This command group provides subcommands for tracking:
    - methods: Track individual method evolution
    - groups: Track clone group evolution
    - all: Track both methods and groups
    """
    pass


@track.command()
@click.argument("data_dir", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=False, dir_okay=True),
    default=".",
    help="Output directory for CSV files (default: current directory)",
)
@click.option(
    "--start-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Start date for filtering revisions (YYYY-MM-DD)",
)
@click.option(
    "--end-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="End date for filtering revisions (YYYY-MM-DD)",
)
@click.option(
    "--similarity",
    type=click.IntRange(0, 100),
    default=70,
    help="Similarity threshold for method matching (0-100, default: 70)",
)
@click.option(
    "--summary",
    "-s",
    is_flag=True,
    help="Display summary statistics",
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option(
    "--parallel",
    "-p",
    is_flag=True,
    help="Enable parallel processing for similarity calculation",
)
@click.option(
    "--max-workers",
    type=click.IntRange(1),
    help="Maximum number of worker processes (default: number of CPU cores)",
)
@click.option(
    "--use-lsh",
    is_flag=True,
    help="Enable LSH indexing for candidate filtering (Phase 5.3.2 optimization, ~100x speedup)",
)
@click.option(
    "--lsh-threshold",
    type=click.FloatRange(0.0, 1.0),
    default=0.7,
    help="LSH similarity threshold (0.0-1.0, default: 0.7). Only used with --use-lsh.",
)
@click.option(
    "--lsh-num-perm",
    type=click.IntRange(32, 256),
    default=128,
    help="Number of LSH permutations (32-256, default: 128). Only used with --use-lsh.",
)
@click.option(
    "--top-k",
    type=click.IntRange(1),
    default=20,
    help="Number of top candidates per source block (default: 20). Only used with --use-lsh.",
)
@click.option(
    "--use-optimized-similarity",
    is_flag=True,
    help="Use optimized similarity with banded LCS (Phase 5.3.2 optimization, ~2x speedup)",
)
@click.option(
    "--progressive-thresholds",
    type=str,
    default=None,
    help='Progressive thresholds as comma-separated values (e.g., "90,80,70"). Phase 5.3.3.',
)
@click.option(
    "--optimize",
    is_flag=True,
    help="Enable all Phase 5.3 optimizations with recommended defaults",
)
def methods(
    data_dir: str,
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
):
    """Track method evolution across revisions.

    DATA_DIR: Directory containing revision subdirectories with code_blocks.csv
    and clone_pairs.csv files.

    Outputs:
    - method_tracking.csv: Method tracking results with state classification
    """
    data_path = Path(data_dir)
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold blue]Tracking methods:[/bold blue] {data_path}")

    if verbose:
        console.print(f"[dim]Similarity threshold: {similarity}[/dim]")
        console.print(f"[dim]Output directory: {output_path}[/dim]")
        if start_date:
            console.print(f"[dim]Start date: {start_date.strftime('%Y-%m-%d')}[/dim]")
        if end_date:
            console.print(f"[dim]End date: {end_date.strftime('%Y-%m-%d')}[/dim]")
        if parallel:
            workers = max_workers if max_workers else "auto (CPU cores)"
            console.print(f"[dim]Parallel processing: enabled (workers: {workers})[/dim]")

    # Phase 5.3.2/5.3.3: Handle --optimize flag
    if optimize:
        use_lsh = True
        use_optimized_similarity = True
        if progressive_thresholds is None:
            progressive_thresholds = "90,80,70"
        if verbose:
            console.print("[dim]Optimization mode: enabled (all Phase 5.3 optimizations)[/dim]")

    # Parse progressive thresholds
    parsed_progressive_thresholds = None
    if progressive_thresholds:
        try:
            parsed_progressive_thresholds = [
                int(t.strip()) for t in progressive_thresholds.split(",")
            ]
            # Validate thresholds
            for t in parsed_progressive_thresholds:
                if not 0 <= t <= 100:
                    console.print(
                        f"[red]Error:[/red] Progressive threshold {t} must be between 0 and 100"
                    )
                    raise click.Abort()
            # Sort in descending order (high to low)
            parsed_progressive_thresholds = sorted(parsed_progressive_thresholds, reverse=True)
        except ValueError:
            console.print(
                "[red]Error:[/red] Progressive thresholds must be comma-separated integers"
            )
            raise click.Abort()

    # Phase 5.3.2/5.3.3: Display optimization settings
    if verbose:
        if use_lsh:
            console.print(
                f"[dim]LSH indexing: enabled "
                f"(threshold={lsh_threshold}, num_perm={lsh_num_perm}, top_k={top_k})[/dim]"
            )
        if use_optimized_similarity:
            console.print("[dim]Optimized similarity: enabled (banded LCS)[/dim]")
        if parsed_progressive_thresholds:
            console.print(f"[dim]Progressive thresholds: {parsed_progressive_thresholds}[/dim]")

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
        status_parts = ["[bold green]Analyzing methods"]
        if use_lsh or use_optimized_similarity:
            status_parts.append(" (optimized)")
        if parallel:
            status_parts.append(" (parallel)")
        status_parts.append("...")
        status_msg = "".join(status_parts)
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
@click.argument("data_dir", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=False, dir_okay=True),
    default=".",
    help="Output directory for CSV files (default: current directory)",
)
@click.option(
    "--start-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Start date for filtering revisions (YYYY-MM-DD)",
)
@click.option(
    "--end-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="End date for filtering revisions (YYYY-MM-DD)",
)
@click.option(
    "--similarity",
    type=click.IntRange(0, 100),
    default=70,
    help="Similarity threshold for group detection (0-100, default: 70)",
)
@click.option(
    "--overlap",
    type=click.FloatRange(0.0, 1.0),
    default=0.5,
    help="Overlap threshold for group matching (0.0-1.0, default: 0.5)",
)
@click.option(
    "--summary",
    "-s",
    is_flag=True,
    help="Display summary statistics",
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option(
    "--use-lsh",
    is_flag=True,
    help="Enable LSH indexing for method matching (Phase 5.3.2 optimization)",
)
@click.option(
    "--lsh-threshold",
    type=click.FloatRange(0.0, 1.0),
    default=0.7,
    help="LSH similarity threshold (0.0-1.0, default: 0.7)",
)
@click.option(
    "--lsh-num-perm",
    type=click.IntRange(32, 256),
    default=128,
    help="Number of LSH permutations (default: 128)",
)
@click.option(
    "--top-k",
    type=click.IntRange(1),
    default=20,
    help="Number of top candidates (default: 20)",
)
@click.option(
    "--use-optimized-similarity",
    is_flag=True,
    help="Use optimized similarity (Phase 5.3.2)",
)
@click.option(
    "--progressive-thresholds",
    type=str,
    default=None,
    help='Progressive thresholds (e.g., "90,80,70")',
)
@click.option(
    "--optimize",
    is_flag=True,
    help="Enable all Phase 5.3 optimizations",
)
def groups(
    data_dir: str,
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
):
    """Track clone group evolution across revisions.

    DATA_DIR: Directory containing revision subdirectories with code_blocks.csv
    and clone_pairs.csv files.

    Outputs:
    - group_tracking.csv: Group tracking results with state classification
    - group_membership.csv: Group membership snapshots for each revision
    """
    data_path = Path(data_dir)
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold blue]Tracking clone groups:[/bold blue] {data_path}")

    if verbose:
        console.print(f"[dim]Similarity threshold: {similarity}[/dim]")
        console.print(f"[dim]Overlap threshold: {overlap}[/dim]")
        console.print(f"[dim]Output directory: {output_path}[/dim]")
        if start_date:
            console.print(f"[dim]Start date: {start_date.strftime('%Y-%m-%d')}[/dim]")
        if end_date:
            console.print(f"[dim]End date: {end_date.strftime('%Y-%m-%d')}[/dim]")

    # Phase 5.3.2/5.3.3: Handle --optimize flag
    if optimize:
        use_lsh = True
        use_optimized_similarity = True
        if progressive_thresholds is None:
            progressive_thresholds = "90,80,70"
        if verbose:
            console.print("[dim]Optimization mode: enabled (all Phase 5.3 optimizations)[/dim]")

    # Parse progressive thresholds
    parsed_progressive_thresholds = None
    if progressive_thresholds:
        try:
            parsed_progressive_thresholds = [
                int(t.strip()) for t in progressive_thresholds.split(",")
            ]
            # Validate thresholds
            for t in parsed_progressive_thresholds:
                if not 0 <= t <= 100:
                    console.print(
                        f"[red]Error:[/red] Progressive threshold {t} must be between 0 and 100"
                    )
                    raise click.Abort()
            # Sort in descending order (high to low)
            parsed_progressive_thresholds = sorted(parsed_progressive_thresholds, reverse=True)
        except ValueError:
            console.print(
                "[red]Error:[/red] Progressive thresholds must be comma-separated integers"
            )
            raise click.Abort()

    # Phase 5.3.2/5.3.3: Display optimization settings
    if verbose:
        if use_lsh:
            console.print(
                f"[dim]LSH indexing: enabled "
                f"(threshold={lsh_threshold}, num_perm={lsh_num_perm}, top_k={top_k})[/dim]"
            )
        if use_optimized_similarity:
            console.print("[dim]Optimized similarity: enabled (banded LCS)[/dim]")
        if parsed_progressive_thresholds:
            console.print(f"[dim]Progressive thresholds: {parsed_progressive_thresholds}[/dim]")

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
        status_parts = ["[bold green]Analyzing clone groups"]
        if use_lsh or use_optimized_similarity:
            status_parts.append(" (optimized)")
        status_parts.append("...")
        status_msg = "".join(status_parts)
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


@track.command()
@click.argument("data_dir", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=False, dir_okay=True),
    default=".",
    help="Output directory for CSV files (default: current directory)",
)
@click.option(
    "--start-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Start date for filtering revisions (YYYY-MM-DD)",
)
@click.option(
    "--end-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="End date for filtering revisions (YYYY-MM-DD)",
)
@click.option(
    "--similarity",
    type=click.IntRange(0, 100),
    default=70,
    help="Similarity threshold (0-100, default: 70)",
)
@click.option(
    "--overlap",
    type=click.FloatRange(0.0, 1.0),
    default=0.5,
    help="Overlap threshold for group matching (0.0-1.0, default: 0.5)",
)
@click.option(
    "--summary",
    "-s",
    is_flag=True,
    help="Display summary statistics",
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def all(
    data_dir: str,
    output: str,
    start_date: datetime | None,
    end_date: datetime | None,
    similarity: int,
    overlap: float,
    summary: bool,
    verbose: bool,
):
    """Track both methods and clone groups across revisions.

    DATA_DIR: Directory containing revision subdirectories with code_blocks.csv
    and clone_pairs.csv files.

    Outputs:
    - method_tracking.csv: Method tracking results
    - group_tracking.csv: Group tracking results
    - group_membership.csv: Group membership snapshots
    """
    data_path = Path(data_dir)
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold blue]Tracking methods and clone groups:[/bold blue] {data_path}")

    if verbose:
        console.print(f"[dim]Similarity threshold: {similarity}[/dim]")
        console.print(f"[dim]Overlap threshold: {overlap}[/dim]")
        console.print(f"[dim]Output directory: {output_path}[/dim]")
        if start_date:
            console.print(f"[dim]Start date: {start_date.strftime('%Y-%m-%d')}[/dim]")
        if end_date:
            console.print(f"[dim]End date: {end_date.strftime('%Y-%m-%d')}[/dim]")

    try:
        # Track methods
        console.print("\n[bold]1. Tracking methods...[/bold]")
        method_tracker = MethodTracker(data_path, similarity_threshold=similarity)

        with console.status("[bold green]Analyzing methods..."):
            method_df = method_tracker.track(start_date=start_date, end_date=end_date)

        if len(method_df) == 0:
            console.print("[yellow]No revisions found in the specified date range.[/yellow]")
            return

        method_file = output_path / "method_tracking.csv"
        method_df.to_csv(method_file, index=False)
        console.print("[green]✓[/green] Method tracking complete!")

        # Track groups
        console.print("\n[bold]2. Tracking clone groups...[/bold]")
        group_tracker = CloneGroupTracker(
            data_path, similarity_threshold=similarity, overlap_threshold=overlap
        )

        with console.status("[bold green]Analyzing clone groups..."):
            group_df, membership_df = group_tracker.track(start_date=start_date, end_date=end_date)

        group_file = output_path / "group_tracking.csv"
        membership_file = output_path / "group_membership.csv"
        group_df.to_csv(group_file, index=False)
        membership_df.to_csv(membership_file, index=False)
        console.print("[green]✓[/green] Group tracking complete!")

        # Summary
        console.print(f"\n[green]All results saved to:[/green] {output_path}")
        console.print(f"  - {method_file.name}")
        console.print(f"  - {group_file.name}")
        console.print(f"  - {membership_file.name}")

        # Display summary if requested
        if summary:
            console.print("\n[bold]Method Tracking Summary:[/bold]")
            _display_method_summary(method_df)
            console.print("\n[bold]Group Tracking Summary:[/bold]")
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
