"""Data types for method matching results.

This module defines the core data structures used in method matching:
- MatchContext: Internal state during matching process
- MatchResult: Final matching results with forward/backward mappings
"""

from dataclasses import dataclass


@dataclass
class MatchContext:
    """Internal context for tracking matching state during processing.

    This class encapsulates the mutable state that gets updated during
    the matching process, reducing the number of parameters passed between methods.

    Attributes:
        forward_matches: Mapping from source block_id to target block_id
        match_types: Type of match for each block_id
        match_similarities: Similarity score for each match (0-100)
        signature_changes: List of signature changes for each match
    """

    forward_matches: dict[str, str]
    match_types: dict[str, str]
    match_similarities: dict[str, int]
    signature_changes: dict[str, list[str]]

    def to_match_result(self) -> "MatchResult":
        """Convert to MatchResult with backward matches computed.

        Returns:
            MatchResult with forward and backward matches.
        """
        backward_matches = {v: k for k, v in self.forward_matches.items()}
        return MatchResult(
            forward_matches=self.forward_matches,
            backward_matches=backward_matches,
            match_types=self.match_types,
            match_similarities=self.match_similarities,
            signature_changes=self.signature_changes,
        )


@dataclass
class MatchResult:
    """Result of method matching between two revisions.

    Attributes:
        forward_matches: Mapping from source block_id to target block_id
        backward_matches: Mapping from target block_id to source block_id
        match_types: Type of match for each block_id:
            - 'name_based': Matched by file_path + function_name (Phase 0)
            - 'token_hash': Matched by token_hash (Phase 1, no move/rename)
            - 'moved': Matched by token_hash, file_path changed (Phase 1)
            - 'renamed': Matched by token_hash, function_name changed (Phase 1)
            - 'moved_and_renamed': Matched by token_hash, both changed (Phase 1)
            - 'similarity': Matched by similarity (Phase 2, no move/rename)
            - 'similarity_moved': Matched by similarity, file_path changed (Phase 2)
            - 'similarity_renamed': Matched by similarity, function_name changed (Phase 2)
            - 'similarity_moved_and_renamed': Matched by similarity, both changed (Phase 2)
        match_similarities: Similarity score for each match (0-100)
        signature_changes: List of signature changes for each match:
            - ['parameters']: Parameters changed
            - ['return_type']: Return type changed
            - ['parameters', 'return_type']: Both changed
            - []: No signature changes
    """

    forward_matches: dict[str, str]
    backward_matches: dict[str, str]
    match_types: dict[str, str]
    match_similarities: dict[str, int]
    signature_changes: dict[str, list[str]]
