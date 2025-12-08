"""Deletion prediction commands."""

import json
from pathlib import Path

import click
import pandas as pd
from rich.console import Console
from rich.table import Table

from b4_thesis.analysis.deletion_prediction.cache_manager import CacheManager
from b4_thesis.analysis.deletion_prediction.evaluator import (
    DetailedRuleEvaluation,
    Evaluator,
    GroupedRuleEvaluation,
)
from b4_thesis.analysis.deletion_prediction.feature_extractor import FeatureExtractor
from b4_thesis.analysis.validation import CsvValidator, DeletionPredictionColumns

console = Console()


@click.group()
def deletion():
    """Detect deletion signs and evaluate prediction rules."""
    pass


@deletion.command()
@click.argument("input_csv", type=click.Path(exists=True))
@click.option(
    "--repo",
    "-r",
    type=click.Path(exists=True),
    required=True,
    help="Path to git repository",
)
@click.option("--output", "-o", type=click.Path(), required=True, help="Output CSV file path")
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
@click.option(
    "--cache-dir",
    type=click.Path(),
    default=None,
    help="Cache directory path (default: ~/.cache/b4-thesis/deletion-prediction)",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Disable caching (forces re-extraction)",
)
@click.option(
    "--lookahead-window",
    type=int,
    default=5,
    show_default=True,
    help="Number of future revisions to check for deletion",
)
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
def extract(
    input_csv: str,
    repo: str,
    output: str,
    rules: str | None,
    base_prefix: str,
    cache_dir: str | None,
    no_cache: bool,
    lookahead_window: int,
    verbose: bool,
):
    """Extract deletion prediction features from method lineage CSV.

    This command:
    1. Reads method_lineage_labeled.csv
    2. Extracts code from git repository
    3. Applies deletion prediction rules
    4. Generates ground truth labels (is_deleted_soon)
    5. Saves results to CSV

    Example:
        b4-thesis deletion extract method_lineage_labeled.csv \\
            --repo /path/to/repo \\
            --output features.csv
    """
    try:
        # Parse rules
        rule_names = rules.split(",") if rules else None
        if rule_names:
            rule_names = [r.strip() for r in rule_names]

        # Setup cache manager
        cache_manager = None
        if not no_cache:
            if cache_dir:
                cache_path = Path(cache_dir)
            else:
                cache_path = Path.home() / ".cache" / "b4-thesis" / "deletion-prediction"

            cache_manager = CacheManager(cache_path)
            if verbose:
                console.print(f"[dim]Cache directory: {cache_path}[/dim]")

        # Initialize extractor
        console.print("[bold blue]Initializing feature extractor...[/bold blue]", highlight=False)
        extractor = FeatureExtractor(
            repo_path=Path(repo),
            base_path_prefix=base_prefix,
            lookahead_window=lookahead_window,
        )

        # Extract features
        console.print(
            f"[bold green]Extracting features from {input_csv}...[/bold green]",
            highlight=False,
        )
        df = extractor.extract(
            Path(input_csv),
            rule_names=rule_names,
            cache_manager=cache_manager,
            use_cache=not no_cache,
        )

        # Save results
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)

        console.print(f"[green]✓[/green] Features saved to: {output_path}", highlight=False)

        # Display summary if verbose
        if verbose:
            rule_cols = [c for c in df.columns if c.startswith("rule_")]
            deleted_count = df["is_deleted_soon"].sum()
            deleted_pct = (deleted_count / len(df) * 100) if len(df) > 0 else 0

            console.print("\n[bold]Summary:[/bold]")
            console.print(f"  Total methods: {len(df):,}")
            console.print(f"  Deleted soon: {deleted_count:,} ({deleted_pct:.1f}%)")
            console.print(f"  Rules applied: {len(rule_cols)}")
            if rule_cols:
                console.print("  Rule names:")
                for col in rule_cols:
                    rule_name = col.replace("rule_", "")
                    positive_count = df[col].sum()
                    positive_pct = (positive_count / len(df) * 100) if len(df) > 0 else 0
                    console.print(f"    - {rule_name}: {positive_count:,} ({positive_pct:.1f}%)")

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}", highlight=False)
        raise click.Abort()
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}", highlight=False)
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}", highlight=False)
        raise click.Abort()


def _create_composite_group_column(
    df: pd.DataFrame,
    group_by: str,
    split_partial_by: str,
    split_value: str = "partial_deleted",
) -> tuple[pd.DataFrame, str]:
    """Create a composite grouping column by subdividing a specific group value.

    Args:
        df: Features DataFrame
        group_by: Primary grouping column (e.g., 'rev_status')
        split_partial_by: Column to use for subdividing (e.g., 'state')
        split_value: Which group value to subdivide (default: 'partial_deleted')

    Returns:
        Tuple of (modified DataFrame with new column, new column name)

    Logic:
        For each row:
        - If df[group_by] != split_value: composite = df[group_by]
        - If df[group_by] == split_value:
          - If df[split_partial_by] == 'deleted': composite = f"{split_value}_deleted"
          - If df[split_partial_by] in ['survived', 'added']: composite = f"{split_value}_survived"
          - Otherwise (NaN or unexpected): composite = f"{split_value}_other"

    Example:
        Input: group_by='rev_status', split_partial_by='state'
        - rev_status='no_deleted' → composite_group='no_deleted'
        - rev_status='all_deleted' → composite_group='all_deleted'
        - rev_status='partial_deleted', state='deleted'
          → composite_group='partial_deleted_deleted'
        - rev_status='partial_deleted', state='survived'
          → composite_group='partial_deleted_survived'
        - rev_status='partial_deleted', state='added'
          → composite_group='partial_deleted_survived' (same as survived!)
        - rev_status='partial_deleted', state=NaN
          → composite_group='partial_deleted_other'
    """
    # Validate columns exist
    if group_by not in df.columns:
        raise ValueError(
            f"Group-by column '{group_by}' not found in DataFrame. "
            f"Available columns: {', '.join(df.columns)}"
        )
    if split_partial_by not in df.columns:
        raise ValueError(
            f"Split column '{split_partial_by}' not found in DataFrame. "
            f"Available columns: {', '.join(df.columns)}"
        )

    # Create composite column
    composite_col_name = f"_composite_{group_by}_{split_partial_by}"
    df = df.copy()

    def create_composite_value(row):
        """Create composite group value for a single row."""
        if row[group_by] != split_value:
            # Not the target group value, use as-is
            return row[group_by]

        # Target group value - subdivide by split column
        split_col_value = row[split_partial_by]

        # Handle deleted state
        if split_col_value == "deleted":
            return f"{split_value}_deleted"

        # Handle survived and added states (both are non-deleted)
        if split_col_value in ["survived", "added"]:
            return f"{split_value}_survived"

        # Handle NaN or unexpected values
        return f"{split_value}_other"

    df[composite_col_name] = df.apply(create_composite_value, axis=1)

    return df, composite_col_name


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
    default=None,
    help="Column name to group evaluation by (e.g., 'rev_status')",
)
@click.option(
    "--no-overall",
    is_flag=True,
    help="Exclude overall evaluation when using --group-by (only show per-group results)",
)
@click.option(
    "--split-partial-by",
    type=str,
    default=None,
    help="Column to subdivide 'partial_deleted' group by (e.g., 'state'). "
    "Requires --group-by to be set to 'rev_status'.",
)
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
    3. Outputs evaluation report
    4. (Optional) Groups evaluation by categorical column with --group-by
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

        # Grouped evaluation by rev_status
        b4-thesis deletion evaluate features.csv \\
            --output grouped_report.json \\
            --format json \\
            --group-by rev_status
    """
    try:
        # Validate flags
        if export_dir and not detailed:
            console.print(
                "[yellow]Warning:[/yellow] --export-dir requires --detailed flag. "
                "Ignoring --export-dir.",
                highlight=False,
            )
            export_dir = None

        if no_overall and not group_by:
            console.print(
                "[yellow]Warning:[/yellow] --no-overall only affects --group-by mode. "
                "Ignoring --no-overall.",
                highlight=False,
            )
            no_overall = False

        # Validate split_partial_by flag
        if split_partial_by and not group_by:
            console.print(
                "[yellow]Warning:[/yellow] --split-partial-by requires --group-by. "
                "Ignoring --split-partial-by.",
                highlight=False,
            )
            split_partial_by = None

        if split_partial_by and group_by != "rev_status":
            console.print(
                "[yellow]Warning:[/yellow] --split-partial-by currently only supports "
                "--group-by rev_status. Ignoring --split-partial-by.",
                highlight=False,
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
            raise ValueError(
                f"{e}. Did you run 'deletion extract' first?"
            )

        rule_cols = [c for c in df.columns if c.startswith("rule_")]
        if not rule_cols:
            raise ValueError("No rule columns found. Did you run 'deletion extract' first?")

        # Evaluate (branching logic for grouped vs standard)
        evaluator = Evaluator()

        if group_by:
            # Create composite column if splitting partial_deleted
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

            # Grouped evaluation path
            console.print(
                f"[bold green]Evaluating rules grouped by '{actual_group_column}'...[/bold green]",
                highlight=False,
            )

            # Validate group column exists (check actual_group_column, not group_by)
            if actual_group_column not in df.columns:
                raise ValueError(
                    f"Group-by column '{actual_group_column}' not found. "
                    f"Available columns: {', '.join(df.columns)}"
                )

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
                _export_grouped_classifications(grouped_results, export_dir, console)
        else:
            # Standard evaluation path (existing code)
            console.print("[bold green]Evaluating rules...[/bold green]", highlight=False)
            results = evaluator.evaluate(df, detailed=detailed, include_combined=combined)

            # Output based on format
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if format == "json":
                with open(output_path, "w") as f:
                    json.dump([r.to_dict() for r in results], f, indent=2)
                console.print(
                    f"[green]✓[/green] Evaluation saved to: {output_path}",
                    highlight=False,
                )

            elif format == "csv":
                results_df = pd.DataFrame([r.to_dict() for r in results])
                results_df.to_csv(output_path, index=False)
                console.print(
                    f"[green]✓[/green] Evaluation saved to: {output_path}",
                    highlight=False,
                )

            elif format == "table":
                # Display rich table
                table = Table(title="Deletion Prediction Rule Evaluation")
                table.add_column("Rule", style="cyan", no_wrap=True)
                table.add_column("TP", justify="right")
                table.add_column("FP", justify="right")
                table.add_column("FN", justify="right")
                table.add_column("TN", justify="right")
                table.add_column("Precision", justify="right")
                table.add_column("Recall", justify="right")
                table.add_column("F1", justify="right", style="bold green")

                for r in results:
                    # Add section separator before combined rule
                    if r.rule_name == "combined_all_rules":
                        table.add_section()
                        table.add_row(
                            f"[bold magenta]{r.rule_name}[/bold magenta]",
                            f"[bold magenta]{r.tp}[/bold magenta]",
                            f"[bold magenta]{r.fp}[/bold magenta]",
                            f"[bold magenta]{r.fn}[/bold magenta]",
                            f"[bold magenta]{r.tn}[/bold magenta]",
                            f"[bold magenta]{r.precision:.4f}[/bold magenta]",
                            f"[bold magenta]{r.recall:.4f}[/bold magenta]",
                            f"[bold magenta]{r.f1:.4f}[/bold magenta]",
                        )
                    else:
                        table.add_row(
                            r.rule_name,
                            str(r.tp),
                            str(r.fp),
                            str(r.fn),
                            str(r.tn),
                            f"{r.precision:.4f}",
                            f"{r.recall:.4f}",
                            f"{r.f1:.4f}",
                        )

                console.print(table)

                # Also save to JSON
                with open(output_path, "w") as f:
                    json.dump([r.to_dict() for r in results], f, indent=2)
                console.print(
                    f"\n[green]✓[/green] Evaluation saved to: {output_path}",
                    highlight=False,
                )

            # Export detailed classifications if requested
            if detailed and export_dir:
                console.print(
                    "\n[bold blue]Exporting detailed classifications...[/bold blue]",
                    highlight=False,
                )
                export_path = Path(export_dir)
                created_files = evaluator.export_classifications_csv(results, export_path)

                console.print(
                    f"[green]✓[/green] Exported {len(created_files)} classification CSV files "
                    f"to: {export_path}",
                    highlight=False,
                )
                if created_files:
                    console.print("\n[dim]Created files:[/dim]")
                    for file_path in created_files:
                        console.print(f"  [dim]- {file_path.name}[/dim]")

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}", highlight=False)
        raise click.Abort()
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}", highlight=False)
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}", highlight=False)
        raise click.Abort()


def _output_grouped_results(
    grouped_results: list[GroupedRuleEvaluation],
    output: str,
    format: str,
    console: Console,
) -> None:
    """Dispatch grouped results to appropriate output formatter."""
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

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
    console.print(
        f"[green]✓[/green] Grouped evaluation saved to: {output_path}",
        highlight=False,
    )


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
    console.print(
        f"[green]✓[/green] Grouped evaluation saved to: {output_path}",
        highlight=False,
    )


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
    console.print(
        f"\n[green]✓[/green] Grouped evaluation saved to: {output_path}",
        highlight=False,
    )


def _export_grouped_classifications(
    grouped_results: list[GroupedRuleEvaluation],
    export_dir: str,
    console: Console,
) -> None:
    """Export detailed classifications for grouped evaluation.

    Creates one CSV per (rule, group) combination.

    Example files:
        short_lifetime_all_deleted_classifications.csv
        short_lifetime_no_deleted_classifications.csv
        short_lifetime_partial_deleted_classifications.csv
        short_lifetime_OVERALL_classifications.csv
    """
    console.print(
        "\n[bold blue]Exporting detailed classifications...[/bold blue]",
        highlight=False,
    )

    export_path = Path(export_dir)
    export_path.mkdir(parents=True, exist_ok=True)

    created_files = []

    for grouped_result in grouped_results:
        rule_name = grouped_result.rule_name

        # Export each group's classifications
        for group_name, evaluation in grouped_result.group_evaluations.items():
            if not isinstance(evaluation, DetailedRuleEvaluation):
                continue
            if evaluation.classifications is None:
                continue

            # Generate filename
            safe_group_name = group_name.replace("/", "_").replace(" ", "_")
            filename = f"{rule_name}_{safe_group_name}_classifications.csv"
            file_path = export_path / filename

            # Export to CSV
            data = [c.to_dict() for c in evaluation.classifications]
            df = pd.DataFrame(data)
            df.to_csv(file_path, index=False)
            created_files.append(file_path)

        # Export overall if present
        if grouped_result.overall_evaluation:
            overall = grouped_result.overall_evaluation
            if isinstance(overall, DetailedRuleEvaluation) and overall.classifications:
                filename = f"{rule_name}_OVERALL_classifications.csv"
                file_path = export_path / filename

                data = [c.to_dict() for c in overall.classifications]
                df = pd.DataFrame(data)
                df.to_csv(file_path, index=False)
                created_files.append(file_path)

    console.print(
        f"[green]✓[/green] Exported {len(created_files)} classification CSV files "
        f"to: {export_path}",
        highlight=False,
    )
    if created_files:
        console.print("\n[dim]Created files:[/dim]")
        for file_path in sorted(created_files):
            console.print(f"  [dim]- {file_path.name}[/dim]")
