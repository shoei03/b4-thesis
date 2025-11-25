"""Report command for generating clone analysis reports."""

from pathlib import Path

import click
import pandas as pd
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from b4_thesis.analysis.code_extractor import GitCodeExtractor
from b4_thesis.analysis.report_generator import ReportGenerator

console = Console()


@click.group()
def report():
    """Generate analysis reports for clone groups.

    This command group provides subcommands for generating:
    - clone-groups: Markdown reports for clone group comparison
    """
    pass


@report.command("clone-groups")
@click.argument("csv_path", type=click.Path(exists=True, file_okay=True, dir_okay=False))
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=False, dir_okay=True),
    default="./output/clone_reports",
    help="Output directory for reports (default: ./output/clone_reports)",
)
@click.option(
    "--group-id",
    "-g",
    multiple=True,
    help="Specific clone group ID(s) to process (can be specified multiple times)",
)
@click.option(
    "--min-members",
    type=click.IntRange(2),
    default=2,
    help="Minimum number of members in a group (default: 2)",
)
@click.option(
    "--base-path",
    default="/app/Repos/pandas/",
    help="Base path prefix to remove from file paths (default: /app/Repos/pandas/)",
)
@click.option(
    "--github-url",
    default="https://github.com/pandas-dev/pandas/blob/",
    help="GitHub base URL for permalinks (empty to disable)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview groups without generating reports",
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def clone_groups(
    csv_path: str,
    repo_path: str,
    output: str,
    group_id: tuple[str, ...],
    min_members: int,
    base_path: str,
    github_url: str,
    dry_run: bool,
    verbose: bool,
):
    """Generate Markdown reports for clone group comparison.

    Reads filtered method lineage data from CSV_PATH (output from 'label filter' command),
    extracts code from REPO_PATH, and generates comparison reports for each clone group.

    \b
    CSV_PATH: Path to partial_deleted.csv file (from 'label filter' command)
    REPO_PATH: Path to the Git repository (e.g., ../projects/pandas)

    \b
    Required workflow:
        # Step 1: Filter data with label filter command
        b4-thesis label filter output/method_lineage_labeled.csv \\
            --status partial_deleted -o output/partial_deleted.csv

        # Step 2: Generate reports
        b4-thesis report clone-groups output/partial_deleted.csv \\
            ../projects/pandas -o ./output/clone_reports
    """
    csv_path = Path(csv_path)
    repo_path = Path(repo_path)
    output_dir = Path(output)

    # Read and filter CSV
    console.print(f"[blue]Reading:[/blue] {csv_path}")

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        console.print(f"[red]Error reading CSV:[/red] {e}")
        raise click.Abort() from e

    # Check required columns
    required_columns = [
        "clone_group_id",
        "global_block_id",
        "revision",
        "function_name",
        "file_path",
        "start_line",
        "end_line",
        "rev_status",  # Required for partial_deleted.csv format
    ]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        console.print(f"[red]Error:[/red] Missing required columns: {missing_columns}")
        if "rev_status" in missing_columns:
            console.print()
            console.print("[yellow]Hint:[/yellow] Input must be from 'label filter' command.")
            console.print(
                "  Run: b4-thesis label filter <input.csv> --status partial_deleted -o <output.csv>"
            )
        raise click.Abort()

    # Filter for records with clone_group_id
    original_count = len(df)
    df = df[df["clone_group_id"].notna()]
    filtered_count = len(df)

    if verbose:
        console.print(f"  Total records: {original_count}")
        console.print(f"  Records with clone_group_id: {filtered_count}")

    if df.empty:
        console.print("[yellow]Warning:[/yellow] No records with clone_group_id found")
        return

    # Filter by specific group IDs if provided
    if group_id:
        df = df[df["clone_group_id"].isin(group_id)]
        if df.empty:
            console.print(f"[yellow]Warning:[/yellow] No records found for group IDs: {group_id}")
            return

    # Group by clone_group_id and filter by min_members
    groups = list(df.groupby("clone_group_id"))
    valid_groups = [(gid, gdf) for gid, gdf in groups if len(gdf) >= min_members]

    console.print(
        f"[blue]Found:[/blue] {len(valid_groups)} clone groups with >= {min_members} members"
    )

    if not valid_groups:
        console.print("[yellow]No valid clone groups to process[/yellow]")
        return

    # Show preview table
    if dry_run or verbose:
        table = Table(title="Clone Groups Preview")
        table.add_column("#", style="dim")
        table.add_column("Group ID", style="cyan")
        table.add_column("Members", justify="right")
        table.add_column("Unique Methods", justify="right")

        for i, (gid, gdf) in enumerate(valid_groups[:20], 1):
            short_id = gid[:8] if len(gid) > 8 else gid
            unique_methods = gdf["global_block_id"].nunique()
            table.add_row(str(i), short_id, str(len(gdf)), str(unique_methods))

        if len(valid_groups) > 20:
            table.add_row("...", f"({len(valid_groups) - 20} more)", "", "")

        console.print(table)

    if dry_run:
        console.print("[dim]Dry run - no reports generated[/dim]")
        return

    # Initialize extractor and generator
    try:
        extractor = GitCodeExtractor(
            repo_path=repo_path,
            base_path_prefix=base_path,
            github_base_url=github_url if github_url else None,
        )
        generator = ReportGenerator(extractor)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort() from e

    # Generate reports with progress
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_paths = []
    errors = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating reports...", total=len(valid_groups))

        for group_id_val, group_df in valid_groups:
            short_id = group_id_val[:8] if len(str(group_id_val)) > 8 else group_id_val
            progress.update(task, description=f"Processing {short_id}...")

            try:
                report_obj = generator.generate_group_report(group_df)
                output_path = generator.save_report(report_obj, output_dir)
                generated_paths.append(output_path)

                if verbose:
                    console.print(f"  [green]Generated:[/green] {output_path.name}")

            except Exception as e:
                errors.append((group_id_val, str(e)))
                if verbose:
                    console.print(f"  [red]Error for {short_id}:[/red] {e}")

            progress.advance(task)

    # Summary
    console.print()
    console.print(f"[green]Generated:[/green] {len(generated_paths)} reports in {output_dir}")

    if errors:
        console.print(f"[red]Errors:[/red] {len(errors)} groups failed")
        if verbose:
            for gid, error in errors[:5]:
                console.print(f"  - {gid[:8]}: {error}")
            if len(errors) > 5:
                console.print(f"  ... and {len(errors) - 5} more errors")
