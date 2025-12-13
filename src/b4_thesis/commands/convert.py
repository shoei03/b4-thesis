"""Convert tracking data to different formats."""

from pathlib import Path

import click
import pandas as pd
from rich.console import Console

from b4_thesis.core.convert.lineage_converter import LineageConverter

console = Console()


@click.group()
def convert():
    """Convert tracking data to different formats."""
    pass


@convert.command()
@click.option(
    "--input-file",
    type=click.Path(exists=True, path_type=Path, file_okay=True, dir_okay=False),
    default="./output/versions/method_tracking.csv",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default="./output/versions/method_lineage.csv",
    help="Output file path",
)
def methods(input_file: Path, output: Path) -> None:
    """
    Convert method tracking data to lineage format.

    This command unifies method identifiers across revisions by assigning
    a global_block_id to each method lineage. Methods that match across
    revisions will share the same global_block_id.

    Examples:
        b4-thesis convert methods ./output/method_tracking.csv -o result.csv
    """
    console.print(f"[blue]Reading:[/blue] {input_file}")
    df = pd.read_csv(input_file)
    console.print(f"[dim]Input rows:[/dim] {df.shape[0]:,}")

    # Convert to lineage format
    converter = LineageConverter(df)
    lineage_df = converter.convert()
    
    # Save output
    output.parent.mkdir(parents=True, exist_ok=True)
    lineage_df.to_csv(output, index=False)

    console.print(f"[green]✓ Saved:[/green] {output}")
    console.print(f"[dim]Output rows:[/dim] {lineage_df.shape[0]:,}")
