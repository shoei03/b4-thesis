"""Refactoring analysis command for RefactoringMiner output."""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from b4_thesis.analysis.refactoring_analyzer import (
    RefactoringTypeStats,
    analyze_directory,
    analyze_single_file,
)
import pandas as pd

console = Console()


@click.group()
def refactoring():
    """Analyze RefactoringMiner output data.

    This command group provides tools for analyzing refactoring patterns
    detected by RefactoringMiner across software versions.
    """
    pass


@refactoring.command(name="analyze-types")
@click.argument("input_path", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output CSV file path (default: refactoring_type_frequency.csv)",
)
@click.option(
    "--top",
    "-t",
    type=int,
    default=10,
    help="Number of top types to display in console table (default: 10)",
)
@click.option(
    "--sort-by",
    type=click.Choice(["count", "percentage", "type"]),
    default="count",
    help="Sort order for results (default: count)",
)
def analyze_types(input_path: str, output: str | None, top: int, sort_by: str):
    """Analyze refactoring type frequencies from RefactoringMiner JSON output.

    INPUT_PATH: Path to JSON file or directory containing RefactoringMiner output

    Analyzes each version pair individually and outputs:
    - Console: Rich table showing top refactoring types per version pair
    - CSV: Complete frequency data (version_pair, type, count, percentage)

    Examples:

        # Analyze single file
        b4-thesis refactoring analyze-types output/refactoring_miner/pandas_v1.0.0_to_v1.1.0.json

        # Analyze all files in directory
        b4-thesis refactoring analyze-types output/refactoring_miner/ -o results.csv
    """
    path = Path(input_path)

    console.print(f"[bold blue]Analyzing refactoring types:[/bold blue] {input_path}")

    try:
        # Determine if input is file or directory
        if path.is_file():
            results = analyze_single_file(path)
            if not results:
                console.print("[yellow]Warning:[/yellow] No valid results found")
                return
        elif path.is_dir():
            results = analyze_directory(path)
            if not results:
                console.print("[yellow]Warning:[/yellow] No JSON files found or all files invalid")
                return
        else:
            console.print("[red]Error:[/red] Path is neither file nor directory")
            raise click.Abort()

        # Convert to DataFrame
        df = _results_to_dataframe(results, sort_by)

        # Display console tables
        _display_results_tables(df, top, console)

        # Export to CSV
        output_path = output or "refactoring_type_frequency.csv"
        df.to_csv(output_path, index=False)
        console.print(f"[bold green]✓[/bold green] Results saved to: {output_path}")

        # Summary
        total_pairs = len(results)
        total_refactorings = sum(r.total_refactorings for r in results)
        console.print(
            f"[dim]Analyzed {total_pairs} version pairs, "
            f"{total_refactorings} total refactorings[/dim]"
        )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


def _results_to_dataframe(results: list[RefactoringTypeStats], sort_by: str) -> pd.DataFrame:
    """Convert analysis results to DataFrame.

    Args:
        results: List of RefactoringTypeStats objects
        sort_by: Sorting criterion ("count", "percentage", or "type")

    Returns:
        DataFrame with columns: version_pair, refactoring_type, count, percentage
    """
    rows = []
    for result in results:
        for ref_type, count in result.type_counts.items():
            percentage = (
                (count / result.total_refactorings * 100) if result.total_refactorings > 0 else 0
            )
            rows.append(
                {
                    "version_pair": result.version_pair,
                    "refactoring_type": ref_type,
                    "count": count,
                    "percentage": percentage,
                }
            )

    df = pd.DataFrame(rows)

    # Sort
    if sort_by == "count":
        df = df.sort_values(["version_pair", "count"], ascending=[True, False])
    elif sort_by == "percentage":
        df = df.sort_values(["version_pair", "percentage"], ascending=[True, False])
    else:  # type
        df = df.sort_values(["version_pair", "refactoring_type"])

    return df


def _display_results_tables(df: pd.DataFrame, top: int, console: Console) -> None:
    """Display results as Rich tables.

    Args:
        df: DataFrame with refactoring type statistics
        top: Number of top types to display per version pair
        console: Rich console instance
    """
    for version_pair in df["version_pair"].unique():
        pair_df = df[df["version_pair"] == version_pair].head(top)

        table = Table(title=f"Refactoring Types - {version_pair}")
        table.add_column("Type", style="cyan")
        table.add_column("Count", style="green", justify="right")
        table.add_column("Percentage", style="yellow", justify="right")

        for _, row in pair_df.iterrows():
            table.add_row(
                row["refactoring_type"],
                str(row["count"]),
                f"{row['percentage']:.2f}%",
            )

        console.print(table)
