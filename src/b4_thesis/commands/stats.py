"""Statistics command for computing metrics."""

import click
import pandas as pd
from rich.console import Console
from rich.table import Table

from b4_thesis.analysis.tracking_stats import (
    calculate_group_stats,
    calculate_method_stats,
    get_lifetime_distribution,
    get_state_distribution,
)

console = Console()


@click.group()
def stats():
    """Compute statistical metrics from data files.

    This command group provides subcommands for:
    - general: General statistical metrics for any CSV file
    - methods: Specialized statistics for method tracking results
    - groups: Specialized statistics for group tracking results
    """
    pass


@stats.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--metrics",
    "-m",
    multiple=True,
    type=click.Choice(["mean", "median", "std", "min", "max", "count"]),
    default=["mean", "std"],
    help="Statistical metrics to compute",
)
@click.option("--column", "-c", help="Specific column to analyze")
def general(input_file: str, metrics: tuple[str, ...], column: str | None):
    """Compute general statistical metrics from CSV files.

    INPUT_FILE: Path to CSV or data file
    """
    console.print(f"[bold blue]Computing statistics for:[/bold blue] {input_file}")

    try:
        # Try to read as CSV
        df = pd.read_csv(input_file)

        if column:
            if column not in df.columns:
                console.print(f"[red]Error:[/red] Column '{column}' not found")
                return
            df = df[[column]]

        # Compute statistics
        table = Table(title="Statistical Summary")
        table.add_column("Metric", style="cyan")

        # Add column headers
        for col in df.select_dtypes(include=["number"]).columns:
            table.add_column(col, style="green")

        # Add metric rows
        for metric in metrics:
            row = [metric.upper()]
            for col in df.select_dtypes(include=["number"]).columns:
                if metric == "mean":
                    value = df[col].mean()
                elif metric == "median":
                    value = df[col].median()
                elif metric == "std":
                    value = df[col].std()
                elif metric == "min":
                    value = df[col].min()
                elif metric == "max":
                    value = df[col].max()
                elif metric == "count":
                    value = df[col].count()
                else:
                    value = "N/A"

                row.append(f"{value:.4f}" if isinstance(value, float) else str(value))

            table.add_row(*row)

        console.print(table)
        console.print(f"[dim]Total rows: {len(df)}[/dim]")
        console.print("[bold green]✓[/bold green] Statistics computed!")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@stats.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file for detailed statistics (CSV format)",
)
def methods(input_file: str, output: str | None):
    """Compute specialized statistics for method tracking results.

    INPUT_FILE: Path to method_tracking.csv file

    Displays comprehensive statistics including:
    - Overall counts (total methods, revisions, unique methods)
    - State distribution (ADDED, SURVIVED, DELETED)
    - Detailed state distribution
    - Clone statistics
    - Lifetime distribution
    """
    console.print(f"[bold blue]Analyzing method tracking results:[/bold blue] {input_file}")

    try:
        df = pd.read_csv(input_file)
        stats = calculate_method_stats(df)

        # Display basic statistics
        basic_table = Table(title="Method Tracking Statistics - Overview")
        basic_table.add_column("Metric", style="cyan")
        basic_table.add_column("Value", style="green", justify="right")

        basic_table.add_row("Total method occurrences", str(stats.total_methods))
        basic_table.add_row("Unique methods tracked", str(stats.unique_methods))
        basic_table.add_row("Total revisions analyzed", str(stats.total_revisions))
        basic_table.add_row("Avg methods per revision", f"{stats.avg_methods_per_revision:.1f}")
        basic_table.add_row("Max methods per revision", str(stats.max_methods_per_revision))
        basic_table.add_row("Min methods per revision", str(stats.min_methods_per_revision))

        console.print(basic_table)

        # Display state distribution
        state_table = Table(title="State Distribution")
        state_table.add_column("State", style="cyan")
        state_table.add_column("Count", style="green", justify="right")
        state_table.add_column("Percentage", style="yellow", justify="right")

        total = sum(stats.state_counts.values())
        for state, count in sorted(stats.state_counts.items()):
            percentage = (count / total * 100) if total > 0 else 0
            state_table.add_row(state.upper(), str(count), f"{percentage:.1f}%")

        console.print(state_table)

        # Display clone statistics
        clone_table = Table(title="Clone Statistics")
        clone_table.add_column("Metric", style="cyan")
        clone_table.add_column("Value", style="green", justify="right")

        clone_table.add_row("Methods in clone groups", str(stats.methods_in_clones))
        if stats.total_methods > 0:
            clone_percentage = stats.methods_in_clones / stats.total_methods * 100
        else:
            clone_percentage = 0
        clone_table.add_row("Clone percentage", f"{clone_percentage:.1f}%")
        clone_table.add_row("Average clone count", f"{stats.avg_clone_count:.2f}")
        clone_table.add_row("Maximum clone count", str(stats.max_clone_count))

        console.print(clone_table)

        # Display lifetime statistics
        lifetime_table = Table(title="Lifetime Statistics")
        lifetime_table.add_column("Metric", style="cyan")
        lifetime_table.add_column("Days", style="green", justify="right")
        lifetime_table.add_column("Revisions", style="yellow", justify="right")

        lifetime_table.add_row(
            "Average", f"{stats.avg_lifetime_days:.1f}", f"{stats.avg_lifetime_revisions:.1f}"
        )
        lifetime_table.add_row(
            "Median", f"{stats.median_lifetime_days:.1f}", f"{stats.median_lifetime_revisions:.1f}"
        )
        lifetime_table.add_row(
            "Maximum", str(stats.max_lifetime_days), str(stats.max_lifetime_revisions)
        )

        console.print(lifetime_table)

        # Save detailed statistics if output specified
        if output:
            # Create detailed distribution tables
            state_dist = get_state_distribution(df, state_col="state")
            detailed_dist = get_state_distribution(df, state_col="state_detail")
            lifetime_dist = get_lifetime_distribution(df, bins=10, column="lifetime_days")

            # Save to Excel
            output_file = output.replace(".csv", ".xlsx") if output.endswith(".csv") else output
            with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
                state_dist.to_excel(writer, sheet_name="State Distribution", index=False)
                detailed_dist.to_excel(writer, sheet_name="Detailed States", index=False)
                lifetime_dist.to_excel(writer, sheet_name="Lifetime Distribution", index=False)

            console.print(f"[green]Detailed statistics saved to:[/green] {output}")

        console.print("[bold green]✓[/bold green] Method statistics computed!")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@stats.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file for detailed statistics (XLSX format)",
)
def groups(input_file: str, output: str | None):
    """Compute specialized statistics for group tracking results.

    INPUT_FILE: Path to group_tracking.csv file

    Displays comprehensive statistics including:
    - Overall counts (total groups, revisions, unique groups)
    - State distribution (BORN, CONTINUED, GROWN, etc.)
    - Group size distribution
    - Member change statistics
    - Lifetime distribution
    """
    console.print(f"[bold blue]Analyzing group tracking results:[/bold blue] {input_file}")

    try:
        df = pd.read_csv(input_file)
        stats = calculate_group_stats(df)

        # Display basic statistics
        basic_table = Table(title="Group Tracking Statistics - Overview")
        basic_table.add_column("Metric", style="cyan")
        basic_table.add_column("Value", style="green", justify="right")

        basic_table.add_row("Total group occurrences", str(stats.total_groups))
        basic_table.add_row("Unique groups tracked", str(stats.unique_groups))
        basic_table.add_row("Total revisions analyzed", str(stats.total_revisions))
        basic_table.add_row("Avg groups per revision", f"{stats.avg_groups_per_revision:.1f}")
        basic_table.add_row("Max groups per revision", str(stats.max_groups_per_revision))
        basic_table.add_row("Min groups per revision", str(stats.min_groups_per_revision))

        console.print(basic_table)

        # Display state distribution
        state_table = Table(title="State Distribution")
        state_table.add_column("State", style="cyan")
        state_table.add_column("Count", style="green", justify="right")
        state_table.add_column("Percentage", style="yellow", justify="right")

        total = sum(stats.state_counts.values())
        for state, count in sorted(stats.state_counts.items()):
            percentage = (count / total * 100) if total > 0 else 0
            state_table.add_row(state.upper(), str(count), f"{percentage:.1f}%")

        console.print(state_table)

        # Display group size statistics
        size_table = Table(title="Group Size Statistics")
        size_table.add_column("Metric", style="cyan")
        size_table.add_column("Value", style="green", justify="right")

        size_table.add_row("Average group size", f"{stats.avg_group_size:.1f}")
        size_table.add_row("Median group size", f"{stats.median_group_size:.1f}")
        size_table.add_row("Maximum group size", str(stats.max_group_size))
        size_table.add_row("Minimum group size", str(stats.min_group_size))

        console.print(size_table)

        # Display member change statistics
        change_table = Table(title="Member Change Statistics")
        change_table.add_column("Metric", style="cyan")
        change_table.add_column("Value", style="green", justify="right")

        change_table.add_row("Avg members added", f"{stats.avg_members_added:.2f}")
        change_table.add_row("Max members added", str(stats.max_members_added))
        change_table.add_row("Avg members removed", f"{stats.avg_members_removed:.2f}")
        change_table.add_row("Max members removed", str(stats.max_members_removed))

        console.print(change_table)

        # Display lifetime statistics
        lifetime_table = Table(title="Lifetime Statistics")
        lifetime_table.add_column("Metric", style="cyan")
        lifetime_table.add_column("Days", style="green", justify="right")
        lifetime_table.add_column("Revisions", style="yellow", justify="right")

        lifetime_table.add_row(
            "Average", f"{stats.avg_lifetime_days:.1f}", f"{stats.avg_lifetime_revisions:.1f}"
        )
        lifetime_table.add_row(
            "Median", f"{stats.median_lifetime_days:.1f}", f"{stats.median_lifetime_revisions:.1f}"
        )
        lifetime_table.add_row(
            "Maximum", str(stats.max_lifetime_days), str(stats.max_lifetime_revisions)
        )

        console.print(lifetime_table)

        # Save detailed statistics if output specified
        if output:
            # Create detailed distribution tables
            state_dist = get_state_distribution(df, state_col="state")
            df_with_id = df.assign(group_id=df["group_id"])
            size_dist = get_lifetime_distribution(df_with_id, bins=10, column="member_count")
            lifetime_dist = get_lifetime_distribution(df, bins=10, column="lifetime_days")

            # Save to Excel
            import openpyxl  # noqa: F401

            output_file = output if output.endswith(".xlsx") else f"{output}.xlsx"
            with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
                state_dist.to_excel(writer, sheet_name="State Distribution", index=False)
                size_dist.to_excel(writer, sheet_name="Size Distribution", index=False)
                lifetime_dist.to_excel(writer, sheet_name="Lifetime Distribution", index=False)

            console.print(f"[green]Detailed statistics saved to:[/green] {output_file}")

        console.print("[bold green]✓[/bold green] Group statistics computed!")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()
