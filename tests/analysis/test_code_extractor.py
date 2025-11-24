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

    def test_clean_path(self, temp_git_repo):
        """Test path cleaning."""
        repo_path, _ = temp_git_repo
        extractor = GitCodeExtractor(repo_path)

        # With prefix
        cleaned = extractor._clean_path("/app/Repos/pandas/pandas/core/frame.py")
        assert cleaned == "pandas/core/frame.py"

        # Without prefix
        assert extractor._clean_path("pandas/core/frame.py") == "pandas/core/frame.py"

    def test_parse_revision_with_timestamp(self, temp_git_repo):
        """Test parsing revision with timestamp prefix."""
        repo_path, _ = temp_git_repo
        extractor = GitCodeExtractor(repo_path)

        # Format: YYYYMMDD_HHMMSS_<git-hash>
        assert extractor._parse_revision("20130212_043101_13c5d72a") == "13c5d72a"
        assert extractor._parse_revision("20121101_053615_026bc001") == "026bc001"
        assert extractor._parse_revision("20120529_212811_10e3edea") == "10e3edea"

    def test_parse_revision_plain_hash(self, temp_git_repo):
        """Test parsing plain git hash (no transformation)."""
        repo_path, _ = temp_git_repo
        extractor = GitCodeExtractor(repo_path)

        # Plain hash should be returned as-is
        assert extractor._parse_revision("abc123def") == "abc123def"
        assert extractor._parse_revision("13c5d72a") == "13c5d72a"

    def test_extract_code_with_timestamp_revision(self, temp_git_repo):
        """Test extracting code with timestamp-prefixed revision."""
        repo_path, commit_hash = temp_git_repo
        extractor = GitCodeExtractor(repo_path, base_path_prefix="")

        # Create timestamp-prefixed revision
        timestamp_revision = f"20230101_120000_{commit_hash[:8]}"

        # This should work because _parse_revision extracts the hash part
        code = extractor.extract_code(timestamp_revision, "test.py", 3, 4)

        assert "def hello():" in code
        assert "print('Hello')" in code

    def test_generate_github_url(self, temp_git_repo):
        """Test GitHub URL generation."""
        repo_path, _ = temp_git_repo
        extractor = GitCodeExtractor(
            repo_path, github_base_url="https://github.com/pandas-dev/pandas/blob/"
        )

        url = extractor._generate_github_url("abc123", "pandas/core/frame.py", 10, 20)

        assert (
            url == "https://github.com/pandas-dev/pandas/blob/abc123/pandas/core/frame.py#L10-L20"
        )

    def test_generate_github_url_disabled(self, temp_git_repo):
        """Test GitHub URL generation when disabled."""
        repo_path, _ = temp_git_repo
        extractor = GitCodeExtractor(repo_path, github_base_url=None)

        url = extractor._generate_github_url("abc123", "pandas/core/frame.py", 10, 20)

        assert url is None

    def test_extract_code(self, temp_git_repo):
        """Test extracting code from repository."""
        repo_path, commit_hash = temp_git_repo
        extractor = GitCodeExtractor(repo_path, base_path_prefix="")

        code = extractor.extract_code(commit_hash, "test.py", 3, 4)

        assert "def hello():" in code
        assert "print('Hello')" in code

    def test_extract_code_single_line(self, temp_git_repo):
        """Test extracting a single line."""
        repo_path, commit_hash = temp_git_repo
        extractor = GitCodeExtractor(repo_path, base_path_prefix="")

        code = extractor.extract_code(commit_hash, "test.py", 1, 1)

        assert code == "# Line 1"

    def test_extract_code_invalid_revision(self, temp_git_repo):
        """Test extracting with invalid revision."""
        repo_path, _ = temp_git_repo
        extractor = GitCodeExtractor(repo_path, base_path_prefix="")

        with pytest.raises(RuntimeError, match="Failed to extract"):
            extractor.extract_code("invalid_revision", "test.py", 1, 5)

    def test_extract_code_invalid_file(self, temp_git_repo):
        """Test extracting with invalid file path."""
        repo_path, commit_hash = temp_git_repo
        extractor = GitCodeExtractor(repo_path, base_path_prefix="")

        with pytest.raises(RuntimeError, match="Failed to extract"):
            extractor.extract_code(commit_hash, "nonexistent.py", 1, 5)

    def test_extract_snippet(self, temp_git_repo):
        """Test extracting a code snippet."""
        repo_path, commit_hash = temp_git_repo
        extractor = GitCodeExtractor(repo_path, base_path_prefix="")

        request = ExtractRequest(
            function_name="hello",
            file_path="test.py",
            revision=commit_hash,
            start_line=3,
            end_line=4,
        )

        snippet = extractor.extract_snippet(request)

        assert snippet.function_name == "hello"
        assert snippet.file_path == "test.py"
        assert snippet.revision == commit_hash
        assert "def hello():" in snippet.code
        assert snippet.github_url is not None

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

    def test_check_revision_exists(self, temp_git_repo):
        """Test checking if revision exists."""
        repo_path, commit_hash = temp_git_repo
        extractor = GitCodeExtractor(repo_path)

        assert extractor.check_revision_exists(commit_hash) is True
        assert extractor.check_revision_exists("invalid_hash") is False
