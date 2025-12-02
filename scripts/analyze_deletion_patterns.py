"""Analyze deletion patterns from clone reports using structured approach."""

import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from clone_report_parser import CloneReportParser, MethodData


@dataclass
class DeletionPattern:
    """Pattern observed in deleted methods."""

    pattern_name: str
    description: str
    frequency: int
    examples: list[str]  # Method names as examples


@dataclass
class FeatureCategory:
    """Category of features related to deletion."""

    category_name: str
    description: str
    features: list[str]
    patterns: list[DeletionPattern]


class DeletionPatternAnalyzer:
    """Analyze patterns in deleted vs survived methods."""

    def __init__(self, methods: list[MethodData]):
        """Initialize analyzer with parsed methods."""
        self.methods = methods
        self.deleted = [m for m in methods if m.is_deleted]
        self.survived = [m for m in methods if m.is_survived]

        print(f"Loaded {len(methods)} methods:")
        print(f"  - Deleted: {len(self.deleted)}")
        print(f"  - Survived: {len(self.survived)}")

    def compute_basic_statistics(self) -> dict:
        """Compute basic statistics about deleted vs survived methods."""
        stats = {
            "total_methods": len(self.methods),
            "deleted_count": len(self.deleted),
            "survived_count": len(self.survived),
            "deletion_rate": len(self.deleted) / len(self.methods) if self.methods else 0,
        }

        # LOC statistics
        deleted_locs = [m.loc for m in self.deleted if m.loc > 0]
        survived_locs = [m.loc for m in self.survived if m.loc > 0]

        stats["deleted_avg_loc"] = sum(deleted_locs) / len(deleted_locs) if deleted_locs else 0
        stats["survived_avg_loc"] = (
            sum(survived_locs) / len(survived_locs) if survived_locs else 0
        )

        # Match type distribution
        stats["deleted_by_match_type"] = Counter(m.match_type for m in self.deleted)
        stats["survived_by_match_type"] = Counter(m.match_type for m in self.survived)

        # Clone group size distribution
        deleted_group_sizes = [m.clone_group_size for m in self.deleted]
        survived_group_sizes = [m.clone_group_size for m in self.survived]

        stats["deleted_avg_group_size"] = (
            sum(deleted_group_sizes) / len(deleted_group_sizes) if deleted_group_sizes else 0
        )
        stats["survived_avg_group_size"] = (
            sum(survived_group_sizes) / len(survived_group_sizes) if survived_group_sizes else 0
        )

        return stats

    def prepare_sample_for_llm_analysis(
        self, sample_size: int = 50, output_file: str = "output/llm_analysis_batch.json"
    ) -> None:
        """Prepare a sample of methods for LLM analysis."""
        import random

        # Stratified sampling
        # Get balanced sample of deleted and survived methods
        deleted_sample_size = min(sample_size // 2, len(self.deleted))
        survived_sample_size = min(sample_size // 2, len(self.survived))

        deleted_sample = random.sample(self.deleted, deleted_sample_size)
        survived_sample = random.sample(self.survived, survived_sample_size)

        samples = []
        for method in deleted_sample + survived_sample:
            code = method.previous_code or method.current_code
            if not code:
                continue

            sample_data = {
                "id": f"{method.clone_group_id}_{method.function_name}",
                "function_name": method.function_name,
                "file_path": method.file_path,
                "is_deleted": method.is_deleted,
                "code": code,
                "loc": method.loc,
                "similarity": method.similarity,
                "match_type": method.match_type,
                "clone_group_size": method.clone_group_size,
                "clone_context": f"Clone group {method.clone_group_id} with {method.clone_group_size} members, match_type: {method.match_type}",
            }
            samples.append(sample_data)

        # Save to file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(samples, f, indent=2, ensure_ascii=False)

        print(f"\nPrepared {len(samples)} methods for LLM analysis")
        print(f"  - Deleted: {deleted_sample_size}")
        print(f"  - Survived: {survived_sample_size}")
        print(f"Saved to: {output_path}")

    def analyze_code_characteristics(self) -> dict:
        """Analyze code characteristics from available code snippets."""
        characteristics = {"deleted": {}, "survived": {}}

        for method_type, methods in [("deleted", self.deleted), ("survived", self.survived)]:
            # Analyze available code
            methods_with_code = [
                m for m in methods if (m.previous_code or m.current_code)
            ]

            if not methods_with_code:
                continue

            # Simple heuristics based on code patterns
            has_docstring = []
            has_try_except = []
            has_todo_fixme = []
            is_private = []
            is_property = []

            for m in methods_with_code:
                code = m.previous_code or m.current_code
                if not code:
                    continue

                # Check for docstring
                has_docstring.append('"""' in code or "'''" in code)

                # Check for try-except
                has_try_except.append("try:" in code and "except" in code)

                # Check for TODO/FIXME
                has_todo_fixme.append("TODO" in code or "FIXME" in code)

                # Check if private (starts with _)
                is_private.append(m.function_name.startswith("_"))

                # Check if property
                is_property.append("@property" in code)

            total = len(methods_with_code)
            characteristics[method_type] = {
                "total_with_code": total,
                "has_docstring_pct": sum(has_docstring) / total * 100 if total else 0,
                "has_try_except_pct": sum(has_try_except) / total * 100 if total else 0,
                "has_todo_fixme_pct": sum(has_todo_fixme) / total * 100 if total else 0,
                "is_private_pct": sum(is_private) / total * 100 if total else 0,
                "is_property_pct": sum(is_property) / total * 100 if total else 0,
            }

        return characteristics

    def generate_preliminary_report(self, output_file: str = "output/deletion_analysis_preliminary.md") -> None:
        """Generate preliminary analysis report."""
        stats = self.compute_basic_statistics()
        characteristics = self.analyze_code_characteristics()

        report = f"""# Deletion Pattern Analysis - Preliminary Report

## Overview

This report provides a preliminary analysis of method deletion patterns from {len(self.methods)} methods across 157 clone group reports.

## Summary Statistics

- **Total Methods**: {stats['total_methods']}
- **Deleted Methods**: {stats['deleted_count']} ({stats['deletion_rate']*100:.1f}%)
- **Survived Methods**: {stats['survived_count']} ({(1-stats['deletion_rate'])*100:.1f}%)

## Code Size Comparison

| Metric | Deleted | Survived | Difference |
|--------|---------|----------|------------|
| Average LOC | {stats['deleted_avg_loc']:.1f} | {stats['survived_avg_loc']:.1f} | {stats['survived_avg_loc'] - stats['deleted_avg_loc']:+.1f} |
| Avg Clone Group Size | {stats['deleted_avg_group_size']:.1f} | {stats['survived_avg_group_size']:.1f} | {stats['survived_avg_group_size'] - stats['deleted_avg_group_size']:+.1f} |

**Key Finding**: {"Deleted methods are smaller on average" if stats['deleted_avg_loc'] < stats['survived_avg_loc'] else "Deleted methods are larger on average"}

## Match Type Distribution

### Deleted Methods

| Match Type | Count | Percentage |
|------------|-------|------------|
"""
        for match_type, count in stats['deleted_by_match_type'].most_common():
            pct = count / stats['deleted_count'] * 100
            report += f"| `{match_type}` | {count} | {pct:.1f}% |\n"

        report += "\n### Survived Methods\n\n| Match Type | Count | Percentage |\n|------------|-------|------------|\n"

        for match_type, count in stats['survived_by_match_type'].most_common():
            pct = count / stats['survived_count'] * 100
            report += f"| `{match_type}` | {count} | {pct:.1f}% |\n"

        report += f"""

## Code Characteristics

### Deleted Methods
"""
        if "deleted" in characteristics:
            d_char = characteristics["deleted"]
            report += f"""
- Methods with code available: {d_char['total_with_code']}
- Has docstring: {d_char['has_docstring_pct']:.1f}%
- Has try-except: {d_char['has_try_except_pct']:.1f}%
- Has TODO/FIXME: {d_char['has_todo_fixme_pct']:.1f}%
- Is private (starts with `_`): {d_char['is_private_pct']:.1f}%
- Is property: {d_char['is_property_pct']:.1f}%
"""

        report += "\n### Survived Methods\n"
        if "survived" in characteristics:
            s_char = characteristics["survived"]
            report += f"""
- Methods with code available: {s_char['total_with_code']}
- Has docstring: {s_char['has_docstring_pct']:.1f}%
- Has try-except: {s_char['has_try_except_pct']:.1f}%
- Has TODO/FIXME: {s_char['has_todo_fixme_pct']:.1f}%
- Is private (starts with `_`): {s_char['is_private_pct']:.1f}%
- Is property: {s_char['is_property_pct']:.1f}%
"""

        report += """

## Next Steps

The preliminary analysis shows quantitative differences between deleted and survived methods. The next phase will involve deeper LLM-based contextual analysis to identify semantic and qualitative patterns.

### Prepared Samples

A stratified sample has been prepared for detailed LLM analysis. See `output/llm_analysis_batch.json`.

"""

        # Save report
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")

        print(f"\nGenerated preliminary report: {output_path}")


def main():
    """Main analysis pipeline."""
    print("=" * 70)
    print("Deletion Pattern Analysis Pipeline")
    print("=" * 70)

    # Step 1: Parse all reports
    print("\n[Step 1] Parsing clone reports...")
    parser = CloneReportParser(Path("output/clone_reports"))
    methods = parser.parse_all_reports()

    # Step 2: Initialize analyzer
    print("\n[Step 2] Initializing analyzer...")
    analyzer = DeletionPatternAnalyzer(methods)

    # Step 3: Generate preliminary report
    print("\n[Step 3] Generating preliminary report...")
    analyzer.generate_preliminary_report()

    # Step 4: Prepare sample for LLM analysis
    print("\n[Step 4] Preparing sample for LLM analysis...")
    analyzer.prepare_sample_for_llm_analysis(sample_size=100)

    print("\n" + "=" * 70)
    print("Pipeline complete!")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Review preliminary report: output/deletion_analysis_preliminary.md")
    print("2. Analyze sample batch: output/llm_analysis_batch.json")
    print("3. Run deep contextual analysis on the sample")


if __name__ == "__main__":
    main()
