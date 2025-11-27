"""Tests for code extractor module."""

import subprocess

import pytest

from b4_thesis.analysis.code_extractor import CodeSnippet, ExtractRequest, GitCodeExtractor


class TestCodeSnippet:
    """Test CodeSnippet dataclass."""

    def test_create_snippet(self):
        """Test creating a code snippet."""
        snippet = CodeSnippet(
            function_name="test_func",
            file_path="src/test.py",
            revision="abc123",
            start_line=10,
            end_line=20,
            code="def test_func():\n    pass",
            github_url="https://github.com/example/repo/blob/abc123/src/test.py#L10-L20",
        )

        assert snippet.function_name == "test_func"
        assert snippet.file_path == "src/test.py"
        assert snippet.revision == "abc123"
        assert snippet.start_line == 10
        assert snippet.end_line == 20
        assert "def test_func" in snippet.code
        assert snippet.github_url is not None

    def test_snippet_without_github_url(self):
        """Test creating a snippet without GitHub URL."""
        snippet = CodeSnippet(
            function_name="func",
            file_path="test.py",
            revision="abc",
            start_line=1,
            end_line=5,
            code="pass",
        )

        assert snippet.github_url is None


class TestExtractRequest:
    """Test ExtractRequest dataclass."""

    def test_create_request(self):
        """Test creating an extraction request."""
        request = ExtractRequest(
            function_name="my_func",
            file_path="/app/Repos/pandas/pandas/core/frame.py",
            revision="abc123def",
            start_line=100,
            end_line=150,
            global_block_id="block_001",
        )

        assert request.function_name == "my_func"
        assert request.file_path == "/app/Repos/pandas/pandas/core/frame.py"
        assert request.revision == "abc123def"
        assert request.start_line == 100
        assert request.end_line == 150
        assert request.global_block_id == "block_001"


class TestGitCodeExtractor:
    """Test GitCodeExtractor class."""

    @pytest.fixture
    def temp_git_repo(self, tmp_path):
        """Create a temporary Git repository for testing."""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Create test file
        test_file = repo_path / "test.py"
        test_file.write_text(
            "# Line 1\n"
            "# Line 2\n"
            "def hello():\n"
            "    print('Hello')\n"
            "# Line 5\n"
            "def world():\n"
            "    print('World')\n"
            "# Line 8\n"
        )

        # Commit
        subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Get commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        commit_hash = result.stdout.strip()

        return repo_path, commit_hash

    def test_init_valid_repo(self, temp_git_repo):
        """Test initializing with a valid repository."""
        repo_path, _ = temp_git_repo
        extractor = GitCodeExtractor(repo_path)

        assert extractor.repo_path == repo_path
        assert extractor.base_path_prefix == "/app/Repos/pandas/"

    def test_init_invalid_path(self, tmp_path):
        """Test initializing with non-existent path."""
        with pytest.raises(ValueError, match="does not exist"):
            GitCodeExtractor(tmp_path / "nonexistent")

    def test_init_not_git_repo(self, tmp_path):
        """Test initializing with a non-git directory."""
        (tmp_path / "not_repo").mkdir()
        with pytest.raises(ValueError, match="Not a Git repository"):
            GitCodeExtractor(tmp_path / "not_repo")

    def test_batch_extract_with_timestamp_revision(self, temp_git_repo):
        """Test batch extraction with timestamp-prefixed revision."""
        repo_path, commit_hash = temp_git_repo
        extractor = GitCodeExtractor(repo_path, base_path_prefix="")

        # Create timestamp-prefixed revision
        timestamp_revision = f"20230101_120000_{commit_hash[:8]}"

        requests = [
            ExtractRequest("hello", "test.py", timestamp_revision, 3, 4),
        ]

        snippets = extractor.batch_extract(requests)

        assert len(snippets) == 1
        assert "def hello():" in snippets[0].code
        assert "print('Hello')" in snippets[0].code

    def test_batch_extract_invalid_revision(self, temp_git_repo):
        """Test batch extraction with invalid revision."""
        repo_path, _ = temp_git_repo
        extractor = GitCodeExtractor(repo_path, base_path_prefix="")

        requests = [
            ExtractRequest("test", "test.py", "invalid_revision", 1, 5),
        ]

        with pytest.raises(RuntimeError, match="Failed to extract"):
            extractor.batch_extract(requests)

    def test_batch_extract_invalid_file(self, temp_git_repo):
        """Test batch extraction with invalid file path."""
        repo_path, commit_hash = temp_git_repo
        extractor = GitCodeExtractor(repo_path, base_path_prefix="")

        requests = [
            ExtractRequest("test", "nonexistent.py", commit_hash, 1, 5),
        ]

        with pytest.raises(RuntimeError, match="Failed to extract"):
            extractor.batch_extract(requests)

    def test_batch_extract(self, temp_git_repo):
        """Test batch extraction."""
        repo_path, commit_hash = temp_git_repo
        extractor = GitCodeExtractor(repo_path, base_path_prefix="")

        requests = [
            ExtractRequest("hello", "test.py", commit_hash, 3, 4),
            ExtractRequest("world", "test.py", commit_hash, 6, 7),
        ]

        snippets = extractor.batch_extract(requests)

        assert len(snippets) == 2
        assert snippets[0].function_name == "hello"
        assert snippets[1].function_name == "world"
        assert "def hello():" in snippets[0].code
        assert "def world():" in snippets[1].code

    def test_batch_extract_empty(self, temp_git_repo):
        """Test batch extraction with empty list."""
        repo_path, _ = temp_git_repo
        extractor = GitCodeExtractor(repo_path)

        snippets = extractor.batch_extract([])

        assert snippets == []

    def test_batch_extract_single_line(self, temp_git_repo):
        """Test batch extraction for a single line."""
        repo_path, commit_hash = temp_git_repo
        extractor = GitCodeExtractor(repo_path, base_path_prefix="")

        requests = [
            ExtractRequest("line1", "test.py", commit_hash, 1, 1),
        ]

        snippets = extractor.batch_extract(requests)

        assert len(snippets) == 1
        assert snippets[0].code == "# Line 1"

    def test_batch_extract_with_github_url(self, temp_git_repo):
        """Test batch extraction includes GitHub URLs."""
        repo_path, commit_hash = temp_git_repo
        extractor = GitCodeExtractor(
            repo_path,
            base_path_prefix="",
            github_base_url="https://github.com/test/repo/blob/",
        )

        requests = [
            ExtractRequest("hello", "test.py", commit_hash, 3, 4),
        ]

        snippets = extractor.batch_extract(requests)

        assert len(snippets) == 1
        assert snippets[0].github_url is not None
        assert "github.com" in snippets[0].github_url
        assert commit_hash in snippets[0].github_url

    def test_batch_extract_without_github_url(self, temp_git_repo):
        """Test batch extraction without GitHub URL generation."""
        repo_path, commit_hash = temp_git_repo
        extractor = GitCodeExtractor(repo_path, base_path_prefix="", github_base_url=None)

        requests = [
            ExtractRequest("hello", "test.py", commit_hash, 3, 4),
        ]

        snippets = extractor.batch_extract(requests)

        assert len(snippets) == 1
        assert snippets[0].github_url is None
