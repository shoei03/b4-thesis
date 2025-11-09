"""Visualization functions for tracking results."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def plot_state_distribution(
    df: pd.DataFrame,
    state_col: str = "state",
    output_path: Path | str | None = None,
    title: str | None = None,
    plot_type: str = "bar",
) -> None:
    """Plot state distribution.

    Args:
        df: DataFrame with tracking results
        state_col: Column name for state
        output_path: Path to save plot (if None, display only)
        title: Plot title
        plot_type: Plot type ('bar' or 'pie')
    """
    if df.empty:
        raise ValueError("DataFrame is empty")

    plt.figure(figsize=(10, 6))
    counts = df[state_col].value_counts()

    if plot_type == "bar":
        ax = sns.barplot(x=counts.index, y=counts.values, palette="viridis")
        ax.set_xlabel("State")
        ax.set_ylabel("Count")
        plt.xticks(rotation=45, ha="right")

        # Add value labels on bars
        for i, v in enumerate(counts.values):
            ax.text(i, v + 0.5, str(v), ha="center", va="bottom")

    elif plot_type == "pie":
        plt.pie(counts.values, labels=counts.index, autopct="%1.1f%%", startangle=90)
        plt.axis("equal")
    else:
        raise ValueError(f"Unknown plot type: {plot_type}")

    if title:
        plt.title(title)
    else:
        plt.title(f"{state_col.replace('_', ' ').title()} Distribution")

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
    else:
        plt.show()

    plt.close()


def plot_lifetime_distribution(
    df: pd.DataFrame,
    column: str = "lifetime_days",
    output_path: Path | str | None = None,
    title: str | None = None,
    bins: int = 20,
) -> None:
    """Plot lifetime distribution histogram.

    Args:
        df: DataFrame with tracking results
        column: Column name for lifetime
        output_path: Path to save plot
        title: Plot title
        bins: Number of bins
    """
    if df.empty or column not in df.columns:
        raise ValueError(f"DataFrame is empty or column '{column}' not found")

    # Use unique methods/groups for lifetime distribution
    id_col = "method_id" if "method_id" in df.columns else "group_id"
    unique_df = df.drop_duplicates(subset=[id_col], keep="first")

    plt.figure(figsize=(10, 6))
    sns.histplot(unique_df[column], bins=bins, kde=True, color="skyblue")

    plt.xlabel(column.replace("_", " ").title())
    plt.ylabel("Count")

    if title:
        plt.title(title)
    else:
        plt.title(f"{column.replace('_', ' ').title()} Distribution")

    # Add statistics
    mean_val = unique_df[column].mean()
    median_val = unique_df[column].median()
    plt.axvline(mean_val, color="red", linestyle="--", label=f"Mean: {mean_val:.1f}")
    plt.axvline(median_val, color="green", linestyle="--", label=f"Median: {median_val:.1f}")
    plt.legend()

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
    else:
        plt.show()

    plt.close()


def plot_timeline(
    df: pd.DataFrame,
    metric: str = "count",
    output_path: Path | str | None = None,
    title: str | None = None,
) -> None:
    """Plot timeline of metrics per revision.

    Args:
        df: DataFrame with tracking results
        metric: Metric to plot ('count', 'avg_clone_count', 'avg_group_size')
        output_path: Path to save plot
        title: Plot title
    """
    if df.empty:
        raise ValueError("DataFrame is empty")

    plt.figure(figsize=(12, 6))
    grouped = df.groupby("revision")

    if metric == "count":
        values = grouped.size()
        ylabel = "Number of Methods/Groups"
    elif metric == "avg_clone_count" and "clone_count" in df.columns:
        values = grouped["clone_count"].mean()
        ylabel = "Average Clone Count"
    elif metric == "avg_group_size" and "member_count" in df.columns:
        values = grouped["member_count"].mean()
        ylabel = "Average Group Size"
    else:
        raise ValueError(f"Unknown metric: {metric}")

    plt.plot(range(len(values)), values.values, marker="o", linewidth=2, markersize=8)
    plt.xticks(range(len(values)), values.index, rotation=45, ha="right")
    plt.xlabel("Revision")
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)

    if title:
        plt.title(title)
    else:
        plt.title(f"{ylabel} Over Time")

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
    else:
        plt.show()

    plt.close()


def plot_state_timeline(
    df: pd.DataFrame,
    state_col: str = "state",
    output_path: Path | str | None = None,
    title: str | None = None,
    stacked: bool = True,
) -> None:
    """Plot timeline of state distribution.

    Args:
        df: DataFrame with tracking results
        state_col: Column name for state
        output_path: Path to save plot
        title: Plot title
        stacked: Whether to use stacked area plot
    """
    if df.empty:
        raise ValueError("DataFrame is empty")

    # Pivot data: revisions × states
    pivot = df.groupby(["revision", state_col]).size().unstack(fill_value=0)

    plt.figure(figsize=(12, 6))

    if stacked:
        pivot.plot(kind="area", stacked=True, alpha=0.7, ax=plt.gca())
    else:
        pivot.plot(kind="line", marker="o", ax=plt.gca())

    plt.xlabel("Revision")
    plt.ylabel("Count")
    plt.xticks(rotation=45, ha="right")
    legend_title = state_col.replace("_", " ").title()
    plt.legend(title=legend_title, bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.grid(True, alpha=0.3)

    if title:
        plt.title(title)
    else:
        plt.title(f"{state_col.replace('_', ' ').title()} Over Time")

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
    else:
        plt.show()

    plt.close()


def plot_group_size_distribution(
    df: pd.DataFrame,
    output_path: Path | str | None = None,
    title: str | None = None,
    plot_type: str = "box",
) -> None:
    """Plot group size distribution.

    Args:
        df: DataFrame with group tracking results
        output_path: Path to save plot
        title: Plot title
        plot_type: Plot type ('box', 'violin', 'hist')
    """
    if df.empty or "member_count" not in df.columns:
        raise ValueError("DataFrame is empty or 'member_count' column not found")

    plt.figure(figsize=(10, 6))

    if plot_type == "box":
        sns.boxplot(y=df["member_count"], color="lightblue")
        plt.ylabel("Group Size (Member Count)")
    elif plot_type == "violin":
        sns.violinplot(y=df["member_count"], color="lightblue")
        plt.ylabel("Group Size (Member Count)")
    elif plot_type == "hist":
        sns.histplot(df["member_count"], bins=20, kde=True, color="skyblue")
        plt.xlabel("Group Size (Member Count)")
        plt.ylabel("Count")
    else:
        raise ValueError(f"Unknown plot type: {plot_type}")

    if title:
        plt.title(title)
    else:
        plt.title("Group Size Distribution")

    # Add statistics
    mean_val = df["member_count"].mean()
    median_val = df["member_count"].median()
    if plot_type == "hist":
        plt.axvline(mean_val, color="red", linestyle="--", label=f"Mean: {mean_val:.1f}")
        plt.axvline(median_val, color="green", linestyle="--", label=f"Median: {median_val:.1f}")
        plt.legend()

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
    else:
        plt.show()

    plt.close()


def plot_member_changes(
    df: pd.DataFrame,
    output_path: Path | str | None = None,
    title: str | None = None,
) -> None:
    """Plot member changes over time.

    Args:
        df: DataFrame with group tracking results
        output_path: Path to save plot
        title: Plot title
    """
    if df.empty:
        raise ValueError("DataFrame is empty")

    required_cols = ["revision", "members_added", "members_removed"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Aggregate by revision
    agg = df.groupby("revision")[["members_added", "members_removed"]].sum()

    plt.figure(figsize=(12, 6))

    x = range(len(agg))
    width = 0.35

    plt.bar(
        [i - width / 2 for i in x],
        agg["members_added"],
        width,
        label="Added",
        color="green",
        alpha=0.7,
    )
    plt.bar(
        [i + width / 2 for i in x],
        agg["members_removed"],
        width,
        label="Removed",
        color="red",
        alpha=0.7,
    )

    plt.xlabel("Revision")
    plt.ylabel("Number of Members")
    plt.xticks(x, agg.index, rotation=45, ha="right")
    plt.legend()
    plt.grid(True, alpha=0.3, axis="y")

    if title:
        plt.title(title)
    else:
        plt.title("Member Changes Over Time")

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
    else:
        plt.show()

    plt.close()


def create_method_tracking_dashboard(
    df: pd.DataFrame,
    output_dir: Path | str,
) -> None:
    """Create a comprehensive dashboard for method tracking results.

    Args:
        df: DataFrame with method tracking results
        output_dir: Directory to save plots
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. State distribution
    plot_state_distribution(
        df,
        state_col="state",
        output_path=output_path / "state_distribution.png",
        title="Method State Distribution",
        plot_type="bar",
    )

    # 2. Detailed state distribution
    plot_state_distribution(
        df,
        state_col="detailed_state",
        output_path=output_path / "detailed_state_distribution.png",
        title="Detailed State Distribution",
        plot_type="bar",
    )

    # 3. Lifetime distribution (days)
    plot_lifetime_distribution(
        df,
        column="lifetime_days",
        output_path=output_path / "lifetime_days_distribution.png",
        title="Method Lifetime Distribution (Days)",
    )

    # 4. Lifetime distribution (revisions)
    plot_lifetime_distribution(
        df,
        column="lifetime_revisions",
        output_path=output_path / "lifetime_revisions_distribution.png",
        title="Method Lifetime Distribution (Revisions)",
    )

    # 5. Timeline: method count
    plot_timeline(
        df,
        metric="count",
        output_path=output_path / "method_count_timeline.png",
        title="Number of Methods Over Time",
    )

    # 6. Timeline: clone count
    if "clone_count" in df.columns:
        plot_timeline(
            df,
            metric="avg_clone_count",
            output_path=output_path / "clone_count_timeline.png",
            title="Average Clone Count Over Time",
        )

    # 7. State timeline
    plot_state_timeline(
        df,
        state_col="state",
        output_path=output_path / "state_timeline.png",
        title="Method States Over Time",
    )


def create_group_tracking_dashboard(
    df: pd.DataFrame,
    output_dir: Path | str,
) -> None:
    """Create a comprehensive dashboard for group tracking results.

    Args:
        df: DataFrame with group tracking results
        output_dir: Directory to save plots
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. State distribution
    plot_state_distribution(
        df,
        state_col="state",
        output_path=output_path / "state_distribution.png",
        title="Group State Distribution",
        plot_type="bar",
    )

    # 2. Group size distribution
    plot_group_size_distribution(
        df,
        output_path=output_path / "group_size_distribution.png",
        title="Group Size Distribution",
        plot_type="hist",
    )

    # 3. Group size box plot
    plot_group_size_distribution(
        df,
        output_path=output_path / "group_size_boxplot.png",
        title="Group Size Distribution (Box Plot)",
        plot_type="box",
    )

    # 4. Timeline: group count
    plot_timeline(
        df,
        metric="count",
        output_path=output_path / "group_count_timeline.png",
        title="Number of Groups Over Time",
    )

    # 5. Timeline: average group size
    plot_timeline(
        df,
        metric="avg_group_size",
        output_path=output_path / "avg_group_size_timeline.png",
        title="Average Group Size Over Time",
    )

    # 6. Member changes
    plot_member_changes(
        df,
        output_path=output_path / "member_changes_timeline.png",
        title="Member Changes Over Time",
    )

    # 7. State timeline
    plot_state_timeline(
        df,
        state_col="state",
        output_path=output_path / "state_timeline.png",
        title="Group States Over Time",
    )
