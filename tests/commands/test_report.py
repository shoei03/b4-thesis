"""Tests for report command."""

import subprocess

from click.testing import CliRunner
import pandas as pd
import pytest

from b4_thesis.cli import main


class TestReportCloneGroups:
    """Test suite for report clone-groups command."""

    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()

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

        # Create subdirectory for pandas-like structure
        pandas_dir = repo_path / "pandas" / "core"
        pandas_dir.mkdir(parents=True)

        # Create test files
        (pandas_dir / "a.py").write_text("def func_a():\n    value = 1\n    return value\n")
        (pandas_dir / "b.py").write_text("def func_b():\n    value = 2\n    return value\n")

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

    @pytest.fixture
    def sample_lineage_csv(self, tmp_path, temp_git_repo):
        """Create a sample partial_deleted.csv for testing."""
        _, commit_hash = temp_git_repo

        data = {
            "global_block_id": ["block_a", "block_b"],
            "revision": [commit_hash, commit_hash],
            "function_name": ["func_a", "func_b"],
            "file_path": ["pandas/core/a.py", "pandas/core/b.py"],
            "start_line": [1, 1],
            "end_line": [3, 3],
            "loc": [3, 3],
            "state": ["survived", "survived"],
            "state_detail": ["remained_clone", "remained_clone"],
            "match_type": ["CLONE_MATCH", "CLONE_MATCH"],
            "match_similarity": [85.0, 85.0],
            "clone_count": [1, 1],
            "clone_group_id": ["group123", "group123"],
            "clone_group_size": [2, 2],
            "avg_similarity_to_group": [90.0, 90.0],
            "lifetime_revisions": [5, 5],
            "lifetime_days": [30, 30],
            "rev_status": ["partial_deleted", "partial_deleted"],
        }
        df = pd.DataFrame(data)

        csv_file = tmp_path / "partial_deleted.csv"
        df.to_csv(csv_file, index=False)
        return csv_file

    @pytest.fixture
    def sample_lineage_no_clones(self, tmp_path):
        """Create a sample CSV without clone groups."""
        data = {
            "global_block_id": ["block_a"],
            "revision": ["abc123"],
            "function_name": ["func_a"],
            "file_path": ["test.py"],
            "start_line": [1],
            "end_line": [5],
            "loc": [5],
            "state": ["survived"],
            "state_detail": ["non_clone"],
            "match_type": ["none"],
            "match_similarity": [None],
            "clone_count": [0],
            "clone_group_id": [None],
            "clone_group_size": [1],
            "avg_similarity_to_group": [None],
            "lifetime_revisions": [1],
            "lifetime_days": [0],
            "rev_status": ["no_deleted"],
        }
        df = pd.DataFrame(data)

        csv_file = tmp_path / "no_clones.csv"
        df.to_csv(csv_file, index=False)
        return csv_file

    def test_report_help(self, runner):
        """Test report command help."""
        result = runner.invoke(main, ["report", "--help"])

        assert result.exit_code == 0
        assert "clone-groups" in result.output

    def test_clone_groups_help(self, runner):
        """Test clone-groups subcommand help."""
        result = runner.invoke(main, ["report", "clone-groups", "--help"])

        assert result.exit_code == 0
        assert "CSV_PATH" in result.output
        assert "REPO_PATH" in result.output
        assert "--output" in result.output
        assert "--group-id" in result.output

    def test_clone_groups_dry_run(self, runner, sample_lineage_csv, temp_git_repo):
        """Test clone-groups with dry-run flag."""
        repo_path, _ = temp_git_repo

        result = runner.invoke(
            main,
            [
                "report",
                "clone-groups",
                str(sample_lineage_csv),
                str(repo_path),
                "--base-path",
                "",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        assert "Clone Groups Preview" in result.output
        assert "group123" in result.output
        assert "Dry run" in result.output

    def test_clone_groups_generate_report(
        self, runner, sample_lineage_csv, temp_git_repo, tmp_path
    ):
        """Test generating actual report."""
        repo_path, _ = temp_git_repo
        output_dir = tmp_path / "reports"

        result = runner.invoke(
            main,
            [
                "report",
                "clone-groups",
                str(sample_lineage_csv),
                str(repo_path),
                "--output",
                str(output_dir),
                "--base-path",
                "",
                "--github-url",
                "",
            ],
        )

        assert result.exit_code == 0
        assert "Generated" in result.output
        assert output_dir.exists()

        # Check report file was created
        report_files = list(output_dir.glob("*.md"))
        assert len(report_files) == 1
        assert "CloneGroup_group123" in report_files[0].name

        # Check report content
        content = report_files[0].read_text()
        assert "# Clone Group Report:" in content
        assert "func_a" in content
        assert "func_b" in content

    def test_clone_groups_no_clones(self, runner, sample_lineage_no_clones, temp_git_repo):
        """Test with CSV that has no clone groups."""
        repo_path, _ = temp_git_repo

        result = runner.invoke(
            main,
            [
                "report",
                "clone-groups",
                str(sample_lineage_no_clones),
                str(repo_path),
            ],
        )

        assert result.exit_code == 0
        assert "No records with clone_group_id found" in result.output

    def test_clone_groups_specific_group_id(
        self, runner, sample_lineage_csv, temp_git_repo, tmp_path
    ):
        """Test filtering by specific group ID."""
        repo_path, _ = temp_git_repo
        output_dir = tmp_path / "reports"

        result = runner.invoke(
            main,
            [
                "report",
                "clone-groups",
                str(sample_lineage_csv),
                str(repo_path),
                "--output",
                str(output_dir),
                "--group-id",
                "group123",
                "--base-path",
                "",
                "--github-url",
                "",
            ],
        )

        assert result.exit_code == 0
        assert "Generated" in result.output

    def test_clone_groups_nonexistent_group_id(self, runner, sample_lineage_csv, temp_git_repo):
        """Test filtering by nonexistent group ID."""
        repo_path, _ = temp_git_repo

        result = runner.invoke(
            main,
            [
                "report",
                "clone-groups",
                str(sample_lineage_csv),
                str(repo_path),
                "--group-id",
                "nonexistent_group",
            ],
        )

        assert result.exit_code == 0
        assert "No records found for group IDs" in result.output

    def test_clone_groups_missing_csv(self, runner, temp_git_repo, tmp_path):
        """Test with nonexistent CSV file."""
        repo_path, _ = temp_git_repo

        result = runner.invoke(
            main,
            [
                "report",
                "clone-groups",
                str(tmp_path / "nonexistent.csv"),
                str(repo_path),
            ],
        )

        assert result.exit_code != 0

    def test_clone_groups_invalid_repo(self, runner, sample_lineage_csv, tmp_path):
        """Test with invalid repository path."""
        not_a_repo = tmp_path / "not_a_repo"
        not_a_repo.mkdir()

        result = runner.invoke(
            main,
            [
                "report",
                "clone-groups",
                str(sample_lineage_csv),
                str(not_a_repo),
            ],
        )

        assert result.exit_code != 0
        assert "Not a Git repository" in result.output

    def test_clone_groups_verbose(self, runner, sample_lineage_csv, temp_git_repo, tmp_path):
        """Test verbose output."""
        repo_path, _ = temp_git_repo
        output_dir = tmp_path / "reports"

        result = runner.invoke(
            main,
            [
                "report",
                "clone-groups",
                str(sample_lineage_csv),
                str(repo_path),
                "--output",
                str(output_dir),
                "--base-path",
                "",
                "--github-url",
                "",
                "--verbose",
            ],
        )

        assert result.exit_code == 0
        assert "Total records" in result.output
        assert "Records with clone_group_id" in result.output

    def test_clone_groups_missing_columns(self, runner, temp_git_repo, tmp_path):
        """Test with CSV missing required columns."""
        repo_path, _ = temp_git_repo

        # Create CSV with missing columns
        df = pd.DataFrame({"some_column": [1, 2, 3]})
        csv_file = tmp_path / "bad.csv"
        df.to_csv(csv_file, index=False)

        result = runner.invoke(
            main,
            [
                "report",
                "clone-groups",
                str(csv_file),
                str(repo_path),
            ],
        )

        assert result.exit_code != 0
        assert "Missing required columns" in result.output

    def test_clone_groups_missing_rev_status(self, runner, temp_git_repo, tmp_path):
        """Test with CSV missing rev_status column (shows helpful hint)."""
        repo_path, _ = temp_git_repo

        # Create CSV without rev_status column
        data = {
            "global_block_id": ["block_a"],
            "revision": ["abc123"],
            "function_name": ["func_a"],
            "file_path": ["test.py"],
            "start_line": [1],
            "end_line": [5],
            "loc": [5],
            "clone_group_id": ["group123"],
        }
        df = pd.DataFrame(data)
        csv_file = tmp_path / "no_rev_status.csv"
        df.to_csv(csv_file, index=False)

        result = runner.invoke(
            main,
            [
                "report",
                "clone-groups",
                str(csv_file),
                str(repo_path),
            ],
        )

        assert result.exit_code != 0
        assert "Missing required columns" in result.output
        assert "rev_status" in result.output
        assert "label filter" in result.output
