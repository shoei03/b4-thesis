"""Rule-based prediction infrastructure."""

from b4_thesis.rules.applicator import RuleApplicator
from b4_thesis.rules.base import CodeSnippet, DeletionRule
from b4_thesis.rules.deletion_prediction.registry import get_rules

__all__ = ["CodeSnippet", "DeletionRule", "RuleApplicator", "get_rules"]
