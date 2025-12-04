"""Feature extraction engine for deletion prediction."""

from pathlib import Path

import pandas as pd
from tqdm import tqdm

from b4_thesis.analysis.code_extractor import ExtractRequest, GitCodeExtractor
from b4_thesis.analysis.deletion_prediction.cache_manager import CacheManager
from b4_thesis.analysis.deletion_prediction.label_generator import LabelGenerator
from b4_thesis.analysis.deletion_prediction.rule_base import CodeSnippet
from b4_thesis.analysis.deletion_prediction.rules import get_all_rules, get_rules_by_name


class FeatureExtractor:
    """Extract deletion prediction features from method lineage CSV.

    This class:
    1. Reads method_lineage_labeled.csv
    2. Extracts code snippets from git repository
    3. Applies deletion prediction rules
    4. Generates ground truth labels (is_deleted_next)
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
        self.code_extractor = GitCodeExtractor(
            repo_path=repo_path,
            base_path_prefix=base_path_prefix,
            github_base_url=github_base_url,
        )
        self.lookahead_window = lookahead_window
        self.label_generator = LabelGenerator(lookahead_window=lookahead_window)

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
            DataFrame with original columns + rule_XXX columns + is_deleted_next

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

        # Load CSV
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        df = pd.read_csv(csv_path)

        # Validate required columns
        required_columns = {
            "global_block_id",
            "revision",
            "function_name",
            "file_path",
            "start_line",
            "end_line",
            "loc",
            "state",
        }
        missing_columns = required_columns - set(df.columns)
        if missing_columns:
            raise ValueError(f"CSV missing required columns: {missing_columns}")

        # Filter out deleted methods (code doesn't exist for them)
        original_count = len(df)
        df = df[df["state"] != "deleted"].copy()
        deleted_count = original_count - len(df)

        if deleted_count > 0:
            print(
                f"Filtered out {deleted_count} deleted methods "
                f"({original_count} -> {len(df)} methods)"
            )

        if len(df) == 0:
            raise ValueError("No methods to process after filtering deleted methods")

        # Get rules to apply
        rules = get_all_rules() if rule_names is None else get_rules_by_name(rule_names)

        # Try to load code snippets from cache
        snippets_df = None
        if use_cache and cache_manager:
            snippets_df = cache_manager.load_snippets(csv_path)
            if snippets_df is not None:
                print(f"✓ Loaded code snippets from cache ({len(snippets_df)} snippets)")
                # Merge with df to add code and github_url columns
                df = df.merge(
                    snippets_df,
                    on=["global_block_id", "revision"],
                    how="left",
                    suffixes=("", "_cached"),
                )

        # Extract code snippets if not cached
        if snippets_df is None:
            # Create extraction requests
            requests = [
                ExtractRequest(
                    function_name=row.function_name,
                    file_path=row.file_path,
                    revision=row.revision,
                    start_line=row.start_line,
                    end_line=row.end_line,
                    global_block_id=row.global_block_id,
                )
                for row in df.itertuples()
            ]

            # Batch extract code snippets
            print(f"Extracting {len(requests)} code snippets from repository...")
            code_snippets_raw = self.code_extractor.batch_extract(requests)

            # Create snippets DataFrame for caching
            snippets_data = []
            for i, snippet_raw in enumerate(code_snippets_raw):
                row = df.iloc[i]
                snippets_data.append(
                    {
                        "global_block_id": row.global_block_id,
                        "revision": row.revision,
                        "code": snippet_raw.code,
                        "github_url": snippet_raw.github_url,
                    }
                )

            snippets_df = pd.DataFrame(snippets_data)

            # Save snippets to cache
            if use_cache and cache_manager:
                cache_manager.save_snippets(csv_path, snippets_df)
                print("✓ Saved code snippets to cache")

            # Merge with df
            df = df.merge(
                snippets_df, on=["global_block_id", "revision"], how="left", suffixes=("", "_new")
            )

        # Create CodeSnippet objects from df for rule application
        code_snippets = []
        for row in df.itertuples():
            code_snippets.append(
                CodeSnippet(
                    code=row.code,
                    function_name=row.function_name,
                    file_path=row.file_path,
                    start_line=row.start_line,
                    end_line=row.end_line,
                    revision=row.revision,
                    loc=row.loc,
                    global_block_id=row.global_block_id,
                )
            )

        # Apply rules
        print(f"Applying {len(rules)} deletion prediction rules...")
        for rule in tqdm(rules, desc="Applying rules"):
            rule_results = []
            for snippet in code_snippets:
                try:
                    result = rule.apply(snippet)
                    rule_results.append(result)
                except Exception as e:
                    # If rule application fails, assume False (no deletion sign)
                    print(
                        f"Warning: Rule {rule.rule_name} failed on "
                        f"{snippet.function_name} (revision {snippet.revision}): {e}"
                    )
                    rule_results.append(False)

            df[f"rule_{rule.rule_name}"] = rule_results

        # Generate ground truth labels
        print("Generating ground truth labels...")
        df["is_deleted_next"] = self.label_generator.generate_labels(df)

        # Save features to cache
        if use_cache and cache_manager:
            cache_manager.save_features(csv_path, rule_names_normalized, df, self.lookahead_window)
            print("✓ Saved features to cache")

        return df
