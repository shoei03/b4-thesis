"""Clone group report generation."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

from b4_thesis.analysis.code_extractor import CodeSnippet, ExtractRequest, GitCodeExtractor


@dataclass
class CloneGroupReport:
    """Report data for a clone group."""

    group_id: str
    member_count: int
    match_type: str | None
    avg_similarity: float | None
    members: list[CodeSnippet] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def short_id(self) -> str:
        """Get shortened group ID (first 8 characters)."""
        return self.group_id[:8] if len(self.group_id) > 8 else self.group_id


class ReportGenerator:
    """Generate Markdown reports for clone groups."""

    def __init__(
        self,
        extractor: GitCodeExtractor,
        use_latest_revision: bool = True,
    ) -> None:
        """
        Initialize ReportGenerator.

        Args:
            extractor: GitCodeExtractor instance for code extraction
            use_latest_revision: Use latest revision for each method (default True)
        """
        self.extractor = extractor
        self.use_latest_revision = use_latest_revision

    def _select_representative_records(self, group_df: pd.DataFrame) -> pd.DataFrame:
        """Select representative record for each method in the group.

        For each global_block_id, selects the record with the latest revision.

        Args:
            group_df: DataFrame with clone group members

        Returns:
            DataFrame with one record per unique method
        """
        if self.use_latest_revision:
            # Sort by revision (descending) and take first for each global_block_id
            sorted_df = group_df.sort_values("revision", ascending=False)
            return sorted_df.drop_duplicates(subset=["global_block_id"], keep="first")
        return group_df.drop_duplicates(subset=["global_block_id"], keep="first")

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
            group_df: DataFrame containing all records for a clone group

        Returns:
            CloneGroupReport with extracted code snippets
        """
        if group_df.empty:
            raise ValueError("Cannot generate report from empty DataFrame")

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

        # Select representative records
        representative_df = self._select_representative_records(group_df)

        # Extract code
        requests = self._create_extract_requests(representative_df)
        snippets = self.extractor.batch_extract(requests, sort_by_revision=True)

        return CloneGroupReport(
            group_id=group_id,
            member_count=len(snippets),
            match_type=match_type,
            avg_similarity=avg_similarity,
            members=snippets,
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
        lines.append("| # | Function | File | Lines | Rev | Link |")
        lines.append("|---|----------|------|-------|-----|------|")

        for i, member in enumerate(report.members, 1):
            # Shorten path for display
            short_path = member.file_path
            if len(short_path) > 40:
                short_path = "..." + short_path[-37:]

            line_range = f"{member.start_line}-{member.end_line}"
            short_rev = member.revision[:7]

            if member.github_url:
                link = f"[GitHub]({member.github_url})"
            else:
                link = "-"

            lines.append(
                f"| {i} | `{member.function_name}` | {short_path} | "
                f"{line_range} | {short_rev} | {link} |"
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
            lines.append("")
            lines.append("```python")
            lines.append(member.code)
            lines.append("```")
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
        csv_path: Path to method_lineage.csv
        repo_path: Path to Git repository
        output_dir: Output directory for reports
        base_path_prefix: Prefix to remove from file paths
        github_base_url: Base URL for GitHub links
        min_members: Minimum number of members in a group
        group_ids: Specific group IDs to process (None for all)

    Returns:
        List of paths to generated report files
    """
    # Read CSV
    df = pd.read_csv(csv_path)

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
    for group_id, group_df in valid_groups:
        report = generator.generate_group_report(group_df)
        output_path = generator.save_report(report, output_dir)
        output_paths.append(output_path)

    return output_paths
