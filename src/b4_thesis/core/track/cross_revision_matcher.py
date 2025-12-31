"""Cross-revision code block matching using NIL-based indexing.

This module adapts NILCloneDetector's 3-phase algorithm for matching code blocks
across different revisions, reducing complexity from O(N×M) to O((N+M)log(N+M)).
"""

import bisect
from collections import defaultdict

from b4_thesis.const.column import ColumnNames


class CrossRevisionMatcher:
    """Matches code blocks across revisions using NIL's 3-phase strategy.

    Adapts NILCloneDetector for cross-revision matching:
    1. Location Phase: Build inverted N-gram index from target revision
    2. Filtration Phase: Filter by N-gram overlap ratio
    3. Verification Phase: Verify with LCS-based similarity

    Complexity: O((N+M)×L×log(L)) vs O(N×M×L²) for brute force
    where N=source blocks, M=target blocks, L=avg sequence length.
    """

    def __init__(
        self,
        n_gram_size: int = 5,
        filter_threshold: float = 0.1,
        verify_threshold: float = 0.7,
    ):
        """Initialize cross-revision matcher.

        Args:
            n_gram_size: Size of N-grams for indexing (default: 5)
            filter_threshold: N-gram overlap threshold for filtration (default: 0.1)
            verify_threshold: LCS similarity threshold for verification (default: 0.7)
        """
        self.n_gram_size = n_gram_size
        self.filter_threshold = filter_threshold
        self.verify_threshold = verify_threshold

    def match_revisions_with_changes(
        self,
        source_blocks: list[dict],
        target_blocks: list[dict],
    ) -> list[dict]:
        """Match blocks and track deletions/additions.

        Returns:
            Single list of all blocks with boolean flags (is_matched, is_deleted, is_added)
        """

        # 空チェック
        if not source_blocks and not target_blocks:
            return []

        if not source_blocks:
            return [
                self._format_block(
                    target_block=block, is_matched=False, is_deleted=False, is_added=True
                )
                for block in target_blocks
            ]

        if not target_blocks:
            return [
                self._format_block(
                    source_block=block, is_matched=False, is_deleted=True, is_added=False
                )
                for block in source_blocks
            ]

        # Phase 1: Build inverted index
        print(f"Building N-gram index for {len(target_blocks)} target blocks...")
        inverted_index = self._build_target_index(target_blocks)

        # インデックスで追跡（軽量なデータ構造）
        matched_source_indices = set()
        matched_target_indices = set()
        match_pairs = []  # [(source_idx, target_idx, similarity), ...]

        # Phase 2-4: Match each source block
        print(f"Matching {len(source_blocks)} source blocks...")
        for source_idx, source_block in enumerate(source_blocks):
            # Location
            candidates = self._find_candidates_for_source(source_block, inverted_index)

            if not candidates:
                continue

            # Filtration
            qualified = self._filter_by_ngram_overlap(
                source_block[ColumnNames.TOKEN_SEQUENCE.value], candidates, target_blocks
            )

            # Verification
            verified_matches = self._verify_similarity(
                source_block[ColumnNames.TOKEN_SEQUENCE.value], qualified, target_blocks
            )

            # マッチがあればインデックスと類似度を記録
            if verified_matches:
                matched_source_indices.add(source_idx)

                for match in verified_matches:
                    target_idx = match["target_idx"]
                    matched_target_indices.add(target_idx)
                    match_pairs.append((source_idx, target_idx, match["similarity"]))

        # Build unified result list
        all_results = []

        # 1. Add matched pairs
        for src_idx, tgt_idx, similarity in match_pairs:
            all_results.append(
                self._format_block(
                    source_block=source_blocks[src_idx],
                    target_block=target_blocks[tgt_idx],
                    similarity=similarity,
                    is_matched=True,
                    is_deleted=False,
                    is_added=False,
                )
            )

        # 2. Add deleted blocks (source blocks with no match)
        for i in range(len(source_blocks)):
            if i not in matched_source_indices:
                all_results.append(
                    self._format_block(
                        source_block=source_blocks[i],
                        is_matched=False,
                        is_deleted=True,
                        is_added=False,
                    )
                )

        # 3. Add added blocks (target blocks with no match)
        for i in range(len(target_blocks)):
            if i not in matched_target_indices:
                all_results.append(
                    self._format_block(
                        target_block=target_blocks[i],
                        is_matched=False,
                        is_deleted=False,
                        is_added=True,
                    )
                )

        return all_results

    def _build_target_index(self, target_blocks: list[dict]) -> dict:
        """
        Constructs an inverted index from code blocks.
        Corresponds to Section 3.1 and Algorithm 1 (conceptually).
        """
        inverted_index = defaultdict(list)

        for idx, block in enumerate(target_blocks):
            token_seq = block[ColumnNames.TOKEN_SEQUENCE.value]
            ngrams = self._generate_ngrams(token_seq)

            for gram in ngrams:
                inverted_index[gram].append(idx)

        return inverted_index

    def _find_candidates_for_source(self, source_block: dict, inverted_index: dict) -> set[int]:
        """
        Location Phase: Collects clone candidates using the inverted index.
        [cite_start]Algorithm 1 Lines 3-12 [cite: 366-390].
        """
        candidates = set()
        source_ngrams = self._generate_ngrams(source_block[ColumnNames.TOKEN_SEQUENCE.value])

        for gram in source_ngrams:
            if gram in inverted_index:
                candidates.update(inverted_index[gram])

        return candidates

    def _filter_by_ngram_overlap(
        self, source_tokens: list[int], candidate_indices: set[int], target_blocks: list[dict]
    ) -> list[int]:
        """Filter candidates by N-gram overlap ratio.

        Args:
            source_tokens: Source token sequence
            candidate_indices: Candidate target block indices
            target_blocks: All target blocks

        Returns:
            List of qualified candidate indices
        """
        source_ngrams = self._generate_ngrams(source_tokens)
        source_ngram_count = len(source_ngrams)

        if source_ngram_count == 0:
            # No N-grams, all candidates qualify
            return list(candidate_indices)

        qualified = []

        for candidate_idx in candidate_indices:
            target_block = target_blocks[candidate_idx]
            target_ngrams = self._generate_ngrams(target_block[ColumnNames.TOKEN_SEQUENCE.value])

            # Calculate filtration_sim
            common_ngrams = len(source_ngrams.intersection(target_ngrams))
            denominator = min(source_ngram_count, len(target_ngrams))

            if denominator > 0:
                filtration_sim = common_ngrams / denominator
                if filtration_sim >= self.filter_threshold:
                    qualified.append(candidate_idx)

        return qualified

    def _verify_similarity(
        self, source_tokens: list[int], candidate_indices: list[int], target_blocks: list[dict]
    ) -> list[dict]:
        """Verify candidates by LCS similarity.

        Args:
            source_tokens: Source token sequence
            candidate_indices: Candidate target block indices
            target_blocks: All target blocks

        Returns:
            List of matches with similarity scores
            [{"target_idx": int, "similarity": float}, ...]
        """
        if not source_tokens:
            return []

        verified = []

        for candidate_idx in candidate_indices:
            target_block = target_blocks[candidate_idx]
            target_tokens = target_block[ColumnNames.TOKEN_SEQUENCE.value]

            if not target_tokens:
                continue

            # Compute LCS length using Hunt-Szymanski algorithm
            lcs_len = self._compute_lcs_hunt_szymanski(source_tokens, target_tokens)

            # Calculate verification_sim
            denominator = min(len(source_tokens), len(target_tokens))

            if denominator == 0:
                continue

            similarity = lcs_len / denominator

            if similarity >= self.verify_threshold:
                verified.append({"target_idx": candidate_idx, "similarity": round(similarity, 2)})

        return verified

    def _generate_ngrams(self, token_seq: list[int]) -> set[tuple]:
        """Generates a set of N-grams from a token sequence."""
        if len(token_seq) < self.n_gram_size:
            return set()
        return {
            tuple(token_seq[i : i + self.n_gram_size])
            for i in range(len(token_seq) - self.n_gram_size + 1)
        }

    def _compute_lcs_hunt_szymanski(self, seq1: list[int], seq2: list[int]) -> int:
        """
        Computes LCS length using the Hunt-Szymanski algorithm.
        [cite_start]Reduces time complexity to O((r + n) log n) [cite: 483-484].
        """
        # Map token to indices in seq1
        indexes = defaultdict(list)
        for i, token in enumerate(seq1):
            indexes[token].append(i)

        # Sort indices in descending order for LIS processing
        for token in indexes:
            indexes[token].reverse()

        # Find match indices in seq1 for tokens in seq2
        match_indices = []
        for token in seq2:
            if token in indexes:
                match_indices.extend(indexes[token])

        # Compute LIS (Longest Increasing Subsequence) on match_indices
        tails = []
        for idx in match_indices:
            pos = bisect.bisect_left(tails, idx)
            if pos < len(tails):
                tails[pos] = idx
            else:
                tails.append(idx)

        return len(tails)

    def _format_block(
        self,
        source_block: dict | None = None,
        target_block: dict | None = None,
        similarity: float | None = None,
        is_matched: bool = False,
        is_deleted: bool = False,
        is_added: bool = False,
    ) -> dict:
        """Format a block with consistent structure and boolean flags.

        Args:
            source_block: Source (previous) block, or None for added blocks
            target_block: Target (current) block, or None for deleted blocks
            similarity: Similarity score, or None for deleted/added blocks
            is_matched: True if this is a matched pair
            is_deleted: True if this block was deleted
            is_added: True if this block was added

        Returns:
            Formatted block dictionary with prev_*, curr_* fields and boolean flags
        """
        # Base field names and their corresponding prev_/curr_ column names
        FIELD_MAPPING = [
            (ColumnNames.REVISION_ID, ColumnNames.PREV_REVISION_ID, ColumnNames.CURR_REVISION_ID),
            (ColumnNames.TOKEN_HASH, ColumnNames.PREV_TOKEN_HASH, ColumnNames.CURR_TOKEN_HASH),
            (ColumnNames.FILE_PATH, ColumnNames.PREV_FILE_PATH, ColumnNames.CURR_FILE_PATH),
            (ColumnNames.METHOD_NAME, ColumnNames.PREV_METHOD_NAME, ColumnNames.CURR_METHOD_NAME),
            (ColumnNames.RETURN_TYPE, ColumnNames.PREV_RETURN_TYPE, ColumnNames.CURR_RETURN_TYPE),
            (ColumnNames.PARAMETERS, ColumnNames.PREV_PARAMETERS, ColumnNames.CURR_PARAMETERS),
            (ColumnNames.START_LINE, ColumnNames.PREV_START_LINE, ColumnNames.CURR_START_LINE),
            (ColumnNames.END_LINE, ColumnNames.PREV_END_LINE, ColumnNames.CURR_END_LINE),
        ]

        result = {
            ColumnNames.SIMILARITY.value: similarity,
            ColumnNames.IS_MATCHED.value: is_matched,
            ColumnNames.IS_DELETED.value: is_deleted,
            ColumnNames.IS_ADDED.value: is_added,
        }

        # Add prev_ and curr_ fields
        for base, prev, curr in FIELD_MAPPING:
            result[prev.value] = source_block[base.value] if source_block else None
            result[curr.value] = target_block[base.value] if target_block else None

        sorted_result = result.reindex(
            columns=[
                ColumnNames.PREV_REVISION_ID.value,
                ColumnNames.CURR_REVISION_ID.value,
                ColumnNames.PREV_FILE_PATH.value,
                ColumnNames.CURR_FILE_PATH.value,
                ColumnNames.PREV_METHOD_NAME.value,
                ColumnNames.CURR_METHOD_NAME.value,
                ColumnNames.PREV_RETURN_TYPE.value,
                ColumnNames.CURR_RETURN_TYPE.value,
                ColumnNames.PREV_PARAMETERS.value,
                ColumnNames.CURR_PARAMETERS.value,
                ColumnNames.PREV_START_LINE.value,
                ColumnNames.CURR_START_LINE.value,
                ColumnNames.PREV_END_LINE.value,
                ColumnNames.CURR_END_LINE.value,
                ColumnNames.SIMILARITY.value,
                ColumnNames.IS_ADDED.value,
                ColumnNames.IS_DELETED.value,
                ColumnNames.IS_MATCHED.value,
            ]
        )

        return sorted_result
