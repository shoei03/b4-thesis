"""Refactoring analysis business logic.

This module processes RefactoringMiner JSON output and calculates
type frequency statistics for each version pair.
"""

from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
import re


@dataclass
class RefactoringTypeStats:
    """Statistics for refactoring types in a version pair.

    Attributes:
        version_pair: Version pair identifier (e.g., "v1.0.0→v1.1.0")
        file_path: Source JSON file path
        total_commits: Total number of commits analyzed
        total_refactorings: Total refactorings found
        type_counts: Dictionary mapping refactoring type to count
        unique_types: Number of unique refactoring types
    """

    version_pair: str
    file_path: str
    total_commits: int
    total_refactorings: int
    type_counts: dict[str, int]
    unique_types: int


def analyze_single_file(file_path: Path) -> list[RefactoringTypeStats]:
    """Analyze a single RefactoringMiner JSON file.

    Args:
        file_path: Path to JSON file

    Returns:
        List containing single RefactoringTypeStats object (or empty list on error)

    The function extracts version pair from filename, parses JSON,
    counts refactoring types across all commits, and returns statistics.
    """
    try:
        # Extract version pair from filename
        version_pair = _extract_version_pair(file_path.name)
        if not version_pair:
            print(f"Warning: Could not extract version pair from {file_path.name}")
            return []

        # Load JSON
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        # Count refactoring types across all commits
        type_counts: Counter = Counter()
        total_commits = len(data.get("commits", []))

        for commit in data.get("commits", []):
            for refactoring in commit.get("refactorings", []):
                ref_type = refactoring.get("type")
                if ref_type:
                    type_counts[ref_type] += 1

        total_refactorings = sum(type_counts.values())
        unique_types = len(type_counts)

        stats = RefactoringTypeStats(
            version_pair=version_pair,
            file_path=str(file_path),
            total_commits=total_commits,
            total_refactorings=total_refactorings,
            type_counts=dict(type_counts),
            unique_types=unique_types,
        )

        return [stats]

    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse JSON from {file_path}: {e}")
        return []
    except Exception as e:
        print(f"Warning: Error processing {file_path}: {e}")
        return []


def analyze_directory(dir_path: Path) -> list[RefactoringTypeStats]:
    """Analyze all RefactoringMiner JSON files in a directory.

    Args:
        dir_path: Path to directory containing JSON files

    Returns:
        List of RefactoringTypeStats objects (one per valid JSON file)

    Only processes files matching pattern "pandas_v*_to_v*.json".
    Invalid files are skipped with warnings.
    """
    results = []
    json_files = sorted(dir_path.glob("pandas_v*_to_v*.json"))

    if not json_files:
        print(f"Warning: No matching JSON files found in {dir_path}")
        return []

    print(f"Found {len(json_files)} JSON files to process")

    for json_file in json_files:
        file_results = analyze_single_file(json_file)
        results.extend(file_results)

    return results


def _extract_version_pair(filename: str) -> str | None:
    """Extract version pair from RefactoringMiner JSON filename.

    Args:
        filename: File name (e.g., "pandas_v1.0.0_to_v1.1.0.json")

    Returns:
        Formatted version pair (e.g., "v1.0.0→v1.1.0") or None if no match

    Expected pattern: "pandas_v{OLD}_to_v{NEW}.json"
    """
    pattern = r"pandas_v(.+?)_to_v(.+?)\.json"
    match = re.match(pattern, filename)

    if match:
        old_version = match.group(1)
        new_version = match.group(2)
        return f"v{old_version}→v{new_version}"

    return None
