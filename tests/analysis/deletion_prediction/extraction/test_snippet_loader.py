"""Tests for SnippetLoader."""

from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from b4_thesis.analysis.code_extractor import CodeSnippet, GitCodeExtractor
from b4_thesis.analysis.deletion_prediction.cache_manager import CacheManager
from b4_thesis.analysis.deletion_prediction.extraction import SnippetLoader, SnippetLoadResult


class TestSnippetLoader:
    """Tests for SnippetLoader class."""

    @pytest.fixture
    def mock_code_extractor(self):
        """Create mock GitCodeExtractor."""
        extractor = MagicMock(spec=GitCodeExtractor)
        extractor.batch_extract.return_value = [
            CodeSnippet(
                code="def foo(): pass",
                function_name="foo",
                file_path="a.py",
                start_line=1,
                end_line=5,
                revision="rev1",
                github_url="https://github.com/repo/blob/rev1/a.py#L1-L5",
            ),
            CodeSnippet(
                code="def bar(): pass",
                function_name="bar",
                file_path="b.py",
                start_line=10,
                end_line=15,
                revision="rev1",
                github_url="https://github.com/repo/blob/rev1/b.py#L10-L15",
            ),
        ]
        return extractor

    @pytest.fixture
    def snippet_loader(self, mock_code_extractor):
        """Create SnippetLoader instance with mock extractor."""
        return SnippetLoader(code_extractor=mock_code_extractor)

    @pytest.fixture
    def sample_df(self):
        """Create sample DataFrame."""
        return pd.DataFrame(
            {
                "global_block_id": ["block1", "block2"],
                "revision": ["rev1", "rev1"],
                "function_name": ["foo", "bar"],
                "file_path": ["a.py", "b.py"],
                "start_line": [1, 10],
                "end_line": [5, 15],
                "loc": [4, 5],
                "state": ["added", "modified"],
            }
        )

    @pytest.fixture
    def mock_cache_manager(self):
        """Create mock CacheManager."""
        return MagicMock(spec=CacheManager)

    def test_init(self, mock_code_extractor):
        """Test SnippetLoader initialization."""
        loader = SnippetLoader(code_extractor=mock_code_extractor)
        assert loader.code_extractor is mock_code_extractor

    def test_load_snippets_cache_hit(self, snippet_loader, sample_df, mock_cache_manager):
        """Test loading snippets from cache."""
        # Setup cache to return snippets
        cached_snippets = pd.DataFrame(
            {
                "global_block_id": ["block1", "block2"],
                "revision": ["rev1", "rev1"],
                "code": ["def foo(): pass", "def bar(): pass"],
                "github_url": [
                    "https://github.com/repo/blob/rev1/a.py#L1-L5",
                    "https://github.com/repo/blob/rev1/b.py#L10-L15",
                ],
            }
        )
        mock_cache_manager.load_snippets.return_value = cached_snippets

        csv_path = Path("/tmp/test.csv")
        result = snippet_loader.load_snippets(
            sample_df, csv_path, cache_manager=mock_cache_manager, use_cache=True
        )

        assert isinstance(result, SnippetLoadResult)
        assert result.cache_hit is True
        assert result.snippets_count == 2
        assert len(result.df) == 2
        assert "code" in result.df.columns
        assert "github_url" in result.df.columns
        assert result.df["code"].tolist() == ["def foo(): pass", "def bar(): pass"]

        # Verify cache was checked
        mock_cache_manager.load_snippets.assert_called_once_with(csv_path)
        # Verify extractor was NOT called (cache hit)
        snippet_loader.code_extractor.batch_extract.assert_not_called()

    def test_load_snippets_cache_miss(self, snippet_loader, sample_df, mock_cache_manager, capsys):
        """Test extracting snippets when cache misses."""
        # Setup cache to return None (cache miss)
        mock_cache_manager.load_snippets.return_value = None

        csv_path = Path("/tmp/test.csv")
        result = snippet_loader.load_snippets(
            sample_df, csv_path, cache_manager=mock_cache_manager, use_cache=True
        )

        assert isinstance(result, SnippetLoadResult)
        assert result.cache_hit is False
        assert result.snippets_count == 2
        assert len(result.df) == 2
        assert "code" in result.df.columns
        assert "github_url" in result.df.columns

        # Verify extractor was called
        snippet_loader.code_extractor.batch_extract.assert_called_once()
        # Verify cache save was called
        mock_cache_manager.save_snippets.assert_called_once()

        # Verify print output
        captured = capsys.readouterr()
        assert "Extracting 2 code snippets from repository..." in captured.out

    def test_load_snippets_no_cache_manager(self, snippet_loader, sample_df):
        """Test extracting snippets without cache manager."""
        csv_path = Path("/tmp/test.csv")
        result = snippet_loader.load_snippets(
            sample_df, csv_path, cache_manager=None, use_cache=True
        )

        assert isinstance(result, SnippetLoadResult)
        assert result.cache_hit is False
        assert result.snippets_count == 2
        assert len(result.df) == 2

        # Verify extractor was called
        snippet_loader.code_extractor.batch_extract.assert_called_once()

    def test_load_snippets_use_cache_false(self, snippet_loader, sample_df, mock_cache_manager):
        """Test extracting snippets when use_cache=False."""
        csv_path = Path("/tmp/test.csv")
        result = snippet_loader.load_snippets(
            sample_df, csv_path, cache_manager=mock_cache_manager, use_cache=False
        )

        assert isinstance(result, SnippetLoadResult)
        assert result.cache_hit is False
        assert result.snippets_count == 2

        # Verify cache was NOT checked
        mock_cache_manager.load_snippets.assert_not_called()
        # Verify extractor was called
        snippet_loader.code_extractor.batch_extract.assert_called_once()
        # Verify cache was NOT saved
        mock_cache_manager.save_snippets.assert_not_called()

    def test_extract_requests_creation(self, snippet_loader, sample_df):
        """Test that ExtractRequests are created correctly."""
        csv_path = Path("/tmp/test.csv")
        snippet_loader.load_snippets(sample_df, csv_path, cache_manager=None, use_cache=False)

        # Verify batch_extract was called with correct requests
        snippet_loader.code_extractor.batch_extract.assert_called_once()
        requests = snippet_loader.code_extractor.batch_extract.call_args[0][0]

        assert len(requests) == 2
        assert requests[0].function_name == "foo"
        assert requests[0].file_path == "a.py"
        assert requests[0].revision == "rev1"
        assert requests[0].global_block_id == "block1"
        assert requests[1].function_name == "bar"
        assert requests[1].file_path == "b.py"

    def test_snippets_dataframe_structure(self, snippet_loader, sample_df):
        """Test that snippets DataFrame has correct structure."""
        csv_path = Path("/tmp/test.csv")
        result = snippet_loader.load_snippets(sample_df, csv_path, cache_manager=None)

        # Verify result DataFrame has all original columns plus code and github_url
        expected_columns = set(sample_df.columns) | {"code", "github_url"}
        assert set(result.df.columns) == expected_columns

        # Verify code and github_url values
        assert result.df["code"].tolist() == ["def foo(): pass", "def bar(): pass"]
        assert len(result.df["github_url"].tolist()) == 2

    def test_dataframe_merge_preserves_order(self, snippet_loader, sample_df):
        """Test that DataFrame merge preserves row order."""
        csv_path = Path("/tmp/test.csv")
        result = snippet_loader.load_snippets(sample_df, csv_path, cache_manager=None)

        # Verify order is preserved
        assert result.df["global_block_id"].tolist() == ["block1", "block2"]
        assert result.df["function_name"].tolist() == ["foo", "bar"]

    def test_single_row_dataframe(self, snippet_loader):
        """Test loading snippets for single-row DataFrame."""
        single_df = pd.DataFrame(
            {
                "global_block_id": ["block1"],
                "revision": ["rev1"],
                "function_name": ["foo"],
                "file_path": ["a.py"],
                "start_line": [1],
                "end_line": [5],
                "loc": [4],
                "state": ["added"],
            }
        )

        # Mock batch_extract to return single snippet
        snippet_loader.code_extractor.batch_extract.return_value = [
            CodeSnippet(
                code="def foo(): pass",
                function_name="foo",
                file_path="a.py",
                start_line=1,
                end_line=5,
                revision="rev1",
                github_url="https://github.com/repo/blob/rev1/a.py#L1-L5",
            )
        ]

        csv_path = Path("/tmp/test.csv")
        result = snippet_loader.load_snippets(single_df, csv_path, cache_manager=None)

        assert result.snippets_count == 1
        assert len(result.df) == 1
        assert result.df["code"].iloc[0] == "def foo(): pass"
        assert "github_url" in result.df.columns

    def test_cache_save_called_with_correct_data(
        self, snippet_loader, sample_df, mock_cache_manager
    ):
        """Test that cache save is called with correct snippets DataFrame."""
        mock_cache_manager.load_snippets.return_value = None

        csv_path = Path("/tmp/test.csv")
        snippet_loader.load_snippets(
            sample_df, csv_path, cache_manager=mock_cache_manager, use_cache=True
        )

        # Verify cache save was called
        mock_cache_manager.save_snippets.assert_called_once()
        call_args = mock_cache_manager.save_snippets.call_args
        assert call_args[0][0] == csv_path

        # Verify snippets DataFrame structure
        snippets_df = call_args[0][1]
        assert set(snippets_df.columns) == {"global_block_id", "revision", "code", "github_url"}
        assert len(snippets_df) == 2
