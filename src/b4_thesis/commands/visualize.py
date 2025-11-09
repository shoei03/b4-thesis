"""Visualization command for creating plots."""

from pathlib import Path

import click
import pandas as pd
from rich.console import Console

from b4_thesis.analysis.tracking_visualizer import (
    create_group_tracking_dashboard,
    create_method_tracking_dashboard,
    plot_group_size_distribution,
    plot_lifetime_distribution,
    plot_state_distribution,
    plot_timeline,
)

console = Console()


@click.group()
def visualize():
    """Create visualizations from data files.

    This command group provides subcommands for:
    - general: General plots for any CSV file
    - methods: Specialized visualizations for method tracking results
    - groups: Specialized visualizations for group tracking results
    """
    pass


@visualize.command()
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
def general(
    input_file: str,
    output: str,
    type: str,
    x_column: str | None,
    y_column: str | None,
    title: str | None,
):
    """Create general visualizations from CSV files.

    INPUT_FILE: Path to CSV or data file
    """
    console.print(f"[bold blue]Creating {type} plot from:[/bold blue] {input_file}")

    try:
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
                console.print(
                    "[red]Error:[/red] --x-column and --y-column required for scatter plot"
                )
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


@visualize.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(file_okay=False, dir_okay=True),
    default="./plots",
    help="Output directory for visualizations (default: ./plots)",
)
@click.option(
    "--plot-type",
    "-t",
    type=click.Choice(["dashboard", "state", "lifetime", "timeline"]),
    default="dashboard",
    help="Type of visualization to create",
)
def methods(input_file: str, output_dir: str, plot_type: str):
    """Create visualizations for method tracking results.

    INPUT_FILE: Path to method_tracking.csv file

    Available plot types:
    - dashboard: Create all plots (state distribution, lifetime, timeline)
    - state: State distribution bar chart
    - lifetime: Lifetime distribution histogram
    - timeline: Method count and clone count over time
    """
    console.print(f"[bold blue]Creating method tracking visualizations:[/bold blue] {input_file}")

    try:
        df = pd.read_csv(input_file)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        if plot_type == "dashboard":
            with console.status("[bold green]Generating dashboard..."):
                create_method_tracking_dashboard(df, output_path)
            console.print("[green]✓[/green] Dashboard created with 7 plots")
            console.print(f"[green]Plots saved to:[/green] {output_path}")

        elif plot_type == "state":
            state_file = output_path / "state_distribution.png"
            plot_state_distribution(
                df,
                state_col="state",
                output_path=state_file,
                title="Method State Distribution",
            )
            console.print(f"[green]✓[/green] State distribution saved to: {state_file}")

        elif plot_type == "lifetime":
            lifetime_file = output_path / "lifetime_distribution.png"
            plot_lifetime_distribution(
                df,
                column="lifetime_days",
                output_path=lifetime_file,
                title="Method Lifetime Distribution",
            )
            console.print(f"[green]✓[/green] Lifetime distribution saved to: {lifetime_file}")

        elif plot_type == "timeline":
            timeline_file = output_path / "method_count_timeline.png"
            plot_timeline(
                df,
                metric="count",
                output_path=timeline_file,
                title="Method Count Over Time",
            )
            console.print(f"[green]✓[/green] Timeline saved to: {timeline_file}")

        console.print("[bold green]✓[/bold green] Visualization complete!")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@visualize.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(file_okay=False, dir_okay=True),
    default="./plots",
    help="Output directory for visualizations (default: ./plots)",
)
@click.option(
    "--plot-type",
    "-t",
    type=click.Choice(["dashboard", "state", "size", "timeline", "members"]),
    default="dashboard",
    help="Type of visualization to create",
)
def groups(input_file: str, output_dir: str, plot_type: str):
    """Create visualizations for group tracking results.

    INPUT_FILE: Path to group_tracking.csv file

    Available plot types:
    - dashboard: Create all plots (state, size, timeline, member changes)
    - state: State distribution bar chart
    - size: Group size distribution
    - timeline: Group count over time
    - members: Member changes over time
    """
    console.print(f"[bold blue]Creating group tracking visualizations:[/bold blue] {input_file}")

    try:
        df = pd.read_csv(input_file)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        if plot_type == "dashboard":
            with console.status("[bold green]Generating dashboard..."):
                create_group_tracking_dashboard(df, output_path)
            console.print("[green]✓[/green] Dashboard created with 7 plots")
            console.print(f"[green]Plots saved to:[/green] {output_path}")

        elif plot_type == "state":
            state_file = output_path / "state_distribution.png"
            plot_state_distribution(
                df,
                state_col="state",
                output_path=state_file,
                title="Group State Distribution",
            )
            console.print(f"[green]✓[/green] State distribution saved to: {state_file}")

        elif plot_type == "size":
            size_file = output_path / "group_size_distribution.png"
            plot_group_size_distribution(
                df,
                output_path=size_file,
                title="Group Size Distribution",
            )
            console.print(f"[green]✓[/green] Size distribution saved to: {size_file}")

        elif plot_type == "timeline":
            timeline_file = output_path / "group_count_timeline.png"
            plot_timeline(
                df,
                metric="count",
                output_path=timeline_file,
                title="Group Count Over Time",
            )
            console.print(f"[green]✓[/green] Timeline saved to: {timeline_file}")

        elif plot_type == "members":
            from b4_thesis.analysis.tracking_visualizer import plot_member_changes

            members_file = output_path / "member_changes.png"
            plot_member_changes(
                df,
                output_path=members_file,
                title="Member Changes Over Time",
            )
            console.print(f"[green]✓[/green] Member changes saved to: {members_file}")

        console.print("[bold green]✓[/bold green] Visualization complete!")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()
