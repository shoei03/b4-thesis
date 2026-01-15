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


@git.command()
@click.option(
    "--input-file",
    "-i",
    type=click.Path(path_type=Path, file_okay=True, dir_okay=False),
    default="./output/versions/git/deleted_files.csv",
    help="Input CSV file path",
)
@click.option(
    "--input",
    type=click.Path(path_type=Path, file_okay=True, dir_okay=False),
    default="./output/versions/nil/methods_tracking_with_clone.csv",
    help="Input CSV file path",
)
@click.option(
    "--output-file",
    "-o",
    type=click.Path(path_type=Path, file_okay=True, dir_okay=False),
    default="./output/versions/git/methods_tracking_with_file_deleted.csv",
    help="Output CSV file path",
)
def classify_is_deleted(input_file: Path, input: Path, output_file: Path) -> None:
    """CSVファイルにis_deletedカラムを追加する"""
    deleted_file_df = pd.read_csv(input_file)
    methods_tracking_df = pd.read_csv(input)

    # is_deletedがTrueの行だけフィルタリング
    deleted_df = methods_tracking_df[
        methods_tracking_df[ColumnNames.IS_DELETED.value] == True
    ].copy()

    # deleted_file_dfのファイルパスをセットに変換（O(1)の検索）
    deleted_file_paths = set(deleted_file_df[ColumnNames.FILE_PATH.value])

    # /app/Repos/pandas/ を取り除く
    # TODO: ここは環境依存なので、将来的に改善が必要
    deleted_df[ColumnNames.PREV_FILE_PATH.value] = deleted_df[
        ColumnNames.PREV_FILE_PATH.value
    ].str.replace("/app/Repos/pandas/", "", regex=False)

    # ベクトル化演算: isin()を使って一括判定
    deleted_df["is_file_deleted"] = deleted_df[ColumnNames.PREV_FILE_PATH.value].isin(
        deleted_file_paths
    )

    deleted_df["is_private"] = deleted_df[ColumnNames.PREV_METHOD_NAME.value].str.contains("_")
    deleted_df["is_test_method"] = deleted_df[ColumnNames.PREV_FILE_PATH.value].str.contains(
        "test_"
    ) | deleted_df[ColumnNames.PREV_FILE_PATH.value].str.contains("_test")

    # deleted_df.to_csv(output_file, index=False)
    # console.print(f"[bold green]Updated file saved to {output_file}[/bold green]")

    print(
        deleted_df.groupby(
            ["is_test_method", "is_private", ColumnNames.HAS_CLONE.value, "is_file_deleted"]
        ).size()
    )
