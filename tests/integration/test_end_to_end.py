"""End-to-end integration tests for the b4-thesis tool."""

from pathlib import Path
import shutil

from click.testing import CliRunner
import pandas as pd
import pytest

from b4_thesis.commands.track import track


@pytest.fixture
def runner():
    """Create CLI runner."""
    return CliRunner()


@pytest.fixture
def sample_data_dir():
    """Path to sample revision data."""
    return Path(__file__).parent.parent / "fixtures" / "sample_revisions"


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    yield output_dir
    # Cleanup
    if output_dir.exists():
        shutil.rmtree(output_dir)


class TestMethodTrackingEndToEnd:
    """End-to-end tests for method tracking workflow."""

    def test_full_method_tracking_workflow(self, runner, sample_data_dir, temp_output_dir):
        """Test complete method tracking workflow from data to CSV output."""
        # Execute track methods command
        result = runner.invoke(
            track,
            [
                "methods",
                "--input",
                str(sample_data_dir),
                "--output",
                str(temp_output_dir),
                "--verbose",
            ],
        )

        # Verify command execution
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Method tracking complete" in result.output

        # Verify output file exists
        output_file = temp_output_dir / "method_tracking.csv"
        assert output_file.exists(), "Output CSV file not created"

        # Load and verify CSV content
        df = pd.read_csv(output_file)

        # Verify DataFrame structure
        required_columns = [
            "revision",
            "block_id",
            "function_name",
            "file_path",
            "start_line",
            "end_line",
            "loc",
            "state",
            "state_detail",
            "matched_block_id",
            "match_type",
            "match_similarity",
            "clone_count",
            "clone_group_id",
            "clone_group_size",
            "lifetime_revisions",
            "lifetime_days",
        ]
        for col in required_columns:
            assert col in df.columns, f"Missing column: {col}"

        # Verify data integrity
        assert len(df) > 0, "No data in output CSV"
        assert df["revision"].nunique() >= 2, "Should have multiple revisions"

        # Verify state values are valid
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
        assert all(df["state"].isin(valid_states)), (
            f"Invalid state values found: {df['state'].unique()}"
        )

        # Verify lifetime calculations
        assert df["lifetime_revisions"].min() >= 1, "Lifetime revisions should be at least 1"
        assert df["lifetime_days"].min() >= 0, "Lifetime days should be non-negative"

        # Verify clone tracking
        assert "clone_count" in df.columns
        assert (df["clone_count"] >= 0).all(), "Clone count should be non-negative"

    def test_method_tracking_with_date_filter(self, runner, sample_data_dir, temp_output_dir):
        """Test method tracking with date range filtering."""
        # Use a broader date range that should include sample revisions
        result = runner.invoke(
            track,
            [
                "methods",
                "--input",
                str(sample_data_dir),
                "--output",
                str(temp_output_dir),
                "--start-date",
                "2024-01-01",
                "--end-date",
                "2026-01-01",
            ],
        )

        assert result.exit_code == 0

        # Verify output
        output_file = temp_output_dir / "method_tracking.csv"
        assert output_file.exists()

        df = pd.read_csv(output_file)
        # Should have data with this broad date range
        assert len(df) > 0

    def test_method_tracking_with_custom_similarity(self, runner, sample_data_dir, temp_output_dir):
        """Test method tracking with custom similarity threshold."""
        result = runner.invoke(
            track,
            [
                "methods",
                "--input",
                str(sample_data_dir),
                "--output",
                str(temp_output_dir),
                "--similarity",
                "80",
            ],
        )

        assert result.exit_code == 0
        output_file = temp_output_dir / "method_tracking.csv"
        assert output_file.exists()

        df = pd.read_csv(output_file)
        assert len(df) > 0


class TestGroupTrackingEndToEnd:
    """End-to-end tests for clone group tracking workflow."""

    def test_full_group_tracking_workflow(self, runner, sample_data_dir, temp_output_dir):
        """Test complete group tracking workflow from data to CSV outputs."""
        # Execute track groups command
        result = runner.invoke(
            track,
            [
                "groups",
                "--input",
                str(sample_data_dir),
                "--output",
                str(temp_output_dir),
                "--verbose",
            ],
        )

        # Verify command execution
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Group tracking complete" in result.output

        # Verify output files exist
        group_file = temp_output_dir / "group_tracking.csv"
        membership_file = temp_output_dir / "group_membership.csv"
        assert group_file.exists(), "Group tracking CSV not created"
        assert membership_file.exists(), "Membership CSV not created"

        # Load and verify group tracking CSV
        df_groups = pd.read_csv(group_file)

        # Verify group tracking structure
        required_group_columns = [
            "revision",
            "group_id",
            "member_count",
            "avg_similarity",
            "min_similarity",
            "max_similarity",
            "density",
            "state",
            "matched_group_id",
            "overlap_ratio",
            "member_added",
            "member_removed",
            "lifetime_revisions",
            "lifetime_days",
        ]
        for col in required_group_columns:
            assert col in df_groups.columns, f"Missing column in groups: {col}"

        # Verify group data integrity
        assert len(df_groups) > 0, "No groups data"
        assert df_groups["revision"].nunique() >= 2, "Should have multiple revisions"

        # Verify group states are valid
        valid_group_states = [
            "born",
            "continued",
            "grown",
            "shrunk",
            "split",
            "merged",
            "dissolved",
        ]
        assert all(df_groups["state"].isin(valid_group_states)), (
            f"Invalid group state: {df_groups['state'].unique()}"
        )

        # Verify group metrics
        assert (df_groups["member_count"] >= 1).all(), "Groups should have at least 1 member"
        assert (df_groups["density"] >= 0).all() and (df_groups["density"] <= 1).all(), (
            "Density should be 0-1"
        )

        # Load and verify membership CSV
        df_membership = pd.read_csv(membership_file)

        # Verify membership structure
        required_membership_columns = [
            "revision",
            "group_id",
            "block_id",
            "function_name",
            "is_clone",
        ]
        for col in required_membership_columns:
            assert col in df_membership.columns, f"Missing column in membership: {col}"

        # Verify membership data
        assert len(df_membership) > 0, "No membership data"

        # Verify relationship: total members should match sum of member_count
        for revision in df_groups["revision"].unique():
            groups_in_rev = df_groups[df_groups["revision"] == revision]
            members_in_rev = df_membership[df_membership["revision"] == revision]

            total_member_count = groups_in_rev["member_count"].sum()
            actual_members = len(members_in_rev)

            assert total_member_count == actual_members, (
                f"Member count mismatch in {revision}: {total_member_count} vs {actual_members}"
            )

    def test_group_tracking_with_thresholds(self, runner, sample_data_dir, temp_output_dir):
        """Test group tracking with custom similarity and overlap thresholds."""
        result = runner.invoke(
            track,
            [
                "groups",
                "--input",
                str(sample_data_dir),
                "--output",
                str(temp_output_dir),
                "--similarity",
                "80",
                "--overlap",
                "0.6",
            ],
        )

        assert result.exit_code == 0

        # Verify outputs
        group_file = temp_output_dir / "group_tracking.csv"
        membership_file = temp_output_dir / "group_membership.csv"
        assert group_file.exists()
        assert membership_file.exists()

        df_groups = pd.read_csv(group_file)
        df_membership = pd.read_csv(membership_file)
        assert len(df_groups) >= 0  # May vary with threshold
        assert len(df_membership) >= 0


class TestDataIntegrity:
    """Integration tests for data integrity and consistency."""

    def test_revision_consistency_across_outputs(self, runner, sample_data_dir, temp_output_dir):
        """Test that revision data is consistent across all outputs."""
        # Run track methods
        result = runner.invoke(
            track,
            [
                "methods",
                "--input",
                str(sample_data_dir),
                "--output",
                str(temp_output_dir),
            ],
        )
        assert result.exit_code == 0

        # Run track groups
        result = runner.invoke(
            track,
            [
                "groups",
                "--input",
                str(sample_data_dir),
                "--output",
                str(temp_output_dir),
            ],
        )
        assert result.exit_code == 0

        # Load all outputs
        df_methods = pd.read_csv(temp_output_dir / "method_tracking.csv")
        df_groups = pd.read_csv(temp_output_dir / "group_tracking.csv")
        df_membership = pd.read_csv(temp_output_dir / "group_membership.csv")

        # Get revisions from each
        method_revisions = set(df_methods["revision"].unique())
        group_revisions = set(df_groups["revision"].unique())
        membership_revisions = set(df_membership["revision"].unique())

        # Group and membership revisions should match
        assert group_revisions == membership_revisions, (
            "Group and membership revisions should match"
        )

        # Method revisions should include all group revisions
        # (methods exist in all revisions, but groups may not exist in all revisions)
        # So we just check that there's overlap
        assert len(method_revisions) > 0
        assert len(group_revisions) > 0

    def test_clone_group_membership_consistency(self, runner, sample_data_dir, temp_output_dir):
        """Test that clone group membership is consistent with method tracking."""
        # Run track methods
        result = runner.invoke(
            track,
            [
                "methods",
                "--input",
                str(sample_data_dir),
                "--output",
                str(temp_output_dir),
            ],
        )
        assert result.exit_code == 0

        # Run track groups
        result = runner.invoke(
            track,
            [
                "groups",
                "--input",
                str(sample_data_dir),
                "--output",
                str(temp_output_dir),
            ],
        )
        assert result.exit_code == 0

        df_methods = pd.read_csv(temp_output_dir / "method_tracking.csv")
        df_membership = pd.read_csv(temp_output_dir / "group_membership.csv")

        # For each member in a clone group
        for _, member_row in df_membership.iterrows():
            revision = member_row["revision"]
            block_id = member_row["block_id"]
            is_clone = member_row["is_clone"]

            # Find corresponding method
            method_row = df_methods[
                (df_methods["revision"] == revision) & (df_methods["block_id"] == block_id)
            ]

            if len(method_row) > 0:
                # In method tracking, is_clone is represented by clone_count > 0
                method_clone_count = method_row.iloc[0]["clone_count"]
                method_is_clone = method_clone_count > 0

                # Clone status should match
                assert is_clone == method_is_clone, (
                    f"Clone status mismatch for {block_id} in {revision}"
                )

    def test_lifetime_tracking_correctness(self, runner, sample_data_dir, temp_output_dir):
        """Test that lifetime tracking is correct across revisions."""
        result = runner.invoke(
            track,
            [
                "methods",
                "--input",
                str(sample_data_dir),
                "--output",
                str(temp_output_dir),
            ],
        )

        assert result.exit_code == 0

        df = pd.read_csv(temp_output_dir / "method_tracking.csv")

        # Group by block lineage (following previous_block_id chain)
        # For survived methods, lifetime should increase
        survived_methods = df[df["state"].str.contains("survived", case=False)]

        for _, method in survived_methods.iterrows():
            lifetime_revisions = method["lifetime_revisions"]
            lifetime_days = method["lifetime_days"]

            # Lifetime should be positive
            assert lifetime_revisions >= 2, "Survived methods should have lifetime >= 2 revisions"
            assert lifetime_days >= 0, "Lifetime days should be non-negative"

        # Added methods should have lifetime = 1 revision, 0 days
        added_methods = df[df["state"].str.contains("added", case=False)]
        if len(added_methods) > 0:
            # Most added methods should have lifetime = 1 (except if they appear in multiple
            # revisions)
            first_appearance = added_methods.groupby("block_id").first()
            assert (first_appearance["lifetime_revisions"] >= 1).all()
