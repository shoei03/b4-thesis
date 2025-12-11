"""Deletion prediction rules."""

from b4_thesis.analysis.deletion_prediction.rule_base import DeletionRule
from b4_thesis.analysis.deletion_prediction.rules.registry import get_rules

__all__ = ["DeletionRule", "get_rules"]
