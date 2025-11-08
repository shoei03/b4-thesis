"""Method matching between revisions for code clone tracking.

This module provides functionality to match methods (code blocks) across
different revisions using a 2-phase approach:
1. Fast token_hash-based exact matching
2. Similarity-based fuzzy matching for remaining blocks
"""

from dataclasses import dataclass

import pandas as pd

from b4_thesis.analysis.similarity import calculate_similarity


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

    def match_blocks(self, source_blocks: pd.DataFrame, target_blocks: pd.DataFrame) -> MatchResult:
        """Match code blocks from source revision to target revision.

        Args:
            source_blocks: DataFrame with columns [block_id, token_hash, token_sequence, ...]
            target_blocks: DataFrame with columns [block_id, token_hash, token_sequence, ...]

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
