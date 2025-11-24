"""Label command for adding classification labels to analysis data."""

from pathlib import Path

import click
import pandas as pd
from rich.console import Console
from rich.table import Table

from b4_thesis.analysis.revision_labeler import RevisionLabeler

console = Console()


@click.group()
def label():
    """Add classification labels to analysis data.

    This command group provides subcommands for labeling:
    - revisions: Label clone groups per revision based on deleted state
    """
    pass


@label.command("revisions")
@click.argument("csv_path", type=click.Path(exists=True, file_okay=True, dir_okay=False))
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    help="Output CSV path (default: method_lineage_labeled.csv in same directory)",
)
@click.option(
    "--summary",
    "-s",
    is_flag=True,
    help="Show summary statistics after labeling",
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def revisions(
    csv_path: str,
    output: str | None,
    summary: bool,
    verbose: bool,
):
    """Add rev_status labels to method lineage data.

    Reads method lineage data from CSV_PATH and adds a 'rev_status' column
    classifying each (clone_group_id, revision) pair:

    \b
    - all_deleted: All members in the group are deleted
    - partial_deleted: Some members are deleted
    - no_deleted: No members are deleted

    \b
    CSV_PATH: Path to method_lineage.csv file

    \b
    Example:
        b4-thesis label revisions output/method_lineage.csv -o output/labeled.csv --summary
    """
    csv_path = Path(csv_path)

    # Determine output path
    if output:
        output_path = Path(output)
    else:
        output_path = csv_path.parent / "method_lineage_labeled.csv"

    # Read CSV
    console.print(f"[blue]Reading:[/blue] {csv_path}")

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        console.print(f"[red]Error reading CSV:[/red] {e}")
        raise click.Abort() from e

    if verbose:
        console.print(f"  Total records: {len(df)}")

    # Label revisions
    labeler = RevisionLabeler()

    try:
        with console.status("[blue]Labeling revisions...[/blue]"):
            labeled_df = labeler.label_revisions(df)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort() from e

    # Filter to only records with clone_group_id for labeling stats
    with_groups = labeled_df[labeled_df["clone_group_id"].notna()]
    unique_pairs = with_groups.drop_duplicates(["clone_group_id", "revision"])

    if verbose:
        console.print(f"  Records with clone_group_id: {len(with_groups)}")
        console.print(f"  Unique (clone_group_id, revision) pairs: {len(unique_pairs)}")

    # Save output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    labeled_df.to_csv(output_path, index=False)
    console.print(f"[green]Saved:[/green] {output_path}")

    # Show summary if requested
    if summary:
        console.print()
        _show_summary(labeler, labeled_df)


def _show_summary(labeler: RevisionLabeler, df: pd.DataFrame) -> None:
    """Display summary statistics table."""
    # Filter to records with clone_group_id
    df_with_groups = df[df["clone_group_id"].notna()]

    if df_with_groups.empty:
        console.print("[yellow]No clone groups found for summary[/yellow]")
        return

    summary_df = labeler.get_revision_summary(df_with_groups)

    # Pivot for display
    pivot = summary_df.pivot(index="revision", columns="rev_status", values="n_groups").fillna(0)
    pivot = pivot.astype(int)

    # Ensure all status columns exist
    for status in ["all_deleted", "partial_deleted", "no_deleted"]:
        if status not in pivot.columns:
            pivot[status] = 0

    # Reorder columns
    pivot = pivot[["no_deleted", "partial_deleted", "all_deleted"]]
    pivot["total"] = pivot.sum(axis=1)

    # Create Rich table
    table = Table(title="Clone Group Status by Revision")
    table.add_column("Revision", style="cyan")
    table.add_column("No Deleted", justify="right", style="green")
    table.add_column("Partial Deleted", justify="right", style="yellow")
    table.add_column("All Deleted", justify="right", style="red")
    table.add_column("Total", justify="right", style="bold")

    for revision in pivot.index:
        row = pivot.loc[revision]
        # Truncate revision for display
        rev_display = str(revision)[:20] if len(str(revision)) > 20 else str(revision)
        table.add_row(
            rev_display,
            str(row["no_deleted"]),
            str(row["partial_deleted"]),
            str(row["all_deleted"]),
            str(row["total"]),
        )

    console.print(table)

    # Overall summary
    console.print()
    total_groups = pivot["total"].sum()
    console.print(f"[bold]Total:[/bold] {total_groups} clone group-revision pairs")


@label.command("filter")
@click.argument("csv_path", type=click.Path(exists=True, file_okay=True, dir_okay=False))
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    help="Output CSV path (default: output/partial_deleted.csv)",
)
@click.option(
    "--status",
    type=click.Choice(["partial_deleted", "all_deleted", "no_deleted"]),
    default="partial_deleted",
    help="rev_status value to filter by (default: partial_deleted)",
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def filter_cmd(
    csv_path: str,
    output: str | None,
    status: str,
    verbose: bool,
):
    """Filter labeled data by rev_status.

    Reads labeled method lineage data from CSV_PATH and extracts rows
    matching the specified rev_status value.

    \b
    CSV_PATH: Path to method_lineage_labeled.csv file

    \b
    Example:
        b4-thesis label filter output/method_lineage_labeled.csv -o output/partial_deleted.csv
    """
    csv_path = Path(csv_path)

    # Determine output path
    if output:
        output_path = Path(output)
    else:
        output_path = Path("output") / f"{status}.csv"

    # Read CSV
    console.print(f"[blue]Reading:[/blue] {csv_path}")

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        console.print(f"[red]Error reading CSV:[/red] {e}")
        raise click.Abort() from e

    # Validate rev_status column exists
    if "rev_status" not in df.columns:
        console.print("[red]Error:[/red] Missing 'rev_status' column. Run 'label revisions' first.")
        raise click.Abort()

    if verbose:
        console.print(f"  Total records: {len(df)}")

    # Filter by status
    filtered_df = df[df["rev_status"] == status]

    if verbose:
        console.print(f"  Filtered records ({status}): {len(filtered_df)}")

    # Save output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    filtered_df.to_csv(output_path, index=False)
    console.print(f"[green]Saved:[/green] {output_path} ({len(filtered_df)} records)")
