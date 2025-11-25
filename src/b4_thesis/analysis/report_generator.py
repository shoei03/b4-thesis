"""Clone group report generation."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

from b4_thesis.analysis.code_extractor import CodeSnippet, ExtractRequest, GitCodeExtractor


@dataclass
class MemberInfo:
    """Metadata for a clone group member."""

    global_block_id: str | None
    revision: str
    function_name: str
    file_path: str
    start_line: int
    end_line: int
    loc: int | None
    state: str | None
    state_detail: str | None
    match_type: str | None
    match_similarity: float | None
    clone_count: int | None
    clone_group_id: str | None
    clone_group_size: int | None
    avg_similarity_to_group: float | None
    lifetime_revisions: int | None
    lifetime_days: int | None
    code_snippet: CodeSnippet | None = None
    previous_code_snippet: CodeSnippet | None = None

    @classmethod
    def from_row(
        cls,
        row: pd.Series,
        code_snippet: CodeSnippet | None = None,
        previous_code_snippet: CodeSnippet | None = None,
    ) -> "MemberInfo":
        """Create MemberInfo from DataFrame row."""
        return cls(
            global_block_id=row.get("global_block_id"),
            revision=row["revision"],
            function_name=row["function_name"],
            file_path=row["file_path"],
            start_line=int(row["start_line"]),
            end_line=int(row["end_line"]),
            loc=int(row["loc"]) if pd.notna(row.get("loc")) else None,
            state=row.get("state"),
            state_detail=row.get("state_detail"),
            match_type=row.get("match_type"),
            match_similarity=float(row["match_similarity"])
            if pd.notna(row.get("match_similarity"))
            else None,
            clone_count=int(row["clone_count"]) if pd.notna(row.get("clone_count")) else None,
            clone_group_id=row.get("clone_group_id"),
            clone_group_size=int(row["clone_group_size"])
            if pd.notna(row.get("clone_group_size"))
            else None,
            avg_similarity_to_group=float(row["avg_similarity_to_group"])
            if pd.notna(row.get("avg_similarity_to_group"))
            else None,
            lifetime_revisions=int(row["lifetime_revisions"])
            if pd.notna(row.get("lifetime_revisions"))
            else None,
            lifetime_days=int(row["lifetime_days"]) if pd.notna(row.get("lifetime_days")) else None,
            code_snippet=code_snippet,
            previous_code_snippet=previous_code_snippet,
        )


@dataclass
class CloneGroupReport:
    """Report data for a clone group."""

    group_id: str
    member_count: int
    match_type: str | None
    avg_similarity: float | None
    members: list[MemberInfo] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def short_id(self) -> str:
        """Get shortened group ID (first 8 characters)."""
        return self.group_id[:8] if len(self.group_id) > 8 else self.group_id


class ReportGenerator:
    """Generate Markdown reports for clone groups."""

    def __init__(self, extractor: GitCodeExtractor) -> None:
        """
        Initialize ReportGenerator.

        Args:
            extractor: GitCodeExtractor instance for code extraction
        """
        self.extractor = extractor

    def _match_previous_revisions(
        self, group_df: pd.DataFrame
    ) -> dict[tuple[str, str], pd.Series | None]:
        """Match each method to its previous revision in the same DataFrame.

        For partial_deleted.csv format, the label filter command has already included
        previous revisions in the same DataFrame. This method simply matches them by
        finding the chronologically previous row for each (clone_group_id, global_block_id).

        Args:
            group_df: DataFrame with method records including rev_status column

        Returns:
            Dict mapping (global_block_id, revision) to the previous revision's record (or None)
        """
        prev_map: dict[tuple[str, str], pd.Series | None] = {}

        if "global_block_id" not in group_df.columns or "clone_group_id" not in group_df.columns:
            return prev_map

        # Group by (clone_group_id, global_block_id) and sort by revision
        for (_, global_bid), group in group_df.groupby(["clone_group_id", "global_block_id"]):
            sorted_group = group.sort_values("revision", ascending=True)
            rows = list(sorted_group.iterrows())

            for i, (_, row) in enumerate(rows):
                revision = row["revision"]

                if i == 0:
                    # First revision has no previous
                    prev_map[(str(global_bid), revision)] = None
                else:
                    # Previous revision is the row before this one
                    prev_map[(str(global_bid), revision)] = rows[i - 1][1]

        return prev_map

    def _create_extract_requests(self, df: pd.DataFrame) -> list[ExtractRequest]:
        """Create extraction requests from DataFrame.

        Args:
            df: DataFrame with method records

        Returns:
            List of ExtractRequest objects
        """
        requests = []
        for _, row in df.iterrows():
            requests.append(
                ExtractRequest(
                    function_name=row["function_name"],
                    file_path=row["file_path"],
                    revision=row["revision"],
                    start_line=int(row["start_line"]),
                    end_line=int(row["end_line"]),
                    global_block_id=row.get("global_block_id"),
                )
            )
        return requests

    def generate_group_report(self, group_df: pd.DataFrame) -> CloneGroupReport:
        """Generate report for a single clone group.

        Args:
            group_df: DataFrame containing all records for a clone group (from partial_deleted.csv)

        Returns:
            CloneGroupReport with extracted code snippets

        Raises:
            ValueError: If DataFrame is empty or missing required columns
        """
        if group_df.empty:
            raise ValueError("Cannot generate report from empty DataFrame")

        # Validate required column
        if "rev_status" not in group_df.columns:
            raise ValueError(
                "Missing 'rev_status' column. "
                "Input must be from 'label filter' command (partial_deleted.csv format)."
            )

        # Get group metadata from first row
        first_row = group_df.iloc[0]
        group_id = str(first_row["clone_group_id"])

        # Calculate statistics
        match_type = first_row.get("match_type")
        avg_similarity = None
        if "avg_similarity_to_group" in group_df.columns:
            similarities = group_df["avg_similarity_to_group"].dropna()
            if not similarities.empty:
                avg_similarity = float(similarities.mean())

        # Get the latest revision for each unique method (global_block_id)
        # Sort by revision descending and take first occurrence
        sorted_df = group_df.sort_values("revision", ascending=False)
        representative_df = sorted_df.drop_duplicates(subset=["global_block_id"], keep="first")

        # Match previous revisions from the same DataFrame
        prev_revision_map = self._match_previous_revisions(group_df)

        # Extract code for current revisions
        requests = self._create_extract_requests(representative_df)
        snippets = self.extractor.batch_extract(requests, sort_by_revision=True)

        # Collect previous revision requests
        prev_requests: list[ExtractRequest] = []
        prev_request_keys: list[tuple[str, str]] = []  # (global_block_id, current_revision)

        for _, row in representative_df.iterrows():
            global_block_id = str(row.get("global_block_id", ""))
            revision = row["revision"]
            prev_record = prev_revision_map.get((global_block_id, revision))

            if prev_record is not None:
                prev_requests.append(
                    ExtractRequest(
                        function_name=prev_record["function_name"],
                        file_path=prev_record["file_path"],
                        revision=prev_record["revision"],
                        start_line=int(prev_record["start_line"]),
                        end_line=int(prev_record["end_line"]),
                        global_block_id=global_block_id,
                    )
                )
                prev_request_keys.append((global_block_id, revision))

        # Extract previous revision code
        prev_snippets: list[CodeSnippet] = []
        if prev_requests:
            prev_snippets = self.extractor.batch_extract(prev_requests, sort_by_revision=True)

        # Build map for quick lookup of previous snippets
        prev_snippet_map: dict[tuple[str, str], CodeSnippet] = {}
        for i, (global_block_id, current_revision) in enumerate(prev_request_keys):
            if i < len(prev_snippets):
                prev_snippet_map[(global_block_id, current_revision)] = prev_snippets[i]

        # Create MemberInfo objects with code snippets
        members = []
        for _, row in representative_df.iterrows():
            global_block_id = str(row.get("global_block_id", ""))
            revision = row["revision"]

            # Find matching current snippet
            snippet = None
            for s in snippets:
                if s.function_name == row["function_name"] and s.revision == revision:
                    snippet = s
                    break

            # Find matching previous snippet
            prev_snippet = prev_snippet_map.get((global_block_id, revision))

            member_info = MemberInfo.from_row(row, snippet, prev_snippet)
            members.append(member_info)

        return CloneGroupReport(
            group_id=group_id,
            member_count=len(members),
            match_type=match_type,
            avg_similarity=avg_similarity,
            members=members,
        )

    def render_markdown(self, report: CloneGroupReport) -> str:
        """Render report as Markdown string.

        Args:
            report: CloneGroupReport to render

        Returns:
            Markdown formatted string
        """
        lines = []

        # Header
        lines.append(f"# Clone Group Report: `{report.short_id}`")
        lines.append("")

        # Overview table
        lines.append("## Overview")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Members | {report.member_count} |")
        lines.append(f"| Match Type | {report.match_type or 'N/A'} |")
        if report.avg_similarity is not None:
            lines.append(f"| Avg Similarity | {report.avg_similarity:.1f}% |")
        else:
            lines.append("| Avg Similarity | N/A |")
        lines.append(f"| Generated | {report.generated_at.strftime('%Y-%m-%d %H:%M')} |")
        lines.append("")

        # Members table
        lines.append("## Members")
        lines.append("")
        lines.append("| # | Function | File | Lines | LOC | State | Rev | Similarity | Link |")
        lines.append("|---|----------|------|-------|-----|-------|-----|------------|------|")

        for i, member in enumerate(report.members, 1):
            # Shorten path for display
            short_path = member.file_path
            if len(short_path) > 40:
                short_path = "..." + short_path[-37:]

            line_range = f"{member.start_line}-{member.end_line}"
            loc = str(member.loc) if member.loc is not None else "-"
            state = member.state or "-"
            short_rev = member.revision[:7]
            similarity = (
                f"{member.avg_similarity_to_group:.1f}%"
                if member.avg_similarity_to_group is not None
                else "-"
            )

            github_url = member.code_snippet.github_url if member.code_snippet else None
            link = f"[GitHub]({github_url})" if github_url else "-"

            lines.append(
                f"| {i} | `{member.function_name}` | {short_path} | "
                f"{line_range} | {loc} | {state} | {short_rev} | {similarity} | {link} |"
            )

        lines.append("")
        lines.append("---")
        lines.append("")

        # Code comparison section
        lines.append("## Code Comparison")
        lines.append("")

        for i, member in enumerate(report.members, 1):
            lines.append(f"### {i}. `{member.function_name}`")
            lines.append("")
            lines.append(
                f"> {member.file_path}:{member.start_line}-{member.end_line} "
                f"@ {member.revision[:7]}"
            )
            if member.state:
                lines.append(f"> State: {member.state}")
            lines.append("")

            # Current revision code
            lines.append(f"#### Current (revision: {member.revision[:7]})")
            lines.append("")
            if member.code_snippet:
                lines.append("```python")
                lines.append(member.code_snippet.code)
                lines.append("```")
            else:
                lines.append("*Code not available*")
            lines.append("")

            # Previous revision code
            if member.previous_code_snippet:
                prev_snippet = member.previous_code_snippet
                lines.append(f"#### Previous (revision: {prev_snippet.revision[:7]})")
                lines.append("")
                lines.append(
                    f"> {prev_snippet.file_path}:{prev_snippet.start_line}-{prev_snippet.end_line}"
                )
                lines.append("")
                lines.append("```python")
                lines.append(prev_snippet.code)
                lines.append("```")
                lines.append("")
            else:
                lines.append("#### Previous")
                lines.append("")
                lines.append("*No previous revision available*")
                lines.append("")

        # Notes section
        lines.append("---")
        lines.append("")
        lines.append("## Analysis Notes")
        lines.append("")
        lines.append("- [ ] Type-1 (identical)")
        lines.append("- [ ] Type-2 (renamed variables)")
        lines.append("- [ ] Type-3 (modified logic)")
        lines.append("")
        lines.append("**Observations:**")
        lines.append("")
        lines.append("<!-- Add your analysis notes here -->")
        lines.append("")

        return "\n".join(lines)

    def save_report(
        self,
        report: CloneGroupReport,
        output_dir: Path,
        filename: str | None = None,
    ) -> Path:
        """Save report to file.

        Args:
            report: CloneGroupReport to save
            output_dir: Output directory
            filename: Custom filename (default: CloneGroup_{short_id}.md)

        Returns:
            Path to saved file
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if filename is None:
            filename = f"CloneGroup_{report.short_id}.md"

        output_path = output_dir / filename
        markdown_content = self.render_markdown(report)

        output_path.write_text(markdown_content, encoding="utf-8")
        return output_path


def generate_reports_from_csv(
    csv_path: Path,
    repo_path: Path,
    output_dir: Path,
    base_path_prefix: str = "/app/Repos/pandas/",
    github_base_url: str | None = "https://github.com/pandas-dev/pandas/blob/",
    min_members: int = 2,
    group_ids: list[str] | None = None,
) -> list[Path]:
    """Convenience function to generate reports from CSV file.

    Args:
        csv_path: Path to partial_deleted.csv (output from 'label filter' command)
        repo_path: Path to Git repository
        output_dir: Output directory for reports
        base_path_prefix: Prefix to remove from file paths
        github_base_url: Base URL for GitHub links
        min_members: Minimum number of members in a group
        group_ids: Specific group IDs to process (None for all)

    Returns:
        List of paths to generated report files

    Raises:
        ValueError: If input CSV is missing rev_status column
    """
    # Read CSV
    df = pd.read_csv(csv_path)

    # Validate rev_status column exists
    if "rev_status" not in df.columns:
        raise ValueError(
            "Missing 'rev_status' column. "
            "Input must be from 'label filter' command. "
            "Run: b4-thesis label filter <input.csv> -o <output.csv>"
        )

    # Filter for records with clone_group_id
    df = df[df["clone_group_id"].notna()]

    if df.empty:
        return []

    # Filter by specific group IDs if provided
    if group_ids:
        df = df[df["clone_group_id"].isin(group_ids)]

    # Group by clone_group_id
    groups = df.groupby("clone_group_id")

    # Filter by minimum members
    valid_groups = [(gid, gdf) for gid, gdf in groups if len(gdf) >= min_members]

    if not valid_groups:
        return []

    # Initialize extractor and generator
    extractor = GitCodeExtractor(
        repo_path=repo_path,
        base_path_prefix=base_path_prefix,
        github_base_url=github_base_url,
    )
    generator = ReportGenerator(extractor)

    # Generate reports
    output_paths = []
    for _, group_df in valid_groups:
        report = generator.generate_group_report(group_df)
        output_path = generator.save_report(report, output_dir)
        output_paths.append(output_path)

    return output_paths
