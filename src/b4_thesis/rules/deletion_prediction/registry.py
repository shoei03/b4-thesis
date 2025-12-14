"""Rule registry for managing deletion prediction rules."""

from b4_thesis.rules.base import DeletionRule
from b4_thesis.rules.deletion_prediction.rule_factory import RuleFactory


class RuleRegistry:
    """Central registry for all deletion prediction rules."""

    _rules: list[DeletionRule] | None = None
    _factory: RuleFactory | None = None

    @classmethod
    def _get_factory(cls) -> RuleFactory:
        """Get or create RuleFactory instance.

        Returns:
            RuleFactory instance
        """
        if cls._factory is None:
            cls._factory = RuleFactory()
        return cls._factory

    @classmethod
    def _load_rules(cls) -> list[DeletionRule]:
        """Lazy load all rule instances from YAML configuration.

        Returns:
            List of rule instances

        Raises:
            FileNotFoundError: If rules.yaml not found
            yaml.YAMLError: If YAML syntax is invalid
            ValueError: If rule configuration is invalid
        """
        if cls._rules is None:
            factory = cls._get_factory()
            cls._rules = factory.load_rules()
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
