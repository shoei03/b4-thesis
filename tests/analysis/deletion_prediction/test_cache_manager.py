"""Tests for CacheManager."""

import pandas as pd
import pytest

from b4_thesis.analysis.deletion_prediction.cache_manager import CacheManager


class TestCacheManager:
    """Test cases for CacheManager."""

    @pytest.fixture
    def cache_manager(self, tmp_path):
        """Create CacheManager instance with temp directory."""
        cache_dir = tmp_path / "cache"
        return CacheManager(cache_dir)

    @pytest.fixture
    def sample_csv(self, tmp_path):
        """Create sample CSV file for testing."""
        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame(
            {
                "global_block_id": ["id1", "id2"],
                "revision": ["rev1", "rev2"],
                "function_name": ["foo", "bar"],
                "file_path": ["/test.py", "/test.py"],
                "start_line": [1, 10],
                "end_line": [5, 15],
                "loc": [5, 6],
                "state": ["survived", "survived"],
            }
        )
        df.to_csv(csv_path, index=False)
        return csv_path

    @pytest.fixture
    def sample_snippets_df(self):
        """Create sample snippets DataFrame."""
        return pd.DataFrame(
            {
                "global_block_id": ["id1", "id2"],
                "revision": ["rev1", "rev2"],
                "code": ["def foo():\n    pass", "def bar():\n    return 1"],
                "github_url": ["https://github.com/test/repo/blob/rev1/test.py#L1-L5", None],
            }
        )

    @pytest.fixture
    def sample_features_df(self):
        """Create sample features DataFrame."""
        return pd.DataFrame(
            {
                "global_block_id": ["id1", "id2"],
                "revision": ["rev1", "rev2"],
                "function_name": ["foo", "bar"],
                "file_path": ["/test.py", "/test.py"],
                "start_line": [1, 10],
                "end_line": [5, 15],
                "loc": [5, 6],
                "state": ["survived", "survived"],
                "code": ["def foo():\n    pass", "def bar():\n    return 1"],
                "rule_short_method": [True, False],
                "is_deleted_soon": [False, False],
            }
        )

    def test_init_creates_cache_dir(self, tmp_path):
        """Test that cache directory is created on initialization."""
        cache_dir = tmp_path / "new_cache"
        assert not cache_dir.exists()

        cache_manager = CacheManager(cache_dir)

        assert cache_dir.exists()
        assert cache_manager.cache_dir == cache_dir

    def test_compute_csv_hash(self, cache_manager, sample_csv):
        """Test CSV file hash computation."""
        hash1 = cache_manager._compute_csv_hash(sample_csv)

        # Hash should be consistent
        hash2 = cache_manager._compute_csv_hash(sample_csv)
        assert hash1 == hash2

        # Hash should be 16 characters
        assert len(hash1) == 16

    def test_compute_csv_hash_different_files(self, cache_manager, tmp_path):
        """Test that different CSV files have different hashes."""
        # Create two different CSV files
        csv1 = tmp_path / "test1.csv"
        pd.DataFrame({"a": [1, 2, 3]}).to_csv(csv1, index=False)

        csv2 = tmp_path / "test2.csv"
        pd.DataFrame({"a": [4, 5, 6]}).to_csv(csv2, index=False)

        hash1 = cache_manager._compute_csv_hash(csv1)
        hash2 = cache_manager._compute_csv_hash(csv2)

        assert hash1 != hash2

    def test_compute_rules_hash(self, cache_manager):
        """Test rule names hash computation."""
        # Same rules should produce same hash
        hash1 = cache_manager._compute_rules_hash(["rule1", "rule2"])
        hash2 = cache_manager._compute_rules_hash(["rule1", "rule2"])
        assert hash1 == hash2

        # Order shouldn't matter (they're sorted)
        hash3 = cache_manager._compute_rules_hash(["rule2", "rule1"])
        assert hash1 == hash3

        # Different rules should produce different hash
        hash4 = cache_manager._compute_rules_hash(["rule1", "rule3"])
        assert hash1 != hash4

        # Empty list should produce "all" hash
        hash_all = cache_manager._compute_rules_hash([])
        assert len(hash_all) == 16

    def test_get_snippets_cache_path(self, cache_manager, sample_csv):
        """Test snippets cache path generation."""
        cache_path = cache_manager.get_snippets_cache_path(sample_csv)

        assert cache_path.parent == cache_manager.cache_dir
        assert cache_path.name.startswith("snippets_")
        assert cache_path.suffix == ".parquet"

    def test_get_features_cache_path(self, cache_manager, sample_csv):
        """Test features cache path generation."""
        rule_names = ["short_method", "has_todo"]
        cache_path = cache_manager.get_features_cache_path(sample_csv, rule_names)

        assert cache_path.parent == cache_manager.cache_dir
        assert cache_path.name.startswith("features_")
        assert cache_path.suffix == ".parquet"

        # Different rules should produce different paths
        cache_path2 = cache_manager.get_features_cache_path(sample_csv, ["short_method"])
        assert cache_path != cache_path2

    def test_save_and_load_snippets(self, cache_manager, sample_csv, sample_snippets_df):
        """Test saving and loading code snippets."""
        # Initially, cache should not exist
        assert cache_manager.load_snippets(sample_csv) is None

        # Save snippets
        cache_manager.save_snippets(sample_csv, sample_snippets_df)

        # Load snippets
        loaded_df = cache_manager.load_snippets(sample_csv)

        assert loaded_df is not None
        assert len(loaded_df) == len(sample_snippets_df)
        assert list(loaded_df.columns) == list(sample_snippets_df.columns)
        pd.testing.assert_frame_equal(loaded_df, sample_snippets_df)

    def test_save_and_load_features(self, cache_manager, sample_csv, sample_features_df):
        """Test saving and loading features."""
        rule_names = ["short_method"]

        # Initially, cache should not exist
        assert cache_manager.load_features(sample_csv, rule_names) is None

        # Save features
        cache_manager.save_features(sample_csv, rule_names, sample_features_df)

        # Load features
        loaded_df = cache_manager.load_features(sample_csv, rule_names)

        assert loaded_df is not None
        assert len(loaded_df) == len(sample_features_df)
        assert list(loaded_df.columns) == list(sample_features_df.columns)
        pd.testing.assert_frame_equal(loaded_df, sample_features_df)

    def test_load_nonexistent_snippets(self, cache_manager, sample_csv):
        """Test loading snippets when cache doesn't exist."""
        result = cache_manager.load_snippets(sample_csv)
        assert result is None

    def test_load_nonexistent_features(self, cache_manager, sample_csv):
        """Test loading features when cache doesn't exist."""
        result = cache_manager.load_features(sample_csv, ["rule1"])
        assert result is None

    def test_clear_cache_all(
        self, cache_manager, sample_csv, sample_snippets_df, sample_features_df
    ):
        """Test clearing all cache files."""
        # Save multiple caches
        cache_manager.save_snippets(sample_csv, sample_snippets_df)
        cache_manager.save_features(sample_csv, ["rule1"], sample_features_df)
        cache_manager.save_features(sample_csv, ["rule2"], sample_features_df)

        # Verify caches exist
        assert cache_manager.load_snippets(sample_csv) is not None
        assert cache_manager.load_features(sample_csv, ["rule1"]) is not None

        # Clear all
        deleted_count = cache_manager.clear_cache()

        # Verify caches cleared
        assert deleted_count == 3
        assert cache_manager.load_snippets(sample_csv) is None
        assert cache_manager.load_features(sample_csv, ["rule1"]) is None

    def test_clear_cache_specific_csv(self, cache_manager, tmp_path, sample_snippets_df):
        """Test clearing cache for specific CSV file."""
        # Create two CSV files
        csv1 = tmp_path / "test1.csv"
        pd.DataFrame({"a": [1]}).to_csv(csv1, index=False)

        csv2 = tmp_path / "test2.csv"
        pd.DataFrame({"b": [2]}).to_csv(csv2, index=False)

        # Save caches for both
        cache_manager.save_snippets(csv1, sample_snippets_df)
        cache_manager.save_snippets(csv2, sample_snippets_df)

        # Clear cache for csv1 only
        deleted_count = cache_manager.clear_cache(csv1)

        # Verify only csv1 cache was cleared
        assert deleted_count >= 1
        assert cache_manager.load_snippets(csv1) is None
        assert cache_manager.load_snippets(csv2) is not None

    def test_features_cache_different_rules(self, cache_manager, sample_csv, sample_features_df):
        """Test that different rule sets create different caches."""
        rules1 = ["short_method"]
        rules2 = ["short_method", "has_todo"]

        # Save with different rule sets
        cache_manager.save_features(sample_csv, rules1, sample_features_df)
        cache_manager.save_features(sample_csv, rules2, sample_features_df)

        # Load both
        df1 = cache_manager.load_features(sample_csv, rules1)
        df2 = cache_manager.load_features(sample_csv, rules2)

        # Both should exist independently
        assert df1 is not None
        assert df2 is not None
        pd.testing.assert_frame_equal(df1, sample_features_df)
        pd.testing.assert_frame_equal(df2, sample_features_df)
