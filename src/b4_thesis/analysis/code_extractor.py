"""Git code extraction for clone analysis reports."""

from dataclasses import dataclass
from pathlib import Path
import subprocess


@dataclass
class CodeSnippet:
    """Extracted code snippet with metadata."""

    function_name: str
    file_path: str
    revision: str
    start_line: int
    end_line: int
    code: str
    github_url: str | None = None


@dataclass
class ExtractRequest:
    """Request for code extraction."""

    function_name: str
    file_path: str
    revision: str
    start_line: int
    end_line: int
    global_block_id: str | None = None


class GitCodeExtractor:
    """Extract code from Git repository using git show command.

    This class uses `git show revision:path` instead of `git checkout`
    to avoid modifying the working tree and enable safe parallel processing.
    """

    def __init__(
        self,
        repo_path: Path,
        base_path_prefix: str = "/app/Repos/pandas/",
        github_base_url: str | None = "https://github.com/pandas-dev/pandas/blob/",
    ) -> None:
        """
        Initialize GitCodeExtractor.

        Args:
            repo_path: Path to the Git repository
            base_path_prefix: Prefix to remove from file paths (from CSV data)
            github_base_url: Base URL for GitHub permalinks (None to disable)
        """
        self.repo_path = Path(repo_path)
        self.base_path_prefix = base_path_prefix
        self.github_base_url = github_base_url

        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")

        if not (self.repo_path / ".git").exists():
            raise ValueError(f"Not a Git repository: {repo_path}")

    def _parse_revision(self, revision: str) -> str:
        """Extract git hash from revision string.

        Handles the format 'YYYYMMDD_HHMMSS_<git-hash>' used in clone analysis data.
        If the revision doesn't contain underscores, it's returned as-is.

        Args:
            revision: Revision string (e.g., '20130212_043101_13c5d72a' or '13c5d72a')

        Returns:
            Git commit hash (e.g., '13c5d72a')
        """
        if "_" in revision:
            return revision.split("_")[-1]
        return revision

    def _clean_path(self, file_path: str) -> str:
        """Remove base path prefix from file path.

        Args:
            file_path: Original file path from CSV

        Returns:
            Relative path for git operations
        """
        if file_path.startswith(self.base_path_prefix):
            return file_path[len(self.base_path_prefix) :]
        return file_path

    def _generate_github_url(
        self, revision: str, relative_path: str, start_line: int, end_line: int
    ) -> str | None:
        """Generate GitHub permalink.

        Args:
            revision: Git commit hash
            relative_path: Relative file path in repository
            start_line: Start line number
            end_line: End line number

        Returns:
            GitHub URL or None if github_base_url is not set
        """
        if not self.github_base_url:
            return None

        return f"{self.github_base_url}{revision}/{relative_path}#L{start_line}-L{end_line}"

    def _extract_code(
        self,
        git_revision: str,
        relative_path: str,
        start_line: int,
        end_line: int,
    ) -> str:
        """Extract code from a specific revision.

        Uses `git show revision:path` to read file content without checkout.

        Args:
            revision: Git commit hash
            file_path: File path (will be cleaned of prefix)
            start_line: Start line number (1-based)
            end_line: End line number (1-based, inclusive)

        Returns:
            Extracted code as string

        Raises:
            RuntimeError: If git command fails
        """
        try:
            result = subprocess.run(
                ["git", "show", f"{git_revision}:{relative_path}"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip()
                raise RuntimeError(
                    f"Failed to extract code from {git_revision}:{relative_path}: {error_msg}"
                )

            lines = result.stdout.splitlines()

            # Convert to 0-based indexing for slicing
            start_idx = max(0, start_line - 1)
            end_idx = min(len(lines), end_line)

            return "\n".join(lines[start_idx:end_idx])

        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"Git command timed out for {git_revision}:{relative_path}") from e

    def _extract_snippet(self, request: ExtractRequest) -> CodeSnippet:
        """Extract a code snippet based on an extraction request.

        Args:
            request: ExtractRequest with file location details

        Returns:
            CodeSnippet with extracted code and metadata
        """
        relative_path = self._clean_path(request.file_path)
        git_revision = self._parse_revision(request.revision)

        code = self._extract_code(
            git_revision,
            relative_path,
            request.start_line,
            request.end_line,
        )

        github_url = self._generate_github_url(
            git_revision,
            relative_path,
            request.start_line,
            request.end_line,
        )

        return CodeSnippet(
            function_name=request.function_name,
            file_path=relative_path,
            revision=request.revision,
            start_line=request.start_line,
            end_line=request.end_line,
            code=code,
            github_url=github_url,
        )

    def batch_extract(
        self,
        requests: list[ExtractRequest],
    ) -> list[CodeSnippet]:
        """Extract multiple code snippets.

        Args:
            requests: List of extraction requests

        Returns:
            List of CodeSnippet objects (in same order as input if not sorted)
        """
        if not requests:
            return []

        # sort by revision to minimize context switches
        indexed_requests = list(enumerate(requests))
        indexed_requests.sort(key=lambda x: x[1].revision)

        results: list[tuple[int, CodeSnippet]] = []
        for original_idx, request in indexed_requests:
            snippet = self._extract_snippet(request)
            results.append((original_idx, snippet))

        # Restore original order
        results.sort(key=lambda x: x[0])
        return [snippet for _, snippet in results]
