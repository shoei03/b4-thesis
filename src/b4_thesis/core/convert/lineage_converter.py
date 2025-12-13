from dataclasses import dataclass

import pandas as pd
from rich.console import Console

from b4_thesis.analysis.union_find import UnionFind

console = Console()


@dataclass(frozen=True)
class BlockIdentifier:
    """Uniquely identifies a code block in a specific revision."""

    revision: str
    block_id: str

    def __str__(self) -> str:
        return f"{self.revision}::{self.block_id}"

    @classmethod
    def from_string(cls, s: str) -> "BlockIdentifier":
        """Parse string like 'rev1::block123' back to BlockIdentifier."""
        revision, block_id = s.split("::", 1)
        return cls(revision, block_id)


@dataclass
class TrackingRecord:
    """Represents a single method tracking record."""

    revision: str
    block_id: str
    matched_block_id: str | None

    @property
    def identifier(self) -> BlockIdentifier:
        return BlockIdentifier(self.revision, self.block_id)

    def has_match(self) -> bool:
        """Check if this record has a matched block in previous revision."""
        return self.matched_block_id is not None and self.matched_block_id != ""


# =============================================================================
# Lineage Builder
# =============================================================================


class LineageBuilder:
    """Builds method lineage relationships using Union-Find algorithm."""

    def __init__(self, records: list[TrackingRecord]):
        self.records = records
        self.union_find = UnionFind()
        self._revision_order = self._build_revision_order()
        self._existing_blocks = self._build_block_index()

    def _build_revision_order(self) -> dict[str, str | None]:
        """
        Create a mapping from each revision to its previous revision.

        Returns:
            Dictionary: {current_revision -> previous_revision or None}
        """
        unique_revisions = sorted(set(record.revision for record in self.records))

        revision_order = {}
        for i, revision in enumerate(unique_revisions):
            previous = unique_revisions[i - 1] if i > 0 else None
            revision_order[revision] = previous

        return revision_order

    def _build_block_index(self) -> set[BlockIdentifier]:
        """
        Create an index of all existing blocks for fast lookup.

        Returns:
            Set of all BlockIdentifiers in the dataset
        """
        return {record.identifier for record in self.records}

    def build_lineage_groups(self) -> dict[BlockIdentifier, str]:
        """
        Build lineage relationships and assign global IDs.

        Returns:
            Dictionary mapping each BlockIdentifier to its global_block_id
        """
        # Step 1: Connect related blocks using Union-Find
        self._connect_matched_blocks()

        # Step 2: Assign global IDs to each lineage group
        return self._assign_global_ids()

    def _connect_matched_blocks(self) -> None:
        """Connect blocks that match across revisions using Union-Find."""
        sorted_records = sorted(self.records, key=lambda r: r.revision)

        for record in sorted_records:
            current_id = str(record.identifier)

            # Register this block in Union-Find
            self.union_find.find(current_id)

            # If this block matches a previous one, connect them
            if record.has_match():
                previous_match = self._find_previous_match(record)
                if previous_match:
                    self.union_find.union(current_id, str(previous_match))

    def _find_previous_match(self, record: TrackingRecord) -> BlockIdentifier | None:
        """
        Find the matched block in the previous revision.

        Args:
            record: Current tracking record

        Returns:
            BlockIdentifier of the matched block, or None if not found
        """
        previous_revision = self._revision_order.get(record.revision)

        if previous_revision is None:
            return None

        matched_identifier = BlockIdentifier(previous_revision, record.matched_block_id)

        if matched_identifier in self._existing_blocks:
            return matched_identifier

        return None

    def _assign_global_ids(self) -> dict[BlockIdentifier, str]:
        """
        Assign a global_block_id to each lineage group.

        Uses the block_id from the earliest revision in each group.

        Returns:
            Dictionary mapping BlockIdentifier to global_block_id
        """
        global_id_map = {}
        groups = self.union_find.get_groups()

        for members in groups.values():
            lineage_group = _create_lineage_group(members)
            earliest_block_id = lineage_group.get_earliest_block_id()

            for identifier in lineage_group.members:
                global_id_map[identifier] = earliest_block_id

        return global_id_map


class LineageGroup:
    """Represents a group of related blocks across revisions."""

    def __init__(self, members: list[BlockIdentifier]):
        self.members = sorted(members, key=lambda x: x.revision)

    def get_earliest_block_id(self) -> str:
        """Get the block_id from the earliest revision."""
        return self.members[0].block_id


def _create_lineage_group(member_strings: list[str]) -> LineageGroup:
    """Helper function to create LineageGroup from string representations."""
    identifiers = [BlockIdentifier.from_string(s) for s in member_strings]
    return LineageGroup(identifiers)


class LineageConverter:
    """Converts tracking DataFrame to lineage format."""

    LINEAGE_COLUMNS = [
        "global_block_id",
        "revision",
        "function_name",
        "file_path",
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

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def convert(self) -> pd.DataFrame:
        """
        Convert tracking DataFrame to lineage format.

        Returns:
            DataFrame with global_block_id column
        """
        # Build lineage relationships
        records = self._extract_records()
        builder = LineageBuilder(records)
        global_id_map = builder.build_lineage_groups()

        # Add global_block_id column
        global_ids = self._map_global_ids(global_id_map)

        # Create result DataFrame with proper column order
        return self._create_result_dataframe(global_ids)

    def _extract_records(self) -> list[TrackingRecord]:
        """Extract TrackingRecord objects from DataFrame."""
        records = []

        for _, row in self.df.iterrows():
            record = TrackingRecord(
                revision=row["revision"],
                block_id=row["block_id"],
                matched_block_id=row["matched_block_id"]
                if pd.notna(row["matched_block_id"])
                else None,
            )
            records.append(record)

        return records

    def _map_global_ids(self, global_id_map: dict[BlockIdentifier, str]) -> list[str]:
        """
        Map each row to its global_block_id.

        Args:
            global_id_map: Mapping from BlockIdentifier to global_block_id

        Returns:
            List of global_block_ids corresponding to DataFrame rows
        """
        global_ids = []

        for _, row in self.df.iterrows():
            identifier = BlockIdentifier(row["revision"], row["block_id"])
            global_id = global_id_map.get(identifier, row["block_id"])
            global_ids.append(global_id)

        return global_ids

    def _create_result_dataframe(self, global_ids: list[str]) -> pd.DataFrame:
        """Create result DataFrame with proper columns."""
        result = self.df.copy()
        result.insert(0, "global_block_id", global_ids)

        # Keep only lineage columns
        available_columns = [col for col in self.LINEAGE_COLUMNS if col in result.columns]
        result = result[available_columns]

        # Check for duplicate rows (this should never happen with valid input)
        duplicates = result.duplicated(subset=["revision", "global_block_id"], keep=False)
        if duplicates.any():
            console.print("[yellow]⚠ Warning: Duplicate rows detected![/yellow]")
            duplicate_rows = result[duplicates]
            console.print(f"[yellow]Found {len(duplicate_rows)} duplicate entries[/yellow]")
            console.print(duplicate_rows[["revision", "global_block_id", "function_name"]])

        return result
