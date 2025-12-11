"""Rule registry for managing deletion prediction rules."""

from b4_thesis.analysis.deletion_prediction.rule_base import DeletionRule


class RuleRegistry:
    """Central registry for all deletion prediction rules."""

    _rules: list[DeletionRule] | None = None

    @classmethod
    def _load_rules(cls) -> list[DeletionRule]:
        """Lazy load all rule instances."""
        if cls._rules is None:
            from b4_thesis.analysis.deletion_prediction.rules.api_usage import (
                UsesAssertWarnRule,
                UsesBothSelectLocRule,
                UsesLocRule,
                UsesSelectRule,
            )
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

            cls._rules = [
                ShortMethodRule(),
                EmptyMethodRule(),
                SingleReturnRule(),
                TodoCommentRule(),
                DeprecatedAnnotationRule(),
                DeprecatedNamingRule(),
                TemporaryNamingRule(),
                PrivateUnusedRule(),
                UsesSelectRule(),
                UsesLocRule(),
                UsesBothSelectLocRule(),
                UsesAssertWarnRule(),
            ]
        return cls._rules

    @classmethod
    def get_all(cls) -> list[DeletionRule]:
        """Get all available rules."""
        return cls._load_rules()

    @classmethod
    def get_by_names(cls, names: list[str]) -> list[DeletionRule]:
        """Get rules by their names.

        Args:
            names: List of rule names

        Returns:
            List of matching rule instances

        Raises:
            ValueError: If any rule name is not found
        """
        all_rules = cls._load_rules()
        rule_dict = {rule.rule_name: rule for rule in all_rules}

        unknown = set(names) - set(rule_dict.keys())
        if unknown:
            available = ", ".join(sorted(rule_dict.keys()))
            raise ValueError(f"Unknown rules: {unknown}. Available: {available}")

        return [rule_dict[name] for name in names]


def get_rules(names: str | list[str] | None = None) -> list[DeletionRule]:
    """Get deletion prediction rules.

    Args:
        names: Rule names to filter. Can be:
            - None: Return all rules
            - str: Comma-separated rule names (e.g., "short_method,has_todo")
            - list[str]: List of rule names (e.g., ["short_method", "has_todo"])

    Returns:
        List of rule instances

    Raises:
        ValueError: If any rule name is not found

    Examples:
        >>> get_rules()  # All rules
        >>> get_rules("short_method,has_todo")  # Specific rules
        >>> get_rules(["short_method", "has_todo"])  # List format
    """
    if names is None:
        return RuleRegistry.get_all()

    if isinstance(names, str):
        names = [name.strip() for name in names.split(",")]

    return RuleRegistry.get_by_names(names)
