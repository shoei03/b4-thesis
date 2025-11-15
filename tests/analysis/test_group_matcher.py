"""Tests for GroupMatcher - matching clone groups across revisions."""

import pytest

from b4_thesis.analysis.group_detector import CloneGroup
from b4_thesis.analysis.group_matcher import GroupMatch, GroupMatcher
from b4_thesis.analysis.matching import MatchResult


@pytest.fixture
def simple_groups_old():
    """Simple clone groups in old revision."""
    return {
        "B1": CloneGroup(
            group_id="B1",
            members=["B1", "B2", "B3"],
            similarities={("B1", "B2"): 80, ("B1", "B3"): 75, ("B2", "B3"): 85},
        ),
        "B4": CloneGroup(
            group_id="B4",
            members=["B4", "B5"],
            similarities={("B4", "B5"): 90},
        ),
        "B6": CloneGroup(group_id="B6", members=["B6"], similarities={}),
    }


@pytest.fixture
def simple_groups_new():
    """Simple clone groups in new revision."""
    return {
        "B1_new": CloneGroup(
            group_id="B1_new",
            members=["B1_new", "B2_new", "B3_new"],
            similarities={
                ("B1_new", "B2_new"): 80,
                ("B1_new", "B3_new"): 75,
                ("B2_new", "B3_new"): 85,
            },
        ),
        "B4_new": CloneGroup(
            group_id="B4_new",
            members=["B4_new", "B5_new"],
            similarities={("B4_new", "B5_new"): 90},
        ),
    }


@pytest.fixture
def simple_method_matches():
    """Simple method matches for 1-to-1 mapping."""
    return MatchResult(
        forward_matches={
            "B1": "B1_new",
            "B2": "B2_new",
            "B3": "B3_new",
            "B4": "B4_new",
            "B5": "B5_new",
            # B6 is deleted (no match)
        },
        backward_matches={
            "B1_new": "B1",
            "B2_new": "B2",
            "B3_new": "B3",
            "B4_new": "B4",
            "B5_new": "B5",
        },
        match_types={
            "B1": "token_hash",
            "B2": "token_hash",
            "B3": "token_hash",
            "B4": "token_hash",
            "B5": "token_hash",
        },
        match_similarities={
            "B1": 100,
            "B2": 100,
            "B3": 100,
            "B4": 100,
            "B5": 100,
        },
        signature_changes={},
    )


class TestGroupMatch:
    """Test GroupMatch dataclass."""

    def test_group_match_creation(self):
        """Test creating a GroupMatch."""
        match = GroupMatch(
            source_group_id="G1",
            target_group_id="G2",
            overlap_count=3,
            overlap_ratio=0.75,
            source_size=4,
            target_size=5,
        )

        assert match.source_group_id == "G1"
        assert match.target_group_id == "G2"
        assert match.overlap_count == 3
        assert match.overlap_ratio == 0.75
        assert match.source_size == 4
        assert match.target_size == 5

    def test_group_match_no_target(self):
        """Test GroupMatch with no target (group dissolved)."""
        match = GroupMatch(
            source_group_id="G1",
            target_group_id=None,
            overlap_count=0,
            overlap_ratio=0.0,
            source_size=3,
            target_size=None,
        )

        assert match.target_group_id is None
        assert match.target_size is None
        assert match.overlap_count == 0


class TestGroupMatcher:
    """Test GroupMatcher class."""

    def test_initialization(self):
        """Test GroupMatcher initialization."""
        matcher = GroupMatcher(overlap_threshold=0.6)
        assert matcher.overlap_threshold == 0.6

    def test_initialization_default(self):
        """Test GroupMatcher with default threshold."""
        matcher = GroupMatcher()
        assert matcher.overlap_threshold == 0.5

    def test_find_group_of_block(self, simple_groups_old):
        """Test finding which group a block belongs to."""
        matcher = GroupMatcher()

        # Test finding groups
        assert matcher._find_group_of_block("B1", simple_groups_old) == "B1"
        assert matcher._find_group_of_block("B2", simple_groups_old) == "B1"
        assert matcher._find_group_of_block("B3", simple_groups_old) == "B1"
        assert matcher._find_group_of_block("B4", simple_groups_old) == "B4"
        assert matcher._find_group_of_block("B5", simple_groups_old) == "B4"
        assert matcher._find_group_of_block("B6", simple_groups_old) == "B6"

    def test_find_group_of_block_not_found(self, simple_groups_old):
        """Test finding group for non-existent block."""
        matcher = GroupMatcher()
        assert matcher._find_group_of_block("B999", simple_groups_old) is None

    def test_simple_matching_1to1(
        self, simple_groups_old, simple_groups_new, simple_method_matches
    ):
        """Test simple 1-to-1 group matching."""
        matcher = GroupMatcher(overlap_threshold=0.5)
        matches = matcher.match_groups(simple_groups_old, simple_groups_new, simple_method_matches)

        # All 3 members of B1 matched -> 100% overlap
        assert "B1" in matches
        assert matches["B1"].target_group_id == "B1_new"
        assert matches["B1"].overlap_count == 3
        assert matches["B1"].overlap_ratio == 1.0
        assert matches["B1"].source_size == 3
        assert matches["B1"].target_size == 3

        # All 2 members of B4 matched -> 100% overlap
        assert "B4" in matches
        assert matches["B4"].target_group_id == "B4_new"
        assert matches["B4"].overlap_count == 2
        assert matches["B4"].overlap_ratio == 1.0
        assert matches["B4"].source_size == 2
        assert matches["B4"].target_size == 2

        # B6 is isolated and deleted -> no match
        assert "B6" in matches
        assert matches["B6"].target_group_id is None
        assert matches["B6"].overlap_count == 0
        assert matches["B6"].overlap_ratio == 0.0

    def test_overlap_ratio_calculation(self):
        """Test overlap ratio calculation with partial matches."""
        matcher = GroupMatcher(overlap_threshold=0.5)

        groups_old = {
            "G1": CloneGroup(
                group_id="G1",
                members=["B1", "B2", "B3", "B4"],  # 4 members
                similarities={},
            )
        }

        groups_new = {
            "G1_new": CloneGroup(
                group_id="G1_new",
                members=["B1_new", "B2_new"],  # 2 members
                similarities={},
            )
        }

        # Only 2 out of 4 members matched
        method_matches = MatchResult(
            forward_matches={"B1": "B1_new", "B2": "B2_new"},
            backward_matches={"B1_new": "B1", "B2_new": "B2"},
            match_types={"B1": "token_hash", "B2": "token_hash"},
            match_similarities={"B1": 100, "B2": 100},
            signature_changes={},
        )

        matches = matcher.match_groups(groups_old, groups_new, method_matches)

        assert "G1" in matches
        assert matches["G1"].overlap_count == 2
        assert matches["G1"].overlap_ratio == 0.5  # 2 / 4
        assert matches["G1"].source_size == 4
        assert matches["G1"].target_size == 2

    def test_below_threshold_no_match(self):
        """Test that groups below overlap threshold don't match."""
        matcher = GroupMatcher(overlap_threshold=0.6)

        groups_old = {
            "G1": CloneGroup(
                group_id="G1",
                members=["B1", "B2", "B3", "B4"],  # 4 members
                similarities={},
            )
        }

        groups_new = {
            "G1_new": CloneGroup(
                group_id="G1_new",
                members=["B1_new", "B2_new"],  # 2 members
                similarities={},
            )
        }

        # Only 2 out of 4 members matched (50% < 60% threshold)
        method_matches = MatchResult(
            forward_matches={"B1": "B1_new", "B2": "B2_new"},
            backward_matches={"B1_new": "B1", "B2_new": "B2"},
            match_types={"B1": "token_hash", "B2": "token_hash"},
            match_similarities={"B1": 100, "B2": 100},
            signature_changes={},
        )

        matches = matcher.match_groups(groups_old, groups_new, method_matches)

        # Should not match because 0.5 < 0.6
        assert "G1" in matches
        assert matches["G1"].target_group_id is None
        assert matches["G1"].overlap_ratio == 0.5

    def test_detect_splits_1_to_many(self):
        """Test detecting group splits (1 old group -> multiple new groups)."""
        matcher = GroupMatcher(overlap_threshold=0.5)

        groups_old = {
            "G1": CloneGroup(
                group_id="G1",
                members=["B1", "B2", "B3", "B4"],
                similarities={},
            )
        }

        groups_new = {
            "G2": CloneGroup(
                group_id="G2",
                members=["B1_new", "B2_new"],
                similarities={},
            ),
            "G3": CloneGroup(
                group_id="G3",
                members=["B3_new", "B4_new"],
                similarities={},
            ),
        }

        # Half members go to G2, half to G3
        method_matches = MatchResult(
            forward_matches={
                "B1": "B1_new",
                "B2": "B2_new",
                "B3": "B3_new",
                "B4": "B4_new",
            },
            backward_matches={
                "B1_new": "B1",
                "B2_new": "B2",
                "B3_new": "B3",
                "B4_new": "B4",
            },
            match_types={
                "B1": "token_hash",
                "B2": "token_hash",
                "B3": "token_hash",
                "B4": "token_hash",
            },
            match_similarities={"B1": 100, "B2": 100, "B3": 100, "B4": 100},
            signature_changes={},
        )

        matches = matcher.match_groups(groups_old, groups_new, method_matches)
        splits = matcher.detect_splits(matches)

        # G1 should split into G2 and G3
        assert len(splits) == 1
        old_group_id, new_group_ids = splits[0]
        assert old_group_id == "G1"
        assert set(new_group_ids) == {"G2", "G3"}

    def test_detect_merges_many_to_1(self):
        """Test detecting group merges (multiple old groups -> 1 new group)."""
        matcher = GroupMatcher(overlap_threshold=0.5)

        groups_old = {
            "G1": CloneGroup(
                group_id="G1",
                members=["B1", "B2"],
                similarities={},
            ),
            "G2": CloneGroup(
                group_id="G2",
                members=["B3", "B4"],
                similarities={},
            ),
        }

        groups_new = {
            "G3": CloneGroup(
                group_id="G3",
                members=["B1_new", "B2_new", "B3_new", "B4_new"],
                similarities={},
            )
        }

        # All members merge into G3
        method_matches = MatchResult(
            forward_matches={
                "B1": "B1_new",
                "B2": "B2_new",
                "B3": "B3_new",
                "B4": "B4_new",
            },
            backward_matches={
                "B1_new": "B1",
                "B2_new": "B2",
                "B3_new": "B3",
                "B4_new": "B4",
            },
            match_types={
                "B1": "token_hash",
                "B2": "token_hash",
                "B3": "token_hash",
                "B4": "token_hash",
            },
            match_similarities={"B1": 100, "B2": 100, "B3": 100, "B4": 100},
            signature_changes={},
        )

        matches = matcher.match_groups(groups_old, groups_new, method_matches)
        merges = matcher.detect_merges(matches)

        # G1 and G2 should merge into G3
        assert len(merges) == 1
        old_group_ids, new_group_id = merges[0]
        assert set(old_group_ids) == {"G1", "G2"}
        assert new_group_id == "G3"

    def test_no_splits_or_merges(self, simple_groups_old, simple_groups_new, simple_method_matches):
        """Test case with no splits or merges (all 1-to-1)."""
        matcher = GroupMatcher(overlap_threshold=0.5)
        matches = matcher.match_groups(simple_groups_old, simple_groups_new, simple_method_matches)

        splits = matcher.detect_splits(matches)
        merges = matcher.detect_merges(matches)

        # No splits or merges in this simple case
        assert len(splits) == 0
        assert len(merges) == 0

    def test_empty_groups(self):
        """Test with empty groups."""
        matcher = GroupMatcher()
        matches = matcher.match_groups(
            {},
            {},
            MatchResult(
                forward_matches={},
                backward_matches={},
                match_types={},
                match_similarities={},
                signature_changes={},
            ),
        )

        assert len(matches) == 0
        assert len(matcher.detect_splits(matches)) == 0
        assert len(matcher.detect_merges(matches)) == 0

    def test_complex_scenario_splits_and_merges(self):
        """Test complex scenario with both splits and merges."""
        matcher = GroupMatcher(overlap_threshold=0.5)

        groups_old = {
            "G1": CloneGroup(group_id="G1", members=["B1", "B2", "B3", "B4"], similarities={}),
            "G2": CloneGroup(group_id="G2", members=["B5", "B6"], similarities={}),
        }

        groups_new = {
            "G3": CloneGroup(
                group_id="G3", members=["B1_new", "B2_new", "B5_new"], similarities={}
            ),
            "G4": CloneGroup(group_id="G4", members=["B3_new", "B4_new"], similarities={}),
        }

        # G1 splits into G3 (B1, B2) and G4 (B3, B4)
        # G2 (B5, B6) partially merges into G3 (B5)
        method_matches = MatchResult(
            forward_matches={
                "B1": "B1_new",
                "B2": "B2_new",
                "B3": "B3_new",
                "B4": "B4_new",
                "B5": "B5_new",
                # B6 deleted
            },
            backward_matches={
                "B1_new": "B1",
                "B2_new": "B2",
                "B3_new": "B3",
                "B4_new": "B4",
                "B5_new": "B5",
            },
            match_types={
                "B1": "token_hash",
                "B2": "token_hash",
                "B3": "token_hash",
                "B4": "token_hash",
                "B5": "token_hash",
            },
            match_similarities={"B1": 100, "B2": 100, "B3": 100, "B4": 100, "B5": 100},
            signature_changes={},
        )

        matches = matcher.match_groups(groups_old, groups_new, method_matches)
        splits = matcher.detect_splits(matches)
        merges = matcher.detect_merges(matches)

        # G1 splits into G3 and G4
        split_group_ids = [split[0] for split in splits]
        assert "G1" in split_group_ids

        # G3 is formed by merging members from G1 and G2
        merge_new_groups = [merge[1] for merge in merges]
        assert "G3" in merge_new_groups
