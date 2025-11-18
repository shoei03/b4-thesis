"""Statistics command for computing metrics."""

import click
import pandas as pd
from rich.console import Console
from rich.table import Table

from b4_thesis.analysis.stats_presenter import (
    display_group_stats_tables,
    display_method_stats_tables,
    export_group_stats_to_excel,
    export_method_stats_to_excel,
)
from b4_thesis.analysis.tracking_stats import calculate_group_stats, calculate_method_stats

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

        # Display statistics using presenter
        display_method_stats_tables(stats, console)

        # Save detailed statistics if output specified
        if output:
            output_file = export_method_stats_to_excel(df, output)
            console.print(f"[green]Detailed statistics saved to:[/green] {output_file}")

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

        # Display statistics using presenter
        display_group_stats_tables(stats, console)

        # Save detailed statistics if output specified
        if output:
            output_file = export_group_stats_to_excel(df, output)
            console.print(f"[green]Detailed statistics saved to:[/green] {output_file}")

        console.print("[bold green]✓[/bold green] Group statistics computed!")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()
