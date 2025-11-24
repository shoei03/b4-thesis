"""CLI entry point for b4-thesis tool."""

import click
from rich.console import Console

from b4_thesis.commands import analyze, convert, report, stats, track, visualize

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="b4-thesis")
@click.pass_context
def main(ctx):
    """Software Engineering Research Analysis Tool.

    A CLI tool for analyzing software repositories and research data.
    """
    ctx.ensure_object(dict)


# Register commands
main.add_command(analyze.analyze)
main.add_command(convert.convert)
main.add_command(report.report)
main.add_command(stats.stats)
main.add_command(track.track)
main.add_command(visualize.visualize)


if __name__ == "__main__":
    main()
