"""Code snippet loader for deletion prediction feature extraction."""

import pandas as pd

from b4_thesis.analysis.code_extractor import ExtractRequest, GitCodeExtractor


class SnippetLoader:
    """Load code snippets from git repository.

    This component handles:
    - Extracting code from git repository
    - Merging snippets with DataFrame
    """

    def __init__(self, code_extractor: GitCodeExtractor):
        """Initialize SnippetLoader.

        Args:
            code_extractor: GitCodeExtractor instance for extracting code
        """
        self.code_extractor = code_extractor

    def load_snippets(self, df: pd.DataFrame) -> pd.DataFrame:
        """Load code snippets for methods in DataFrame.

        Args:
            df: DataFrame with method metadata (columns: global_block_id, revision,
                function_name, file_path, start_line, end_line)

        Returns:
            - df: DataFrame with 'code' and 'github_url' columns added
        """
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
        code_snippets_raw = self.code_extractor.batch_extract(requests)

        # Create snippets DataFrame
        snippets_data = []
        for i, snippet_raw in enumerate(code_snippets_raw):
            row = df.iloc[i]
            snippets_data.append(
                {
                    "global_block_id": row.global_block_id,
                    "revision": row.revision,
                    "code": snippet_raw.code,
                }
            )

        snippets_df = pd.DataFrame(
            snippets_data,
            columns=["global_block_id", "revision", "code"],
        )

        return snippets_df
