from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
from rich.console import Console

from b4_thesis.const.column import ColumnNames
from b4_thesis.core.track.validate import validate_code_block

console = Console()


@dataclass(frozen=True, slots=True)
class RevisionInfo:
    timestamp: datetime
    directory: Path
    clone_pairs_path: Path
    code_blocks_path: Path


class RevisionManager:
    REQUIRED_FILES = ("clone_pairs.csv", "code_blocks.csv")

    def load_code_blocks(self, revision: RevisionInfo) -> pd.DataFrame:
        code_blocks = pd.read_csv(
            revision.code_blocks_path,
            header=None,
            names=[
                ColumnNames.TOKEN_HASH.value,
                ColumnNames.FILE_PATH.value,
                ColumnNames.START_LINE.value,
                ColumnNames.END_LINE.value,
                ColumnNames.METHOD_NAME.value,
                ColumnNames.RETURN_TYPE.value,
                ColumnNames.PARAMETERS.value,
                "commit_hash",
                ColumnNames.TOKEN_SEQUENCE.value,
            ],
            dtype={
                ColumnNames.TOKEN_HASH.value: "string",
                ColumnNames.FILE_PATH.value: "string",
                ColumnNames.START_LINE.value: "Int64",
                ColumnNames.END_LINE.value: "Int64",
                ColumnNames.METHOD_NAME.value: "string",
                ColumnNames.RETURN_TYPE.value: "string",
                ColumnNames.PARAMETERS.value: "string",
                "commit_hash": "string",
                ColumnNames.TOKEN_SEQUENCE.value: "string",
            },
        )

        code_blocks[ColumnNames.TOKEN_SEQUENCE.value] = (
            code_blocks[ColumnNames.TOKEN_SEQUENCE.value]
            .str[1:-1]
            .str.split(";")
            .apply(lambda x: [int(i) for i in x])
        ).astype("string")

        # 重複する関数定義があれば、関数名の末尾に番号を付与する
        dup_columns = [
            ColumnNames.FILE_PATH.value,
            ColumnNames.METHOD_NAME.value,
            ColumnNames.RETURN_TYPE.value,
            ColumnNames.PARAMETERS.value,
        ]
        # NaN を扱えるように fillna で一時的に置換してから groupby
        code_blocks["_dup_count"] = code_blocks.groupby(dup_columns, dropna=False).cumcount()
        code_blocks["_is_dup"] = code_blocks.duplicated(subset=dup_columns, keep=False)
        code_blocks[ColumnNames.METHOD_NAME.value] = code_blocks[
            ColumnNames.METHOD_NAME.value
        ].where(
            ~code_blocks["_is_dup"],
            code_blocks[ColumnNames.METHOD_NAME.value]
            + "_"
            + (code_blocks["_dup_count"] + 1).astype(str),
        )

        try:
            validate_code_block(code_blocks)
        except Exception as e:
            console.print(f"[red]Warning[/red]: Code block validation failed: {e}")

        return code_blocks

    def load_clone_pairs(self, revision: RevisionInfo) -> pd.DataFrame:
        clone_pairs = pd.read_csv(
            revision.clone_pairs_path,
            header=None,
            names=[
                ColumnNames.TOKEN_HASH_1.value,
                ColumnNames.TOKEN_HASH_2.value,
                ColumnNames.NGRAM_OVERLAP.value,
                ColumnNames.VERIFY_SIMILARITY.value,
            ],
        )
        return clone_pairs

    def get_revisions(self, data_dir: Path) -> list[RevisionInfo]:
        if not data_dir.exists():
            raise FileNotFoundError(f"Input directory does not exist: {data_dir}")

        revisions = [
            rev
            for dir_path in data_dir.iterdir()
            if dir_path.is_dir() and (rev := self._try_create_revision(dir_path))
        ]
        return sorted(revisions, key=lambda r: r.timestamp)

    def _try_create_revision(self, dir_path: Path) -> RevisionInfo | None:
        clone_pairs = dir_path / self.REQUIRED_FILES[0]
        code_blocks = dir_path / self.REQUIRED_FILES[1]

        if not (clone_pairs.exists() and code_blocks.exists()):
            raise ValueError(f"Required files missing in revision directory: {dir_path}")

        return RevisionInfo(
            timestamp=self._parse_revision_timestamp(dir_path.name),
            directory=dir_path,
            clone_pairs_path=clone_pairs,
            code_blocks_path=code_blocks,
        )

    @staticmethod
    def _parse_revision_timestamp(dir_name: str) -> datetime:
        """ディレクトリ名(YYYYMMDD_HHMMSS_<hash>)からタイムスタンプを取得"""
        parts = dir_name.split("_", 2)
        if len(parts) < 2:
            raise ValueError(f"Invalid revision directory name: {dir_name}")
        return datetime.strptime(f"{parts[0]}_{parts[1]}", "%Y%m%d_%H%M%S")
