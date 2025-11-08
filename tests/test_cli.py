"""Tests for CLI commands."""

from click.testing import CliRunner
import pytest

from b4_thesis.cli import main


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


def test_main_help(runner):
    """Test main help command."""
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Software Engineering Research Analysis Tool" in result.output


def test_version(runner):
    """Test version command."""
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_analyze_help(runner):
    """Test analyze help command."""
    result = runner.invoke(main, ["analyze", "--help"])
    assert result.exit_code == 0
    assert "Analyze software repository" in result.output


def test_stats_help(runner):
    """Test stats help command."""
    result = runner.invoke(main, ["stats", "--help"])
    assert result.exit_code == 0
    assert "Compute statistical metrics" in result.output


def test_visualize_help(runner):
    """Test visualize help command."""
    result = runner.invoke(main, ["visualize", "--help"])
    assert result.exit_code == 0
    assert "Create visualizations" in result.output
