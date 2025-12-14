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
    console.print(f"[blue]Reading:[/blue] {input_file}")
    df = pd.read_csv(input_file)
    # TODO: 本来はこの行は不要だが、変換処理の確認のため一時的に出力
    console.print(f"[dim]Input rows:[/dim] {df.shape[0]:,}")

    # Convert to lineage format
    converter = LineageConverter()
    lineage_df = converter.convert(df)
    
    # Save output
    output.parent.mkdir(parents=True, exist_ok=True)
    lineage_df.to_csv(output, index=False)

    console.print(f"[green]✓ Saved:[/green] {output}")
    # TODO: 本来はこの行は不要だが、変換処理の確認のため一時的に出力
    console.print(f"[dim]Output rows:[/dim] {lineage_df.shape[0]:,}")
