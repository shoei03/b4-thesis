import pandas as pd


class MergeSplitsTracker:
    def __init__(self) -> None:
        pass

    def merge_splits(
        self, method_tracking_df: pd.DataFrame, verify_threshold: float = 0.7
    ) -> pd.DataFrame:
        import numpy as np

        # TODO: 行数ではなく，トークン数に変更する
        # LOC計算（ベクトル化された操作）
        prev_loc = method_tracking_df["prev_end_line"] - method_tracking_df["prev_start_line"] + 1
        curr_loc = method_tracking_df["curr_end_line"] - method_tracking_df["curr_start_line"] + 1

        # 条件計算（再利用のため事前計算）
        is_split = prev_loc * verify_threshold > curr_loc
        is_merged = prev_loc < curr_loc * verify_threshold

        # デフォルトはFalse、条件に応じてTrueを設定
        method_tracking_df["prev_loc"] = prev_loc
        method_tracking_df["curr_loc"] = curr_loc
        method_tracking_df["is_split"] = is_split
        method_tracking_df["is_merged"] = is_merged
        method_tracking_df["survived"] = ~is_split & ~is_merged

        return method_tracking_df
