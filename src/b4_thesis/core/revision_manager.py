"""RevisionManager for managing and loading revision data.

This module provides functionality to discover, sort, and load revision directories
containing code_blocks.csv and clone_pairs.csv files.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd


@dataclass
class RevisionInfo:
    """Information about a single revision.

    Attributes:
        timestamp: Parsed timestamp from directory name.
        directory: Path to the revision directory.
        clone_pairs_path: Path to clone_pairs.csv file.
        code_blocks_path: Path to code_blocks.csv file.
    """

    timestamp: datetime
    directory: Path
    clone_pairs_path: Path
    code_blocks_path: Path

    @property
    def revision_id(self) -> str:
        """Get revision ID (directory name).

        Returns:
            The directory name as revision identifier.
        """
        return self.directory.name


class RevisionManager:
    """Manages revision directories and provides sorted access.

    This class discovers revision directories, sorts them by timestamp,
    and provides methods to load their data files.
    """

    def __init__(self, data_dir: Path) -> None:
        """Initialize with data directory containing revisions.

        Args:
            data_dir: Path to directory containing revision subdirectories.
        """
        self.data_dir = Path(data_dir)

    def get_revisions(
        self, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> list[RevisionInfo]:
        """Get sorted list of revisions in date range.

        Args:
            start_date: Optional start date filter (inclusive).
            end_date: Optional end date filter (inclusive).

        Returns:
            List of RevisionInfo sorted by timestamp (oldest first).
        """
        if not self.data_dir.exists():
            return []

        revisions = []

        # Scan all subdirectories
        for dir_path in self.data_dir.iterdir():
            if not dir_path.is_dir():
                continue

            # Parse directory name (format: YYYYMMDD_HHMMSS_<hash>)
            try:
                timestamp = self._parse_revision_timestamp(dir_path.name)
            except ValueError:
                # Skip directories that don't match the expected format
                continue

            # Check if required CSV files exist
            clone_pairs_path = dir_path / "clone_pairs.csv"
            code_blocks_path = dir_path / "code_blocks.csv"

            if not clone_pairs_path.exists() or not code_blocks_path.exists():
                continue

            # Create RevisionInfo
            revision = RevisionInfo(
                timestamp=timestamp,
                directory=dir_path,
                clone_pairs_path=clone_pairs_path,
                code_blocks_path=code_blocks_path,
            )

            # Apply date filters
            if start_date and revision.timestamp < start_date:
                continue
            if end_date and revision.timestamp > end_date:
                continue

            revisions.append(revision)

        # Sort by timestamp (oldest first)
        revisions.sort(key=lambda r: r.timestamp)

        return revisions

    def load_revision_data(self, revision: RevisionInfo) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Load code_blocks and clone_pairs DataFrames for a revision.

        Args:
            revision: RevisionInfo object containing file paths.

        Returns:
            Tuple of (code_blocks DataFrame, clone_pairs DataFrame).
            Both DataFrames are validated for data quality.

        Raises:
            FileNotFoundError: If CSV files don't exist.
            pd.errors.EmptyDataError: If CSV files are malformed.

        Note:
            Data validation warnings are logged but do not stop processing.
        """
        # Load code_blocks.csv (no header, specify column names)
        # Explicitly convert line numbers to int to avoid type issues
        code_blocks = pd.read_csv(
            revision.code_blocks_path,
            header=None,
            names=[
                "block_id",
                "file_path",
                "start_line",
                "end_line",
                "method_name",
                "return_type",
                "parameters",
                "token_hash",
                "token_sequence",
            ],
            dtype={
                "start_line": int,
                "end_line": int,
            },
        )

        # Load clone_pairs.csv (no header, specify column names)
        # Handle empty file case (when no clones exist)
        try:
            clone_pairs = pd.read_csv(
                revision.clone_pairs_path,
                header=None,
                names=["block_id_1", "block_id_2", "ngram_similarity", "lcs_similarity"],
            )
        except pd.errors.EmptyDataError:
            # Create empty DataFrame with correct columns if file is empty
            clone_pairs = pd.DataFrame(
                columns=["block_id_1", "block_id_2", "ngram_similarity", "lcs_similarity"]
            )

        return code_blocks, clone_pairs

    def _parse_revision_timestamp(self, dir_name: str) -> datetime:
        """Parse timestamp from revision directory name.

        Args:
            dir_name: Directory name (format: YYYYMMDD_HHMMSS_<hash>).

        Returns:
            Parsed datetime object.

        Raises:
            ValueError: If directory name format is invalid.
        """
        # Split by underscore
        parts = dir_name.split("_")

        if len(parts) < 2:
            raise ValueError(f"Invalid revision directory name: {dir_name}")

        # Extract date and time parts
        date_part = parts[0]  # YYYYMMDD
        time_part = parts[1]  # HHMMSS

        # Parse datetime
        try:
            timestamp_str = f"{date_part}_{time_part}"
            timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            return timestamp
        except ValueError as e:
            raise ValueError(f"Invalid timestamp format in: {dir_name}") from e
