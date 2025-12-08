"""Result types for feature extraction components."""

from dataclasses import dataclass

import pandas as pd


@dataclass
class CsvLoadResult:
    """Result of CSV loading operation.

    Attributes:
        df: Validated DataFrame with non-deleted methods
        deleted_df: DataFrame containing only deleted methods
        original_count: Total number of methods in original CSV
        deleted_count: Number of deleted methods filtered out
        filtered_count: Number of methods remaining after filtering
    """

    df: pd.DataFrame
    deleted_df: pd.DataFrame
    original_count: int
    deleted_count: int
    filtered_count: int


@dataclass
class SnippetLoadResult:
    """Result of snippet loading operation.

    Attributes:
        df: DataFrame with 'code' and 'github_url' columns added
        cache_hit: Whether snippets were loaded from cache
        snippets_count: Number of snippets loaded
    """

    df: pd.DataFrame
    cache_hit: bool
    snippets_count: int


@dataclass
class RuleApplicationResult:
    """Result of rule application.

    Attributes:
        df: DataFrame with rule_* columns added
        rules_applied: Number of rules applied
        errors_count: Number of errors encountered during rule application
    """

    df: pd.DataFrame
    rules_applied: int
    errors_count: int
