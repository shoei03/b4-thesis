from pathlib import Path

from b4_thesis.const.column import ColumnNames
from b4_thesis.core.track.cross_revision_matcher import CrossRevisionMatcher
from b4_thesis.utils.revision_manager import RevisionManager
import pandas as pd


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

        # 最初のリビジョンをロード
        prev_revision = revisions[0]
        prev_code_blocks = self.revision_manager.load_code_blocks(prev_revision)

        # 2番目以降のリビジョンを順にずらして処理
        for curr_revision in revisions[1:]:
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

            # 次のイテレーションの準備
            prev_revision = curr_revision
            prev_code_blocks = curr_code_blocks.drop(ColumnNames.REVISION_ID.value, axis=1)

        # Return empty DataFrame if no results
        if len(all_results) == 0:
            return pd.DataFrame()

        all_results_df = pd.DataFrame(all_results)
        method_tracking_with_merge_splits_df = self._merge_splits(
            all_results_df, verify_threshold=similarity_threshold
        )

        # Convert to DataFrame
        return method_tracking_with_merge_splits_df

    def _merge_splits(
        self, method_tracking_df: pd.DataFrame, verify_threshold: float = 0.7
    ) -> pd.DataFrame:
        import numpy as np

        # TODO: 行数ではなく，トークン数に変更する
        # LOC計算（ベクトル化された操作）
        prev_loc = (
            method_tracking_df[ColumnNames.PREV_END_LINE.value]
            - method_tracking_df[ColumnNames.PREV_START_LINE.value]
            + 1
        )
        curr_loc = (
            method_tracking_df[ColumnNames.CURR_END_LINE.value]
            - method_tracking_df[ColumnNames.CURR_START_LINE.value]
            + 1
        )

        # 条件計算（再利用のため事前計算）
        is_split = prev_loc * verify_threshold > curr_loc
        is_merged = prev_loc < curr_loc * verify_threshold

        # デフォルトはFalse、条件に応じてTrueを設定
        method_tracking_df[ColumnNames.PREV_LOC.value] = prev_loc
        method_tracking_df[ColumnNames.CURR_LOC.value] = curr_loc
        method_tracking_df[ColumnNames.IS_SPLIT.value] = is_split
        method_tracking_df[ColumnNames.IS_MERGED.value] = is_merged
        method_tracking_df[ColumnNames.IS_MODIFIED.value] = ~is_split & ~is_merged

        return method_tracking_df
