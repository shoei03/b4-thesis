"""Cache management for deletion prediction feature extraction."""

import hashlib
from pathlib import Path

import pandas as pd


class CacheManager:
    """Manage caching for code snippet extraction and feature computation.

    This class provides two-level caching:
    1. Code snippets cache: Saves git extraction results (most time-consuming)
    2. Features cache: Saves rule application results (final output)

    Cache files are stored in Parquet format for efficient storage and fast I/O.
    Cache keys are computed from CSV file content hash and rule set hash.
    """

    def __init__(self, cache_dir: Path):
        """Initialize CacheManager.

        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _compute_csv_hash(self, csv_path: Path) -> str:
        """Compute hash of CSV file content.

        Args:
            csv_path: Path to CSV file

        Returns:
            First 16 characters of SHA256 hash
        """
        with open(csv_path, "rb") as f:
            content = f.read()
        return hashlib.sha256(content).hexdigest()[:16]

    def _compute_rules_hash(self, rule_names: list[str]) -> str:
        """Compute hash of rule names.

        Args:
            rule_names: List of rule names (empty list for all rules)

        Returns:
            First 16 characters of SHA256 hash
        """
        # Sort rule names for consistent hashing
        rules_str = ",".join(sorted(rule_names)) if rule_names else "all"
        return hashlib.sha256(rules_str.encode()).hexdigest()[:16]

    def get_snippets_cache_path(self, csv_path: Path) -> Path:
        """Get cache file path for code snippets.

        Args:
            csv_path: Path to source CSV file

        Returns:
            Path to snippets cache file (Parquet format)
        """
        csv_hash = self._compute_csv_hash(csv_path)
        return self.cache_dir / f"snippets_{csv_hash}.parquet"

    def get_features_cache_path(
        self, csv_path: Path, rule_names: list[str], lookahead_window: int = 5
    ) -> Path:
        """Get cache file path for features.

        Args:
            csv_path: Path to source CSV file
            rule_names: List of rule names applied
            lookahead_window: Lookahead window for deletion prediction

        Returns:
            Path to features cache file (Parquet format)
        """
        csv_hash = self._compute_csv_hash(csv_path)
        rules_hash = self._compute_rules_hash(rule_names)
        lookahead_hash = hashlib.sha256(str(lookahead_window).encode()).hexdigest()[:8]
        return self.cache_dir / f"features_{csv_hash}_{rules_hash}_{lookahead_hash}.parquet"

    def load_snippets(self, csv_path: Path) -> pd.DataFrame | None:
        """Load code snippets from cache.

        Args:
            csv_path: Path to source CSV file

        Returns:
            DataFrame with cached code snippets, or None if cache miss
        """
        cache_path = self.get_snippets_cache_path(csv_path)
        if cache_path.exists():
            return pd.read_parquet(cache_path)
        return None

    def save_snippets(self, csv_path: Path, snippets_df: pd.DataFrame) -> None:
        """Save code snippets to cache.

        Args:
            csv_path: Path to source CSV file
            snippets_df: DataFrame containing code snippets
        """
        cache_path = self.get_snippets_cache_path(csv_path)
        snippets_df.to_parquet(cache_path, index=False)

    def load_features(
        self, csv_path: Path, rule_names: list[str], lookahead_window: int = 5
    ) -> pd.DataFrame | None:
        """Load features from cache.

        Args:
            csv_path: Path to source CSV file
            rule_names: List of rule names applied
            lookahead_window: Lookahead window for deletion prediction

        Returns:
            DataFrame with cached features, or None if cache miss
        """
        cache_path = self.get_features_cache_path(csv_path, rule_names, lookahead_window)
        if cache_path.exists():
            return pd.read_parquet(cache_path)
        return None

    def save_features(
        self,
        csv_path: Path,
        rule_names: list[str],
        features_df: pd.DataFrame,
        lookahead_window: int = 5,
    ) -> None:
        """Save features to cache.

        Args:
            csv_path: Path to source CSV file
            rule_names: List of rule names applied
            features_df: DataFrame containing features
            lookahead_window: Lookahead window for deletion prediction
        """
        cache_path = self.get_features_cache_path(csv_path, rule_names, lookahead_window)
        features_df.to_parquet(cache_path, index=False)

    def clear_cache(self, csv_path: Path | None = None) -> int:
        """Clear cache files.

        Args:
            csv_path: If provided, only clear caches for this CSV file.
                     If None, clear all caches.

        Returns:
            Number of cache files deleted
        """
        if csv_path is None:
            # Clear all cache files
            cache_files = list(self.cache_dir.glob("*.parquet"))
        else:
            # Clear caches for specific CSV
            csv_hash = self._compute_csv_hash(csv_path)
            cache_files = list(self.cache_dir.glob(f"*{csv_hash}*.parquet"))

        for cache_file in cache_files:
            cache_file.unlink()

        return len(cache_files)
