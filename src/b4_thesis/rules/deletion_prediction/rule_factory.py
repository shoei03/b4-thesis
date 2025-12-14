"""Factory for creating rule instances from YAML configuration.

This module provides the RuleFactory class which loads rule definitions
from a YAML configuration file and instantiates appropriate rule classes
based on the rule type.
"""

import importlib
from pathlib import Path
from typing import Any

import yaml

from b4_thesis.rules.base import DeletionRule
from b4_thesis.rules.deletion_prediction.generic_rules import (
    CompositeRule,
    RegexFunctionNameRule,
    RegexRule,
    ThresholdRule,
    TrivialStatementsRule,
)


class RuleFactory:
    """Factory for creating rule instances from YAML configuration.

    Supports the following rule types:
    - regex: Pattern matching on code content
    - regex_function_name: Pattern matching on function names
    - threshold: Effective line count comparison
    - trivial_statements: Trivial statement detection
    - composite: Multiple patterns combined with AND/OR
    - custom: Custom Python class implementation
    """

    def __init__(self, config_path: Path | str | None = None):
        """Initialize RuleFactory.

        Args:
            config_path: Path to YAML config file. If None, uses default location
                (src/b4_thesis/rules/deletion_prediction/rules.yaml).
        """
        if config_path is None:
            # Default: rules.yaml in same directory as this file
            config_path = Path(__file__).parent / "rules.yaml"
        else:
            config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(
                f"Rule configuration file not found: {config_path}\n"
                f"Create rules.yaml or specify --config-path"
            )

        self.config_path = config_path
        self._rules_cache: list[DeletionRule] | None = None

    def load_rules(self) -> list[DeletionRule]:
        """Load all enabled rules from YAML config.

        Returns:
            List of DeletionRule instances

        Raises:
            yaml.YAMLError: If YAML syntax is invalid
            ValueError: If rule configuration is invalid
            FileNotFoundError: If config file not found
        """
        if self._rules_cache is not None:
            return self._rules_cache

        try:
            with open(self.config_path) as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML syntax in {self.config_path}\nError: {e}") from e

        if not config or "rules" not in config:
            raise ValueError(
                f"Invalid rule configuration: missing 'rules' key in {self.config_path}"
            )

        rules = []
        for rule_config in config["rules"]:
            # Skip disabled rules
            if not rule_config.get("enabled", True):
                continue

            try:
                rule = self._create_rule(rule_config)
                rules.append(rule)
            except Exception as e:
                rule_name = rule_config.get("name", "unknown")
                raise ValueError(f"Failed to create rule '{rule_name}': {e}") from e

        self._rules_cache = rules
        return rules

    def _create_rule(self, config: dict[str, Any]) -> DeletionRule:
        """Create rule instance from config dict.

        Args:
            config: Rule configuration dictionary

        Returns:
            DeletionRule instance

        Raises:
            ValueError: If rule type is unknown or required fields are missing
        """
        # Validate required fields
        required_fields = ["name", "type", "description"]
        missing_fields = [f for f in required_fields if f not in config]
        if missing_fields:
            raise ValueError(f"Missing required fields for rule: {missing_fields}")

        rule_type = config["type"]
        name = config["name"]
        description = config["description"]

        # Create rule based on type
        if rule_type == "regex":
            if "patterns" not in config:
                raise ValueError(f"Rule '{name}': missing required field 'patterns' for regex rule")
            return RegexRule(
                name=name,
                description=description,
                patterns=config["patterns"],
                flags=config.get("flags"),
            )

        elif rule_type == "regex_function_name":
            if "patterns" not in config:
                raise ValueError(
                    f"Rule '{name}': missing required field 'patterns' for regex_function_name rule"
                )
            return RegexFunctionNameRule(
                name=name,
                description=description,
                patterns=config["patterns"],
                flags=config.get("flags"),
            )

        elif rule_type == "threshold":
            if "threshold" not in config:
                raise ValueError(
                    f"Rule '{name}': missing required field 'threshold' for threshold rule"
                )
            return ThresholdRule(
                name=name,
                description=description,
                threshold=config["threshold"],
            )

        elif rule_type == "trivial_statements":
            if "trivial_statements" not in config:
                raise ValueError(f"Rule '{name}': missing 'trivial_statements' field")
            return TrivialStatementsRule(
                name=name,
                description=description,
                trivial_statements=config["trivial_statements"],
            )

        elif rule_type == "composite":
            required = ["operator", "sub_patterns"]
            missing = [f for f in required if f not in config]
            if missing:
                raise ValueError(
                    f"Rule '{name}': missing required fields for composite rule: {missing}"
                )
            return CompositeRule(
                name=name,
                description=description,
                operator=config["operator"],
                sub_patterns=config["sub_patterns"],
            )

        elif rule_type == "custom":
            if "class" not in config:
                raise ValueError(f"Rule '{name}': missing required field 'class' for custom rule")
            return self._load_custom_rule(config["class"])

        else:
            available_types = [
                "regex",
                "regex_function_name",
                "threshold",
                "trivial_statements",
                "composite",
                "custom",
            ]
            raise ValueError(
                f"Unknown rule type: {rule_type}. Available types: {', '.join(available_types)}"
            )

    def _load_custom_rule(self, class_path: str) -> DeletionRule:
        """Dynamically import and instantiate custom rule class.

        Args:
            class_path: Full Python class path (e.g., "module.ClassName")

        Returns:
            Rule instance

        Raises:
            ImportError: If module cannot be imported
            AttributeError: If class not found in module
        """
        try:
            module_path, class_name = class_path.rsplit(".", 1)
        except ValueError as e:
            raise ValueError(
                f"Invalid class path: {class_path}. Expected format: 'module.path.ClassName'"
            ) from e

        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            raise ImportError(
                f"Failed to import module '{module_path}' for custom rule: {e}"
            ) from e

        try:
            rule_class = getattr(module, class_name)
        except AttributeError as e:
            raise AttributeError(
                f"Class '{class_name}' not found in module '{module_path}': {e}"
            ) from e

        # Instantiate rule class (assumes no-arg constructor)
        return rule_class()

    def clear_cache(self):
        """Clear the rules cache.

        Useful for testing or when config file has been modified.
        """
        self._rules_cache = None
