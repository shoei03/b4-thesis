from pathlib import Path

import pandas as pd

from b4_thesis.const.column import ColumnNames
from b4_thesis.core.track.cross_revision_matcher import CrossRevisionMatcher
from b4_thesis.utils.revision_manager import RevisionManager


class MethodTracker:
    def __init__(self) -> None:
        self.revision_manager = RevisionManager()

    def track(
        self,
        data_dir: Path,
        similarity_threshold: float = 0.7,
        n_gram_size: int = 5,
        filter_threshold: float = 0.1,
    ) -> pd.DataFrame:
        """Track methods across revisions.

        Returns:
            Single DataFrame with all tracking data and boolean flags
        """
        cross_revision_matcher = CrossRevisionMatcher(
            n_gram_size=n_gram_size,
            filter_threshold=filter_threshold,
            verify_threshold=similarity_threshold,
        )

        revisions = self.revision_manager.get_revisions(data_dir)

        # Collect all results
        all_results: list[dict] = []

        # Iterate through revision pairs
        for prev_revision, curr_revision in zip(revisions[:-1], revisions[1:]):
            prev_code_blocks = self.revision_manager.load_code_blocks(prev_revision)
            curr_code_blocks = self.revision_manager.load_code_blocks(curr_revision)

            prev_code_blocks[ColumnNames.REVISION_ID.value] = prev_revision.timestamp
            curr_code_blocks[ColumnNames.REVISION_ID.value] = curr_revision.timestamp

            # Convert DataFrames to list of dicts for NIL-based matching
            source_blocks = prev_code_blocks.to_dict("records")
            target_blocks = curr_code_blocks.to_dict("records")

            print(
                f"Revision {prev_revision.timestamp} -> {curr_revision.timestamp}: "
                f"{len(source_blocks)}×{len(target_blocks)} blocks to match"
            )

            # Use NIL-based cross-revision matching
            match_results = cross_revision_matcher.match_revisions_with_changes(
                source_blocks, target_blocks
            )

            # Accumulate results
            all_results.extend(match_results)

        # Convert to DataFrame
        return pd.DataFrame(all_results)
