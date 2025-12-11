"""Deletion prediction commands."""

import functools
import json
from pathlib import Path
from typing import Callable

import click
import pandas as pd
from rich.console import Console
from rich.table import Table

from b4_thesis.analysis.code_extractor import GitCodeExtractor
from b4_thesis.analysis.deletion_prediction.evaluator import (
    Evaluator,
    GroupedRuleEvaluation,
)
from b4_thesis.analysis.deletion_prediction.extraction.rule_applicator import RuleApplicator
from b4_thesis.analysis.deletion_prediction.extraction.snippet_loader import SnippetLoader
from b4_thesis.analysis.deletion_prediction.label_generator import LabelGenerator
from b4_thesis.analysis.deletion_prediction.rules import get_rules
from b4_thesis.analysis.validation import CsvValidator, DeletionPredictionColumns

console = Console()


# ============================================================================
# Common Utilities
# ============================================================================


def handle_command_errors(func: Callable) -> Callable:
    """Decorator to handle common command errors with consistent messaging."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            console.print(f"[red]Error:[/red] {e}", highlight=False)
            raise click.Abort()
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}", highlight=False)
            raise click.Abort()
        except Exception as e:
            console.print(f"[red]Unexpected error:[/red] {e}", highlight=False)
            raise click.Abort()

    return wrapper


def print_success(message: str, output_path: Path) -> None:
    """Print success message with output path."""
    console.print(f"[green]✓[/green] {message}: {output_path}", highlight=False)


def print_warning(message: str) -> None:
    """Print warning message."""
    console.print(f"[yellow]Warning:[/yellow] {message}", highlight=False)


def prepare_output_path(output: str) -> Path:
    """Prepare output path by creating parent directories."""
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@click.group()
def deletion():
    """Detect deletion signs and evaluate prediction rules."""
    pass


@deletion.command()
@click.argument(
    "input_csv",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default="./output/method_lineage_labeled.csv",
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
    default="./output/method_lineage/snippets.csv",
    type=click.Path(path_type=Path, file_okay=True, dir_okay=False),
    required=True,
    help="Output CSV file path",
)
@click.option(
    "--rules",
    type=str,
    default=None,
    help="Comma-separated rule names (default: all rules)",
)
@click.option(
    "--base-prefix",
    type=str,
    default="/app/Repos/pandas/",
    help="Base path prefix to remove from file paths",
)
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
@handle_command_errors
def extract(
    input_csv: Path,
    repo: Path,
    output: Path,
    base_prefix: str,
):
    """Extract deletion prediction features from method lineage CSV.

    This command:
    1. Reads method_lineage_labeled.csv
    2. Extracts code from git repository
    3. Saves results to CSV

    """
    # load csv
    method_lineage_df = pd.read_csv(input_csv)

    # divide into deleted and non-deleted
    non_deleted_df = method_lineage_df[method_lineage_df["state"] != "deleted"].copy()
    # extract snippets for non-deleted
    snippet_loader = SnippetLoader(
        code_extractor=GitCodeExtractor(
            repo_path=repo,
            base_path_prefix=base_prefix,
            github_base_url=None,
        )
    )
    snippet_df = snippet_loader.load_snippets(non_deleted_df)

    # save snippets to csv
    snippet_df.to_csv(output, index=False)


@deletion.command()
@click.argument(
    "input_csv",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default="./output/method_lineage_labeled.csv",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path, file_okay=True, dir_okay=False),
    default="./output/method_lineage/ground_truth.csv",
    help="Output CSV file path (default: method_lineage/ground_truth.csv in input CSV directory)",
)
@click.option(
    "--lookahead-window",
    type=int,
    default=5,
    show_default=True,
    help="Number of future revisions to check for deletion",
)
def generate(input_csv: Path, output: Path, lookahead_window: int):
    """Generate ground truth labels for deletion prediction.

    This command reads a CSV with method lineage and code snippets,
    then generates the 'is_deleted_soon' labels based on future revisions.

    Example:
        b4-thesis deletion generate ./output/method_lineage.csv
    """
    # Load CSV
    method_lineage_df = pd.read_csv(input_csv)

    # Initialize feature extractor (dummy repo path since we only need labeling)
    label_generator = LabelGenerator(lookahead_window=lookahead_window)

    # Generate labels
    labeled_df = label_generator.generate_labels(method_lineage_df)

    # extract only necessary columns
    ground_truth_df = labeled_df[
        ["global_block_id", "revision", "state_with_clone", "is_deleted_soon"]
    ]

    # Save labeled DataFrame
    ground_truth_df.to_csv(output, index=False)


@deletion.command()
@click.option(
    "--input-snippets",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default="./output/method_lineage/snippets.csv",
)
@click.option(
    "--input-metadata",
    type=click.Path(path_type=Path, exists=True, file_okay=True, dir_okay=False),
    default="./output/method_lineage_labeled.csv",
    help="CSV with method metadata (function_name, file_path, loc, etc.)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path, file_okay=True, dir_okay=False),
    default="./output/method_lineage/with_rules.csv",
    help="Output file path",
)
@click.option(
    "--rules",
    type=str,
    default=None,
    help="Comma-separated rule names to apply (default: all rules)",
)
def rule(input_snippets: Path, input_metadata: Path, output: Path, rules: str | None):
    """Apply deletion prediction rules and output results.

    This command reads a CSV with method lineage and code snippets,
    applies deletion prediction rules, and outputs a CSV with rule results.

    Example:
        b4-thesis deletion rule ./output/method_lineage/snippets.csv \\
            --output ./output/method_lineage/with_rules.csv \\
            --rules short_method,has_todo
    """
    # Load CSV
    snippets_df = pd.read_csv(input_snippets)
    metadata_df = pd.read_csv(
        input_metadata,
        usecols=[
            "global_block_id",
            "revision",
            "function_name",
            "file_path",
            "start_line",
            "end_line",
            "loc",
        ],
    )

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

    if split_partial_by and group_by != "rev_status":
        print_warning(
            "--split-partial-by currently only supports --group-by rev_status. "
            "Ignoring --split-partial-by."
        )
        split_partial_by = None

    # Load features
    console.print(
        f"[bold blue]Loading features from {input_csv}...[/bold blue]",
        highlight=False,
    )
    df = pd.read_csv(input_csv)

    # Validate required columns
    try:
        CsvValidator.validate_required_columns(
            df,
            DeletionPredictionColumns.EVALUATION_BASIC,
            context="features CSV",
        )
    except ValueError as e:
        raise ValueError(f"{e}. Did you run 'deletion extract' first?")

    rule_cols = [c for c in df.columns if c.startswith("rule_")]
    if not rule_cols:
        raise ValueError("No rule columns found. Did you run 'deletion extract' first?")

    # Create composite column if splitting partial_deleted
    evaluator = Evaluator()

    if split_partial_by:
        console.print(
            f"[bold blue]Creating composite groups: "
            f"subdividing 'partial_deleted' by '{split_partial_by}'...[/bold blue]",
            highlight=False,
        )
        df, actual_group_column = _create_composite_group_column(
            df,
            group_by=group_by,
            split_partial_by=split_partial_by,
        )
    else:
        actual_group_column = group_by

    # Validate group column exists
    console.print(
        f"[bold green]Evaluating rules grouped by '{actual_group_column}'...[/bold green]",
        highlight=False,
    )

    if actual_group_column not in df.columns:
        raise ValueError(
            f"Group-by column '{actual_group_column}' not found. "
            f"Available columns: {', '.join(df.columns)}"
        )

    # Execute grouped evaluation
    grouped_results = evaluator.evaluate_by_group(
        df,
        group_by_column=actual_group_column,
        detailed=detailed,
        include_combined=combined,
        include_overall=not no_overall,
    )

    # Output grouped results
    _output_grouped_results(grouped_results, output, format, console)

    # Export detailed classifications if requested
    if detailed and export_dir:
        console.print(
            "\n[bold blue]Exporting detailed classifications...[/bold blue]",
            highlight=False,
        )
        export_path = Path(export_dir)
        created_files_dict = evaluator.export_grouped_classifications_csv(
            grouped_results, export_path
        )

        # Count total files created
        total_files = sum(
            len(classification_files)
            for group_files in created_files_dict.values()
            for classification_files in group_files.values()
        )

        console.print(
            f"[green]✓[/green] Exported {total_files} classification CSV file{'s' if total_files != 1 else ''}",
            highlight=False,
        )
        console.print(f"    to: {export_path}", highlight=False)

        # Display created structure
        console.print("\n[dim]Created structure:[/dim]")
        for rule_name in sorted(created_files_dict.keys()):
            console.print(f"  [dim]{rule_name}/[/dim]")
            for group_name in sorted(created_files_dict[rule_name].keys()):
                console.print(f"    [dim]{group_name}/[/dim]")
                for classification_type in ["TP", "FP", "FN", "TN"]:
                    console.print(f"      [dim]- {classification_type}.csv[/dim]")


def _output_grouped_results(
    grouped_results: list[GroupedRuleEvaluation],
    output: str,
    format: str,
    console: Console,
) -> None:
    """Dispatch grouped results to appropriate output formatter."""
    output_path = prepare_output_path(output)

    if format == "json":
        _output_grouped_results_json(grouped_results, output_path, console)
    elif format == "csv":
        _output_grouped_results_csv(grouped_results, output_path, console)
    elif format == "table":
        _output_grouped_results_table(grouped_results, output_path, console)


def _output_grouped_results_json(
    grouped_results: list[GroupedRuleEvaluation],
    output_path: Path,
    console: Console,
) -> None:
    """Output grouped results in JSON format."""
    with open(output_path, "w") as f:
        json.dump([gr.to_dict() for gr in grouped_results], f, indent=2)
    print_success("Grouped evaluation saved to", output_path)


def _output_grouped_results_csv(
    grouped_results: list[GroupedRuleEvaluation],
    output_path: Path,
    console: Console,
) -> None:
    """Output grouped results in CSV format (flattened structure)."""
    rows = []

    for grouped_result in grouped_results:
        group_col = grouped_result.group_by_column

        # Add rows for each group
        for group_name, evaluation in grouped_result.group_evaluations.items():
            row = evaluation.to_dict()
            row["group_by_column"] = group_col
            row["group_value"] = group_name
            rows.append(row)

        # Add overall row if present
        if grouped_result.overall_evaluation:
            row = grouped_result.overall_evaluation.to_dict()
            row["group_by_column"] = group_col
            row["group_value"] = "OVERALL"
            rows.append(row)

    df = pd.DataFrame(rows)

    # Reorder columns for readability
    col_order = [
        "rule_name",
        "group_by_column",
        "group_value",
        "TP",
        "FP",
        "FN",
        "TN",
        "precision",
        "recall",
        "f1",
    ]
    df = df[col_order]

    df.to_csv(output_path, index=False)
    print_success("Grouped evaluation saved to", output_path)


def _output_grouped_results_table(
    grouped_results: list[GroupedRuleEvaluation],
    output_path: Path,
    console: Console,
) -> None:
    """Output grouped results in Rich table format."""
    for grouped_result in grouped_results:
        rule_name = grouped_result.rule_name
        group_col = grouped_result.group_by_column

        # Create table for this rule
        title = f"Rule: {rule_name} (grouped by {group_col})"
        table = Table(title=title, show_header=True, header_style="bold magenta")

        table.add_column("Group", style="cyan", no_wrap=True)
        table.add_column("TP", justify="right")
        table.add_column("FP", justify="right")
        table.add_column("FN", justify="right")
        table.add_column("TN", justify="right")
        table.add_column("Precision", justify="right")
        table.add_column("Recall", justify="right")
        table.add_column("F1", justify="right", style="bold green")

        # Add rows for each group
        for group_name in grouped_result.get_group_names():
            evaluation = grouped_result.group_evaluations[group_name]
            table.add_row(
                group_name,
                str(evaluation.tp),
                str(evaluation.fp),
                str(evaluation.fn),
                str(evaluation.tn),
                f"{evaluation.precision:.4f}",
                f"{evaluation.recall:.4f}",
                f"{evaluation.f1:.4f}",
            )

        # Add separator before overall
        if grouped_result.overall_evaluation:
            table.add_section()
            overall = grouped_result.overall_evaluation
            table.add_row(
                "[bold]OVERALL[/bold]",
                f"[bold]{overall.tp}[/bold]",
                f"[bold]{overall.fp}[/bold]",
                f"[bold]{overall.fn}[/bold]",
                f"[bold]{overall.tn}[/bold]",
                f"[bold]{overall.precision:.4f}[/bold]",
                f"[bold]{overall.recall:.4f}[/bold]",
                f"[bold]{overall.f1:.4f}[/bold]",
            )

        console.print()
        console.print(table)

    # Also save to JSON for persistence
    with open(output_path, "w") as f:
        json.dump([gr.to_dict() for gr in grouped_results], f, indent=2)
    console.print()
    print_success("Grouped evaluation saved to", output_path)
