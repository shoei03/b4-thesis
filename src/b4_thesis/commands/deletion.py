"""Deletion prediction commands."""

from pathlib import Path

import click
import pandas as pd
from rich.console import Console

from b4_thesis.analysis.deletion_prediction.extraction.rule_applicator import RuleApplicator
from b4_thesis.analysis.deletion_prediction.rules import get_rules
from b4_thesis.core.deletion.truth import deletion_truth
from b4_thesis.error.cmd import handle_command_errors

console = Console()


def print_success(message: str, output_path: Path) -> None:
    """Print success message with output path."""
    console.print(f"[green]✓[/green] {message}: {output_path}", highlight=False)


def print_warning(message: str) -> None:
    """Print warning message."""
    console.print(f"[yellow]Warning:[/yellow] {message}", highlight=False)


@click.group()
def deletion():
    """Detect deletion signs and evaluate prediction rules."""
    pass


@deletion.command()
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
def truth(input: Path, output: Path, lookahead_window: int):
    deletion_truth(
        input=input,
        output=output,
        lookahead_window=lookahead_window,
    )


@deletion.command()
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
def rule(input_snippets: Path, input_metadata: Path, output: Path, rules: str | None):
    """Apply deletion prediction rules and output results.

    This command reads a CSV with method lineage and code snippets,
    applies deletion prediction rules, and outputs a CSV with rule results.

    """
    # Load CSV
    snippets_df = pd.read_csv(input_snippets)
    metadata_df = pd.read_csv(input_metadata)

    # Merge snippets with metadata (inner join to ensure both exist)
    merged_df = snippets_df.merge(
        metadata_df,
        on=["global_block_id", "revision"],
        how="inner",
    )

    rule_applicator = RuleApplicator()

    # Apply rules
    rule_result = rule_applicator.apply_rules(merged_df, get_rules(rules))

    # drop unnecessary columns
    rule_result.df = rule_result.df.drop(
        columns=["function_name", "file_path", "start_line", "end_line", "loc", "code"]
    )

    # sort
    rule_result.df = rule_result.df.sort_values(by=["global_block_id", "revision"]).reset_index(
        drop=True
    )

    # Save results
    rule_result.df.to_csv(output, index=False)

    print_success(
        f"Applied {rule_result.rules_applied} rules ({rule_result.errors_count} errors) to", output
    )


@deletion.command()
@click.argument("input_csv", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), required=True, help="Output file path")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "csv", "table"]),
    default="table",
    help="Output format (default: table)",
)
@click.option(
    "--detailed",
    is_flag=True,
    help="Enable detailed tracking of TP/FP/FN/TN methods per rule",
)
@click.option(
    "--export-dir",
    type=click.Path(),
    default=None,
    help="Directory to export detailed classification CSVs (requires --detailed)",
)
@click.option(
    "--combined",
    is_flag=True,
    help="Include combined evaluation of all rules (OR logic)",
)
@click.option(
    "--group-by",
    type=str,
    default="rev_status",
    help="Column name to group evaluation by (default: 'rev_status')",
)
@click.option(
    "--no-overall",
    is_flag=True,
    help="Exclude overall evaluation (only show per-group results)",
)
@click.option(
    "--split-partial-by",
    type=str,
    default=None,
    help="Column to subdivide 'partial_deleted' group by (e.g., 'state'). "
    "Only works when --group-by is 'rev_status'.",
)
@handle_command_errors
def evaluate(
    input_csv: str,
    output: str,
    format: str,
    detailed: bool,
    export_dir: str | None,
    combined: bool,
    group_by: str | None,
    no_overall: bool,
    split_partial_by: str | None,
):
    """Evaluate deletion prediction rules.

    This command:
    1. Reads features CSV (from extract command)
    2. Calculates Precision, Recall, F1 for each rule
    3. Groups evaluation by categorical column (default: rev_status)
    4. Outputs evaluation report
    5. (Optional) Exports detailed classification CSVs with --detailed --export-dir

    Example:
        b4-thesis deletion evaluate features.csv \\
            --output report.json \\
            --format json

        # With detailed tracking
        b4-thesis deletion evaluate features.csv \\
            --output report.json \\
            --detailed \\
            --export-dir ./classifications/

        # Split partial_deleted group by state
        b4-thesis deletion evaluate features.csv \\
            --output grouped_report.json \\
            --format json \\
            --split-partial-by state
    """
    # Validate flags
    if export_dir and not detailed:
        print_warning("--export-dir requires --detailed flag. Ignoring --export-dir.")
        export_dir = None

    if split_partial_by:
        print_warning(
            "--split-partial-by is not yet implemented. "
            "This feature will be available in a future release."
        )
        split_partial_by = None

    # Load features
    console.print(
        f"[bold blue]Loading features from {input_csv}...[/bold blue]",
        highlight=False,
    )
    df = pd.read_csv(input_csv)
