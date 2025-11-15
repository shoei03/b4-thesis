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

import pandas as pd

from b4_thesis.analysis.lsh_index import LSHIndex
from b4_thesis.analysis.match_filters import (
    _cached_similarity,
    _compute_similarity_for_pair,
    _should_skip_by_jaccard,
    _should_skip_by_length,
)
from b4_thesis.analysis.match_types import MatchContext, MatchResult
from b4_thesis.analysis.matching_constants import (
    MatchingDefaults,
    ParallelConfig,
)
from b4_thesis.analysis.similarity import parse_token_sequence

# Re-export for backward compatibility
__all__ = ["MethodMatcher", "MatchResult", "MatchContext"]


class MethodMatcher:
    """Matches methods across revisions using name, token hash, and similarity.

    This class implements a 3-phase matching strategy:
    Phase 0: Name-based matching (file_path + function_name) - highest priority
             - Unconditionally matches methods with same file_path and function_name
             - Detects signature changes (parameters, return_type)
    Phase 1: Fast token_hash-based exact matching (O(n))
             - Detects moves (file_path changed) and renames (function_name changed)
    Phase 2: Similarity-based fuzzy matching for unmatched blocks
             - Detects moves and renames for similar methods

    Phase 5.3.2 optimizations:
    - LSH indexing for candidate filtering (100x speedup)
    - Banded LCS with early termination (2x speedup)
    - Top-k candidate filtering (1.5-2x speedup)
    """

    def __init__(
        self,
        similarity_threshold: int = MatchingDefaults.SIMILARITY_THRESHOLD,
        use_lsh: bool = False,
        lsh_threshold: float = MatchingDefaults.LSH_THRESHOLD,
        lsh_num_perm: int = MatchingDefaults.LSH_NUM_PERM,
        top_k: int = MatchingDefaults.TOP_K_CANDIDATES,
        use_optimized_similarity: bool = False,
        progressive_thresholds: list[int] | None = None,
    ) -> None:
        """Initialize MethodMatcher.

        Args:
            similarity_threshold: Minimum similarity score (0-100) for fuzzy matching.
            use_lsh: Enable LSH indexing for candidate filtering.
            lsh_threshold: LSH similarity threshold 0.0-1.0.
            lsh_num_perm: Number of LSH permutations.
            top_k: Number of top candidates to consider per source block.
            use_optimized_similarity: Use optimized similarity with banded LCS.
            progressive_thresholds: List of thresholds to try progressively
                                   (e.g., [90, 80, 70]). If None, uses single threshold.
                                   Higher thresholds are tried first.
        """
        self.similarity_threshold = similarity_threshold
        self.use_lsh = use_lsh
        self.lsh_threshold = lsh_threshold
        self.lsh_num_perm = lsh_num_perm
        self.top_k = top_k
        self.use_optimized_similarity = use_optimized_similarity
        self.progressive_thresholds = progressive_thresholds

    def match_blocks(
        self,
        source_blocks: pd.DataFrame,
        target_blocks: pd.DataFrame,
        parallel: bool = False,
        max_workers: int | None = None,
        auto_parallel: bool = True,
        parallel_threshold: int = ParallelConfig.AUTO_PARALLEL_THRESHOLD,
    ) -> MatchResult:
        """Match code blocks from source revision to target revision.

        This method orchestrates a 3-phase matching strategy:
        1. Phase 0: Name-based matching (file_path + function_name)
        2. Phase 1: Token hash-based exact matching
        3. Phase 2: Similarity-based fuzzy matching

        Args:
            source_blocks: DataFrame with columns [block_id, file_path, function_name,
                          parameters, return_type, token_hash, token_sequence, ...]
            target_blocks: DataFrame with columns [block_id, file_path, function_name,
                          parameters, return_type, token_hash, token_sequence, ...]
            parallel: If True, use parallel processing for similarity calculation (default: False)
            max_workers: Maximum number of worker processes for parallel processing.
                        If None, defaults to number of CPU cores.
            auto_parallel: If True, automatically select parallel mode based on data size.
                          This overrides the 'parallel' parameter.
            parallel_threshold: Number of unmatched pairs above which parallel processing
                               is automatically enabled.

        Returns:
            MatchResult containing forward matches, backward matches, types, similarities,
            and signature changes.
        """
        # Initialize matching context
        context = MatchContext(
            forward_matches={},
            match_types={},
            match_similarities={},
            signature_changes={},
        )

        # Phase 0: Name-based matching (highest priority)
        self._match_phase0_name_based(source_blocks, target_blocks, context)

        # Phase 1: Token hash-based fast matching
        self._match_phase1_token_hash(source_blocks, target_blocks, context)

        # Phase 2: Similarity-based matching for unmatched blocks
        self._match_phase2_similarity(
            source_blocks,
            target_blocks,
            context,
            parallel,
            max_workers,
            auto_parallel,
            parallel_threshold,
        )

        return context.to_match_result()

    def _match_phase0_name_based(
        self,
        source_blocks: pd.DataFrame,
        target_blocks: pd.DataFrame,
        context: MatchContext,
    ) -> None:
        """Phase 0: Name-based matching (file_path + function_name).

        Match methods with same file_path and function_name.
        This is the highest priority matching as it assumes methods
        that keep their location and name are the same method.

        Args:
            source_blocks: Source blocks DataFrame
            target_blocks: Target blocks DataFrame
            context: Matching context to update
        """
        name_index = self._build_name_index(target_blocks)

        for _, source_row in source_blocks.iterrows():
            self._try_match_by_name(source_row, name_index, context)

    def _build_name_index(self, blocks: pd.DataFrame) -> dict[tuple[str, str], dict]:
        """Build index mapping (file_path, function_name) to block metadata.

        Args:
            blocks: DataFrame containing block information

        Returns:
            Dictionary mapping (file_path, function_name) to block metadata
            containing block_id, parameters, and return_type.
            Only the first occurrence is indexed if duplicates exist.
        """
        index = {}
        for _, row in blocks.iterrows():
            key = (row["file_path"], row["function_name"])
            if key not in index:
                index[key] = {
                    "block_id": row["block_id"],
                    "parameters": row.get("parameters", ""),
                    "return_type": row.get("return_type", ""),
                }
        return index

    def _try_match_by_name(
        self,
        source_row: pd.Series,
        name_index: dict[tuple[str, str], dict],
        context: MatchContext,
    ) -> None:
        """Try to match a source block by name using the name index.

        Args:
            source_row: Source block row from DataFrame
            name_index: Pre-built name index
            context: Matching context to update
        """
        block_id_source = source_row["block_id"]
        key = (source_row["file_path"], source_row["function_name"])

        if key not in name_index:
            return

        target_data = name_index[key]
        block_id_target = target_data["block_id"]

        # Record the match
        context.forward_matches[block_id_source] = block_id_target
        context.match_types[block_id_source] = "name_based"
        context.match_similarities[block_id_source] = 100

        # Detect signature changes
        signature_changes = self._detect_signature_changes(source_row, target_data)
        context.signature_changes[block_id_source] = signature_changes

    def _detect_signature_changes(
        self, source_row: pd.Series, target_data: dict
    ) -> list[str]:
        """Detect changes in method signature between source and target.

        Args:
            source_row: Source block row
            target_data: Target block metadata

        Returns:
            List of changed signature components: 'parameters', 'return_type', or empty list
        """
        changes = []
        if source_row.get("parameters", "") != target_data["parameters"]:
            changes.append("parameters")
        if source_row.get("return_type", "") != target_data["return_type"]:
            changes.append("return_type")
        return changes

    def _match_phase1_token_hash(
        self,
        source_blocks: pd.DataFrame,
        target_blocks: pd.DataFrame,
        context: MatchContext,
    ) -> None:
        """Phase 1: Token hash-based fast matching.

        Match methods with identical token_hash (exact code match).
        Detects moves (file_path changed) and renames (function_name changed).

        Args:
            source_blocks: Source blocks DataFrame
            target_blocks: Target blocks DataFrame
            context: Matching context to update
        """
        # Build token_hash index
        token_hash_index = {}
        for _, row in target_blocks.iterrows():
            token_hash = row["token_hash"]
            if token_hash not in token_hash_index:
                token_hash_index[token_hash] = {
                    "block_id": row["block_id"],
                    "file_path": row["file_path"],
                    "function_name": row["function_name"],
                }

        for _, source_row in source_blocks.iterrows():
            block_id_source = source_row["block_id"]
            token_hash_source = source_row["token_hash"]

            # Skip if already matched in Phase 0
            if block_id_source in context.forward_matches:
                continue

            if token_hash_source in token_hash_index:
                # Exact match found via token_hash
                target_data = token_hash_index[token_hash_source]
                block_id_target = target_data["block_id"]

                # Skip if target already matched in Phase 0
                if block_id_target in set(context.forward_matches.values()):
                    continue

                # Detect move/rename using common method
                match_type = self._detect_match_type(
                    source_row["file_path"],
                    source_row["function_name"],
                    target_data["file_path"],
                    target_data["function_name"],
                    "token_hash",
                )

                context.forward_matches[block_id_source] = block_id_target
                context.match_types[block_id_source] = match_type
                context.match_similarities[block_id_source] = 100
                context.signature_changes[block_id_source] = []  # No sig change for Phase 1

    def _match_phase2_similarity(
        self,
        source_blocks: pd.DataFrame,
        target_blocks: pd.DataFrame,
        context: MatchContext,
        parallel: bool,
        max_workers: int | None,
        auto_parallel: bool,
        parallel_threshold: int,
    ) -> None:
        """Phase 2: Similarity-based matching for unmatched blocks.

        Uses fuzzy matching based on token sequence similarity for blocks
        that weren't matched in Phase 0 or Phase 1. Supports multiple strategies:
        - Progressive thresholds (try high thresholds first)
        - LSH indexing for candidate filtering
        - Sequential or parallel processing

        Args:
            source_blocks: Source blocks DataFrame
            target_blocks: Target blocks DataFrame
            context: Matching context to update
            parallel: If True, use parallel processing
            max_workers: Maximum number of worker processes
            auto_parallel: If True, automatically select parallel mode
            parallel_threshold: Threshold for auto-parallel selection
        """
        # Phase 5.3.3: Progressive thresholds
        if self.progressive_thresholds:
            # Use progressive thresholds (high to low)
            thresholds = sorted(self.progressive_thresholds, reverse=True)
            self._match_with_progressive_thresholds(
                source_blocks,
                target_blocks,
                context.forward_matches,
                context.match_types,
                context.match_similarities,
                context.signature_changes,
                thresholds,
                parallel,
                max_workers,
                auto_parallel,
                parallel_threshold,
            )
        else:
            # Single threshold matching
            unmatched_source = source_blocks[
                ~source_blocks["block_id"].isin(context.forward_matches.keys())
            ]
            matched_target_ids = set(context.forward_matches.values())
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
                    context.forward_matches,
                    context.match_types,
                    context.match_similarities,
                    context.signature_changes,
                )
            elif use_parallel:
                # Parallel processing version
                self._match_similarity_parallel(
                    unmatched_source,
                    unmatched_target,
                    context.forward_matches,
                    context.match_types,
                    context.match_similarities,
                    context.signature_changes,
                    max_workers,
                )
            else:
                # Sequential processing version
                self._match_similarity_sequential(
                    unmatched_source,
                    unmatched_target,
                    context.forward_matches,
                    context.match_types,
                    context.match_similarities,
                    context.signature_changes,
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

    def _detect_match_type(
        self,
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
        self,
        unmatched_source: pd.DataFrame,
        unmatched_target: pd.DataFrame,
        forward_matches: dict[str, str],
        match_types: dict[str, str],
        match_similarities: dict[str, int],
        signature_changes: dict[str, list[str]],
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
        """
        # Build LSH index from target blocks
        lsh_index = LSHIndex(threshold=self.lsh_threshold, num_perm=self.lsh_num_perm)

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
            candidate_ids = candidate_ids[: self.top_k]

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

                # Detect move/rename using common method
                target_data = target_lookup[best_match_id]
                match_type = self._detect_match_type(
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
        self,
        unmatched_source: pd.DataFrame,
        unmatched_target: pd.DataFrame,
        forward_matches: dict[str, str],
        match_types: dict[str, str],
        match_similarities: dict[str, int],
        signature_changes: dict[str, list[str]],
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

                if similarity >= self.similarity_threshold:
                    candidates.append((block_id_target, similarity))
                    # Store target data for move/rename detection
                    target_data_map[block_id_target] = {
                        "file_path": target_row["file_path"],
                        "function_name": target_row["function_name"],
                    }

            if candidates:
                # Select the best match (highest similarity)
                best_match_id, best_similarity = max(candidates, key=lambda x: x[1])

                # Detect move/rename using common method
                target_data = target_data_map[best_match_id]
                match_type = self._detect_match_type(
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
        self,
        unmatched_source: pd.DataFrame,
        unmatched_target: pd.DataFrame,
        forward_matches: dict[str, str],
        match_types: dict[str, str],
        match_similarities: dict[str, int],
        signature_changes: dict[str, list[str]],
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

                    # Detect move/rename using common method
                    source_data = source_data_map[block_id_source]
                    target_data = target_data_map[best_match_id]
                    match_type = self._detect_match_type(
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
        self,
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
        """
        for i, threshold in enumerate(thresholds):
            # Get unmatched blocks
            unmatched_source = source_blocks[
                ~source_blocks["block_id"].isin(forward_matches.keys())
            ]

            if len(unmatched_source) == 0:
                # All blocks matched, stop early
                break

            matched_target_ids = set(forward_matches.values())
            unmatched_target = target_blocks[~target_blocks["block_id"].isin(matched_target_ids)]

            if len(unmatched_target) == 0:
                # No more target blocks to match
                break

            # Temporarily set the threshold for this iteration
            original_threshold = self.similarity_threshold
            self.similarity_threshold = threshold

            # Phase 5.3.1: Smart parallel mode selection
            use_parallel = parallel
            if auto_parallel:
                num_pairs = len(unmatched_source) * len(unmatched_target)
                use_parallel = num_pairs > parallel_threshold

            # Perform matching with current threshold
            if self.use_lsh:
                # Use LSH index for candidate filtering
                self._match_similarity_lsh(
                    unmatched_source,
                    unmatched_target,
                    forward_matches,
                    match_types,
                    match_similarities,
                    signature_changes,
                )
            elif use_parallel:
                # Parallel processing version
                self._match_similarity_parallel(
                    unmatched_source,
                    unmatched_target,
                    forward_matches,
                    match_types,
                    match_similarities,
                    signature_changes,
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
                    signature_changes,
                )

            # Restore original threshold
            self.similarity_threshold = original_threshold
