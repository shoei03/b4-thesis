"""Feature extraction engine for deletion prediction."""

from pathlib import Path

import pandas as pd

from b4_thesis.analysis.code_extractor import GitCodeExtractor
from b4_thesis.analysis.deletion_prediction.cache_manager import CacheManager
from b4_thesis.analysis.deletion_prediction.extraction import (
    CsvDataLoader,
    RuleApplicator,
    SnippetLoader,
)
from b4_thesis.analysis.deletion_prediction.label_generator import LabelGenerator
from b4_thesis.analysis.deletion_prediction.rules import get_all_rules, get_rules_by_name


class FeatureExtractor:
    """Extract deletion prediction features from method lineage CSV.

    This class coordinates:
    1. CSV loading and validation (CsvDataLoader)
    2. Code snippet extraction (SnippetLoader)
    3. Rule application (RuleApplicator)
    4. Label generation (LabelGenerator)
    """

    def __init__(
        self,
        repo_path: Path,
        base_path_prefix: str = "/app/Repos/pandas/",
        github_base_url: str | None = None,
        lookahead_window: int = 5,
    ):
        """Initialize FeatureExtractor.

        Args:
            repo_path: Path to git repository
            base_path_prefix: Prefix to remove from file paths in CSV
            github_base_url: GitHub base URL for permalink generation
            lookahead_window: Number of future revisions to check for deletion
                             (default: 5)
        """
        # Initialize existing components
        self.code_extractor = GitCodeExtractor(
            repo_path=repo_path,
            base_path_prefix=base_path_prefix,
            github_base_url=github_base_url,
        )
        self.lookahead_window = lookahead_window
        self.label_generator = LabelGenerator(lookahead_window=lookahead_window)

        # Initialize extraction components
        self.csv_loader = CsvDataLoader()
        self.snippet_loader = SnippetLoader(code_extractor=self.code_extractor)
        self.rule_applicator = RuleApplicator()

    def extract(
        self,
        csv_path: Path,
        rule_names: list[str] | None = None,
        cache_manager: CacheManager | None = None,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """Extract features from method lineage CSV.

        Args:
            csv_path: Path to method_lineage_labeled.csv
            rule_names: List of rule names to apply (None = all rules)
            cache_manager: CacheManager instance for caching (None = no cache)
            use_cache: Whether to use cache (default: True)

        Returns:
            DataFrame with original columns + rule_XXX columns + is_deleted_soon

        Raises:
            FileNotFoundError: If CSV file not found
            ValueError: If CSV missing required columns
        """
        # Normalize rule_names for consistent caching
        # If rule_names is None, get actual rule names for proper cache key generation
        if rule_names is None:
            all_rules = get_all_rules()
            rule_names_normalized = [rule.rule_name for rule in all_rules]
        else:
            rule_names_normalized = rule_names

        # Try to load from features cache first (complete result)
        if use_cache and cache_manager:
            features_df = cache_manager.load_features(
                csv_path, rule_names_normalized, self.lookahead_window
            )
            if features_df is not None:
                print(f"✓ Loaded features from cache ({len(features_df)} methods)")
                return features_df

        # Step 1: Load and validate CSV
        csv_result = self.csv_loader.load_and_validate(csv_path)
        df = csv_result.df

        if csv_result.deleted_count > 0:
            print(
                f"Filtered out {csv_result.deleted_count} deleted methods "
                f"({csv_result.original_count} -> {csv_result.filtered_count} methods)"
            )

        # Step 2: Load code snippets (with caching)
        snippet_result = self.snippet_loader.load_snippets(df, csv_path, cache_manager, use_cache)
        df = snippet_result.df

        if snippet_result.cache_hit:
            print(f"✓ Loaded code snippets from cache ({snippet_result.snippets_count} snippets)")
        else:
            if use_cache and cache_manager:
                print("✓ Saved code snippets to cache")

        # Step 3: Get rules and apply them
        rules = get_all_rules() if rule_names is None else get_rules_by_name(rule_names)

        print(f"Applying {len(rules)} deletion prediction rules...")
        rule_result = self.rule_applicator.apply_rules(df, rules)
        df = rule_result.df

        # Step 4: Generate labels
        print("Generating ground truth labels...")
        df["is_deleted_soon"] = self.label_generator.generate_labels(df, csv_result.deleted_df)

        # Save features to cache
        if use_cache and cache_manager:
            cache_manager.save_features(csv_path, rule_names_normalized, df, self.lookahead_window)
            print("✓ Saved features to cache")

        return df
