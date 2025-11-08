"""UnionFind (Disjoint Set Union) data structure with path compression.

This module provides an efficient implementation of the Union-Find data structure
for detecting connected components in clone groups.
"""


class UnionFind:
    """Union-Find (Disjoint Set Union) data structure with path compression.

    This data structure efficiently maintains disjoint sets and supports
    union and find operations in nearly constant amortized time.

    Attributes:
        parent: Dictionary mapping each element to its parent in the tree structure.
    """

    def __init__(self) -> None:
        """Initialize empty Union-Find structure."""
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        """Find root of element x with path compression.

        Path compression optimization: All nodes along the path to the root
        are made direct children of the root, flattening the tree structure.

        Args:
            x: Element to find the root of.

        Returns:
            The root element of the set containing x.
        """
        if x not in self.parent:
            self.parent[x] = x
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  # Path compression
        return self.parent[x]

    def union(self, x: str, y: str) -> None:
        """Union two sets containing x and y.

        Merges the set containing x with the set containing y by making
        the root of one set point to the root of the other.

        Args:
            x: Element from first set.
            y: Element from second set.
        """
        root_x = self.find(x)
        root_y = self.find(y)
        if root_x != root_y:
            self.parent[root_x] = root_y

    def get_groups(self) -> dict[str, list[str]]:
        """Get all connected components as {root: [members]}.

        Returns:
            Dictionary mapping each root element to a list of all elements
            in its connected component.
        """
        groups: dict[str, list[str]] = {}
        for node in self.parent.keys():
            root = self.find(node)
            if root not in groups:
                groups[root] = []
            groups[root].append(node)
        return groups

    def is_connected(self, x: str, y: str) -> bool:
        """Check if x and y are in the same set.

        Args:
            x: First element.
            y: Second element.

        Returns:
            True if x and y are in the same connected component, False otherwise.
        """
        return self.find(x) == self.find(y)

    def size(self) -> int:
        """Get number of elements.

        Returns:
            Total number of elements in the Union-Find structure.
        """
        return len(self.parent)

    def num_groups(self) -> int:
        """Get number of distinct groups.

        Returns:
            Number of distinct connected components.
        """
        if not self.parent:
            return 0
        return len(set(self.find(node) for node in self.parent.keys()))
