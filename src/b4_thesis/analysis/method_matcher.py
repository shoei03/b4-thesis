"""Method matching between revisions for code clone tracking.

This module provides functionality to match methods (code blocks) across
different revisions using a 2-phase approach:
1. Fast token_hash-based exact matching
2. Similarity-based fuzzy matching for remaining blocks
"""

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

import pandas as pd

from b4_thesis.analysis.similarity import calculate_similarity


def _compute_similarity_for_pair(
    args: tuple[str, str, str, str, int],
) -> tuple[str, str, int] | None:
    """Compute similarity for a source-target pair (helper for parallel processing).

    Args:
        args: Tuple of (block_id_source, token_seq_source, block_id_target,
              token_seq_target, similarity_threshold)

    Returns:
        Tuple of (block_id_source, block_id_target, similarity) if similarity >= threshold,
        None otherwise.
    """
    block_id_source, token_seq_source, block_id_target, token_seq_target, threshold = args

    try:
        similarity = calculate_similarity(token_seq_source, token_seq_target)
    except ValueError:
        # Skip if token sequences are invalid
        return None

    if similarity >= threshold:
        return (block_id_source, block_id_target, similarity)
    return None


@dataclass
class MatchResult:
    """Result of method matching between two revisions.

    Attributes:
        forward_matches: Mapping from source block_id to target block_id
        backward_matches: Mapping from target block_id to source block_id
        match_types: Type of match for each block_id ('token_hash', 'similarity', or 'none')
        match_similarities: Similarity score for each match (0-100)
    """

    forward_matches: dict[str, str]
    backward_matches: dict[str, str]
    match_types: dict[str, str]
    match_similarities: dict[str, int]


class MethodMatcher:
    """Matches methods across revisions using token hash and similarity.

    This class implements a 2-phase matching strategy:
    Phase 1: Fast token_hash-based exact matching (O(n))
    Phase 2: Similarity-based fuzzy matching for unmatched blocks (O(m × k × s))
    """

    def __init__(self, similarity_threshold: int = 70) -> None:
        """Initialize MethodMatcher.

        Args:
            similarity_threshold: Minimum similarity score (0-100) for fuzzy matching.
                                Default is 70.
        """
        self.similarity_threshold = similarity_threshold

    def match_blocks(
        self,
        source_blocks: pd.DataFrame,
        target_blocks: pd.DataFrame,
        parallel: bool = False,
        max_workers: int | None = None,
    ) -> MatchResult:
        """Match code blocks from source revision to target revision.

        Args:
            source_blocks: DataFrame with columns [block_id, token_hash, token_sequence, ...]
            target_blocks: DataFrame with columns [block_id, token_hash, token_sequence, ...]
            parallel: If True, use parallel processing for similarity calculation (default: False)
            max_workers: Maximum number of worker processes for parallel processing.
                        If None, defaults to number of CPU cores.

        Returns:
            MatchResult containing forward matches, backward matches, types, and similarities.
        """
        forward_matches = {}
        match_types = {}
        match_similarities = {}

        # Phase 1: token_hash-based fast matching
        token_hash_index = target_blocks.set_index("token_hash")["block_id"].to_dict()

        for _, row in source_blocks.iterrows():
            block_id_source = row["block_id"]
            token_hash_source = row["token_hash"]

            if token_hash_source in token_hash_index:
                # Exact match found via token_hash
                block_id_target = token_hash_index[token_hash_source]
                forward_matches[block_id_source] = block_id_target
                match_types[block_id_source] = "token_hash"
                match_similarities[block_id_source] = 100

        # Phase 2: similarity-based matching for unmatched blocks
        unmatched_source = source_blocks[~source_blocks["block_id"].isin(forward_matches.keys())]
        matched_target_ids = set(forward_matches.values())
        unmatched_target = target_blocks[~target_blocks["block_id"].isin(matched_target_ids)]

        if parallel:
            # Parallel processing version
            self._match_similarity_parallel(
                unmatched_source,
                unmatched_target,
                forward_matches,
                match_types,
                match_similarities,
                max_workers,
            )
        else:
            # Sequential processing version (original implementation)
            self._match_similarity_sequential(
                unmatched_source,
                unmatched_target,
                forward_matches,
                match_types,
                match_similarities,
            )

        # Create backward matches (reverse mapping)
        backward_matches = {v: k for k, v in forward_matches.items()}

        return MatchResult(
            forward_matches=forward_matches,
            backward_matches=backward_matches,
            match_types=match_types,
            match_similarities=match_similarities,
        )

    def bidirectional_match(
        self, blocks_old: pd.DataFrame, blocks_new: pd.DataFrame
    ) -> tuple[MatchResult, MatchResult]:
        """Perform bidirectional matching between two revisions.

        Args:
            blocks_old: DataFrame for older revision
            blocks_new: DataFrame for newer revision

        Returns:
            Tuple of (old_to_new_matches, new_to_old_matches)
        """
        # Match old → new
        old_to_new = self.match_blocks(blocks_old, blocks_new)

        # Match new → old
        new_to_old = self.match_blocks(blocks_new, blocks_old)

        return old_to_new, new_to_old

    def _match_similarity_sequential(
        self,
        unmatched_source: pd.DataFrame,
        unmatched_target: pd.DataFrame,
        forward_matches: dict[str, str],
        match_types: dict[str, str],
        match_similarities: dict[str, int],
    ) -> None:
        """Sequential similarity-based matching (original implementation).

        Args:
            unmatched_source: Unmatched source blocks
            unmatched_target: Unmatched target blocks
            forward_matches: Dict to update with matches
            match_types: Dict to update with match types
            match_similarities: Dict to update with similarities
        """
        for _, source_row in unmatched_source.iterrows():
            block_id_source = source_row["block_id"]
            token_seq_source = source_row["token_sequence"]

            candidates = []

            for _, target_row in unmatched_target.iterrows():
                block_id_target = target_row["block_id"]
                token_seq_target = target_row["token_sequence"]

                # Calculate similarity dynamically
                try:
                    similarity = calculate_similarity(token_seq_source, token_seq_target)
                except ValueError:
                    # Skip if token sequences are invalid
                    continue

                if similarity >= self.similarity_threshold:
                    candidates.append((block_id_target, similarity))

            if candidates:
                # Select the best match (highest similarity)
                best_match_id, best_similarity = max(candidates, key=lambda x: x[1])
                forward_matches[block_id_source] = best_match_id
                match_types[block_id_source] = "similarity"
                match_similarities[block_id_source] = best_similarity

                # Remove matched target from unmatched pool to prevent double matching
                unmatched_target = unmatched_target[unmatched_target["block_id"] != best_match_id]

    def _match_similarity_parallel(
        self,
        unmatched_source: pd.DataFrame,
        unmatched_target: pd.DataFrame,
        forward_matches: dict[str, str],
        match_types: dict[str, str],
        match_similarities: dict[str, int],
        max_workers: int | None = None,
    ) -> None:
        """Parallel similarity-based matching using ProcessPoolExecutor.

        Args:
            unmatched_source: Unmatched source blocks
            unmatched_target: Unmatched target blocks
            forward_matches: Dict to update with matches
            match_types: Dict to update with match types
            match_similarities: Dict to update with similarities
            max_workers: Maximum number of worker processes
        """
        # Prepare all source-target pairs for parallel computation
        pairs_to_compute: list[tuple[str, str, str, str, int]] = []

        for _, source_row in unmatched_source.iterrows():
            block_id_source = source_row["block_id"]
            token_seq_source = source_row["token_sequence"]

            for _, target_row in unmatched_target.iterrows():
                block_id_target = target_row["block_id"]
                token_seq_target = target_row["token_sequence"]

                pairs_to_compute.append(
                    (
                        block_id_source,
                        token_seq_source,
                        block_id_target,
                        token_seq_target,
                        self.similarity_threshold,
                    )
                )

        # Compute similarities in parallel
        results: dict[str, list[tuple[str, int]]] = {}

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            for result in executor.map(_compute_similarity_for_pair, pairs_to_compute):
                if result is not None:
                    block_id_source, block_id_target, similarity = result
                    if block_id_source not in results:
                        results[block_id_source] = []
                    results[block_id_source].append((block_id_target, similarity))

        # Select best matches and prevent double matching
        matched_targets = set()

        for block_id_source in unmatched_source["block_id"]:
            if block_id_source in results:
                # Filter out already matched targets
                candidates = [
                    (target_id, sim)
                    for target_id, sim in results[block_id_source]
                    if target_id not in matched_targets
                ]

                if candidates:
                    # Select the best match (highest similarity)
                    best_match_id, best_similarity = max(candidates, key=lambda x: x[1])
                    forward_matches[block_id_source] = best_match_id
                    match_types[block_id_source] = "similarity"
                    match_similarities[block_id_source] = best_similarity
                    matched_targets.add(best_match_id)
