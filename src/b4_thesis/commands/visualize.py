"""Visualization command for creating plots."""

import click
from pathlib import Path
from rich.console import Console

console = Console()


@click.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    required=True,
    help="Output file path for the visualization",
)
@click.option(
    "--type",
    "-t",
    type=click.Choice(["scatter", "line", "bar", "histogram", "heatmap"]),
    default="scatter",
    help="Type of visualization",
)
@click.option("--x-column", help="Column for x-axis")
@click.option("--y-column", help="Column for y-axis")
@click.option("--title", help="Plot title")
def visualize(
    input_file: str,
    output: str,
    type: str,
    x_column: str | None,
    y_column: str | None,
    title: str | None,
):
    """Create visualizations from data files.

    INPUT_FILE: Path to CSV or data file
    """
    console.print(f"[bold blue]Creating {type} plot from:[/bold blue] {input_file}")

    try:
        import pandas as pd
        import matplotlib.pyplot as plt
        import seaborn as sns

        # Set style
        sns.set_theme(style="whitegrid")

        # Read data
        df = pd.read_csv(input_file)

        # Create figure
        plt.figure(figsize=(10, 6))

        # Generate plot based on type
        if type == "scatter":
            if not x_column or not y_column:
                console.print("[red]Error:[/red] --x-column and --y-column required for scatter plot")
                return
            sns.scatterplot(data=df, x=x_column, y=y_column)

        elif type == "line":
            if not x_column or not y_column:
                console.print("[red]Error:[/red] --x-column and --y-column required for line plot")
                return
            sns.lineplot(data=df, x=x_column, y=y_column)

        elif type == "bar":
            if not x_column or not y_column:
                console.print("[red]Error:[/red] --x-column and --y-column required for bar plot")
                return
            sns.barplot(data=df, x=x_column, y=y_column)

        elif type == "histogram":
            if not x_column:
                console.print("[red]Error:[/red] --x-column required for histogram")
                return
            sns.histplot(data=df, x=x_column, kde=True)

        elif type == "heatmap":
            # Select numeric columns only
            numeric_df = df.select_dtypes(include=["number"])
            sns.heatmap(numeric_df.corr(), annot=True, cmap="coolwarm", center=0)

        if title:
            plt.title(title)

        # Save plot
        plt.tight_layout()
        plt.savefig(output, dpi=300, bbox_inches="tight")

        console.print(f"[bold green]✓[/bold green] Visualization saved to: {output}")

    except ImportError as e:
        console.print(f"[red]Error:[/red] Missing required library: {e}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
