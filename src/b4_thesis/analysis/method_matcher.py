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

from b4_thesis.analysis.match_filters import (
    _cached_similarity,
    _compute_similarity_for_pair,
    _should_skip_by_jaccard,
    _should_skip_by_length,
)
from b4_thesis.analysis.match_strategies import (
    _detect_match_type,
    _match_similarity_lsh,
    _match_similarity_parallel,
    _match_similarity_sequential,
    _match_with_progressive_thresholds,
)
from b4_thesis.analysis.match_types import MatchContext, MatchResult
from b4_thesis.analysis.matching_constants import (
    MatchingDefaults,
    ParallelConfig,
)

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
            _match_with_progressive_thresholds(
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
                self.use_lsh,
                self.lsh_threshold,
                self.lsh_num_perm,
                self.top_k,
                self.similarity_threshold,
                self.use_optimized_similarity,
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
                _match_similarity_lsh(
                    unmatched_source,
                    unmatched_target,
                    context.forward_matches,
                    context.match_types,
                    context.match_similarities,
                    context.signature_changes,
                    self.lsh_threshold,
                    self.lsh_num_perm,
                    self.top_k,
                    self.similarity_threshold,
                    self.use_optimized_similarity,
                )
            elif use_parallel:
                # Parallel processing version
                _match_similarity_parallel(
                    unmatched_source,
                    unmatched_target,
                    context.forward_matches,
                    context.match_types,
                    context.match_similarities,
                    context.signature_changes,
                    self.similarity_threshold,
                    max_workers,
                )
            else:
                # Sequential processing version
                _match_similarity_sequential(
                    unmatched_source,
                    unmatched_target,
                    context.forward_matches,
                    context.match_types,
                    context.match_similarities,
                    context.signature_changes,
                    self.similarity_threshold,
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

        This method is a wrapper around the standalone function for backward compatibility.

        Args:
            source_file_path: File path in source revision
            source_function_name: Function name in source revision
            target_file_path: File path in target revision
            target_function_name: Function name in target revision
            base_type: Base match type ("token_hash" or "similarity")

        Returns:
            Match type string
        """
        return _detect_match_type(
            source_file_path, source_function_name, target_file_path, target_function_name, base_type
        )
