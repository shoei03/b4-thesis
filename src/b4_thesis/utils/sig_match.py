import pandas as pd
from rich.console import Console

from b4_thesis.const.column import ColumnNames

console = Console()


def pre_process(
    prev_code_blocks: pd.DataFrame, curr_code_blocks: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    prev_code_blocks = prev_code_blocks[
        [
            ColumnNames.REVISION_ID.value,
            ColumnNames.TOKEN_HASH.value,
            ColumnNames.FILE_PATH.value,
            ColumnNames.METHOD_NAME.value,
            ColumnNames.RETURN_TYPE.value,
            ColumnNames.PARAMETERS.value,
        ]
    ]
    curr_code_blocks = curr_code_blocks[
        [
            ColumnNames.REVISION_ID.value,
            ColumnNames.TOKEN_HASH.value,
            ColumnNames.FILE_PATH.value,
            ColumnNames.METHOD_NAME.value,
            ColumnNames.RETURN_TYPE.value,
            ColumnNames.PARAMETERS.value,
        ]
    ]

    prev_code_blocks = prev_code_blocks.add_prefix("prev_")
    curr_code_blocks = curr_code_blocks.add_prefix("curr_")

    return prev_code_blocks, curr_code_blocks


def apply_signature_matching(
    prev_code_blocks: pd.DataFrame, curr_code_blocks: pd.DataFrame
) -> pd.DataFrame:
    matched_df = prev_code_blocks.merge(
        curr_code_blocks,
        left_on=[
            ColumnNames.PREV_FILE_PATH.value,
            ColumnNames.PREV_METHOD_NAME.value,
            ColumnNames.PREV_RETURN_TYPE.value,
            ColumnNames.PREV_PARAMETERS.value,
        ],
        right_on=[
            ColumnNames.CURR_FILE_PATH.value,
            ColumnNames.CURR_METHOD_NAME.value,
            ColumnNames.CURR_RETURN_TYPE.value,
            ColumnNames.CURR_PARAMETERS.value,
        ],
        how="left",
    )

    matched_df["is_sig_matched"] = (
        matched_df[ColumnNames.PREV_FILE_PATH.value].notnull()
        & matched_df[ColumnNames.CURR_FILE_PATH.value].notnull()
    )
    matched_df["is_sig_deleted"] = matched_df[ColumnNames.CURR_FILE_PATH.value].isnull()
    matched_df["is_sig_added"] = matched_df[ColumnNames.PREV_FILE_PATH.value].isnull()

    return matched_df


def validate_counts(
    prev_code_blocks: pd.DataFrame, matched_df: pd.DataFrame, prev_rev_timestamp: str
) -> None:
    sig_matched_count = matched_df["is_sig_matched"].sum()
    sig_deleted_count = matched_df["is_sig_deleted"].sum()

    total_prev = len(prev_code_blocks)
    total_matched = sig_matched_count + sig_deleted_count

    if total_prev != total_matched:
        console.print(
            f"[red]Count mismatch for revision {prev_rev_timestamp}: "
            f"Total previous code blocks: {total_prev}, "
            f"Matched (sig matched + deleted): {total_matched} "
            f"(sig matched: {sig_matched_count}, sig deleted: {sig_deleted_count})[/red]"
        )
