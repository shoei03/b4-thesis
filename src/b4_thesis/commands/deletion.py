"""Deletion prediction commands."""

import json
from pathlib import Path

import click
import pandas as pd
from rich.console import Console
from rich.table import Table

from b4_thesis.analysis.deletion_prediction.cache_manager import CacheManager
from b4_thesis.analysis.deletion_prediction.evaluator import Evaluator
from b4_thesis.analysis.deletion_prediction.feature_extractor import FeatureExtractor

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
def evaluate(input_csv: str, output: str, format: str, detailed: bool, export_dir: str | None):
    """Evaluate deletion prediction rules.

    This command:
    1. Reads features CSV (from extract command)
    2. Calculates Precision, Recall, F1 for each rule
    3. Outputs evaluation report
    4. (Optional) Exports detailed classification CSVs with --detailed --export-dir

    Example:
        b4-thesis deletion evaluate features.csv \\
            --output report.json \\
            --format json

        # With detailed tracking
        b4-thesis deletion evaluate features.csv \\
            --output report.json \\
            --detailed \\
            --export-dir ./classifications/
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

        # Load features
        console.print(
            f"[bold blue]Loading features from {input_csv}...[/bold blue]",
            highlight=False,
        )
        df = pd.read_csv(input_csv)

        # Validate
        if "is_deleted_next" not in df.columns:
            raise ValueError(
                "Missing 'is_deleted_next' column. Did you run 'deletion extract' first?"
            )

        rule_cols = [c for c in df.columns if c.startswith("rule_")]
        if not rule_cols:
            raise ValueError("No rule columns found. Did you run 'deletion extract' first?")

        # Evaluate
        console.print("[bold green]Evaluating rules...[/bold green]", highlight=False)
        evaluator = Evaluator()
        results = evaluator.evaluate(df, detailed=detailed)

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
