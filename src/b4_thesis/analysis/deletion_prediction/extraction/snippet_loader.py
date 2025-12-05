"""Code snippet loader for deletion prediction feature extraction."""

from pathlib import Path

import pandas as pd

from b4_thesis.analysis.code_extractor import ExtractRequest, GitCodeExtractor
from b4_thesis.analysis.deletion_prediction.cache_manager import CacheManager
from b4_thesis.analysis.deletion_prediction.extraction.result_types import SnippetLoadResult


class SnippetLoader:
    """Load code snippets from git repository with caching.

    This component handles:
    - Checking snippet cache
    - Extracting code from git repository
    - Saving snippets to cache
    - Merging snippets with DataFrame
    """

    def __init__(self, code_extractor: GitCodeExtractor):
        """Initialize SnippetLoader.

        Args:
            code_extractor: GitCodeExtractor instance for extracting code
        """
        self.code_extractor = code_extractor

    def load_snippets(
        self,
        df: pd.DataFrame,
        csv_path: Path,
        cache_manager: CacheManager | None = None,
        use_cache: bool = True,
    ) -> SnippetLoadResult:
        """Load code snippets for methods in DataFrame.

        Args:
            df: DataFrame with method metadata
            csv_path: Path to source CSV (for cache key)
            cache_manager: CacheManager instance (None = no cache)
            use_cache: Whether to use cache

        Returns:
            SnippetLoadResult with DataFrame containing code and github_url columns
        """
        # Try to load snippets from cache
        snippets_df = None
        if use_cache and cache_manager:
            snippets_df = cache_manager.load_snippets(csv_path)
            if snippets_df is not None:
                # Merge with df to add code and github_url columns
                result_df = df.merge(
                    snippets_df,
                    on=["global_block_id", "revision"],
                    how="left",
                    suffixes=("", "_cached"),
                )
                return SnippetLoadResult(
                    df=result_df,
                    cache_hit=True,
                    snippets_count=len(snippets_df),
                )

        # Extract code snippets if not cached
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

        # Create DataFrame with explicit columns to handle empty case
        snippets_df = pd.DataFrame(
            snippets_data,
            columns=["global_block_id", "revision", "code", "github_url"],
        )

        # Save snippets to cache
        if use_cache and cache_manager:
            cache_manager.save_snippets(csv_path, snippets_df)

        # Merge with df
        result_df = df.merge(
            snippets_df, on=["global_block_id", "revision"], how="left", suffixes=("", "_new")
        )

        return SnippetLoadResult(
            df=result_df,
            cache_hit=False,
            snippets_count=len(snippets_df),
        )
