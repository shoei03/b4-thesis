"""Method tracking across revisions."""

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from b4_thesis.analysis.group_detector import GroupDetector
from b4_thesis.analysis.matching import MatchingDefaults, MethodMatcher
from b4_thesis.analysis.state_classifier import StateClassifier
from b4_thesis.analysis.tracking import (
    LifetimeTracker,
    RevisionPairProcessor,
    calculate_avg_similarity_to_group,
    find_group_for_block,
)
from b4_thesis.core.revision_manager import RevisionManager


@dataclass
class MethodTrackingResult:
    """Result of method tracking analysis."""

    revision: str
    block_id: str
    function_name: str
    file_path: str
    start_line: int
    end_line: int
    loc: int
    state: str
    state_detail: str
    matched_block_id: str | None
    match_type: str
    match_similarity: int | None
    clone_count: int
    clone_group_id: str | None
    clone_group_size: int
    avg_similarity_to_group: int | None
    lifetime_revisions: int
    lifetime_days: int


class MethodTracker:
    """Tracks method evolution across revisions."""

    def __init__(
        self,
        data_dir: Path,
        similarity_threshold: int = MatchingDefaults.SIMILARITY_THRESHOLD,
        use_lsh: bool = False,
        lsh_threshold: float = MatchingDefaults.LSH_THRESHOLD,
        lsh_num_perm: int = MatchingDefaults.LSH_NUM_PERM,
        top_k: int = MatchingDefaults.TOP_K_CANDIDATES,
        use_optimized_similarity: bool = False,
        progressive_thresholds: list[int] | None = None,
    ) -> None:
        """
        Initialize method tracker.

        Args:
            data_dir: Directory containing revision subdirectories
            similarity_threshold: Similarity threshold for matching (0-100)
            use_lsh: Enable LSH indexing for candidate filtering (Phase 5.3.2)
            lsh_threshold: LSH similarity threshold 0.0-1.0 (Phase 5.3.2)
            lsh_num_perm: Number of LSH permutations (Phase 5.3.2)
            top_k: Number of top candidates to consider per source block (Phase 5.3.2)
            use_optimized_similarity: Use optimized similarity with banded LCS (Phase 5.3.2)
            progressive_thresholds: List of thresholds to try progressively (Phase 5.3.3)
                                   (e.g., [90, 80, 70]). If None, uses single threshold.
        """
        self.data_dir = data_dir
        self.similarity_threshold = similarity_threshold
        self.use_lsh = use_lsh
        self.lsh_threshold = lsh_threshold
        self.lsh_num_perm = lsh_num_perm
        self.top_k = top_k
        self.use_optimized_similarity = use_optimized_similarity
        self.progressive_thresholds = progressive_thresholds
        self.revision_manager = RevisionManager(data_dir)
        self.method_matcher = MethodMatcher(
            similarity_threshold=similarity_threshold,
            use_lsh=use_lsh,
            lsh_threshold=lsh_threshold,
            lsh_num_perm=lsh_num_perm,
            top_k=top_k,
            use_optimized_similarity=use_optimized_similarity,
            progressive_thresholds=progressive_thresholds,
        )
        self.group_detector = GroupDetector(similarity_threshold=similarity_threshold)
        self.state_classifier = StateClassifier()
        self.pair_processor = RevisionPairProcessor(
            revision_manager=self.revision_manager,
            method_matcher=self.method_matcher,
            group_detector=self.group_detector,
            state_classifier=self.state_classifier,
        )

        # Internal state for format conversion
        self._results_df: pd.DataFrame | None = None

    def track(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        parallel: bool = False,
        max_workers: int | None = None,
    ) -> pd.DataFrame:
        """
        Track methods across revisions.

        Args:
            start_date: Start date for filtering revisions
            end_date: End date for filtering revisions
            parallel: If True, use parallel processing for similarity calculation
            max_workers: Maximum number of worker processes (if parallel=True)

        Returns:
            DataFrame with method tracking results
        """
        revisions = self.revision_manager.get_revisions(start_date=start_date, end_date=end_date)

        if len(revisions) == 0:
            # Return empty DataFrame with correct columns
            return pd.DataFrame(
                columns=[
                    "revision",
                    "block_id",
                    "function_name",
                    "file_path",
                    "start_line",
                    "end_line",
                    "loc",
                    "state",
                    "state_detail",
                    "matched_block_id",
                    "match_type",
                    "match_similarity",
                    "clone_count",
                    "clone_group_id",
                    "clone_group_size",
                    "avg_similarity_to_group",
                    "lifetime_revisions",
                    "lifetime_days",
                ]
            )

        all_results: list[MethodTrackingResult] = []
        lifetime_tracker = LifetimeTracker()

        # Process first revision (all methods are "added")
        first_revision = revisions[0]
        code_blocks_first, clone_pairs_first = self.revision_manager.load_revision_data(
            first_revision
        )
        groups_first = self.group_detector.detect_groups(code_blocks_first, clone_pairs_first)

        for _, block_row in code_blocks_first.iterrows():
            block_id = block_row["block_id"]
            group = find_group_for_block(block_id, groups_first)

            # Calculate average similarity to group members
            avg_similarity = calculate_avg_similarity_to_group(block_id, group)

            result = MethodTrackingResult(
                revision=first_revision.revision_id,
                block_id=block_id,
                function_name=block_row["function_name"],
                file_path=block_row["file_path"],
                start_line=int(block_row["start_line"]),
                end_line=int(block_row["end_line"]),
                loc=int(block_row["end_line"]) - int(block_row["start_line"]) + 1,
                state="added",
                state_detail="added_isolated"
                if group is None
                else ("added_to_group" if group.size > 1 else "added_isolated"),
                matched_block_id=None,
                match_type="none",
                match_similarity=None,
                clone_count=group.size - 1 if group and group.is_clone else 0,
                clone_group_id=group.group_id if group and group.is_clone else None,
                clone_group_size=group.size if group else 1,
                avg_similarity_to_group=avg_similarity,
                lifetime_revisions=1,
                lifetime_days=0,
            )
            all_results.append(result)

            # Initialize lifetime tracking
            lifetime_tracker.initialize_block(block_id, first_revision.timestamp)

        # Process consecutive revision pairs
        for i in range(len(revisions) - 1):
            revision_old = revisions[i]
            revision_new = revisions[i + 1]

            pair_results = self.pair_processor.process_pair(
                revision_old,
                revision_new,
                lifetime_tracker,
                parallel=parallel,
                max_workers=max_workers,
            )
            all_results.extend(pair_results)

        # Convert to DataFrame
        df = pd.DataFrame([asdict(r) for r in all_results])
        df = df.sort_values(["revision", "clone_group_id", "state", "state_detail", "file_path"])
        # Store results for lineage format conversion
        self._results_df = df

        return df
