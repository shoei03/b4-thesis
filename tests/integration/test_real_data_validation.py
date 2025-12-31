"""Real data validation tests for the b4-thesis tool.

This module contains integration tests that use real repository data
to validate the tool's functionality with actual production data.
"""

import os
from pathlib import Path
import time

from click.testing import CliRunner
import pytest

from b4_thesis.commands.nil import track
import pandas as pd

# Path to real data directory
REAL_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "clone_NIL"


def has_real_data():
    """Check if real data directory exists and has data."""
    if not REAL_DATA_DIR.exists():
        return False
    # Check if there are at least 3 revision directories
    revision_dirs = [d for d in REAL_DATA_DIR.iterdir() if d.is_dir()]
    return len(revision_dirs) >= 3


def is_ci():
    """Check if running in CI environment."""
    return os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"


@pytest.fixture
def runner():
    """Create CLI runner."""
    return CliRunner()


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def small_real_data_subset(tmp_path):
    """Create a small subset (2 revisions) of real data for testing.

    This fixture creates symbolic links to 2 non-empty revisions
    to avoid copying large files.
    """
    if not has_real_data():
        pytest.skip("Real data not available")

    # Get all revision directories (sorted by name)
    all_revisions = sorted([d for d in REAL_DATA_DIR.iterdir() if d.is_dir()])

    # Filter out empty revisions (those with empty code_blocks.csv)
    non_empty_revisions = []
    for rev_dir in all_revisions:
        code_blocks_file = rev_dir / "code_blocks.csv"
        # At least 100 bytes to be considered non-empty
        if code_blocks_file.exists() and code_blocks_file.stat().st_size > 100:
            non_empty_revisions.append(rev_dir)
            if len(non_empty_revisions) >= 2:  # We only need 2 revisions
                break

    if len(non_empty_revisions) < 2:
        pytest.skip("Not enough non-empty revisions available")

    # Create subset directory
    subset_dir = tmp_path / "real_data_subset_small"
    subset_dir.mkdir()

    # Create symbolic links for the first 2 non-empty revisions
    for rev_dir in non_empty_revisions:
        link_path = subset_dir / rev_dir.name
        link_path.symlink_to(rev_dir)

    return subset_dir


@pytest.fixture
def medium_real_data_subset(tmp_path):
    """Create a medium subset (3 revisions) of real data for testing.

    This fixture creates symbolic links to 3 non-empty revisions.
    """
    if not has_real_data():
        pytest.skip("Real data not available")

    # Get all revision directories (sorted by name)
    all_revisions = sorted([d for d in REAL_DATA_DIR.iterdir() if d.is_dir()])

    # Filter out empty revisions
    non_empty_revisions = []
    for rev_dir in all_revisions:
        code_blocks_file = rev_dir / "code_blocks.csv"
        if code_blocks_file.exists() and code_blocks_file.stat().st_size > 100:
            non_empty_revisions.append(rev_dir)
            if len(non_empty_revisions) >= 3:  # We need 3 revisions for medium test
                break

    if len(non_empty_revisions) < 3:
        pytest.skip("Not enough non-empty revisions available")

    # Create subset directory
    subset_dir = tmp_path / "real_data_subset_medium"
    subset_dir.mkdir()

    # Create symbolic links
    for rev_dir in non_empty_revisions:
        link_path = subset_dir / rev_dir.name
        link_path.symlink_to(rev_dir)

    return subset_dir


@pytest.mark.skipif(not has_real_data(), reason="Real data not available")
class TestSmallRealDataset:
    """Tests with small real dataset (3 revisions)."""

    def test_method_tracking_with_real_data(self, runner, small_real_data_subset, temp_output_dir):
        """Test method tracking with small real dataset."""
        # Execute track methods command
        result = runner.invoke(
            track,
            [
                "methods",
                "--input",
                str(small_real_data_subset),
                "--output",
                str(temp_output_dir),
            ],
        )

        # Verify command execution
        assert result.exit_code == 0, f"Command failed with output:\n{result.output}"

        # Verify output file exists
        output_file = temp_output_dir / "method_tracking.csv"
        assert output_file.exists(), "Method tracking CSV not created"

        # Load and verify CSV content
        df = pd.read_csv(output_file)

        # Verify basic structure
        assert len(df) > 0, "No data in output CSV"
        assert "revision" in df.columns
        assert "block_id" in df.columns
        assert "state" in df.columns

        # Verify we have data from 2 revisions
        assert df["revision"].nunique() == 2, (
            f"Expected 2 revisions, got {df['revision'].nunique()}"
        )

        # Verify data types
        assert df["block_id"].dtype == object
        assert df["state"].dtype == object
        assert pd.api.types.is_numeric_dtype(df["lifetime_revisions"])
        assert pd.api.types.is_numeric_dtype(df["lifetime_days"])

        # Verify lifetime values are reasonable
        assert df["lifetime_revisions"].min() >= 1
        assert df["lifetime_days"].min() >= 0

    def test_group_tracking_with_real_data(self, runner, small_real_data_subset, temp_output_dir):
        """Test group tracking with small real dataset."""
        # Execute track groups command
        result = runner.invoke(
            track,
            [
                "groups",
                "--input",
                str(small_real_data_subset),
                "--output",
                str(temp_output_dir),
            ],
        )

        # Verify command execution
        assert result.exit_code == 0, f"Command failed with output:\n{result.output}"

        # Verify output files exist
        group_file = temp_output_dir / "group_tracking.csv"
        membership_file = temp_output_dir / "group_membership.csv"
        assert group_file.exists(), "Group tracking CSV not created"
        assert membership_file.exists(), "Membership CSV not created"

        # Load CSVs
        df_groups = pd.read_csv(group_file)
        df_membership = pd.read_csv(membership_file)

        # Verify basic structure
        assert "revision" in df_groups.columns
        assert "group_id" in df_groups.columns
        assert "state" in df_groups.columns
        assert "member_count" in df_groups.columns

        # Verify membership structure
        assert "revision" in df_membership.columns
        assert "group_id" in df_membership.columns
        assert "block_id" in df_membership.columns

        # Verify data consistency: member_count should match actual members
        for revision in df_groups["revision"].unique():
            groups_in_rev = df_groups[df_groups["revision"] == revision]
            members_in_rev = df_membership[df_membership["revision"] == revision]

            total_member_count = groups_in_rev["member_count"].sum()
            actual_members = len(members_in_rev)

            assert total_member_count == actual_members, (
                f"Member count mismatch in {revision}: {total_member_count} vs {actual_members}"
            )


@pytest.mark.skipif(not has_real_data(), reason="Real data not available")
class TestMediumRealDataset:
    """Tests with medium real dataset (3 revisions)."""

    @pytest.mark.ci
    @pytest.mark.skipif(not is_ci(), reason="Performance test only runs in CI")
    def test_track_all_performance(self, runner, medium_real_data_subset, temp_output_dir):
        """Test tracking with medium dataset and measure performance."""
        # Measure execution time
        start_time = time.time()

        # Run track methods
        result = runner.invoke(
            track,
            [
                "methods",
                "--input",
                str(medium_real_data_subset),
                "--output",
                str(temp_output_dir),
                "--verbose",
                "--optimize",
            ],
        )
        assert result.exit_code == 0, f"Methods command failed with output:\n{result.output}"

        # Run track groups
        result = runner.invoke(
            track,
            [
                "groups",
                "--input",
                str(medium_real_data_subset),
                "--output",
                str(temp_output_dir),
                "--verbose",
                "--optimize",
            ],
        )
        assert result.exit_code == 0, f"Groups command failed with output:\n{result.output}"

        elapsed_time = time.time() - start_time

        # Performance check: should complete in reasonable time
        # For 3 revisions, allow up to 3 minutes (this is generous for testing)
        assert elapsed_time < 180, f"Processing took too long: {elapsed_time:.2f} seconds"

        # Verify outputs exist and have data
        method_file = temp_output_dir / "method_tracking.csv"
        group_file = temp_output_dir / "group_tracking.csv"

        assert method_file.exists()
        assert group_file.exists()

        df_methods = pd.read_csv(method_file)
        df_groups = pd.read_csv(group_file)

        # Should have 3 revisions
        assert df_methods["revision"].nunique() == 3

        # Print some stats for debugging
        print("\nPerformance stats for 3 revisions:")
        print(f"  - Elapsed time: {elapsed_time:.2f} seconds")
        print(f"  - Total methods tracked: {len(df_methods)}")
        print(f"  - Total groups tracked: {len(df_groups)}")
        print(f"  - Unique revisions: {df_methods['revision'].nunique()}")


@pytest.mark.skipif(not has_real_data(), reason="Real data not available")
class TestRealDataQuality:
    """Tests for data quality with real data."""

    def test_no_invalid_states(self, runner, small_real_data_subset, temp_output_dir):
        """Test that all state values are valid."""
        result = runner.invoke(
            track,
            [
                "methods",
                "--input",
                str(small_real_data_subset),
                "--output",
                str(temp_output_dir),
            ],
        )

        assert result.exit_code == 0

        df = pd.read_csv(temp_output_dir / "method_tracking.csv")

        # Define valid states
        valid_states = [
            "deleted",
            "deleted_isolated",
            "deleted_from_group",
            "survived",
            "survived_unchanged",
            "survived_modified",
            "survived_clone_unchanged",
            "survived_clone_modified",
            "added",
            "added_isolated",
            "added_to_group",
        ]

        # Check all states are valid
        invalid_states = df[~df["state"].isin(valid_states)]["state"].unique()
        assert len(invalid_states) == 0, f"Found invalid states: {invalid_states}"

    def test_no_missing_critical_columns(self, runner, small_real_data_subset, temp_output_dir):
        """Test that critical columns have no missing values."""
        result = runner.invoke(
            track,
            [
                "methods",
                "--input",
                str(small_real_data_subset),
                "--output",
                str(temp_output_dir),
            ],
        )

        assert result.exit_code == 0

        df_methods = pd.read_csv(temp_output_dir / "method_tracking.csv")

        # Critical columns that should never have missing values
        critical_columns = ["revision", "block_id", "state", "lifetime_revisions", "lifetime_days"]

        for col in critical_columns:
            missing_count = df_methods[col].isna().sum()
            assert missing_count == 0, (
                f"Column '{col}' has {missing_count} missing values (should be 0)"
            )

    def test_lifetime_consistency(self, runner, small_real_data_subset, temp_output_dir):
        """Test that lifetime values are consistent and reasonable."""
        result = runner.invoke(
            track,
            [
                "methods",
                "--input",
                str(small_real_data_subset),
                "--output",
                str(temp_output_dir),
            ],
        )

        assert result.exit_code == 0

        df = pd.read_csv(temp_output_dir / "method_tracking.csv")

        # Test 1: All lifetime_revisions should be >= 1
        assert df["lifetime_revisions"].min() >= 1, "lifetime_revisions should be at least 1"

        # Test 2: All lifetime_days should be >= 0
        assert df["lifetime_days"].min() >= 0, "lifetime_days should be non-negative"

        # Test 3: For survived methods, lifetime should be >= 2
        survived_methods = df[df["state"].str.contains("survived", case=False)]
        if len(survived_methods) > 0:
            assert survived_methods["lifetime_revisions"].min() >= 2, (
                "Survived methods should have lifetime >= 2"
            )

    def test_clone_group_metrics(self, runner, small_real_data_subset, temp_output_dir):
        """Test that clone group metrics are within valid ranges."""
        result = runner.invoke(
            track,
            [
                "groups",
                "--input",
                str(small_real_data_subset),
                "--output",
                str(temp_output_dir),
            ],
        )

        assert result.exit_code == 0

        group_file = temp_output_dir / "group_tracking.csv"
        if not group_file.exists():
            pytest.skip("No groups detected in real data")

        df_groups = pd.read_csv(group_file)

        if len(df_groups) == 0:
            pytest.skip("No groups in output")

        # Test 1: member_count should be >= 1 (groups must have at least 1 member)
        assert df_groups["member_count"].min() >= 1, "Groups should have at least 1 member"

        # Test 2: density should be between 0 and 1
        assert df_groups["density"].min() >= 0, (
            f"Density should be >= 0, got {df_groups['density'].min()}"
        )
        assert df_groups["density"].max() <= 1, (
            f"Density should be <= 1, got {df_groups['density'].max()}"
        )

        # Test 3: similarity values should be between 0 and 100
        assert df_groups["avg_similarity"].min() >= 0, (
            f"avg_similarity should be >= 0, got {df_groups['avg_similarity'].min()}"
        )
        assert df_groups["avg_similarity"].max() <= 100, (
            f"avg_similarity should be <= 100, got {df_groups['avg_similarity'].max()}"
        )
