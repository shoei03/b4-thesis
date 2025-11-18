"""Presentation layer for statistics command.

This module handles the display and export of tracking statistics,
separating presentation logic from command orchestration.
"""

import pandas as pd
from rich.console import Console
from rich.table import Table

from b4_thesis.analysis.tracking_stats import (
    GroupTrackingStats,
    MethodTrackingStats,
    get_lifetime_distribution,
    get_state_distribution,
)


def display_method_stats_tables(stats: MethodTrackingStats, console: Console) -> None:
    """Display method tracking statistics as Rich tables.

    Args:
        stats: Method tracking statistics data
        console: Rich console for output

    Displays four tables:
    1. Overview (total methods, unique methods, revisions, etc.)
    2. State Distribution (ADDED, SURVIVED, DELETED)
    3. Clone Statistics (methods in clones, percentages, averages)
    4. Lifetime Statistics (average/median/max lifetime in days and revisions)
    """
    # Display overview table
    basic_table = Table(title="Method Tracking Statistics - Overview")
    basic_table.add_column("Metric", style="cyan")
    basic_table.add_column("Value", style="green", justify="right")

    basic_table.add_row("Total method occurrences", str(stats.total_methods))
    basic_table.add_row("Unique methods tracked", str(stats.unique_methods))
    basic_table.add_row("Total revisions analyzed", str(stats.total_revisions))
    basic_table.add_row("Avg methods per revision", f"{stats.avg_methods_per_revision:.1f}")
    basic_table.add_row("Max methods per revision", str(stats.max_methods_per_revision))
    basic_table.add_row("Min methods per revision", str(stats.min_methods_per_revision))

    console.print(basic_table)

    # Display state distribution
    _display_state_distribution_table(stats.state_counts, console)

    # Display clone statistics
    clone_table = Table(title="Clone Statistics")
    clone_table.add_column("Metric", style="cyan")
    clone_table.add_column("Value", style="green", justify="right")

    clone_table.add_row("Methods in clone groups", str(stats.methods_in_clones))
    if stats.total_methods > 0:
        clone_percentage = stats.methods_in_clones / stats.total_methods * 100
    else:
        clone_percentage = 0
    clone_table.add_row("Clone percentage", f"{clone_percentage:.1f}%")
    clone_table.add_row("Average clone count", f"{stats.avg_clone_count:.2f}")
    clone_table.add_row("Maximum clone count", str(stats.max_clone_count))

    console.print(clone_table)

    # Display lifetime statistics
    _display_lifetime_statistics_table(
        avg_days=stats.avg_lifetime_days,
        median_days=stats.median_lifetime_days,
        max_days=stats.max_lifetime_days,
        avg_revisions=stats.avg_lifetime_revisions,
        median_revisions=stats.median_lifetime_revisions,
        max_revisions=stats.max_lifetime_revisions,
        console=console,
    )


def display_group_stats_tables(stats: GroupTrackingStats, console: Console) -> None:
    """Display group tracking statistics as Rich tables.

    Args:
        stats: Group tracking statistics data
        console: Rich console for output

    Displays five tables:
    1. Overview (total groups, unique groups, revisions, etc.)
    2. State Distribution (BORN, CONTINUED, GROWN, etc.)
    3. Group Size Statistics (average/median/max/min size)
    4. Member Change Statistics (added/removed members)
    5. Lifetime Statistics (average/median/max lifetime in days and revisions)
    """
    # Display overview table
    basic_table = Table(title="Group Tracking Statistics - Overview")
    basic_table.add_column("Metric", style="cyan")
    basic_table.add_column("Value", style="green", justify="right")

    basic_table.add_row("Total group occurrences", str(stats.total_groups))
    basic_table.add_row("Unique groups tracked", str(stats.unique_groups))
    basic_table.add_row("Total revisions analyzed", str(stats.total_revisions))
    basic_table.add_row("Avg groups per revision", f"{stats.avg_groups_per_revision:.1f}")
    basic_table.add_row("Max groups per revision", str(stats.max_groups_per_revision))
    basic_table.add_row("Min groups per revision", str(stats.min_groups_per_revision))

    console.print(basic_table)

    # Display state distribution
    _display_state_distribution_table(stats.state_counts, console)

    # Display group size statistics
    size_table = Table(title="Group Size Statistics")
    size_table.add_column("Metric", style="cyan")
    size_table.add_column("Value", style="green", justify="right")

    size_table.add_row("Average group size", f"{stats.avg_group_size:.1f}")
    size_table.add_row("Median group size", f"{stats.median_group_size:.1f}")
    size_table.add_row("Maximum group size", str(stats.max_group_size))
    size_table.add_row("Minimum group size", str(stats.min_group_size))

    console.print(size_table)

    # Display member change statistics
    change_table = Table(title="Member Change Statistics")
    change_table.add_column("Metric", style="cyan")
    change_table.add_column("Value", style="green", justify="right")

    change_table.add_row("Avg members added", f"{stats.avg_members_added:.2f}")
    change_table.add_row("Max members added", str(stats.max_members_added))
    change_table.add_row("Avg members removed", f"{stats.avg_members_removed:.2f}")
    change_table.add_row("Max members removed", str(stats.max_members_removed))

    console.print(change_table)

    # Display lifetime statistics
    _display_lifetime_statistics_table(
        avg_days=stats.avg_lifetime_days,
        median_days=stats.median_lifetime_days,
        max_days=stats.max_lifetime_days,
        avg_revisions=stats.avg_lifetime_revisions,
        median_revisions=stats.median_lifetime_revisions,
        max_revisions=stats.max_lifetime_revisions,
        console=console,
    )


def export_method_stats_to_excel(df: pd.DataFrame, output_path: str) -> str:
    """Export method tracking statistics to Excel file.

    Args:
        df: Method tracking DataFrame
        output_path: Output file path (will be converted to .xlsx if needed)

    Returns:
        Actual output file path used

    Creates an Excel file with three sheets:
    - State Distribution: Distribution of states (ADDED, SURVIVED, DELETED)
    - Detailed States: Distribution of detailed states
    - Lifetime Distribution: Lifetime distribution in bins
    """
    # Create detailed distribution tables
    state_dist = get_state_distribution(df, state_col="state")
    detailed_dist = get_state_distribution(df, state_col="state_detail")
    lifetime_dist = get_lifetime_distribution(df, bins=10, column="lifetime_days")

    # Ensure .xlsx extension
    output_file = (
        output_path.replace(".csv", ".xlsx") if output_path.endswith(".csv") else output_path
    )
    if not output_file.endswith(".xlsx"):
        output_file = f"{output_file}.xlsx"

    # Save to Excel
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        state_dist.to_excel(writer, sheet_name="State Distribution", index=False)
        detailed_dist.to_excel(writer, sheet_name="Detailed States", index=False)
        lifetime_dist.to_excel(writer, sheet_name="Lifetime Distribution", index=False)

    return output_file


def export_group_stats_to_excel(df: pd.DataFrame, output_path: str) -> str:
    """Export group tracking statistics to Excel file.

    Args:
        df: Group tracking DataFrame
        output_path: Output file path (will be converted to .xlsx if needed)

    Returns:
        Actual output file path used

    Creates an Excel file with three sheets:
    - State Distribution: Distribution of states (BORN, CONTINUED, etc.)
    - Size Distribution: Distribution of group sizes
    - Lifetime Distribution: Lifetime distribution in bins
    """
    # Create detailed distribution tables
    state_dist = get_state_distribution(df, state_col="state")
    df_with_id = df.assign(group_id=df["group_id"])
    size_dist = get_lifetime_distribution(df_with_id, bins=10, column="member_count")
    lifetime_dist = get_lifetime_distribution(df, bins=10, column="lifetime_days")

    # Ensure .xlsx extension
    output_file = output_path if output_path.endswith(".xlsx") else f"{output_path}.xlsx"

    # Save to Excel
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        state_dist.to_excel(writer, sheet_name="State Distribution", index=False)
        size_dist.to_excel(writer, sheet_name="Size Distribution", index=False)
        lifetime_dist.to_excel(writer, sheet_name="Lifetime Distribution", index=False)

    return output_file


# Helper functions for creating common table structures


def _display_state_distribution_table(state_counts: dict[str, int], console: Console) -> None:
    """Display state distribution as a Rich table.

    Args:
        state_counts: Dictionary mapping state names to counts
        console: Rich console for output
    """
    state_table = Table(title="State Distribution")
    state_table.add_column("State", style="cyan")
    state_table.add_column("Count", style="green", justify="right")
    state_table.add_column("Percentage", style="yellow", justify="right")

    total = sum(state_counts.values())
    for state, count in sorted(state_counts.items()):
        percentage = (count / total * 100) if total > 0 else 0
        state_table.add_row(state.upper(), str(count), f"{percentage:.1f}%")

    console.print(state_table)


def _display_lifetime_statistics_table(
    avg_days: float,
    median_days: float,
    max_days: int,
    avg_revisions: float,
    median_revisions: float,
    max_revisions: int,
    console: Console,
) -> None:
    """Display lifetime statistics as a Rich table.

    Args:
        avg_days: Average lifetime in days
        median_days: Median lifetime in days
        max_days: Maximum lifetime in days
        avg_revisions: Average lifetime in revisions
        median_revisions: Median lifetime in revisions
        max_revisions: Maximum lifetime in revisions
        console: Rich console for output
    """
    lifetime_table = Table(title="Lifetime Statistics")
    lifetime_table.add_column("Metric", style="cyan")
    lifetime_table.add_column("Days", style="green", justify="right")
    lifetime_table.add_column("Revisions", style="yellow", justify="right")

    lifetime_table.add_row("Average", f"{avg_days:.1f}", f"{avg_revisions:.1f}")
    lifetime_table.add_row("Median", f"{median_days:.1f}", f"{median_revisions:.1f}")
    lifetime_table.add_row("Maximum", str(max_days), str(max_revisions))

    console.print(lifetime_table)
