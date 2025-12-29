import pandas as pd


class ValidationError(Exception):
    """バリデーションエラー"""

    pass


REQUIRED_COLUMNS = [
    "block_id",
    "file_path",
    "start_line",
    "end_line",
    "function_name",
    "return_type",
    "parameters",
    "commit_hash",
    "token_sequence",
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

    # block_idの重複チェック
    if "block_id" in code_block.columns:
        duplicates = code_block[code_block["block_id"].duplicated()]
        if not duplicates.empty:
            dup_ids = duplicates["block_id"].tolist()
            errors.append(f"block_idに重複が{len(dup_ids)}件あります: {dup_ids[:5]}...")

    # 必須カラムの欠損値チェック
    non_nullable_columns = ["block_id", "file_path", "start_line", "end_line", "function_name"]
    for col in non_nullable_columns:
        if col in code_block.columns:
            null_count = code_block[col].isna().sum()
            if null_count > 0:
                errors.append(f"カラム'{col}'に{null_count}件の欠損値があります")

    # データ型・値の妥当性チェック
    if "start_line" in code_block.columns and "end_line" in code_block.columns:
        invalid_lines = code_block[code_block["start_line"] > code_block["end_line"]]
        if not invalid_lines.empty:
            errors.append(f"start_line > end_lineの不正なデータが{len(invalid_lines)}件あります")

    # 行番号の正数チェック
    for col in ["start_line", "end_line"]:
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

    required_columns = ["block_id_1", "block_id_2", "ngram_similarity", "lcs_similarity"]
    missing_columns = set(required_columns) - set(clone_pairs.columns)
    if missing_columns:
        errors.append(f"必須カラムが不足しています: {missing_columns}")

    # block_id_1, block_id_2の欠損値チェック
    for col in ["block_id_1", "block_id_2"]:
        if col in clone_pairs.columns:
            null_count = clone_pairs[col].isna().sum()
            if null_count > 0:
                errors.append(f"カラム'{col}'に{null_count}件の欠損値があります")

    # block_id_1とblock_id_2が同一のペアがないかチェック
    if "block_id_1" in clone_pairs.columns and "block_id_2" in clone_pairs.columns:
        self_pairs = clone_pairs[clone_pairs["block_id_1"] == clone_pairs["block_id_2"]]
        if not self_pairs.empty:
            errors.append(f"block_id_1とblock_id_2が同一のペアが{len(self_pairs)}件あります")

    # ngram_similarityの範囲チェック (0-100)
    if "ngram_similarity" in clone_pairs.columns:
        invalid = clone_pairs[
            (clone_pairs["ngram_similarity"] < 0) | (clone_pairs["ngram_similarity"] > 100)
        ]
        if not invalid.empty:
            errors.append(f"ngram_similarityが0-100の範囲外のデータが{len(invalid)}件あります")

    if errors:
        raise ValidationError("\n".join(errors))
