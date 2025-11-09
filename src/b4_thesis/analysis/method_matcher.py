"""Method matching between revisions for code clone tracking.

This module provides functionality to match methods (code blocks) across
different revisions using a 2-phase approach:
1. Fast token_hash-based exact matching
2. Similarity-based fuzzy matching for remaining blocks

Performance optimizations:
- Phase 5.3.1: Pre-filters, LRU cache, smart parallel mode
- Phase 5.3.2: LSH index, banded LCS, top-k filtering
"""

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from b4_thesis.analysis.lsh_index import LSHIndex
from b4_thesis.analysis.similarity import (
    calculate_similarity,
    calculate_similarity_optimized,
    parse_token_sequence,
)


def _should_skip_by_length(token_seq_1: str, token_seq_2: str, max_diff_ratio: float = 0.3) -> bool:
    """Check if two sequences should be skipped based on length difference.

    Args:
        token_seq_1: First token sequence string
        token_seq_2: Second token sequence string
        max_diff_ratio: Maximum allowed length difference ratio (default: 0.3 = 30%)

    Returns:
        True if length difference is too large and should skip, False otherwise.
    """
    try:
        tokens_1 = parse_token_sequence(token_seq_1)
        tokens_2 = parse_token_sequence(token_seq_2)
    except ValueError:
        # Invalid sequences should be skipped
        return True

    len_1, len_2 = len(tokens_1), len(tokens_2)
    if len_1 == 0 or len_2 == 0:
        return True

    # Calculate length difference ratio
    max_len = max(len_1, len_2)
    min_len = min(len_1, len_2)
    diff_ratio = (max_len - min_len) / max_len

    return diff_ratio > max_diff_ratio


def _calculate_jaccard(token_seq_1: str, token_seq_2: str) -> float:
    """Calculate Jaccard similarity between two token sequences.

    Args:
        token_seq_1: First token sequence string
        token_seq_2: Second token sequence string

    Returns:
        Jaccard similarity (0.0-1.0)
    """
    try:
        tokens_1 = parse_token_sequence(token_seq_1)
        tokens_2 = parse_token_sequence(token_seq_2)
    except ValueError:
        return 0.0

    set_1 = set(tokens_1)
    set_2 = set(tokens_2)

    if not set_1 or not set_2:
        return 0.0

    intersection = len(set_1 & set_2)
    union = len(set_1 | set_2)

    if union == 0:
        return 0.0

    return intersection / union


def _should_skip_by_jaccard(token_seq_1: str, token_seq_2: str, min_jaccard: float = 0.3) -> bool:
    """Check if two sequences should be skipped based on Jaccard similarity.

    Args:
        token_seq_1: First token sequence string
        token_seq_2: Second token sequence string
        min_jaccard: Minimum required Jaccard similarity (default: 0.3)

    Returns:
        True if Jaccard similarity is too low and should skip, False otherwise.
    """
    jaccard = _calculate_jaccard(token_seq_1, token_seq_2)
    return jaccard < min_jaccard


@lru_cache(maxsize=10000)
def _cached_similarity(
    token_seq_1: str, token_seq_2: str, use_optimized: bool = False
) -> int | None:
    """Calculate similarity with LRU caching.

    Args:
        token_seq_1: First token sequence string
        token_seq_2: Second token sequence string
        use_optimized: If True, use optimized similarity (Phase 5.3.2)

    Returns:
        Similarity score (0-100), or None if below threshold (optimized mode only)

    Raises:
        ValueError: If token sequences are invalid.
    """
    # Sort sequences to ensure cache hits for bidirectional matching
    seq_a, seq_b = sorted([token_seq_1, token_seq_2])

    if use_optimized:
        return calculate_similarity_optimized(seq_a, seq_b)
    else:
        return calculate_similarity(seq_a, seq_b)


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

    # Phase 5.3.1 optimization: Pre-filters
    if _should_skip_by_length(token_seq_source, token_seq_target):
        return None

    if _should_skip_by_jaccard(token_seq_source, token_seq_target):
        return None

    try:
        # Use cached similarity calculation
        similarity = _cached_similarity(token_seq_source, token_seq_target)
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
    Phase 2: Similarity-based fuzzy matching for unmatched blocks

    Phase 5.3.2 optimizations:
    - LSH indexing for candidate filtering (100x speedup)
    - Banded LCS with early termination (2x speedup)
    - Top-k candidate filtering (1.5-2x speedup)
    """

    def __init__(
        self,
        similarity_threshold: int = 70,
        use_lsh: bool = False,
        lsh_threshold: float = 0.7,
        lsh_num_perm: int = 128,
        top_k: int = 20,
        use_optimized_similarity: bool = False,
    ) -> None:
        """Initialize MethodMatcher.

        Args:
            similarity_threshold: Minimum similarity score (0-100) for fuzzy matching (default: 70).
            use_lsh: Enable LSH indexing for candidate filtering (default: False).
            lsh_threshold: LSH similarity threshold 0.0-1.0 (default: 0.7).
            lsh_num_perm: Number of LSH permutations (default: 128).
            top_k: Number of top candidates to consider per source block (default: 20).
            use_optimized_similarity: Use optimized similarity with banded LCS (default: False).
        """
        self.similarity_threshold = similarity_threshold
        self.use_lsh = use_lsh
        self.lsh_threshold = lsh_threshold
        self.lsh_num_perm = lsh_num_perm
        self.top_k = top_k
        self.use_optimized_similarity = use_optimized_similarity

    def match_blocks(
        self,
        source_blocks: pd.DataFrame,
        target_blocks: pd.DataFrame,
        parallel: bool = False,
        max_workers: int | None = None,
        auto_parallel: bool = True,
        parallel_threshold: int = 100000,
    ) -> MatchResult:
        """Match code blocks from source revision to target revision.

        Args:
            source_blocks: DataFrame with columns [block_id, token_hash, token_sequence, ...]
            target_blocks: DataFrame with columns [block_id, token_hash, token_sequence, ...]
            parallel: If True, use parallel processing for similarity calculation (default: False)
            max_workers: Maximum number of worker processes for parallel processing.
                        If None, defaults to number of CPU cores.
            auto_parallel: If True, automatically select parallel mode based on data size
                          (default: True). This overrides the 'parallel' parameter.
            parallel_threshold: Number of unmatched pairs above which parallel processing
                               is automatically enabled (default: 100000).

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

        # Phase 5.3.1: Smart parallel mode selection
        use_parallel = parallel
        if auto_parallel:
            num_pairs = len(unmatched_source) * len(unmatched_target)
            use_parallel = num_pairs > parallel_threshold

        # Phase 5.3.2: LSH-based matching
        if self.use_lsh:
            # Use LSH index for candidate filtering
            self._match_similarity_lsh(
                unmatched_source,
                unmatched_target,
                forward_matches,
                match_types,
                match_similarities,
            )
        elif use_parallel:
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
            # Sequential processing version
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

    def _match_similarity_lsh(
        self,
        unmatched_source: pd.DataFrame,
        unmatched_target: pd.DataFrame,
        forward_matches: dict[str, str],
        match_types: dict[str, str],
        match_similarities: dict[str, int],
    ) -> None:
        """LSH-based similarity matching with Phase 5.3.2 optimizations.

        Optimizations:
        - LSH indexing for candidate filtering (reduces candidates to 1-5%)
        - Top-k candidate filtering (only consider top-k candidates)
        - Banded LCS with early termination
        - Phase 5.3.1 optimizations (length/Jaccard pre-filters, LRU cache)

        Args:
            unmatched_source: Unmatched source blocks
            unmatched_target: Unmatched target blocks
            forward_matches: Dict to update with matches
            match_types: Dict to update with match types
            match_similarities: Dict to update with similarities
        """
        # Build LSH index from target blocks
        lsh_index = LSHIndex(threshold=self.lsh_threshold, num_perm=self.lsh_num_perm)

        # Create lookup dict for target blocks
        target_lookup = {}
        for _, row in unmatched_target.iterrows():
            block_id = row["block_id"]
            token_seq = row["token_sequence"]
            target_lookup[block_id] = token_seq

            # Add to LSH index
            try:
                tokens = parse_token_sequence(token_seq)
                lsh_index.add(block_id, tokens)
            except ValueError:
                # Skip invalid sequences
                continue

        # Query LSH index for each source block
        matched_targets = set()

        for _, source_row in unmatched_source.iterrows():
            block_id_source = source_row["block_id"]
            token_seq_source = source_row["token_sequence"]

            try:
                tokens_source = parse_token_sequence(token_seq_source)
            except ValueError:
                # Skip invalid sequences
                continue

            # Get candidates from LSH index
            candidate_ids = lsh_index.query(tokens_source)

            # Filter out already matched targets
            candidate_ids = [cid for cid in candidate_ids if cid not in matched_targets]

            # Apply top-k filtering
            candidate_ids = candidate_ids[: self.top_k]

            # Calculate similarity for candidates
            candidates = []

            for candidate_id in candidate_ids:
                token_seq_target = target_lookup[candidate_id]

                # Phase 5.3.1 optimization: Pre-filters
                if _should_skip_by_length(token_seq_source, token_seq_target):
                    continue

                if _should_skip_by_jaccard(token_seq_source, token_seq_target):
                    continue

                # Calculate similarity with optimizations
                try:
                    if self.use_optimized_similarity:
                        similarity = _cached_similarity(
                            token_seq_source, token_seq_target, use_optimized=True
                        )
                        # Optimized similarity returns None if below threshold
                        if similarity is None:
                            continue
                    else:
                        similarity = _cached_similarity(token_seq_source, token_seq_target)
                        if similarity < self.similarity_threshold:
                            continue
                except ValueError:
                    # Skip if token sequences are invalid
                    continue

                candidates.append((candidate_id, similarity))

            if candidates:
                # Select the best match (highest similarity)
                best_match_id, best_similarity = max(candidates, key=lambda x: x[1])
                forward_matches[block_id_source] = best_match_id
                match_types[block_id_source] = "similarity"
                match_similarities[block_id_source] = best_similarity
                matched_targets.add(best_match_id)

    def _match_similarity_sequential(
        self,
        unmatched_source: pd.DataFrame,
        unmatched_target: pd.DataFrame,
        forward_matches: dict[str, str],
        match_types: dict[str, str],
        match_similarities: dict[str, int],
    ) -> None:
        """Sequential similarity-based matching with Phase 5.3.1 optimizations.

        Optimizations:
        - Length-based pre-filter (skip if length diff > 30%)
        - Jaccard-based pre-filter (skip if Jaccard < 0.3)
        - LRU cache for similarity calculations

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

                # Phase 5.3.1 optimization: Pre-filters
                if _should_skip_by_length(token_seq_source, token_seq_target):
                    continue

                if _should_skip_by_jaccard(token_seq_source, token_seq_target):
                    continue

                # Calculate similarity with caching
                try:
                    similarity = _cached_similarity(token_seq_source, token_seq_target)
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
