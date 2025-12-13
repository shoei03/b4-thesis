from pathlib import Path

import click

from b4_thesis.core.snippets import extract_snippets
from b4_thesis.error.cmd import handle_command_errors


@click.group()
def extract():
    pass


@extract.command()
@click.argument(
    "input_csv",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default="./output/versions/method_lineage_labeled.csv",
)
@click.option(
    "--repo",
    "-r",
    type=click.Path(path_type=Path, exists=True),
    default="../projects/pandas",
    help="Path to git repository",
)
@click.option(
    "--output",
    "-o",
    default="./output/versions/method_lineage/snippets.csv",
    type=click.Path(path_type=Path, file_okay=True, dir_okay=False),
    required=True,
    help="Output CSV file path",
)
@click.option(
    "--base-prefix",
    type=str,
    default="/app/Repos/pandas/",
    help="Base path prefix to remove from file paths",
)
@handle_command_errors
def snippets(
    input_csv: Path,
    repo: Path,
    output: Path,
    base_prefix: str,
):
    extract_snippets(
        input_csv=input_csv,
        repo=repo,
        output=output,
        base_prefix=base_prefix,
    )
