"""Convert tracking data to different formats."""

from pathlib import Path

import click
import pandas as pd
from rich.console import Console

from b4_thesis.analysis.union_find import UnionFind

console = Console()


@click.group()
def convert():
    """Convert tracking data to different formats."""
    pass


@convert.command()
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--lineage",
    is_flag=True,
    help="Convert to lineage format with unified global_block_id",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output file path (default: method_lineage.csv)",
)
def methods(input_file: Path, lineage: bool, output: Path | None) -> None:
    """
    Convert method tracking data to different formats.

    INPUT_FILE: Path to method_tracking.csv file

    Examples:
        b4-thesis convert methods ./output/method_tracking.csv --lineage -o result.csv
    """
    # Validate input
    if not lineage:
        console.print("[red]Error:[/red] No conversion option specified. Use --lineage")
        raise click.Abort()

    # Set default output path
    if output is None:
        output = Path("method_lineage.csv")

    # Read input CSV
    try:
        df = pd.read_csv(input_file)
    except Exception as e:
        console.print(f"[red]Error reading input file:[/red] {e}")
        raise click.Abort()

    # Validate required columns
    required_columns = ["revision", "block_id", "matched_block_id"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        console.print(f"[red]Error:[/red] Missing required columns: {', '.join(missing_columns)}")
        raise click.Abort()

    console.print(f"[bold blue]Converting:[/bold blue] {input_file}")
    console.print(f"[dim]Input rows:[/dim] {len(df)}")

    # Convert to lineage format
    lineage_df = _convert_to_lineage_format(df)

    # Save output
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        lineage_df.to_csv(output, index=False)
        console.print(f"[bold green]Saved:[/bold green] {output}")
        console.print(f"[dim]Output rows:[/dim] {len(lineage_df)}")
    except Exception as e:
        console.print(f"[red]Error writing output file:[/red] {e}")
        raise click.Abort()


def _convert_to_lineage_format(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert method tracking DataFrame to lineage format.

    Adds global_block_id column and removes block_id and matched_block_id columns.
    The global_block_id is unified across revisions based on matched_block_id relationships.

    Args:
        df: Input DataFrame with tracking data (must have revision, block_id, matched_block_id)

    Returns:
        DataFrame with lineage format (17 columns with global_block_id)
    """
    # Build global_block_id mapping using Union-Find
    global_block_id_map = _build_global_block_id_map(df)

    # Add global_block_id column using vectorized operations (much faster than apply)
    # Create list of keys using zip (vectorized)
    keys = list(zip(df["revision"], df["block_id"]))
    # Use list comprehension for fast dictionary lookup with fallback
    global_block_ids = [global_block_id_map.get(k, k[1]) for k in keys]

    # Create result DataFrame with only needed columns (avoid copying unnecessary data)
    # Define columns to keep (exclude block_id and matched_block_id)
    columns = ["revision", "function_name", "file_path"]
    columns.extend(
        [
            "start_line",
            "end_line",
            "loc",
            "state",
            "state_detail",
            "match_type",
            "match_similarity",
            "clone_count",
            "clone_group_id",
            "clone_group_size",
            "avg_similarity_to_group",
            "lifetime_revisions",
            "lifetime_days",
        ]
    )

    # Copy only needed columns and insert global_block_id at the beginning
    result_df = df[columns].copy()
    result_df.insert(0, "global_block_id", global_block_ids)

    return result_df


def _build_global_block_id_map(df: pd.DataFrame) -> dict[tuple[str, str], str]:
    """
    Build a mapping from (revision, block_id) to global_block_id.

    Uses Union-Find to track lineage relationships through matched_block_id.
    Optimized with pre-computed dictionaries for O(N) complexity instead of O(N²).

    Args:
        df: Input DataFrame with revision, block_id, matched_block_id columns

    Returns:
        Dictionary mapping (revision, block_id) to global_block_id
    """
    # Create Union-Find structure
    uf = UnionFind()

    # Helper function to encode (revision, block_id) as string
    def encode_key(revision: str, block_id: str) -> str:
        return f"{revision}::{block_id}"

    # Helper function to decode string back to (revision, block_id)
    def decode_key(key: str) -> tuple[str, str]:
        parts = key.split("::", 1)
        return (parts[0], parts[1])

    # Pre-compute revision order: O(R log R) where R is number of unique revisions
    # This avoids repeated DataFrame filtering (was O(N) per row)
    sorted_revisions = sorted(df["revision"].unique())
    revision_to_prev: dict[str, str | None] = {}
    for i, rev in enumerate(sorted_revisions):
        revision_to_prev[rev] = sorted_revisions[i - 1] if i > 0 else None

    # Pre-compute block existence: O(N) using vectorized pandas operations
    # This creates a set for fast O(1) lookup (was O(N) DataFrame scan per row)
    block_exists = set(zip(df["revision"], df["block_id"]))

    # Sort by revision to process chronologically
    sorted_df = df.sort_values("revision")

    # First pass: union matched blocks - now O(N) instead of O(N²)
    for _, row in sorted_df.iterrows():
        revision = row["revision"]
        block_id = row["block_id"]
        matched_block_id = row["matched_block_id"]

        current_key = encode_key(revision, block_id)

        # If matched_block_id is not null/empty, find previous revision's block
        if pd.notna(matched_block_id) and matched_block_id != "":
            # Get the immediately previous revision: O(1) dictionary lookup
            prev_revision = revision_to_prev.get(revision)

            if prev_revision is not None:
                # Check if the matched block exists in previous revision: O(1) set lookup
                if (prev_revision, matched_block_id) in block_exists:
                    # Union current block with matched block from previous revision
                    prev_key = encode_key(prev_revision, matched_block_id)
                    uf.union(current_key, prev_key)
        else:
            # Ensure the element is in the UnionFind structure even if not matched
            uf.find(current_key)

    # Second pass: assign global_block_id to each group
    # Use the block_id from the earliest revision in each group as the global_block_id
    global_block_id_map: dict[tuple[str, str], str] = {}

    # Get all groups
    groups = uf.get_groups()

    # For each group, find the earliest member and use its block_id as global_block_id
    for root, members in groups.items():
        # Decode all members
        decoded_members = [decode_key(member) for member in members]

        # Sort by revision to find the earliest
        decoded_members.sort(key=lambda x: x[0])

        # Use the block_id from the earliest member as global_block_id
        global_block_id = decoded_members[0][1]

        # Assign to all members in the group
        for member in decoded_members:
            global_block_id_map[member] = global_block_id

    return global_block_id_map
