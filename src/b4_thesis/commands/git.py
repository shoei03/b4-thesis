from pathlib import Path
from typing import Iterator

import click
from pydriller import Repository
from rich.console import Console
from tqdm import tqdm

from b4_thesis.const.column import ColumnNames
import pandas as pd

console = Console()


@click.group()
def git():
    pass


@git.command()
@click.option(
    "--repo-path",
    "-r",
    type=click.Path(path_type=Path, exists=True),
    default="../projects/pandas",
    help="Path to git repository",
)
@click.option(
    "--output_file",
    "-o",
    type=click.Path(path_type=Path, file_okay=True, dir_okay=False),
    default="./output/versions/git/deleted_files.csv",
    help="Output CSV file path",
)
def find_file(
    repo_path: Path,
    output_file: Path,
) -> None:
    """Gitリポジトリから削除されたファイルの情報をCSVに出力する"""
    df = pd.DataFrame(get_deleted_files(repo_path))
    df.to_csv(output_file, index=False)
    console.print(f"Output saved to {output_file}")


def get_deleted_files(repo_path: Path) -> Iterator[dict[str, str]]:
    """削除されたファイルの情報を生成する"""
    for commit in tqdm(Repository(str(repo_path)).traverse_commits(), desc="Processing commits"):
        for modified_file in commit.modified_files:
            if modified_file.change_type.name == "DELETE":
                yield {
                    ColumnNames.COMMIT_HASH.value: commit.hash[:7],
                    ColumnNames.REVISION_ID.value: commit.committer_date.isoformat(),
                    ColumnNames.FILE_PATH.value: modified_file.old_path,
                    ColumnNames.COMMIT_MESSAGE.value: commit.msg.strip(),
                }
