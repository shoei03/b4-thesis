from b4_thesis.const.column import ColumnNames
import pandas as pd


def merge_splits(
    method_tracking_df: pd.DataFrame, verify_threshold: float = 0.7
) -> pd.DataFrame:
    # マッチした行のマスクを作成
    is_matched = method_tracking_df[ColumnNames.IS_MATCHED.value] == True

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

    # matchedの行には計算値を設定、それ以外はFalse
    method_tracking_df[ColumnNames.PREV_LOC.value] = prev_loc
    method_tracking_df[ColumnNames.CURR_LOC.value] = curr_loc
    method_tracking_df[ColumnNames.IS_SPLIT.value] = is_split & is_matched
    method_tracking_df[ColumnNames.IS_MERGED.value] = is_merged & is_matched
    method_tracking_df[ColumnNames.IS_MODIFIED.value] = ~is_split & ~is_merged & is_matched

    return method_tracking_df
