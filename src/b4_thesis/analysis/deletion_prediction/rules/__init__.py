"""Deletion prediction rules."""

from b4_thesis.analysis.deletion_prediction.rule_base import DeletionRule

__all__ = ["DeletionRule", "get_all_rules", "get_rules_by_name"]


def get_all_rules() -> list[DeletionRule]:
    """Get instances of all available deletion prediction rules.

    Returns:
        List of all rule instances
    """
    # Import here to avoid circular imports
    from b4_thesis.analysis.deletion_prediction.rules.code_quality import (
        EmptyMethodRule,
        ShortMethodRule,
        SingleReturnRule,
    )
    from b4_thesis.analysis.deletion_prediction.rules.comment import (
        DeprecatedAnnotationRule,
        TodoCommentRule,
    )
    from b4_thesis.analysis.deletion_prediction.rules.naming import (
        DeprecatedNamingRule,
        PrivateUnusedRule,
        TemporaryNamingRule,
    )

    return [
        ShortMethodRule(),
        EmptyMethodRule(),
        SingleReturnRule(),
        TodoCommentRule(),
        DeprecatedAnnotationRule(),
        DeprecatedNamingRule(),
        TemporaryNamingRule(),
        PrivateUnusedRule(),
    ]


def get_rules_by_name(rule_names: list[str]) -> list[DeletionRule]:
    """Get rule instances by their names.

    Args:
        rule_names: List of rule names (e.g., ["short_method", "has_todo"])

    Returns:
        List of matching rule instances

    Raises:
        ValueError: If any rule name is not found
    """
    all_rules = get_all_rules()
    rule_dict = {rule.rule_name: rule for rule in all_rules}

    # Check for unknown rule names
    unknown_rules = set(rule_names) - set(rule_dict.keys())
    if unknown_rules:
        available = ", ".join(sorted(rule_dict.keys()))
        raise ValueError(f"Unknown rule names: {unknown_rules}. Available rules: {available}")

    return [rule_dict[name] for name in rule_names]
