"""Parse clone group reports to extract method data for deletion pattern analysis."""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Optional


@dataclass
class MethodData:
    """Represents a method from a clone report."""

    # Identification
    function_name: str
    file_path: str
    revision: str
    state: str  # deleted, survived, added

    # Metrics
    start_line: int
    end_line: int
    loc: int
    similarity: float

    # Code content
    current_code: Optional[str] = None
    previous_code: Optional[str] = None

    # Clone group context
    clone_group_id: str = ""
    clone_group_size: int = 0
    match_type: str = ""
    avg_similarity: float = 0.0

    @property
    def is_deleted(self) -> bool:
        """Check if method was deleted."""
        return self.state == "deleted"

    @property
    def is_survived(self) -> bool:
        """Check if method survived."""
        return self.state == "survived"

    def has_code_history(self) -> bool:
        """Check if method has both current and previous code."""
        return self.current_code is not None and self.previous_code is not None


class CloneReportParser:
    """Parser for clone group markdown reports."""

    def __init__(self, reports_dir: Path):
        """Initialize parser with reports directory."""
        self.reports_dir = Path(reports_dir)

    def parse_all_reports(self) -> list[MethodData]:
        """Parse all clone group reports and extract method data."""
        all_methods = []

        report_files = sorted(self.reports_dir.glob("CloneGroup_*.md"))
        print(f"Found {len(report_files)} clone group reports")

        for report_file in report_files:
            methods = self.parse_report(report_file)
            all_methods.extend(methods)
            print(f"  {report_file.name}: {len(methods)} methods")

        return all_methods

    def parse_report(self, report_path: Path) -> list[MethodData]:
        """Parse a single clone report file."""
        content = report_path.read_text(encoding="utf-8")

        # Extract clone group metadata
        clone_group_id = report_path.stem  # CloneGroup_xxxxxxxx
        metadata = self._extract_metadata(content)

        # Extract members table data
        members_data = self._extract_members_table(content)

        # Extract code snippets for each member
        code_snippets = self._extract_code_snippets(content)

        # Combine into MethodData objects
        methods = []
        for i, member in enumerate(members_data):
            method = MethodData(
                function_name=member["function"],
                file_path=member["file"],
                revision=member["revision"],
                state=member["state"],
                start_line=member["start_line"],
                end_line=member["end_line"],
                loc=member["loc"],
                similarity=member["similarity"],
                current_code=code_snippets[i].get("current"),
                previous_code=code_snippets[i].get("previous"),
                clone_group_id=clone_group_id,
                clone_group_size=metadata["members"],
                match_type=metadata["match_type"],
                avg_similarity=metadata["avg_similarity"],
            )
            methods.append(method)

        return methods

    def _extract_metadata(self, content: str) -> dict:
        """Extract metadata from overview section."""
        metadata = {
            "members": 0,
            "match_type": "unknown",
            "avg_similarity": 0.0,
        }

        # Extract members count
        if match := re.search(r"\|\s*Members\s*\|\s*(\d+)", content):
            metadata["members"] = int(match.group(1))

        # Extract match type
        if match := re.search(r"\|\s*Match Type\s*\|\s*`([^`]+)`", content):
            metadata["match_type"] = match.group(1)

        # Extract average similarity
        if match := re.search(r"\|\s*Avg Similarity\s*\|\s*([\d.]+)%", content):
            metadata["avg_similarity"] = float(match.group(1))

        return metadata

    def _extract_members_table(self, content: str) -> list[dict]:
        """Extract data from members table."""
        members = []

        # Find the members table
        table_pattern = r"## Members.*?\n\n(.*?)(?=\n##|\Z)"
        if not (table_match := re.search(table_pattern, content, re.DOTALL)):
            return members

        table_content = table_match.group(1)

        # Parse table rows (skip header and separator)
        rows = table_content.strip().split("\n")[2:]  # Skip header and separator

        for row in rows:
            if not row.strip() or not row.startswith("|"):
                continue

            # Split by | and clean
            cells = [cell.strip() for cell in row.split("|")[1:-1]]

            if len(cells) < 8:
                continue

            try:
                # Parse line range (e.g., "123-456")
                lines = cells[4].split("-")
                start_line = int(lines[0])
                end_line = int(lines[1]) if len(lines) > 1 else start_line

                members.append(
                    {
                        "state": cells[1],
                        "function": cells[2].replace("...", ""),
                        "file": cells[3].replace("...", ""),
                        "start_line": start_line,
                        "end_line": end_line,
                        "loc": int(cells[5]),
                        "revision": cells[6],
                        "similarity": float(cells[7].replace("%", "")),
                    }
                )
            except (ValueError, IndexError) as e:
                print(f"Warning: Failed to parse row: {row[:50]}... ({e})")
                continue

        return members

    def _extract_code_snippets(self, content: str) -> list[dict]:
        """Extract code snippets for each member."""
        snippets = []

        # Find all member sections (format: ### 1. `MethodName`)
        member_sections = re.split(r"\n### \d+\.", content)[1:]

        for section in member_sections:
            snippet = {"current": None, "previous": None}

            # Extract current code
            current_pattern = r"#### Current.*?```python\n(.*?)```"
            if current_match := re.search(current_pattern, section, re.DOTALL):
                snippet["current"] = current_match.group(1).strip()

            # Extract previous code
            previous_pattern = r"#### Previous.*?```python\n(.*?)```"
            if previous_match := re.search(previous_pattern, section, re.DOTALL):
                snippet["previous"] = previous_match.group(1).strip()

            snippets.append(snippet)

        return snippets


def main():
    """Test the parser."""
    reports_dir = Path("output/clone_reports")
    parser = CloneReportParser(reports_dir)

    print("Parsing clone reports...")
    methods = parser.parse_all_reports()

    print(f"\nTotal methods extracted: {len(methods)}")
    print(f"Deleted methods: {sum(1 for m in methods if m.is_deleted)}")
    print(f"Survived methods: {sum(1 for m in methods if m.is_survived)}")
    print(f"Added methods: {sum(1 for m in methods if m.state == 'added')}")

    # Show sample
    print("\n--- Sample Deleted Method ---")
    for method in methods:
        if method.is_deleted and method.previous_code:
            print(f"Function: {method.function_name}")
            print(f"File: {method.file_path}")
            print(f"Clone Group: {method.clone_group_id}")
            print(f"Match Type: {method.match_type}")
            print("Previous Code (first 200 chars):")
            print(method.previous_code[:200])
            break


if __name__ == "__main__":
    main()
