"""Tests for RevisionManager."""

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from b4_thesis.core.revision_manager import RevisionInfo, RevisionManager


class TestRevisionInfo:
    """Test RevisionInfo dataclass."""

    def test_revision_info_creation(self):
        """Test creating RevisionInfo."""
        timestamp = datetime(2025, 1, 1, 10, 0, 0)
        directory = Path("tests/fixtures/sample_revisions/20250101_100000_hash1")
        clone_pairs_path = directory / "clone_pairs.csv"
        code_blocks_path = directory / "code_blocks.csv"

        info = RevisionInfo(
            timestamp=timestamp,
            directory=directory,
            clone_pairs_path=clone_pairs_path,
            code_blocks_path=code_blocks_path,
        )

        assert info.timestamp == timestamp
        assert info.directory == directory
        assert info.clone_pairs_path == clone_pairs_path
        assert info.code_blocks_path == code_blocks_path

    def test_revision_id_property(self):
        """Test revision_id property returns directory name."""
        timestamp = datetime(2025, 1, 1, 10, 0, 0)
        directory = Path("tests/fixtures/sample_revisions/20250101_100000_hash1")

        info = RevisionInfo(
            timestamp=timestamp,
            directory=directory,
            clone_pairs_path=directory / "clone_pairs.csv",
            code_blocks_path=directory / "code_blocks.csv",
        )

        assert info.revision_id == "20250101_100000_hash1"


class TestRevisionManager:
    """Test RevisionManager."""

    @pytest.fixture
    def sample_data_dir(self):
        """Path to sample test data."""
        return Path("tests/fixtures/sample_revisions")

    def test_initialization(self, sample_data_dir):
        """Test RevisionManager initialization."""
        manager = RevisionManager(sample_data_dir)
        assert manager.data_dir == sample_data_dir

    def test_get_revisions_sorted(self, sample_data_dir):
        """Test get_revisions returns sorted list."""
        manager = RevisionManager(sample_data_dir)
        revisions = manager.get_revisions()

        # Should return 4 revisions
        assert len(revisions) == 4

        # Should be sorted by timestamp (oldest first)
        assert revisions[0].revision_id == "20250101_100000_hash1"
        assert revisions[1].revision_id == "20250101_110000_hash2"
        assert revisions[2].revision_id == "20250101_120000_hash3"
        assert revisions[3].revision_id == "20250101_130000_hash4"

        # Timestamps should be in order
        assert (
            revisions[0].timestamp
            < revisions[1].timestamp
            < revisions[2].timestamp
            < revisions[3].timestamp
        )

    def test_get_revisions_with_start_date(self, sample_data_dir):
        """Test get_revisions with start_date filter."""
        manager = RevisionManager(sample_data_dir)

        # Filter from 11:00:00
        start_date = datetime(2025, 1, 1, 11, 0, 0)
        revisions = manager.get_revisions(start_date=start_date)

        # Should return 3 revisions (11:00, 12:00, and 13:00)
        assert len(revisions) == 3
        assert revisions[0].revision_id == "20250101_110000_hash2"
        assert revisions[1].revision_id == "20250101_120000_hash3"
        assert revisions[2].revision_id == "20250101_130000_hash4"

    def test_get_revisions_with_end_date(self, sample_data_dir):
        """Test get_revisions with end_date filter."""
        manager = RevisionManager(sample_data_dir)

        # Filter until 11:00:00
        end_date = datetime(2025, 1, 1, 11, 0, 0)
        revisions = manager.get_revisions(end_date=end_date)

        # Should return 2 revisions (10:00 and 11:00)
        assert len(revisions) == 2
        assert revisions[0].revision_id == "20250101_100000_hash1"
        assert revisions[1].revision_id == "20250101_110000_hash2"

    def test_get_revisions_with_date_range(self, sample_data_dir):
        """Test get_revisions with both start and end dates."""
        manager = RevisionManager(sample_data_dir)

        # Filter from 10:30 to 11:30
        start_date = datetime(2025, 1, 1, 10, 30, 0)
        end_date = datetime(2025, 1, 1, 11, 30, 0)
        revisions = manager.get_revisions(start_date=start_date, end_date=end_date)

        # Should return only the middle revision (11:00)
        assert len(revisions) == 1
        assert revisions[0].revision_id == "20250101_110000_hash2"

    def test_get_revisions_no_match(self, sample_data_dir):
        """Test get_revisions with date range that matches nothing."""
        manager = RevisionManager(sample_data_dir)

        # Filter for dates in the future
        start_date = datetime(2025, 1, 2, 0, 0, 0)
        revisions = manager.get_revisions(start_date=start_date)

        assert len(revisions) == 0

    def test_load_revision_data(self, sample_data_dir):
        """Test loading code_blocks and clone_pairs DataFrames."""
        manager = RevisionManager(sample_data_dir)
        revisions = manager.get_revisions()

        # Load data from first revision
        code_blocks, clone_pairs = manager.load_revision_data(revisions[0])

        # Check code_blocks DataFrame
        assert isinstance(code_blocks, pd.DataFrame)
        assert len(code_blocks) == 4  # 4 blocks in first revision
        assert "block_id" in code_blocks.columns
        assert "function_name" in code_blocks.columns
        assert "token_sequence" in code_blocks.columns

        # Check specific data
        assert "block_a" in code_blocks["block_id"].values
        assert "block_b" in code_blocks["block_id"].values
        assert "block_c" in code_blocks["block_id"].values
        assert "block_d" in code_blocks["block_id"].values

        # Check clone_pairs DataFrame
        assert isinstance(clone_pairs, pd.DataFrame)
        assert "block_id_1" in clone_pairs.columns
        assert "block_id_2" in clone_pairs.columns
        assert len(clone_pairs) == 2  # 2 clone pairs in first revision

        # Check clone pair data
        assert "block_a" in clone_pairs["block_id_1"].values
        assert "block_b" in clone_pairs["block_id_2"].values

    def test_load_revision_data_second_revision(self, sample_data_dir):
        """Test loading data from second revision."""
        manager = RevisionManager(sample_data_dir)
        revisions = manager.get_revisions()

        # Load data from second revision
        code_blocks, clone_pairs = manager.load_revision_data(revisions[1])

        assert len(code_blocks) == 3
        assert "block_a2" in code_blocks["block_id"].values
        assert "block_b2" in code_blocks["block_id"].values
        assert "block_d" in code_blocks["block_id"].values

    def test_invalid_directory(self):
        """Test with non-existent directory."""
        invalid_dir = Path("non/existent/directory")
        manager = RevisionManager(invalid_dir)

        # Should return empty list for non-existent directory
        revisions = manager.get_revisions()
        assert len(revisions) == 0

    def test_revision_directory_validation(self, sample_data_dir):
        """Test that only valid revision directories are detected."""
        manager = RevisionManager(sample_data_dir)
        revisions = manager.get_revisions()

        # All revisions should have proper format
        for rev in revisions:
            assert rev.directory.exists()
            assert rev.clone_pairs_path.exists()
            assert rev.code_blocks_path.exists()
