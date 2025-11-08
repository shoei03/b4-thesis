"""Tests for UnionFind data structure."""

from b4_thesis.analysis.union_find import UnionFind


class TestUnionFind:
    """Test UnionFind data structure."""

    def test_initialization(self):
        """Test empty UnionFind creation."""
        uf = UnionFind()
        assert uf.size() == 0
        assert uf.num_groups() == 0

    def test_single_element(self):
        """Test single element behavior."""
        uf = UnionFind()
        root = uf.find("A")
        assert root == "A"
        assert uf.size() == 1
        assert uf.num_groups() == 1

    def test_union_two_elements(self):
        """Test union of two elements."""
        uf = UnionFind()
        uf.union("A", "B")
        assert uf.is_connected("A", "B")
        assert uf.num_groups() == 1

    def test_multiple_groups(self):
        """Test formation of multiple groups."""
        uf = UnionFind()
        uf.union("A", "B")
        uf.union("C", "D")
        uf.union("E", "F")

        assert uf.is_connected("A", "B")
        assert uf.is_connected("C", "D")
        assert uf.is_connected("E", "F")
        assert not uf.is_connected("A", "C")
        assert uf.num_groups() == 3

    def test_transitive_union(self):
        """Test transitive property: union(A,B), union(B,C) -> A~C."""
        uf = UnionFind()
        uf.union("A", "B")
        uf.union("B", "C")
        assert uf.is_connected("A", "C")

    def test_path_compression(self):
        """Test path compression optimization."""
        uf = UnionFind()
        # Create chain: A -> B -> C -> D
        uf.union("A", "B")
        uf.union("B", "C")
        uf.union("C", "D")

        # After find(A), path should be compressed
        root = uf.find("A")
        # All should point to same root
        assert uf.find("B") == root
        assert uf.find("C") == root
        assert uf.find("D") == root

    def test_get_groups(self):
        """Test get_groups method returns correct structure."""
        uf = UnionFind()
        uf.union("A", "B")
        uf.union("C", "D")
        uf.union("B", "E")  # A-B-E group

        groups = uf.get_groups()
        assert len(groups) == 2

        # Find group with A
        a_root = uf.find("A")
        assert set(groups[a_root]) == {"A", "B", "E"}

        # Find group with C
        c_root = uf.find("C")
        assert set(groups[c_root]) == {"C", "D"}

    def test_large_group(self):
        """Test with larger number of elements."""
        uf = UnionFind()
        # Create group of 100 elements
        for i in range(1, 100):
            uf.union(f"elem_{0}", f"elem_{i}")

        assert uf.num_groups() == 1
        assert uf.size() == 100

        groups = uf.get_groups()
        assert len(groups) == 1
        group_members = list(groups.values())[0]
        assert len(group_members) == 100

    def test_union_idempotent(self):
        """Test that repeated union operations are idempotent."""
        uf = UnionFind()
        uf.union("A", "B")
        uf.union("A", "B")  # Same union again
        uf.union("B", "A")  # Reverse order

        assert uf.is_connected("A", "B")
        assert uf.num_groups() == 1
        groups = uf.get_groups()
        assert len(groups) == 1

    def test_find_creates_singleton(self):
        """Test that find creates a singleton group if element not exists."""
        uf = UnionFind()
        root = uf.find("X")
        assert root == "X"
        assert uf.size() == 1
        assert uf.num_groups() == 1

    def test_is_connected_same_element(self):
        """Test that an element is connected to itself."""
        uf = UnionFind()
        uf.find("A")
        assert uf.is_connected("A", "A")

    def test_empty_get_groups(self):
        """Test get_groups on empty UnionFind."""
        uf = UnionFind()
        groups = uf.get_groups()
        assert groups == {}
