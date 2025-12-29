from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd


@dataclass(frozen=True, slots=True)
class RevisionInfo:
    timestamp: datetime
    directory: Path
    clone_pairs_path: Path
    code_blocks_path: Path


class RevisionManager:
    REQUIRED_FILES = ("clone_pairs.csv", "code_blocks.csv")

    def load_revision_data(self, revision: RevisionInfo) -> tuple[pd.DataFrame, pd.DataFrame]:
        code_blocks = pd.read_csv(
            revision.code_blocks_path,
            header=None,
            names=[
                "block_id",
                "file_path",
                "start_line",
                "end_line",
                "function_name",
                "return_type",
                "parameters",
                "commit_hash",
                "token_sequence",
            ],
            dtype={
                "start_line": int,
                "end_line": int,
            },
        )

        clone_pairs = pd.read_csv(
            revision.clone_pairs_path,
            header=None,
            names=[
                "block_id_1",
                "block_id_2",
                "ngram_similarity",
                "lcs_similarity",
            ],
        )

        return code_blocks, clone_pairs

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
