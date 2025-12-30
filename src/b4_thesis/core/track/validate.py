from b4_thesis.const.column import ColumnNames
import pandas as pd


class ValidationError(Exception):
    """バリデーションエラー"""

    pass


REQUIRED_COLUMNS = [
    ColumnNames.TOKEN_HASH.value,
    ColumnNames.FILE_PATH.value,
    ColumnNames.START_LINE.value,
    ColumnNames.END_LINE.value,
    ColumnNames.METHOD_NAME.value,
    ColumnNames.RETURN_TYPE.value,
    ColumnNames.PARAMETERS.value,
    "commit_hash",
    ColumnNames.TOKEN_SEQUENCE.value,
]


def validate_code_block(code_block: pd.DataFrame) -> None:
    """
    code_block DataFrameのバリデーションを行う

    Args:
        code_block: code_blocks.csvから読み込んだDataFrame

    Raises:
        ValidationError: バリデーションに失敗した場合
    """
    errors: list[str] = []

    # 必須カラムの存在チェック
    missing_columns = set(REQUIRED_COLUMNS) - set(code_block.columns)
    if missing_columns:
        errors.append(f"必須カラムが不足しています: {missing_columns}")

    # token_hashの重複チェック
    if ColumnNames.TOKEN_HASH.value in code_block.columns:
        duplicates = code_block[code_block[ColumnNames.TOKEN_HASH.value].duplicated()]
        if not duplicates.empty:
            dup_ids = duplicates[ColumnNames.TOKEN_HASH.value].tolist()
            errors.append(f"{ColumnNames.TOKEN_HASH.value}に重複が{len(dup_ids)}件あります")

    # 必須カラムの欠損値チェック
    non_nullable_columns = [
        ColumnNames.TOKEN_HASH.value,
        ColumnNames.FILE_PATH.value,
        ColumnNames.START_LINE.value,
        ColumnNames.END_LINE.value,
        ColumnNames.METHOD_NAME.value,
    ]
    for col in non_nullable_columns:
        if col in code_block.columns:
            null_count = code_block[col].isna().sum()
            if null_count > 0:
                errors.append(f"カラム'{col}'に{null_count}件の欠損値があります")

    # データ型・値の妥当性チェック
    if (
        ColumnNames.START_LINE.value in code_block.columns
        and ColumnNames.END_LINE.value in code_block.columns
    ):
        invalid_lines = code_block[
            code_block[ColumnNames.START_LINE.value] > code_block[ColumnNames.END_LINE.value]
        ]
        if not invalid_lines.empty:
            errors.append(
                f"{ColumnNames.START_LINE.value} > {ColumnNames.END_LINE.value}の不正なデータが{len(invalid_lines)}件あります"
            )

    # 行番号の正数チェック
    for col in [ColumnNames.START_LINE.value, ColumnNames.END_LINE.value]:
        if col in code_block.columns:
            negative = code_block[code_block[col] <= 0]
            if not negative.empty:
                errors.append(f"カラム'{col}'に0以下の値が{len(negative)}件あります")

    if errors:
        raise ValidationError("\n".join(errors))


def validate_clone_pairs(clone_pairs: pd.DataFrame) -> None:
    """
    clone_pairs DataFrameのバリデーションを行う

    Args:
        clone_pairs: clone_pairs.csvから読み込んだDataFrame

    Raises:
        ValidationError: バリデーションに失敗した場合
    """
    errors: list[str] = []

    required_columns = [
        ColumnNames.TOKEN_HASH_1.value,
        ColumnNames.TOKEN_HASH_2.value,
        ColumnNames.NGRAM_OVERLAP.value,
        ColumnNames.VERIFY_SIMILARITY.value,
    ]
    missing_columns = set(required_columns) - set(clone_pairs.columns)
    if missing_columns:
        errors.append(f"必須カラムが不足しています: {missing_columns}")

    # block_id_1, block_id_2の欠損値チェック
    for col in [ColumnNames.TOKEN_HASH_1.value, ColumnNames.TOKEN_HASH_2.value]:
        if col in clone_pairs.columns:
            null_count = clone_pairs[col].isna().sum()
            if null_count > 0:
                errors.append(f"カラム'{col}'に{null_count}件の欠損値があります")

    # block_id_1とblock_id_2が同一のペアがないかチェック
    if (
        ColumnNames.TOKEN_HASH_1.value in clone_pairs.columns
        and ColumnNames.TOKEN_HASH_2.value in clone_pairs.columns
    ):
        self_pairs = clone_pairs[
            clone_pairs[ColumnNames.TOKEN_HASH_1.value]
            == clone_pairs[ColumnNames.TOKEN_HASH_2.value]
        ]
        if not self_pairs.empty:
            errors.append(
                f"{ColumnNames.TOKEN_HASH_1.value}と{ColumnNames.TOKEN_HASH_2.value}が同一のペアが{len(self_pairs)}件あります"
            )

    # {ColumnNames.NGRAM_OVERLAP.value}の範囲チェック (0-100)
    if ColumnNames.NGRAM_OVERLAP.value in clone_pairs.columns:
        invalid = clone_pairs[
            (clone_pairs[ColumnNames.NGRAM_OVERLAP.value] < 0)
            | (clone_pairs[ColumnNames.NGRAM_OVERLAP.value] > 100)
        ]
        if not invalid.empty:
            errors.append(
                f"{ColumnNames.NGRAM_OVERLAP.value}が0-100の範囲外のデータが{len(invalid)}件あります"
            )

    if errors:
        raise ValidationError("\n".join(errors))
