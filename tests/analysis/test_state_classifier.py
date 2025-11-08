"""Tests for StateClassifier."""

import pytest

from b4_thesis.analysis.group_detector import CloneGroup
from b4_thesis.analysis.group_matcher import GroupMatch
from b4_thesis.analysis.method_matcher import MatchResult
from b4_thesis.analysis.state_classifier import (
    GroupState,
    MethodState,
    MethodStateDetail,
    StateClassifier,
)


@pytest.fixture
def classifier():
    """Create StateClassifier instance."""
    return StateClassifier()


# ==================== Method State Classification Tests ====================


def test_deleted_isolated(classifier):
    """Test classification of deleted method without clones."""
    # No match (deleted), no group
    match_result = MatchResult(
        forward_matches={},
        backward_matches={},
        match_types={},
        match_similarities={},
    )

    state, detail = classifier.classify_method_state(
        block_id="block1",
        match_result=match_result,
        direction="forward",
        group_old=None,
        group_new=None,
    )

    assert state == MethodState.DELETED
    assert detail == MethodStateDetail.DELETED_ISOLATED


def test_deleted_from_group(classifier):
    """Test classification of deleted method from a group."""
    # No match (deleted), was in group with multiple members
    match_result = MatchResult(
        forward_matches={},
        backward_matches={},
        match_types={},
        match_similarities={},
    )

    group_old = CloneGroup(
        group_id="group1", members=["block1", "block2", "block3"], similarities={}
    )

    state, detail = classifier.classify_method_state(
        block_id="block1",
        match_result=match_result,
        direction="forward",
        group_old=group_old,
        group_new=None,
    )

    assert state == MethodState.DELETED
    assert detail == MethodStateDetail.DELETED_FROM_GROUP


def test_deleted_last_member(classifier):
    """Test classification of last member deleted from group."""
    # No match (deleted), was the last member of the group
    match_result = MatchResult(
        forward_matches={},
        backward_matches={},
        match_types={},
        match_similarities={},
    )

    group_old = CloneGroup(group_id="group1", members=["block1"], similarities={})

    state, detail = classifier.classify_method_state(
        block_id="block1",
        match_result=match_result,
        direction="forward",
        group_old=group_old,
        group_new=None,
        is_last_member=True,
    )

    assert state == MethodState.DELETED
    assert detail == MethodStateDetail.DELETED_LAST_MEMBER


def test_survived_unchanged(classifier):
    """Test classification of unchanged method (token_hash match)."""
    match_result = MatchResult(
        forward_matches={"block1": "block2"},
        backward_matches={"block2": "block1"},
        match_types={"block1": "token_hash"},
        match_similarities={"block1": 100},
    )

    group_old = CloneGroup(group_id="group1", members=["block1", "block3"], similarities={})
    group_new = CloneGroup(group_id="group1", members=["block2", "block4"], similarities={})

    state, detail = classifier.classify_method_state(
        block_id="block1",
        match_result=match_result,
        direction="forward",
        group_old=group_old,
        group_new=group_new,
    )

    assert state == MethodState.SURVIVED
    assert detail == MethodStateDetail.SURVIVED_UNCHANGED


def test_survived_modified(classifier):
    """Test classification of modified method (similarity match)."""
    match_result = MatchResult(
        forward_matches={"block1": "block2"},
        backward_matches={"block2": "block1"},
        match_types={"block1": "similarity"},
        match_similarities={"block1": 85},
    )

    group_old = CloneGroup(group_id="group1", members=["block1", "block3"], similarities={})
    group_new = CloneGroup(group_id="group1", members=["block2", "block4"], similarities={})

    state, detail = classifier.classify_method_state(
        block_id="block1",
        match_result=match_result,
        direction="forward",
        group_old=group_old,
        group_new=group_new,
    )

    assert state == MethodState.SURVIVED
    assert detail == MethodStateDetail.SURVIVED_MODIFIED


def test_survived_clone_gained(classifier):
    """Test classification of survived method that gained clones."""
    match_result = MatchResult(
        forward_matches={"block1": "block2"},
        backward_matches={"block2": "block1"},
        match_types={"block1": "token_hash"},
        match_similarities={"block1": 100},
    )

    # Was isolated, now in a group
    group_old = None
    group_new = CloneGroup(group_id="group1", members=["block2", "block3"], similarities={})

    state, detail = classifier.classify_method_state(
        block_id="block1",
        match_result=match_result,
        direction="forward",
        group_old=group_old,
        group_new=group_new,
    )

    assert state == MethodState.SURVIVED
    assert detail == MethodStateDetail.SURVIVED_CLONE_GAINED


def test_survived_clone_lost(classifier):
    """Test classification of survived method that lost clones."""
    match_result = MatchResult(
        forward_matches={"block1": "block2"},
        backward_matches={"block2": "block1"},
        match_types={"block1": "token_hash"},
        match_similarities={"block1": 100},
    )

    # Was in group, now isolated
    group_old = CloneGroup(group_id="group1", members=["block1", "block3"], similarities={})
    group_new = None

    state, detail = classifier.classify_method_state(
        block_id="block1",
        match_result=match_result,
        direction="forward",
        group_old=group_old,
        group_new=group_new,
    )

    assert state == MethodState.SURVIVED
    assert detail == MethodStateDetail.SURVIVED_CLONE_LOST


def test_added_isolated(classifier):
    """Test classification of newly added isolated method."""
    match_result = MatchResult(
        forward_matches={},
        backward_matches={},
        match_types={},
        match_similarities={},
    )

    # New method, no group
    state, detail = classifier.classify_method_state(
        block_id="block1",
        match_result=match_result,
        direction="backward",
        group_old=None,
        group_new=None,
    )

    assert state == MethodState.ADDED
    assert detail == MethodStateDetail.ADDED_ISOLATED


def test_added_to_group(classifier):
    """Test classification of method added to existing group."""
    match_result = MatchResult(
        forward_matches={},
        backward_matches={},
        match_types={},
        match_similarities={},
    )

    # New method, added to existing group (size > 2 suggests it existed before)
    group_new = CloneGroup(
        group_id="group1", members=["block1", "block2", "block3"], similarities={}
    )

    state, detail = classifier.classify_method_state(
        block_id="block1",
        match_result=match_result,
        direction="backward",
        group_old=None,
        group_new=group_new,
        is_new_group=False,
    )

    assert state == MethodState.ADDED
    assert detail == MethodStateDetail.ADDED_TO_GROUP


def test_added_new_group(classifier):
    """Test classification of method forming new group."""
    match_result = MatchResult(
        forward_matches={},
        backward_matches={},
        match_types={},
        match_similarities={},
    )

    # New method in a new group
    group_new = CloneGroup(group_id="group1", members=["block1", "block2"], similarities={})

    state, detail = classifier.classify_method_state(
        block_id="block1",
        match_result=match_result,
        direction="backward",
        group_old=None,
        group_new=group_new,
        is_new_group=True,
    )

    assert state == MethodState.ADDED
    assert detail == MethodStateDetail.ADDED_NEW_GROUP


# ==================== Group State Classification Tests ====================


def test_group_continued(classifier):
    """Test classification of continued group (size within ±10%)."""
    match = GroupMatch(
        source_group_id="group1",
        target_group_id="group2",
        overlap_count=9,
        overlap_ratio=0.9,
        source_size=10,
        target_size=11,  # 10% increase, within tolerance
    )

    state = classifier.classify_group_state(match, is_split=False, is_merged=False)

    assert state == GroupState.CONTINUED


def test_group_grown(classifier):
    """Test classification of grown group (>10% increase)."""
    match = GroupMatch(
        source_group_id="group1",
        target_group_id="group2",
        overlap_count=8,
        overlap_ratio=0.8,
        source_size=10,
        target_size=12,  # 20% increase
    )

    state = classifier.classify_group_state(match, is_split=False, is_merged=False)

    assert state == GroupState.GROWN


def test_group_shrunk(classifier):
    """Test classification of shrunk group (>10% decrease)."""
    match = GroupMatch(
        source_group_id="group1",
        target_group_id="group2",
        overlap_count=7,
        overlap_ratio=0.7,
        source_size=10,
        target_size=8,  # 20% decrease
    )

    state = classifier.classify_group_state(match, is_split=False, is_merged=False)

    assert state == GroupState.SHRUNK


def test_group_split(classifier):
    """Test classification of split group."""
    match = GroupMatch(
        source_group_id="group1",
        target_group_id="group2",
        overlap_count=5,
        overlap_ratio=0.5,
        source_size=10,
        target_size=5,
    )

    # Split flag takes precedence
    state = classifier.classify_group_state(match, is_split=True, is_merged=False)

    assert state == GroupState.SPLIT


def test_group_merged(classifier):
    """Test classification of merged group."""
    match = GroupMatch(
        source_group_id="group1",
        target_group_id="group2",
        overlap_count=5,
        overlap_ratio=0.5,
        source_size=10,
        target_size=20,
    )

    # Merge flag takes precedence
    state = classifier.classify_group_state(match, is_split=False, is_merged=True)

    assert state == GroupState.MERGED


def test_group_dissolved(classifier):
    """Test classification of dissolved group."""
    match = GroupMatch(
        source_group_id="group1",
        target_group_id=None,  # No match
        overlap_count=0,
        overlap_ratio=0.0,
        source_size=10,
        target_size=None,
    )

    state = classifier.classify_group_state(match, is_split=False, is_merged=False)

    assert state == GroupState.DISSOLVED


def test_group_born(classifier):
    """Test classification of born group (new group)."""
    # For born groups, we pass None as match since it's from the new revision
    state = classifier.classify_group_state(None, is_split=False, is_merged=False)

    assert state == GroupState.BORN


def test_group_boundary_case_upper(classifier):
    """Test boundary case: exactly 10% increase should be CONTINUED."""
    match = GroupMatch(
        source_group_id="group1",
        target_group_id="group2",
        overlap_count=9,
        overlap_ratio=0.9,
        source_size=10,
        target_size=11,  # Exactly 10% increase
    )

    state = classifier.classify_group_state(match, is_split=False, is_merged=False)

    # Should be CONTINUED (within tolerance)
    assert state == GroupState.CONTINUED


def test_group_boundary_case_lower(classifier):
    """Test boundary case: exactly 10% decrease should be CONTINUED."""
    match = GroupMatch(
        source_group_id="group1",
        target_group_id="group2",
        overlap_count=8,
        overlap_ratio=0.8,
        source_size=10,
        target_size=9,  # Exactly 10% decrease
    )

    state = classifier.classify_group_state(match, is_split=False, is_merged=False)

    # Should be CONTINUED (within tolerance)
    assert state == GroupState.CONTINUED


def test_split_takes_precedence_over_shrink(classifier):
    """Test that split status takes precedence over shrunk."""
    match = GroupMatch(
        source_group_id="group1",
        target_group_id="group2",
        overlap_count=3,
        overlap_ratio=0.3,
        source_size=10,
        target_size=3,  # Shrunk significantly
    )

    # Even though it shrunk, split takes precedence
    state = classifier.classify_group_state(match, is_split=True, is_merged=False)

    assert state == GroupState.SPLIT


def test_merge_takes_precedence_over_grown(classifier):
    """Test that merge status takes precedence over grown."""
    match = GroupMatch(
        source_group_id="group1",
        target_group_id="group2",
        overlap_count=8,
        overlap_ratio=0.8,
        source_size=10,
        target_size=25,  # Grown significantly
    )

    # Even though it grew, merge takes precedence
    state = classifier.classify_group_state(match, is_split=False, is_merged=True)

    assert state == GroupState.MERGED
