"""Statistics calculator for tracking results."""

from dataclasses import dataclass

import pandas as pd


@dataclass
class MethodTrackingStats:
    """Statistics for method tracking results."""

    total_methods: int
    total_revisions: int
    unique_methods: int

    # State distribution
    state_counts: dict[str, int]
    detailed_state_counts: dict[str, int]

    # Clone statistics
    methods_in_clones: int
    avg_clone_count: float
    max_clone_count: int

    # Lifetime statistics
    avg_lifetime_days: float
    avg_lifetime_revisions: float
    max_lifetime_days: int
    max_lifetime_revisions: int
    median_lifetime_days: float
    median_lifetime_revisions: float

    # Per-revision statistics
    avg_methods_per_revision: float
    max_methods_per_revision: int
    min_methods_per_revision: int


@dataclass
class GroupTrackingStats:
    """Statistics for group tracking results."""

    total_groups: int
    total_revisions: int
    unique_groups: int

    # State distribution
    state_counts: dict[str, int]

    # Group size statistics
    avg_group_size: float
    max_group_size: int
    min_group_size: int
    median_group_size: float

    # Member change statistics
    avg_members_added: float
    avg_members_removed: float
    max_members_added: int
    max_members_removed: int

    # Lifetime statistics
    avg_lifetime_days: float
    avg_lifetime_revisions: float
    max_lifetime_days: int
    max_lifetime_revisions: int
    median_lifetime_days: float
    median_lifetime_revisions: float

    # Per-revision statistics
    avg_groups_per_revision: float
    max_groups_per_revision: int
    min_groups_per_revision: int


def calculate_method_stats(df: pd.DataFrame) -> MethodTrackingStats:
    """Calculate statistics for method tracking results.

    Args:
        df: DataFrame with method tracking results

    Returns:
        MethodTrackingStats object with calculated statistics

    Raises:
        ValueError: If DataFrame is empty or missing required columns
    """
    if df.empty:
        raise ValueError("DataFrame is empty")

    required_cols = [
        "block_id",
        "revision",
        "state",
        "state_detail",
        "clone_count",
        "lifetime_days",
        "lifetime_revisions",
    ]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Basic counts
    total_methods = len(df)
    total_revisions = df["revision"].nunique()
    unique_methods = df["block_id"].nunique()

    # State distribution
    state_counts = df["state"].value_counts().to_dict()
    detailed_state_counts = df["state_detail"].value_counts().to_dict()

    # Clone statistics
    methods_in_clones = len(df[df["clone_count"] > 0])
    avg_clone_count = df["clone_count"].mean()
    max_clone_count = df["clone_count"].max()

    # Lifetime statistics (use first appearance for each unique method)
    unique_df = df.drop_duplicates(subset=["block_id"], keep="first")
    avg_lifetime_days = unique_df["lifetime_days"].mean()
    avg_lifetime_revisions = unique_df["lifetime_revisions"].mean()
    max_lifetime_days = unique_df["lifetime_days"].max()
    max_lifetime_revisions = unique_df["lifetime_revisions"].max()
    median_lifetime_days = unique_df["lifetime_days"].median()
    median_lifetime_revisions = unique_df["lifetime_revisions"].median()

    # Per-revision statistics
    methods_per_revision = df.groupby("revision").size()
    avg_methods_per_revision = methods_per_revision.mean()
    max_methods_per_revision = methods_per_revision.max()
    min_methods_per_revision = methods_per_revision.min()

    return MethodTrackingStats(
        total_methods=total_methods,
        total_revisions=total_revisions,
        unique_methods=unique_methods,
        state_counts=state_counts,
        detailed_state_counts=detailed_state_counts,
        methods_in_clones=methods_in_clones,
        avg_clone_count=avg_clone_count,
        max_clone_count=max_clone_count,
        avg_lifetime_days=avg_lifetime_days,
        avg_lifetime_revisions=avg_lifetime_revisions,
        max_lifetime_days=max_lifetime_days,
        max_lifetime_revisions=max_lifetime_revisions,
        median_lifetime_days=median_lifetime_days,
        median_lifetime_revisions=median_lifetime_revisions,
        avg_methods_per_revision=avg_methods_per_revision,
        max_methods_per_revision=max_methods_per_revision,
        min_methods_per_revision=min_methods_per_revision,
    )


def calculate_group_stats(df: pd.DataFrame) -> GroupTrackingStats:
    """Calculate statistics for group tracking results.

    Args:
        df: DataFrame with group tracking results

    Returns:
        GroupTrackingStats object with calculated statistics

    Raises:
        ValueError: If DataFrame is empty or missing required columns
    """
    if df.empty:
        raise ValueError("DataFrame is empty")

    required_cols = [
        "group_id",
        "revision",
        "state",
        "member_count",
        "member_added",
        "member_removed",
        "lifetime_days",
        "lifetime_revisions",
    ]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Basic counts
    total_groups = len(df)
    total_revisions = df["revision"].nunique()
    unique_groups = df["group_id"].nunique()

    # State distribution
    state_counts = df["state"].value_counts().to_dict()

    # Group size statistics
    avg_group_size = df["member_count"].mean()
    max_group_size = df["member_count"].max()
    min_group_size = df["member_count"].min()
    median_group_size = df["member_count"].median()

    # Member change statistics
    avg_members_added = df["member_added"].mean()
    avg_members_removed = df["member_removed"].mean()
    max_members_added = df["member_added"].max()
    max_members_removed = df["member_removed"].max()

    # Lifetime statistics (use first appearance for each unique group)
    unique_df = df.drop_duplicates(subset=["group_id"], keep="first")
    avg_lifetime_days = unique_df["lifetime_days"].mean()
    avg_lifetime_revisions = unique_df["lifetime_revisions"].mean()
    max_lifetime_days = unique_df["lifetime_days"].max()
    max_lifetime_revisions = unique_df["lifetime_revisions"].max()
    median_lifetime_days = unique_df["lifetime_days"].median()
    median_lifetime_revisions = unique_df["lifetime_revisions"].median()

    # Per-revision statistics
    groups_per_revision = df.groupby("revision").size()
    avg_groups_per_revision = groups_per_revision.mean()
    max_groups_per_revision = groups_per_revision.max()
    min_groups_per_revision = groups_per_revision.min()

    return GroupTrackingStats(
        total_groups=total_groups,
        total_revisions=total_revisions,
        unique_groups=unique_groups,
        state_counts=state_counts,
        avg_group_size=avg_group_size,
        max_group_size=max_group_size,
        min_group_size=min_group_size,
        median_group_size=median_group_size,
        avg_members_added=avg_members_added,
        avg_members_removed=avg_members_removed,
        max_members_added=max_members_added,
        max_members_removed=max_members_removed,
        avg_lifetime_days=avg_lifetime_days,
        avg_lifetime_revisions=avg_lifetime_revisions,
        max_lifetime_days=max_lifetime_days,
        max_lifetime_revisions=max_lifetime_revisions,
        median_lifetime_days=median_lifetime_days,
        median_lifetime_revisions=median_lifetime_revisions,
        avg_groups_per_revision=avg_groups_per_revision,
        max_groups_per_revision=max_groups_per_revision,
        min_groups_per_revision=min_groups_per_revision,
    )


def get_state_distribution(df: pd.DataFrame, state_col: str = "state") -> pd.DataFrame:
    """Get state distribution with counts and percentages.

    Args:
        df: DataFrame with tracking results
        state_col: Column name for state

    Returns:
        DataFrame with state, count, and percentage columns
    """
    if df.empty:
        return pd.DataFrame(columns=["state", "count", "percentage"])

    counts = df[state_col].value_counts()
    percentages = (counts / len(df) * 100).round(2)

    return pd.DataFrame(
        {"state": counts.index, "count": counts.values, "percentage": percentages.values}
    )


def get_lifetime_distribution(
    df: pd.DataFrame, bins: int = 10, column: str = "lifetime_days"
) -> pd.DataFrame:
    """Get lifetime distribution histogram.

    Args:
        df: DataFrame with tracking results
        bins: Number of bins for histogram
        column: Column name for lifetime (lifetime_days or lifetime_revisions)

    Returns:
        DataFrame with bin ranges and counts
    """
    if df.empty or column not in df.columns:
        return pd.DataFrame(columns=["bin", "count"])

    # Use unique methods/groups for lifetime distribution
    id_col = "block_id" if "block_id" in df.columns else "group_id"
    unique_df = df.drop_duplicates(subset=[id_col], keep="first")

    counts, bin_edges = pd.cut(unique_df[column], bins=bins, retbins=True, include_lowest=True)
    dist = counts.value_counts().sort_index()

    # Format bin labels
    bin_labels = [f"{int(edge)}-{int(bin_edges[i + 1])}" for i, edge in enumerate(bin_edges[:-1])]

    return pd.DataFrame({"bin": bin_labels, "count": dist.values})


def get_revision_timeline(df: pd.DataFrame, metric: str = "count") -> pd.DataFrame:
    """Get timeline of metrics per revision.

    Args:
        df: DataFrame with tracking results
        metric: Metric to calculate ('count', 'avg_clone_count', 'avg_group_size')

    Returns:
        DataFrame with revision and metric columns
    """
    if df.empty:
        return pd.DataFrame(columns=["revision", metric])

    grouped = df.groupby("revision")

    if metric == "count":
        values = grouped.size()
    elif metric == "avg_clone_count" and "clone_count" in df.columns:
        values = grouped["clone_count"].mean()
    elif metric == "avg_group_size" and "member_count" in df.columns:
        values = grouped["member_count"].mean()
    else:
        raise ValueError(f"Unknown metric: {metric}")

    return pd.DataFrame({"revision": values.index, metric: values.values})
