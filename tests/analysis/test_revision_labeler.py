"""Tests for RevisionLabeler."""

import pandas as pd
import pytest

from b4_thesis.analysis.revision_labeler import RevisionLabeler, RevisionStatus


@pytest.fixture
def labeler():
    """Create RevisionLabeler instance."""
    return RevisionLabeler()


@pytest.fixture
def sample_df():
    """Create sample method lineage DataFrame."""
    return pd.DataFrame(
        {
            "clone_group_id": ["g1", "g1", "g1", "g2", "g2", "g3", "g3"],
            "revision": ["r1", "r1", "r1", "r1", "r1", "r2", "r2"],
            "state": [
                "survived",
                "survived",
                "deleted",  # g1@r1: partial_deleted
                "deleted",
                "deleted",  # g2@r1: all_deleted
                "survived",
                "added",  # g3@r2: no_deleted
            ],
            "function_name": ["f1", "f2", "f3", "f4", "f5", "f6", "f7"],
        }
    )


# ==================== Validation Tests ====================


def test_validate_missing_columns(labeler):
    """Test validation fails with missing required columns."""
    df = pd.DataFrame({"clone_group_id": ["g1"], "revision": ["r1"]})

    with pytest.raises(ValueError) as exc_info:
        labeler.label_revisions(df)

    assert "Missing required columns" in str(exc_info.value)
    assert "state" in str(exc_info.value)


def test_validate_all_columns_present(labeler):
    """Test validation passes with all required columns."""
    df = pd.DataFrame({"clone_group_id": ["g1"], "revision": ["r1"], "state": ["survived"]})

    # Should not raise
    result = labeler.label_revisions(df)
    assert "rev_status" in result.columns


# ==================== Labeling Tests ====================


def test_all_deleted_status(labeler):
    """Test all_deleted status when all members are deleted."""
    df = pd.DataFrame(
        {
            "clone_group_id": ["g1", "g1"],
            "revision": ["r1", "r1"],
            "state": ["deleted", "deleted"],
        }
    )

    result = labeler.label_revisions(df)

    assert (result["rev_status"] == RevisionStatus.ALL_DELETED.value).all()


def test_partial_deleted_status(labeler):
    """Test partial_deleted status when some members are deleted."""
    df = pd.DataFrame(
        {
            "clone_group_id": ["g1", "g1", "g1"],
            "revision": ["r1", "r1", "r1"],
            "state": ["deleted", "survived", "added"],
        }
    )

    result = labeler.label_revisions(df)

    assert (result["rev_status"] == RevisionStatus.PARTIAL_DELETED.value).all()


def test_no_deleted_status(labeler):
    """Test no_deleted status when no members are deleted."""
    df = pd.DataFrame(
        {
            "clone_group_id": ["g1", "g1"],
            "revision": ["r1", "r1"],
            "state": ["survived", "added"],
        }
    )

    result = labeler.label_revisions(df)

    assert (result["rev_status"] == RevisionStatus.NO_DELETED.value).all()


def test_multiple_groups_same_revision(labeler, sample_df):
    """Test labeling with multiple groups in the same revision."""
    result = labeler.label_revisions(sample_df)

    # g1@r1: partial_deleted (1 deleted, 2 others)
    g1_r1 = result[(result["clone_group_id"] == "g1") & (result["revision"] == "r1")]
    assert (g1_r1["rev_status"] == "partial_deleted").all()

    # g2@r1: all_deleted (2 deleted, 0 others)
    g2_r1 = result[(result["clone_group_id"] == "g2") & (result["revision"] == "r1")]
    assert (g2_r1["rev_status"] == "all_deleted").all()

    # g3@r2: no_deleted (0 deleted, 2 others)
    g3_r2 = result[(result["clone_group_id"] == "g3") & (result["revision"] == "r2")]
    assert (g3_r2["rev_status"] == "no_deleted").all()


def test_empty_dataframe(labeler):
    """Test labeling empty DataFrame."""
    df = pd.DataFrame(columns=["clone_group_id", "revision", "state"])

    result = labeler.label_revisions(df)

    assert "rev_status" in result.columns
    assert len(result) == 0


def test_single_member_group(labeler):
    """Test labeling single member group."""
    df = pd.DataFrame(
        {
            "clone_group_id": ["g1"],
            "revision": ["r1"],
            "state": ["deleted"],
        }
    )

    result = labeler.label_revisions(df)

    assert result["rev_status"].iloc[0] == RevisionStatus.ALL_DELETED.value


def test_preserves_existing_columns(labeler):
    """Test that existing columns are preserved."""
    df = pd.DataFrame(
        {
            "clone_group_id": ["g1"],
            "revision": ["r1"],
            "state": ["survived"],
            "extra_col": ["value"],
        }
    )

    result = labeler.label_revisions(df)

    assert "extra_col" in result.columns
    assert result["extra_col"].iloc[0] == "value"


# ==================== Summary Tests ====================


def test_get_revision_summary(labeler, sample_df):
    """Test revision summary generation."""
    labeled = labeler.label_revisions(sample_df)
    summary = labeler.get_revision_summary(labeled)

    assert "revision" in summary.columns
    assert "rev_status" in summary.columns
    assert "n_groups" in summary.columns

    # Check r1 has 2 groups (g1: partial_deleted, g2: all_deleted)
    r1_summary = summary[summary["revision"] == "r1"]
    assert len(r1_summary) == 2  # Two different statuses

    # Check r2 has 1 group (g3: no_deleted)
    r2_summary = summary[summary["revision"] == "r2"]
    assert len(r2_summary) == 1


def test_summary_requires_rev_status(labeler):
    """Test summary raises error if rev_status column missing."""
    df = pd.DataFrame({"clone_group_id": ["g1"], "revision": ["r1"], "state": ["survived"]})

    with pytest.raises(ValueError) as exc_info:
        labeler.get_revision_summary(df)

    assert "rev_status" in str(exc_info.value)


def test_summary_counts_unique_groups(labeler):
    """Test summary counts unique groups, not records."""
    # Same group appears multiple times in same revision
    df = pd.DataFrame(
        {
            "clone_group_id": ["g1", "g1", "g1"],
            "revision": ["r1", "r1", "r1"],
            "state": ["survived", "survived", "survived"],
        }
    )

    labeled = labeler.label_revisions(df)
    summary = labeler.get_revision_summary(labeled)

    # Should count as 1 group, not 3 records
    assert summary["n_groups"].iloc[0] == 1
