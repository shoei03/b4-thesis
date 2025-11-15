"""Matching strategy implementations for Phase 2 similarity matching.

This module provides different matching strategies:
- LSH-based matching (fast, approximate)
- Sequential matching (slower, exact)
- Parallel matching (fast, exact)
- Progressive threshold matching (Phase 5.3.3)
"""

from concurrent.futures import ProcessPoolExecutor

import pandas as pd

from b4_thesis.analysis.lsh_index import LSHIndex
from b4_thesis.analysis.matching.match_filters import (
    _cached_similarity,
    _compute_similarity_for_pair,
    _should_skip_by_jaccard,
    _should_skip_by_length,
)
from b4_thesis.analysis.similarity import parse_token_sequence


def _detect_match_type(
    source_file_path: str,
    source_function_name: str,
    target_file_path: str,
    target_function_name: str,
    base_type: str,
) -> str:
    """Detect match type based on file_path and function_name changes.

    Args:
        source_file_path: File path in source revision
        source_function_name: Function name in source revision
        target_file_path: File path in target revision
        target_function_name: Function name in target revision
        base_type: Base match type ("token_hash" or "similarity")

    Returns:
        Match type string:
        - For "token_hash": "token_hash", "moved", "renamed", "moved_and_renamed"
        - For "similarity": "similarity", "similarity_moved", "similarity_renamed",
                           "similarity_moved_and_renamed"
    """
    file_path_changed = source_file_path != target_file_path
    function_name_changed = source_function_name != target_function_name

    if not file_path_changed and not function_name_changed:
        # No move/rename detected
        return base_type

    # Determine the type of change
    if file_path_changed and function_name_changed:
        suffix = "moved_and_renamed"
    elif file_path_changed:
        suffix = "moved"
    else:  # function_name_changed
        suffix = "renamed"

    # Construct the match type string
    if base_type == "token_hash":
        return suffix
    else:  # base_type == "similarity"
        return f"similarity_{suffix}"


def _match_similarity_lsh(
    unmatched_source: pd.DataFrame,
    unmatched_target: pd.DataFrame,
    forward_matches: dict[str, str],
    match_types: dict[str, str],
    match_similarities: dict[str, int],
    signature_changes: dict[str, list[str]],
    lsh_threshold: float,
    lsh_num_perm: int,
    top_k: int,
    similarity_threshold: int,
    use_optimized_similarity: bool,
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
        signature_changes: Dict to update with signature changes
        lsh_threshold: LSH similarity threshold (0.0-1.0)
        lsh_num_perm: Number of LSH permutations
        top_k: Number of top candidates to consider
        similarity_threshold: Minimum similarity score (0-100)
        use_optimized_similarity: If True, use optimized similarity calculation
    """
    # Build LSH index from target blocks
    lsh_index = LSHIndex(threshold=lsh_threshold, num_perm=lsh_num_perm)

    # Create lookup dict for target blocks
    target_lookup = {}
    for _, row in unmatched_target.iterrows():
        block_id = row["block_id"]
        token_seq = row["token_sequence"]
        target_lookup[block_id] = {
            "token_sequence": token_seq,
            "file_path": row["file_path"],
            "function_name": row["function_name"],
        }

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
        candidate_ids = candidate_ids[:top_k]

        # Calculate similarity for candidates
        candidates = []

        for candidate_id in candidate_ids:
            target_data = target_lookup[candidate_id]
            token_seq_target = target_data["token_sequence"]

            # Phase 5.3.1 optimization: Pre-filters
            if _should_skip_by_length(token_seq_source, token_seq_target):
                continue

            if _should_skip_by_jaccard(token_seq_source, token_seq_target):
                continue

            # Calculate similarity with optimizations
            try:
                if use_optimized_similarity:
                    similarity = _cached_similarity(
                        token_seq_source, token_seq_target, use_optimized=True
                    )
                    # Optimized similarity returns None if below threshold
                    if similarity is None:
                        continue
                else:
                    similarity = _cached_similarity(token_seq_source, token_seq_target)
                    if similarity < similarity_threshold:
                        continue
            except ValueError:
                # Skip if token sequences are invalid
                continue

            candidates.append((candidate_id, similarity))

        if candidates:
            # Select the best match (highest similarity)
            best_match_id, best_similarity = max(candidates, key=lambda x: x[1])

            # Detect move/rename
            target_data = target_lookup[best_match_id]
            match_type = _detect_match_type(
                source_row["file_path"],
                source_row["function_name"],
                target_data["file_path"],
                target_data["function_name"],
                "similarity",
            )

            forward_matches[block_id_source] = best_match_id
            match_types[block_id_source] = match_type
            match_similarities[block_id_source] = best_similarity
            signature_changes[block_id_source] = []  # No sig change for Phase 2
            matched_targets.add(best_match_id)


def _match_similarity_sequential(
    unmatched_source: pd.DataFrame,
    unmatched_target: pd.DataFrame,
    forward_matches: dict[str, str],
    match_types: dict[str, str],
    match_similarities: dict[str, int],
    signature_changes: dict[str, list[str]],
    similarity_threshold: int,
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
        signature_changes: Dict to update with signature changes
        similarity_threshold: Minimum similarity score (0-100)
    """
    for _, source_row in unmatched_source.iterrows():
        block_id_source = source_row["block_id"]
        token_seq_source = source_row["token_sequence"]

        candidates = []
        target_data_map = {}  # Store target data for later move/rename detection

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

            if similarity >= similarity_threshold:
                candidates.append((block_id_target, similarity))
                # Store target data for move/rename detection
                target_data_map[block_id_target] = {
                    "file_path": target_row["file_path"],
                    "function_name": target_row["function_name"],
                }

        if candidates:
            # Select the best match (highest similarity)
            best_match_id, best_similarity = max(candidates, key=lambda x: x[1])

            # Detect move/rename
            target_data = target_data_map[best_match_id]
            match_type = _detect_match_type(
                source_row["file_path"],
                source_row["function_name"],
                target_data["file_path"],
                target_data["function_name"],
                "similarity",
            )

            forward_matches[block_id_source] = best_match_id
            match_types[block_id_source] = match_type
            match_similarities[block_id_source] = best_similarity
            signature_changes[block_id_source] = []  # No sig change for Phase 2

            # Remove matched target from unmatched pool to prevent double matching
            unmatched_target = unmatched_target[unmatched_target["block_id"] != best_match_id]


def _match_similarity_parallel(
    unmatched_source: pd.DataFrame,
    unmatched_target: pd.DataFrame,
    forward_matches: dict[str, str],
    match_types: dict[str, str],
    match_similarities: dict[str, int],
    signature_changes: dict[str, list[str]],
    similarity_threshold: int,
    max_workers: int | None = None,
) -> None:
    """Parallel similarity-based matching using ProcessPoolExecutor.

    Args:
        unmatched_source: Unmatched source blocks
        unmatched_target: Unmatched target blocks
        forward_matches: Dict to update with matches
        match_types: Dict to update with match types
        match_similarities: Dict to update with similarities
        signature_changes: Dict to update with signature changes
        similarity_threshold: Minimum similarity score (0-100)
        max_workers: Maximum number of worker processes
    """
    # Prepare all source-target pairs for parallel computation
    pairs_to_compute: list[tuple[str, str, str, str, int]] = []

    # Create lookup maps for move/rename detection
    source_data_map = {}
    target_data_map = {}

    for _, source_row in unmatched_source.iterrows():
        block_id_source = source_row["block_id"]
        token_seq_source = source_row["token_sequence"]
        source_data_map[block_id_source] = {
            "file_path": source_row["file_path"],
            "function_name": source_row["function_name"],
        }

        for _, target_row in unmatched_target.iterrows():
            block_id_target = target_row["block_id"]
            token_seq_target = target_row["token_sequence"]

            if block_id_target not in target_data_map:
                target_data_map[block_id_target] = {
                    "file_path": target_row["file_path"],
                    "function_name": target_row["function_name"],
                }

            pairs_to_compute.append(
                (
                    block_id_source,
                    token_seq_source,
                    block_id_target,
                    token_seq_target,
                    similarity_threshold,
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

                # Detect move/rename
                source_data = source_data_map[block_id_source]
                target_data = target_data_map[best_match_id]
                match_type = _detect_match_type(
                    source_data["file_path"],
                    source_data["function_name"],
                    target_data["file_path"],
                    target_data["function_name"],
                    "similarity",
                )

                forward_matches[block_id_source] = best_match_id
                match_types[block_id_source] = match_type
                match_similarities[block_id_source] = best_similarity
                signature_changes[block_id_source] = []  # No sig change for Phase 2
                matched_targets.add(best_match_id)


def _match_with_progressive_thresholds(
    source_blocks: pd.DataFrame,
    target_blocks: pd.DataFrame,
    forward_matches: dict[str, str],
    match_types: dict[str, str],
    match_similarities: dict[str, int],
    signature_changes: dict[str, list[str]],
    thresholds: list[int],
    parallel: bool,
    max_workers: int | None,
    auto_parallel: bool,
    parallel_threshold: int,
    use_lsh: bool,
    lsh_threshold: float,
    lsh_num_perm: int,
    top_k: int,
    similarity_threshold_original: int,
    use_optimized_similarity: bool,
) -> None:
    """Match blocks using progressive thresholds (Phase 5.3.3).

    This method tries multiple thresholds progressively from high to low.
    Higher thresholds are tried first to prioritize high-quality matches,
    then lower thresholds are used for remaining unmatched blocks.

    Args:
        source_blocks: Source blocks DataFrame
        target_blocks: Target blocks DataFrame
        forward_matches: Dict to update with matches
        match_types: Dict to update with match types
        match_similarities: Dict to update with similarities
        signature_changes: Dict to update with signature changes
        thresholds: List of thresholds in descending order (e.g., [90, 80, 70])
        parallel: If True, use parallel processing
        max_workers: Maximum number of worker processes
        auto_parallel: If True, automatically select parallel mode
        parallel_threshold: Threshold for auto-parallel selection
        use_lsh: If True, use LSH indexing
        lsh_threshold: LSH similarity threshold
        lsh_num_perm: Number of LSH permutations
        top_k: Number of top candidates to consider
        similarity_threshold_original: Original similarity threshold to restore after iteration
        use_optimized_similarity: If True, use optimized similarity calculation
    """
    for i, threshold in enumerate(thresholds):
        # Get unmatched blocks
        unmatched_source = source_blocks[~source_blocks["block_id"].isin(forward_matches.keys())]

        if len(unmatched_source) == 0:
            # All blocks matched, stop early
            break

        matched_target_ids = set(forward_matches.values())
        unmatched_target = target_blocks[~target_blocks["block_id"].isin(matched_target_ids)]

        if len(unmatched_target) == 0:
            # No more target blocks to match
            break

        # Phase 5.3.1: Smart parallel mode selection
        use_parallel = parallel
        if auto_parallel:
            num_pairs = len(unmatched_source) * len(unmatched_target)
            use_parallel = num_pairs > parallel_threshold

        # Perform matching with current threshold
        if use_lsh:
            # Use LSH index for candidate filtering
            _match_similarity_lsh(
                unmatched_source,
                unmatched_target,
                forward_matches,
                match_types,
                match_similarities,
                signature_changes,
                lsh_threshold,
                lsh_num_perm,
                top_k,
                threshold,  # Use current threshold
                use_optimized_similarity,
            )
        elif use_parallel:
            # Parallel processing version
            _match_similarity_parallel(
                unmatched_source,
                unmatched_target,
                forward_matches,
                match_types,
                match_similarities,
                signature_changes,
                threshold,  # Use current threshold
                max_workers,
            )
        else:
            # Sequential processing version
            _match_similarity_sequential(
                unmatched_source,
                unmatched_target,
                forward_matches,
                match_types,
                match_similarities,
                signature_changes,
                threshold,  # Use current threshold
            )
