"""Deletion prediction commands."""

from pathlib import Path

import click
from rich.console import Console

from b4_thesis.core.predict.evaluate import evaluate
from b4_thesis.core.predict.rule import rule
from b4_thesis.core.predict.truth import truth
from b4_thesis.error.cmd import handle_command_errors

console = Console()


def print_success(message: str, output_path: Path) -> None:
    """Print success message with output path."""
    console.print(f"[green]✓[/green] {message}: {output_path}", highlight=False)


def print_warning(message: str) -> None:
    """Print warning message."""
    console.print(f"[yellow]Warning:[/yellow] {message}", highlight=False)


@click.group()
def predict():
    """Detect deletion signs and evaluate prediction rules."""
    pass


@predict.command()
@click.option(
    "--input",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default="./output/versions/method_lineage_labeled.csv",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path, file_okay=True, dir_okay=False),
    default="./output/versions/method_lineage/ground_truth.csv",
    help="Output CSV file path (default: method_lineage/ground_truth.csv in input CSV directory)",
)
@click.option(
    "--lookahead-window",
    type=int,
    default=5,
    show_default=True,
    help="Number of future revisions to check for deletion",
)
@handle_command_errors
def make_truth(input: Path, output: Path, lookahead_window: int):
    truth(
        input=input,
        output=output,
        lookahead_window=lookahead_window,
    )


@predict.command()
@click.option(
    "--input-snippets",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default="./output/versions/method_lineage/snippets.csv",
)
@click.option(
    "--input-metadata",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default="./output/versions/method_lineage_labeled.csv",
    help="CSV with method metadata (function_name, file_path, loc, etc.)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path, file_okay=True, dir_okay=False),
    default="./output/versions/method_lineage/with_rules.csv",
    help="Output file path",
)
@click.option(
    "--rules",
    type=str,
    default=None,
    help="Comma-separated rule names to apply (default: all rules)",
)
@handle_command_errors
def apply_rule(input_snippets: Path, input_metadata: Path, output: Path, rules: str | None):
    rule(
        input_snippets=input_snippets,
        input_metadata=input_metadata,
        output=output,
        rules=rules,
    )


@predict.command()
@click.option(
    "--feature",
    type=click.Path(path_type=Path, file_okay=True, dir_okay=False, exists=True),
    default="./output/versions/method_lineage/with_rules.csv",
)
@click.option(
    "--target",
    type=click.Path(path_type=Path, file_okay=True, dir_okay=False, exists=True),
    default="./output/versions/method_lineage/ground_truth.csv",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path, file_okay=True, dir_okay=False),
    default="./output/versions/method_lineage/evaluation.csv",
    required=True,
    help="Output file path",
)
@handle_command_errors
def evaluate_rules(
    feature: str,
    target: str,
    output: str,
):
    evaluate(feature_csv=Path(feature), target_csv=Path(target), output=Path(output))
