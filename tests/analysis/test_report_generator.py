"""Tests for report generator module."""

from unittest.mock import MagicMock

import pandas as pd
import pytest

from b4_thesis.analysis.code_extractor import CodeSnippet, ExtractRequest, GitCodeExtractor
from b4_thesis.analysis.report_generator import CloneGroupReport, MemberInfo, ReportGenerator


class TestCloneGroupReport:
    """Test CloneGroupReport dataclass."""

    def test_create_report(self):
        """Test creating a clone group report."""
        snippet = CodeSnippet(
            function_name="func_a",
            file_path="src/module.py",
            revision="abc123",
            start_line=10,
            end_line=20,
            code="def func_a():\n    pass",
        )
        members = [
            MemberInfo(
                global_block_id="block_a",
                revision="abc123",
                function_name="func_a",
                file_path="src/module.py",
                start_line=10,
                end_line=20,
                loc=10,
                state="survived",
                state_detail=None,
                match_type="CLONE_MATCH",
                match_similarity=95.5,
                clone_count=2,
                clone_group_id="abc123def456",
                clone_group_size=2,
                avg_similarity_to_group=95.5,
                lifetime_revisions=5,
                lifetime_days=100,
                code_snippet=snippet,
            ),
        ]

        report = CloneGroupReport(
            group_id="abc123def456",
            member_count=1,
            match_type="CLONE_MATCH",
            avg_similarity=95.5,
            members=members,
        )

        assert report.group_id == "abc123def456"
        assert report.member_count == 1
        assert report.match_type == "CLONE_MATCH"
        assert report.avg_similarity == 95.5
        assert len(report.members) == 1

    def test_short_id(self):
        """Test short ID property."""
        report = CloneGroupReport(
            group_id="abc123def456ghij",
            member_count=0,
            match_type=None,
            avg_similarity=None,
        )

        assert report.short_id == "abc123de"

    def test_short_id_already_short(self):
        """Test short ID when already short."""
        report = CloneGroupReport(
            group_id="abc",
            member_count=0,
            match_type=None,
            avg_similarity=None,
        )

        assert report.short_id == "abc"


class TestReportGenerator:
    """Test ReportGenerator class."""

    @pytest.fixture
    def mock_extractor(self):
        """Create a mock GitCodeExtractor."""
        extractor = MagicMock(spec=GitCodeExtractor)

        # Mock batch_extract to return CodeSnippets
        def mock_batch_extract(requests, sort_by_revision=True):
            snippets = []
            for req in requests:
                snippets.append(
                    CodeSnippet(
                        function_name=req.function_name,
                        file_path=req.file_path,
                        revision=req.revision,
                        start_line=req.start_line,
                        end_line=req.end_line,
                        code=f"def {req.function_name}():\n    pass",
                        github_url=f"https://github.com/example/repo/blob/{req.revision}/{req.file_path}#L{req.start_line}-L{req.end_line}",
                    )
                )
            return snippets

        extractor.batch_extract.side_effect = mock_batch_extract
        return extractor

    @pytest.fixture
    def sample_group_df(self):
        """Create a sample DataFrame for a clone group (partial_deleted.csv format)."""
        return pd.DataFrame(
            {
                "clone_group_id": ["group123"] * 4,
                "global_block_id": ["block_a", "block_a", "block_b", "block_c"],
                "revision": ["rev1", "rev2", "rev1", "rev1"],  # block_a has 2 revisions
                "function_name": ["func_a", "func_a", "func_b", "func_c"],
                "file_path": [
                    "pandas/core/a.py",
                    "pandas/core/a.py",
                    "pandas/core/b.py",
                    "pandas/core/c.py",
                ],
                "start_line": [10, 10, 20, 30],
                "end_line": [20, 20, 35, 45],
                "loc": [10, 10, 15, 15],
                "state": ["survived", "survived", "deleted", "survived"],
                "state_detail": [None, None, None, None],
                "match_type": ["CLONE_MATCH"] * 4,
                "match_similarity": [92.0, 93.0, 88.0, 90.0],
                "clone_count": [3, 3, 3, 3],
                "clone_group_size": [3, 3, 3, 3],
                "avg_similarity_to_group": [92.0, 93.0, 88.0, 90.0],
                "lifetime_revisions": [5, 5, 3, 4],
                "lifetime_days": [100, 100, 50, 80],
                "rev_status": [
                    "no_deleted",
                    "partial_deleted",
                    "partial_deleted",
                    "partial_deleted",
                ],
            }
        )

    def test_init(self, mock_extractor):
        """Test generator initialization."""
        generator = ReportGenerator(mock_extractor)

        assert generator.extractor == mock_extractor

    def test_create_extract_requests(self, mock_extractor, sample_group_df):
        """Test creating extraction requests from DataFrame."""
        generator = ReportGenerator(mock_extractor)

        # Use first 2 rows
        df = sample_group_df.head(2)
        requests = generator._create_extract_requests(df)

        assert len(requests) == 2
        assert all(isinstance(req, ExtractRequest) for req in requests)
        assert requests[0].function_name == "func_a"
        assert requests[0].start_line == 10

    def test_generate_group_report(self, mock_extractor, sample_group_df):
        """Test generating a group report."""
        generator = ReportGenerator(mock_extractor)

        report = generator.generate_group_report(sample_group_df)

        assert report.group_id == "group123"
        assert report.member_count == 3  # 3 unique methods
        assert report.match_type == "CLONE_MATCH"
        assert report.avg_similarity is not None
        assert len(report.members) == 3
        # Verify members are MemberInfo objects with metadata
        for member in report.members:
            assert isinstance(member, MemberInfo)
            assert member.state is not None
            assert member.code_snippet is not None

    def test_generate_group_report_empty_df(self, mock_extractor):
        """Test generating report from empty DataFrame."""
        generator = ReportGenerator(mock_extractor)

        with pytest.raises(ValueError, match="empty DataFrame"):
            generator.generate_group_report(pd.DataFrame())

    def test_generate_group_report_missing_rev_status(self, mock_extractor):
        """Test generating report without rev_status column."""
        generator = ReportGenerator(mock_extractor)

        # Create DataFrame without rev_status column
        df = pd.DataFrame(
            {
                "clone_group_id": ["group123"],
                "global_block_id": ["block_a"],
                "revision": ["rev1"],
                "function_name": ["func_a"],
                "file_path": ["pandas/core/a.py"],
                "start_line": [10],
                "end_line": [20],
                "loc": [10],
                "state": ["survived"],
            }
        )

        with pytest.raises(ValueError, match="rev_status"):
            generator.generate_group_report(df)

    def test_render_markdown(self, mock_extractor):
        """Test rendering report as Markdown."""
        generator = ReportGenerator(mock_extractor)

        snippet_a = CodeSnippet(
            function_name="func_a",
            file_path="pandas/core/module.py",
            revision="abc123def",
            start_line=10,
            end_line=20,
            code="def func_a():\n    return 1",
            github_url="https://github.com/pandas-dev/pandas/blob/abc123def/pandas/core/module.py#L10-L20",
        )
        snippet_b = CodeSnippet(
            function_name="func_b",
            file_path="pandas/core/other.py",
            revision="abc123def",
            start_line=30,
            end_line=40,
            code="def func_b():\n    return 2",
            github_url="https://github.com/pandas-dev/pandas/blob/abc123def/pandas/core/other.py#L30-L40",
        )

        members = [
            MemberInfo(
                global_block_id="block_a",
                revision="abc123def",
                function_name="func_a",
                file_path="pandas/core/module.py",
                start_line=10,
                end_line=20,
                loc=10,
                state="survived",
                state_detail=None,
                match_type="CLONE_MATCH",
                match_similarity=92.5,
                clone_count=2,
                clone_group_id="test_group_123",
                clone_group_size=2,
                avg_similarity_to_group=92.5,
                lifetime_revisions=5,
                lifetime_days=100,
                code_snippet=snippet_a,
            ),
            MemberInfo(
                global_block_id="block_b",
                revision="abc123def",
                function_name="func_b",
                file_path="pandas/core/other.py",
                start_line=30,
                end_line=40,
                loc=10,
                state="deleted",
                state_detail=None,
                match_type="CLONE_MATCH",
                match_similarity=92.5,
                clone_count=2,
                clone_group_id="test_group_123",
                clone_group_size=2,
                avg_similarity_to_group=92.5,
                lifetime_revisions=5,
                lifetime_days=100,
                code_snippet=snippet_b,
            ),
        ]

        report = CloneGroupReport(
            group_id="test_group_123",
            member_count=2,
            match_type="CLONE_MATCH",
            avg_similarity=92.5,
            members=members,
        )

        markdown = generator.render_markdown(report)

        # Check header
        assert "# Clone Group Report: `test_gro`" in markdown

        # Check overview table
        assert "| Members | 2 |" in markdown
        assert "| Match Type | CLONE_MATCH |" in markdown
        assert "| Avg Similarity | 92.5% |" in markdown

        # Check members table
        assert "`func_a`" in markdown
        assert "`func_b`" in markdown
        assert "[GitHub](" in markdown
        # Check state column
        assert "survived" in markdown
        assert "deleted" in markdown

        # Check code blocks
        assert "```python" in markdown
        assert "def func_a():" in markdown
        assert "def func_b():" in markdown

        # Check notes section
        assert "## Analysis Notes" in markdown
        assert "- [ ] Type-1 (identical)" in markdown

    def test_render_markdown_no_similarity(self, mock_extractor):
        """Test rendering report without similarity data."""
        generator = ReportGenerator(mock_extractor)

        report = CloneGroupReport(
            group_id="test_group",
            member_count=1,
            match_type=None,
            avg_similarity=None,
            members=[],
        )

        markdown = generator.render_markdown(report)

        assert "| Match Type | N/A |" in markdown
        assert "| Avg Similarity | N/A |" in markdown

    def test_save_report(self, mock_extractor, tmp_path):
        """Test saving report to file."""
        generator = ReportGenerator(mock_extractor)

        report = CloneGroupReport(
            group_id="test_save_group",
            member_count=0,
            match_type=None,
            avg_similarity=None,
            members=[],
        )

        output_path = generator.save_report(report, tmp_path)

        assert output_path.exists()
        assert output_path.name == "CloneGroup_test_sav.md"
        assert output_path.parent == tmp_path

        content = output_path.read_text()
        assert "# Clone Group Report:" in content

    def test_save_report_custom_filename(self, mock_extractor, tmp_path):
        """Test saving report with custom filename."""
        generator = ReportGenerator(mock_extractor)

        report = CloneGroupReport(
            group_id="test_group",
            member_count=0,
            match_type=None,
            avg_similarity=None,
            members=[],
        )

        output_path = generator.save_report(report, tmp_path, filename="custom_report.md")

        assert output_path.name == "custom_report.md"

    def test_save_report_creates_directory(self, mock_extractor, tmp_path):
        """Test that save_report creates output directory if needed."""
        generator = ReportGenerator(mock_extractor)

        report = CloneGroupReport(
            group_id="test_group",
            member_count=0,
            match_type=None,
            avg_similarity=None,
            members=[],
        )

        nested_dir = tmp_path / "nested" / "output"
        output_path = generator.save_report(report, nested_dir)

        assert nested_dir.exists()
        assert output_path.exists()
