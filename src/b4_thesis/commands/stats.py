"""Statistics command for computing metrics."""

import click
import pandas as pd
from rich.console import Console
from rich.table import Table

console = Console()


@click.command()
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
def stats(input_file: str, metrics: tuple[str, ...], column: str | None):
    """Compute statistical metrics from data files.

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
