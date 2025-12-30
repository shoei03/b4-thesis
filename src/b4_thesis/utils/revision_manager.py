from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from b4_thesis.const.column import ColumnNames
from b4_thesis.core.track.validate import validate_code_block
import pandas as pd


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
                ColumnNames.START_LINE.value: int,
                ColumnNames.END_LINE.value: int,
            },
        )

        code_blocks[ColumnNames.TOKEN_SEQUENCE.value] = (
            code_blocks[ColumnNames.TOKEN_SEQUENCE.value]
            .str[1:-1]
            .str.split(";")
            .apply(lambda x: [int(i) for i in x])
        )

        try:
            validate_code_block(code_blocks)
        except Exception as e:
            print(f"Warning: Code block validation failed: {e}")

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
