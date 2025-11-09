"""Clone group detection using UnionFind."""

from dataclasses import dataclass

import pandas as pd

from b4_thesis.analysis.union_find import UnionFind


@dataclass
class CloneGroup:
    """A group of cloned methods."""

    group_id: str  # Root block_id
    members: list[str]  # Block IDs
    similarities: dict[tuple[str, str], int]  # Pair similarities

    @property
    def size(self) -> int:
        """Number of members in the group."""
        return len(self.members)

    @property
    def avg_similarity(self) -> float | None:
        """Average similarity of all pairs."""
        if not self.similarities:
            return None
        return sum(self.similarities.values()) / len(self.similarities)

    @property
    def min_similarity(self) -> int | None:
        """Minimum similarity among pairs."""
        if not self.similarities:
            return None
        return min(self.similarities.values())

    @property
    def max_similarity(self) -> int | None:
        """Maximum similarity among pairs."""
        if not self.similarities:
            return None
        return max(self.similarities.values())

    @property
    def density(self) -> float:
        """Graph density: actual_edges / possible_edges."""
        if self.size <= 1:
            return 0.0
        possible_edges = self.size * (self.size - 1) // 2
        actual_edges = len(self.similarities)
        return actual_edges / possible_edges

    @property
    def is_clone(self) -> bool:
        """True if group has 2+ members."""
        return self.size >= 2


class GroupDetector:
    """Detects clone groups within a single revision using UnionFind."""

    def __init__(self, similarity_threshold: int = 70) -> None:
        """
        Initialize with similarity threshold for group formation.

        Args:
            similarity_threshold: Minimum similarity to form a clone group (0-100)
        """
        self.similarity_threshold = similarity_threshold

    def detect_groups(
        self, code_blocks: pd.DataFrame, clone_pairs: pd.DataFrame
    ) -> dict[str, CloneGroup]:
        """
        Detect clone groups in a revision.

        Args:
            code_blocks: DataFrame with code block information (column 0 = block_id)
            clone_pairs: DataFrame with clone pairs (columns: block_id_1, block_id_2,
                        ngram_similarity, lcs_similarity)

        Returns:
            Dictionary mapping group_id -> CloneGroup
        """
        # Initialize UnionFind with all block IDs
        uf = UnionFind()
        # Support both integer and string column names
        block_id_col = "block_id" if "block_id" in code_blocks.columns else 0
        block_ids = code_blocks[block_id_col].tolist()

        # Track similarities between pairs
        pair_similarities: dict[tuple[str, str], int] = {}

        # Support both integer and string column names for clone_pairs
        id1_col = "block_id_1" if "block_id_1" in clone_pairs.columns else 0
        id2_col = "block_id_2" if "block_id_2" in clone_pairs.columns else 1

        # Process clone pairs
        for _, row in clone_pairs.iterrows():
            block_id_1 = row[id1_col]
            block_id_2 = row[id2_col]

            # Get effective similarity
            similarity = self._get_effective_similarity(row)

            # If similarity meets threshold, union the blocks
            if similarity >= self.similarity_threshold:
                uf.union(block_id_1, block_id_2)

                # Store similarity (normalize pair order)
                pair_key = tuple(sorted([block_id_1, block_id_2]))
                pair_similarities[pair_key] = similarity

        # Get groups from UnionFind
        uf_groups = uf.get_groups()

        # Convert to CloneGroup objects
        result: dict[str, CloneGroup] = {}

        # First, add all groups found by UnionFind
        for root, members in uf_groups.items():
            # Get similarities for pairs in this group
            group_similarities: dict[tuple[str, str], int] = {}
            for i, block_1 in enumerate(members):
                for block_2 in members[i + 1 :]:
                    pair_key = tuple(sorted([block_1, block_2]))
                    if pair_key in pair_similarities:
                        group_similarities[pair_key] = pair_similarities[pair_key]

            result[root] = CloneGroup(
                group_id=root, members=sorted(members), similarities=group_similarities
            )

        # Add isolated blocks (blocks not in any clone pair)
        for block_id in block_ids:
            # If block_id is not in UnionFind, it's isolated
            if block_id not in uf.parent:
                result[block_id] = CloneGroup(
                    group_id=block_id, members=[block_id], similarities={}
                )

        return result

    def _get_effective_similarity(self, pair_row: pd.Series) -> int:
        """
        Get effective similarity from clone_pairs row.

        Args:
            pair_row: Row from clone_pairs DataFrame

        Returns:
            Effective similarity (ngram if >= threshold, otherwise LCS)
        """
        # Support both integer and string column names
        ngram_col = "ngram_similarity" if "ngram_similarity" in pair_row.index else 2
        lcs_col = "lcs_similarity" if "lcs_similarity" in pair_row.index else 3

        ngram_similarity = pair_row[ngram_col]

        # If N-gram >= threshold, use N-gram
        if ngram_similarity >= self.similarity_threshold:
            return int(ngram_similarity)

        # Otherwise, use LCS similarity
        lcs_similarity = pair_row[lcs_col]

        # Handle empty LCS values
        if pd.isna(lcs_similarity) or lcs_similarity == "":
            return int(ngram_similarity)

        return int(lcs_similarity)
