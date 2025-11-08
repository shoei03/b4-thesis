"""Tests for GroupDetector."""

import pandas as pd

from b4_thesis.analysis.group_detector import CloneGroup, GroupDetector


class TestCloneGroup:
    """Test CloneGroup dataclass and properties."""

    def test_clone_group_initialization(self):
        """Test CloneGroup initialization."""
        group = CloneGroup(
            group_id="block_a",
            members=["block_a", "block_b", "block_c"],
            similarities={
                ("block_a", "block_b"): 80,
                ("block_a", "block_c"): 75,
                ("block_b", "block_c"): 85,
            },
        )
        assert group.group_id == "block_a"
        assert len(group.members) == 3
        assert group.size == 3

    def test_size_property(self):
        """Test size property."""
        group = CloneGroup(group_id="block_a", members=["block_a", "block_b"], similarities={})
        assert group.size == 2

    def test_is_clone_property(self):
        """Test is_clone property (True if 2+ members)."""
        # Clone group (2+ members)
        clone_group = CloneGroup(
            group_id="block_a", members=["block_a", "block_b"], similarities={}
        )
        assert clone_group.is_clone is True

        # Isolated method (1 member)
        isolated = CloneGroup(group_id="block_x", members=["block_x"], similarities={})
        assert isolated.is_clone is False

    def test_avg_similarity(self):
        """Test average similarity calculation."""
        group = CloneGroup(
            group_id="block_a",
            members=["block_a", "block_b", "block_c"],
            similarities={
                ("block_a", "block_b"): 80,
                ("block_a", "block_c"): 70,
                ("block_b", "block_c"): 90,
            },
        )
        assert group.avg_similarity == 80.0

    def test_avg_similarity_no_pairs(self):
        """Test average similarity when no pairs exist."""
        group = CloneGroup(group_id="block_a", members=["block_a"], similarities={})
        assert group.avg_similarity is None

    def test_min_similarity(self):
        """Test minimum similarity calculation."""
        group = CloneGroup(
            group_id="block_a",
            members=["block_a", "block_b", "block_c"],
            similarities={
                ("block_a", "block_b"): 80,
                ("block_a", "block_c"): 70,
                ("block_b", "block_c"): 90,
            },
        )
        assert group.min_similarity == 70

    def test_max_similarity(self):
        """Test maximum similarity calculation."""
        group = CloneGroup(
            group_id="block_a",
            members=["block_a", "block_b", "block_c"],
            similarities={
                ("block_a", "block_b"): 80,
                ("block_a", "block_c"): 70,
                ("block_b", "block_c"): 90,
            },
        )
        assert group.max_similarity == 90

    def test_density(self):
        """Test graph density calculation."""
        # Complete graph (all pairs connected): density = 1.0
        group_complete = CloneGroup(
            group_id="block_a",
            members=["block_a", "block_b", "block_c"],
            similarities={
                ("block_a", "block_b"): 80,
                ("block_a", "block_c"): 75,
                ("block_b", "block_c"): 85,
            },
        )
        assert group_complete.density == 1.0

        # Partial graph (2 out of 3 pairs): density = 2/3
        group_partial = CloneGroup(
            group_id="block_a",
            members=["block_a", "block_b", "block_c"],
            similarities={
                ("block_a", "block_b"): 80,
                ("block_a", "block_c"): 75,
            },
        )
        assert abs(group_partial.density - 2 / 3) < 0.001

    def test_density_single_member(self):
        """Test density for single member group (undefined)."""
        group = CloneGroup(group_id="block_a", members=["block_a"], similarities={})
        assert group.density == 0.0


class TestGroupDetector:
    """Test GroupDetector clone group detection."""

    def test_single_group_detection(self):
        """Test detection of a single clone group."""
        # Create test data: 3 blocks forming one group
        code_blocks = pd.DataFrame(
            {
                0: ["block_a", "block_b", "block_c"],  # block_id
                1: ["src/util.py", "src/util.py", "src/util.py"],  # file_path
                4: ["func_a", "func_b", "func_c"],  # function_name
            }
        )

        clone_pairs = pd.DataFrame(
            {
                0: ["block_a", "block_a", "block_b"],  # block_id_1
                1: ["block_b", "block_c", "block_c"],  # block_id_2
                2: [80, 75, 85],  # ngram_similarity
                3: ["", "", ""],  # lcs_similarity
            }
        )

        detector = GroupDetector(similarity_threshold=70)
        groups = detector.detect_groups(code_blocks, clone_pairs)

        assert len(groups) == 1
        group = list(groups.values())[0]
        assert group.size == 3
        assert set(group.members) == {"block_a", "block_b", "block_c"}
        assert group.is_clone is True

    def test_multiple_groups_detection(self):
        """Test detection of multiple separate groups."""
        code_blocks = pd.DataFrame(
            {
                0: ["block_a", "block_b", "block_c", "block_d"],
                1: ["src/util.py"] * 4,
                4: ["func_a", "func_b", "func_c", "func_d"],
            }
        )

        # Two groups: {a, b} and {c, d}
        clone_pairs = pd.DataFrame(
            {
                0: ["block_a", "block_c"],
                1: ["block_b", "block_d"],
                2: [75, 80],
                3: ["", ""],
            }
        )

        detector = GroupDetector(similarity_threshold=70)
        groups = detector.detect_groups(code_blocks, clone_pairs)

        assert len(groups) == 2
        group_members = [set(g.members) for g in groups.values()]
        assert {"block_a", "block_b"} in group_members
        assert {"block_c", "block_d"} in group_members

    def test_isolated_methods(self):
        """Test handling of isolated methods (no clone pairs)."""
        code_blocks = pd.DataFrame(
            {
                0: ["block_a", "block_b", "block_c"],
                1: ["src/util.py"] * 3,
                4: ["func_a", "func_b", "func_c"],
            }
        )

        # Only one pair above threshold
        clone_pairs = pd.DataFrame({0: ["block_a"], 1: ["block_b"], 2: [75], 3: [""]})

        detector = GroupDetector(similarity_threshold=70)
        groups = detector.detect_groups(code_blocks, clone_pairs)

        # One group of 2, one isolated
        assert len(groups) == 2
        sizes = sorted([g.size for g in groups.values()])
        assert sizes == [1, 2]

    def test_threshold_boundary(self):
        """Test behavior at similarity threshold boundary."""
        code_blocks = pd.DataFrame(
            {
                0: ["block_a", "block_b", "block_c", "block_d"],
                1: ["src/util.py"] * 4,
                4: ["func_a", "func_b", "func_c", "func_d"],
            }
        )

        # Pairs with similarities: 70 (exactly threshold), 69 (below), 71 (above)
        clone_pairs = pd.DataFrame(
            {
                0: ["block_a", "block_b", "block_c"],
                1: ["block_b", "block_c", "block_d"],
                2: [70, 69, 71],
                3: ["", "", ""],
            }
        )

        detector = GroupDetector(similarity_threshold=70)
        groups = detector.detect_groups(code_blocks, clone_pairs)

        # block_a-block_b (70, included) and block_c-block_d (71, included)
        # block_b-block_c (69, excluded)
        # Results in 2 groups: {a, b} and {c, d}
        assert len(groups) == 2

    def test_effective_similarity_ngram_high(self):
        """Test effective similarity when ngram >= 70."""
        code_blocks = pd.DataFrame(
            {0: ["block_a", "block_b"], 1: ["src/util.py"] * 2, 4: ["func_a", "func_b"]}
        )

        # ngram_similarity = 75, lcs_similarity is empty
        clone_pairs = pd.DataFrame({0: ["block_a"], 1: ["block_b"], 2: [75], 3: [""]})

        detector = GroupDetector(similarity_threshold=70)
        groups = detector.detect_groups(code_blocks, clone_pairs)

        # Should use ngram_similarity (75)
        group = list(groups.values())[0]
        assert ("block_a", "block_b") in group.similarities
        assert group.similarities[("block_a", "block_b")] == 75

    def test_effective_similarity_lcs_used(self):
        """Test effective similarity when ngram < 70, use LCS."""
        code_blocks = pd.DataFrame(
            {0: ["block_a", "block_b"], 1: ["src/util.py"] * 2, 4: ["func_a", "func_b"]}
        )

        # ngram_similarity = 50 (< 70), lcs_similarity = 80
        clone_pairs = pd.DataFrame({0: ["block_a"], 1: ["block_b"], 2: [50], 3: [80]})

        detector = GroupDetector(similarity_threshold=70)
        groups = detector.detect_groups(code_blocks, clone_pairs)

        # Should use lcs_similarity (80)
        group = list(groups.values())[0]
        assert group.similarities[("block_a", "block_b")] == 80

    def test_empty_clone_pairs(self):
        """Test handling of empty clone_pairs."""
        code_blocks = pd.DataFrame(
            {0: ["block_a", "block_b"], 1: ["src/util.py"] * 2, 4: ["func_a", "func_b"]}
        )

        clone_pairs = pd.DataFrame({0: [], 1: [], 2: [], 3: []})

        detector = GroupDetector(similarity_threshold=70)
        groups = detector.detect_groups(code_blocks, clone_pairs)

        # Each block is isolated
        assert len(groups) == 2
        for group in groups.values():
            assert group.size == 1
            assert group.is_clone is False

    def test_group_metrics_calculation(self):
        """Test comprehensive metrics calculation for groups."""
        code_blocks = pd.DataFrame(
            {
                0: ["block_a", "block_b", "block_c"],
                1: ["src/util.py"] * 3,
                4: ["func_a", "func_b", "func_c"],
            }
        )

        clone_pairs = pd.DataFrame(
            {
                0: ["block_a", "block_a", "block_b"],
                1: ["block_b", "block_c", "block_c"],
                2: [80, 70, 90],
                3: ["", "", ""],
            }
        )

        detector = GroupDetector(similarity_threshold=70)
        groups = detector.detect_groups(code_blocks, clone_pairs)

        group = list(groups.values())[0]
        assert group.avg_similarity == 80.0
        assert group.min_similarity == 70
        assert group.max_similarity == 90
        assert group.density == 1.0  # All pairs connected

    def test_custom_threshold(self):
        """Test custom similarity threshold."""
        code_blocks = pd.DataFrame(
            {0: ["block_a", "block_b"], 1: ["src/util.py"] * 2, 4: ["func_a", "func_b"]}
        )

        clone_pairs = pd.DataFrame({0: ["block_a"], 1: ["block_b"], 2: [75], 3: [""]})

        # Threshold = 80: pair should not form group
        detector_high = GroupDetector(similarity_threshold=80)
        groups_high = detector_high.detect_groups(code_blocks, clone_pairs)
        assert len(groups_high) == 2  # Two isolated groups
        assert all(g.size == 1 for g in groups_high.values())

        # Threshold = 70: pair should form group
        detector_low = GroupDetector(similarity_threshold=70)
        groups_low = detector_low.detect_groups(code_blocks, clone_pairs)
        assert len(groups_low) == 1
        assert groups_low[list(groups_low.keys())[0]].size == 2

    def test_effective_similarity_respects_threshold(self):
        """Test that _get_effective_similarity respects the configured threshold."""
        code_blocks = pd.DataFrame(
            {0: ["block_a", "block_b"], 1: ["src/util.py"] * 2, 4: ["func_a", "func_b"]}
        )

        # ngram=60 (< 80), lcs=85
        # With threshold=80, should use LCS (85)
        clone_pairs = pd.DataFrame({0: ["block_a"], 1: ["block_b"], 2: [60], 3: [85]})

        detector = GroupDetector(similarity_threshold=80)
        groups = detector.detect_groups(code_blocks, clone_pairs)

        # Should form a group because LCS (85) >= threshold (80)
        assert len(groups) == 1
        group = list(groups.values())[0]
        assert group.size == 2
        assert group.similarities[("block_a", "block_b")] == 85

    def test_effective_similarity_threshold_50(self):
        """Test effective similarity with threshold=50."""
        code_blocks = pd.DataFrame(
            {0: ["block_a", "block_b"], 1: ["src/util.py"] * 2, 4: ["func_a", "func_b"]}
        )

        # ngram=55 (>= 50), lcs=90
        # With threshold=50, should use ngram (55) instead of LCS
        clone_pairs = pd.DataFrame({0: ["block_a"], 1: ["block_b"], 2: [55], 3: [90]})

        detector = GroupDetector(similarity_threshold=50)
        groups = detector.detect_groups(code_blocks, clone_pairs)

        # Should form a group and store ngram similarity (55)
        group = list(groups.values())[0]
        assert group.similarities[("block_a", "block_b")] == 55
