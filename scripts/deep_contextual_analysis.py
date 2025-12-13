"""Deep contextual analysis of deleted vs survived methods."""

from collections import defaultdict
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass
class ContextualFeature:
    """A contextual feature extracted from code analysis."""

    feature_name: str
    category: str
    description: str
    deleted_count: int = 0
    survived_count: int = 0
    examples_deleted: list[str] = None
    examples_survived: list[str] = None

    def __post_init__(self):
        if self.examples_deleted is None:
            self.examples_deleted = []
        if self.examples_survived is None:
            self.examples_survived = []

    @property
    def deletion_ratio(self) -> float:
        """Calculate ratio of deleted to total."""
        total = self.deleted_count + self.survived_count
        return self.deleted_count / total if total > 0 else 0


def analyze_code_sample(sample: dict) -> dict:
    """Analyze a single code sample and extract contextual features."""
    code = sample["code"]
    is_deleted = sample["is_deleted"]
    function_name = sample["function_name"]

    features = {
        "id": sample["id"],
        "function_name": function_name,
        "is_deleted": is_deleted,
        "loc": sample["loc"],
        "detected_patterns": [],
    }

    # Pattern 1: Simple wrapper functions
    if "return " in code and code.count("return") == 1 and sample["loc"] <= 5:
        features["detected_patterns"].append("simple_wrapper")

    # Pattern 2: Delegation functions (just calls another function)
    lines = code.strip().split("\n")
    code_lines = [l for l in lines if l.strip() and not l.strip().startswith("#")]
    if len(code_lines) <= 3 and any("return self." in l or "return " in l for l in code_lines):
        features["detected_patterns"].append("delegation")

    # Pattern 3: Conversion/casting functions
    if any(
        keyword in code.lower()
        for keyword in ["convert", "cast", "to_", "as_", "from_"]
    ):
        if sample["loc"] <= 15:
            features["detected_patterns"].append("conversion_utility")

    # Pattern 4: Validation functions
    if "raise" in code or "assert" in code or "check" in function_name.lower():
        features["detected_patterns"].append("validation")

    # Pattern 5: Deprecated or transitional code
    if any(
        marker in code.lower()
        for marker in ["deprecated", "todo", "fixme", "xxx", "hack"]
    ):
        features["detected_patterns"].append("deprecated_or_todo")

    # Pattern 6: One-liner or very small functions
    if sample["loc"] <= 3:
        features["detected_patterns"].append("very_small")

    # Pattern 7: Functions with complex logic
    if any(keyword in code for keyword in ["for ", "while ", "if "]):
        control_flow_count = (
            code.count("for ")
            + code.count("while ")
            + code.count("if ")
            + code.count("elif ")
        )
        if control_flow_count >= 3:
            features["detected_patterns"].append("complex_control_flow")

    # Pattern 8: Functions with error handling
    if "try:" in code and "except" in code:
        features["detected_patterns"].append("has_error_handling")

    # Pattern 9: Property decorators
    if "@property" in code or "@cached_property" in code:
        features["detected_patterns"].append("property_decorator")

    # Pattern 10: Private/internal functions (naming convention)
    if function_name.startswith("_") and not function_name.startswith("__"):
        features["detected_patterns"].append("private_function")

    # Pattern 11: Test helper functions
    if any(keyword in function_name.lower() for keyword in ["assert", "check", "verify", "mock"]):
        features["detected_patterns"].append("test_helper")

    # Pattern 12: Compatibility shims
    if any(keyword in code.lower() for keyword in ["compat", "fallback", "backward"]):
        features["detected_patterns"].append("compatibility_shim")

    # Pattern 13: Functions with documentation
    if '"""' in code or "'''" in code:
        features["detected_patterns"].append("has_docstring")
    else:
        features["detected_patterns"].append("no_docstring")

    # Pattern 14: Functions that modify state
    if "self." in code and any(op in code for op in [" = ", "+=", "-=", "*="]):
        features["detected_patterns"].append("modifies_state")

    # Pattern 15: Pure utility functions (no self parameter)
    first_line = code.split("\n")[0]
    if "def " in first_line and "self" not in first_line:
        features["detected_patterns"].append("static_utility")

    return features


def main():
    """Perform deep contextual analysis on samples."""
    print("=" * 70)
    print("Deep Contextual Analysis")
    print("=" * 70)

    # Load samples
    sample_path = Path("output/llm_analysis_batch.json")
    with open(sample_path, encoding="utf-8") as f:
        samples = json.load(f)

    print(f"\nAnalyzing {len(samples)} code samples...")

    # Analyze each sample
    analyzed = []
    for sample in samples:
        analysis = analyze_code_sample(sample)
        analyzed.append(analysis)

    # Aggregate pattern frequencies
    pattern_counts = defaultdict(lambda: {"deleted": 0, "survived": 0, "examples": []})

    for analysis in analyzed:
        status = "deleted" if analysis["is_deleted"] else "survived"
        for pattern in analysis["detected_patterns"]:
            pattern_counts[pattern][status] += 1
            if len(pattern_counts[pattern]["examples"]) < 3:
                pattern_counts[pattern]["examples"].append(
                    f"{analysis['function_name']} ({status})"
                )

    # Calculate deletion ratios
    pattern_stats = []
    for pattern, counts in pattern_counts.items():
        total = counts["deleted"] + counts["survived"]
        deletion_ratio = counts["deleted"] / total if total > 0 else 0
        pattern_stats.append(
            {
                "pattern": pattern,
                "deleted": counts["deleted"],
                "survived": counts["survived"],
                "total": total,
                "deletion_ratio": deletion_ratio,
                "examples": counts["examples"],
            }
        )

    # Sort by deletion ratio
    pattern_stats.sort(key=lambda x: x["deletion_ratio"], reverse=True)

    # Generate report
    report = """# Deep Contextual Analysis Report

## Overview

This report presents findings from deep contextual analysis of 100 method samples (50 deleted, 50 survived).

## Key Patterns Predicting Deletion

The following patterns were identified through contextual code analysis. Patterns are ranked by **deletion ratio** (proportion of methods with this pattern that were deleted).

### Pattern Analysis

| Pattern | Deleted | Survived | Total | Deletion Ratio | Interpretation |
|---------|---------|----------|-------|----------------|----------------|
"""

    for stat in pattern_stats:
        pattern = stat["pattern"].replace("_", " ").title()
        report += f"| {pattern} | {stat['deleted']} | {stat['survived']} | {stat['total']} | {stat['deletion_ratio']*100:.1f}% | {'**High risk**' if stat['deletion_ratio'] > 0.6 else '**Moderate**' if stat['deletion_ratio'] > 0.4 else 'Low'} |\n"

    report += "\n## Detailed Pattern Descriptions\n\n"

    # Pattern descriptions
    pattern_descriptions = {
        "simple_wrapper": "Very small functions (≤5 LOC) with single return statement. Often refactored into callers.",
        "delegation": "Functions that simply delegate to another method without adding logic.",
        "conversion_utility": "Small utility functions for type conversion or casting operations.",
        "validation": "Functions focused on validation, checking, or raising errors.",
        "deprecated_or_todo": "Code marked as deprecated, TODO, FIXME, or containing technical debt markers.",
        "very_small": "Extremely small functions (≤3 LOC), often candidates for inlining.",
        "complex_control_flow": "Functions with complex control flow (≥3 if/for/while statements).",
        "has_error_handling": "Functions with try-except error handling.",
        "property_decorator": "Methods decorated as properties.",
        "private_function": "Private/internal methods (start with single underscore).",
        "test_helper": "Helper functions for testing (assert, verify, mock, etc.).",
        "compatibility_shim": "Compatibility or fallback code for backward compatibility.",
        "has_docstring": "Functions with docstrings.",
        "no_docstring": "Functions without docstrings.",
        "modifies_state": "Methods that modify object state (assignments to self.*).",
        "static_utility": "Static utility functions (no self parameter).",
    }

    for stat in pattern_stats[:10]:  # Top 10 patterns
        pattern = stat["pattern"]
        report += f"### {pattern.replace('_', ' ').title()}\n\n"
        report += f"**Description**: {pattern_descriptions.get(pattern, 'Pattern detected through code analysis.')}\n\n"
        report += f"**Statistics**:\n"
        report += f"- Deleted: {stat['deleted']}\n"
        report += f"- Survived: {stat['survived']}\n"
        report += f"- Deletion Ratio: {stat['deletion_ratio']*100:.1f}%\n\n"
        report += f"**Examples**:\n"
        for example in stat["examples"][:3]:
            report += f"- {example}\n"
        report += "\n"

    # High-risk patterns
    high_risk = [p for p in pattern_stats if p["deletion_ratio"] > 0.5]
    report += f"\n## High-Risk Patterns (Deletion Ratio > 50%)\n\n"
    report += f"The following {len(high_risk)} patterns show strong correlation with deletion:\n\n"
    for stat in high_risk:
        report += f"- **{stat['pattern'].replace('_', ' ').title()}**: {stat['deletion_ratio']*100:.1f}% deletion rate\n"

    # Protective patterns
    protective = [p for p in pattern_stats if p["deletion_ratio"] < 0.3]
    report += f"\n## Protective Patterns (Deletion Ratio < 30%)\n\n"
    report += f"The following {len(protective)} patterns correlate with method survival:\n\n"
    for stat in protective:
        report += f"- **{stat['pattern'].replace('_', ' ').title()}**: {stat['deletion_ratio']*100:.1f}% deletion rate (protective)\n"

    # Save detailed analysis
    detailed_output = Path("output/contextual_features_analysis.json")
    with open(detailed_output, "w", encoding="utf-8") as f:
        json.dump(
            {"pattern_statistics": pattern_stats, "analyzed_samples": analyzed},
            f,
            indent=2,
            ensure_ascii=False,
        )

    # Save report
    report_path = Path("output/deep_contextual_analysis.md")
    report_path.write_text(report, encoding="utf-8")

    print(f"\n✓ Analyzed {len(analyzed)} samples")
    print(f"✓ Identified {len(pattern_stats)} patterns")
    print(f"✓ High-risk patterns: {len(high_risk)}")
    print(f"✓ Protective patterns: {len(protective)}")
    print(f"\nReports generated:")
    print(f"  - {report_path}")
    print(f"  - {detailed_output}")


if __name__ == "__main__":
    main()
