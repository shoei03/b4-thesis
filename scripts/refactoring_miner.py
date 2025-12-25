from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from pathlib import Path
import re
import subprocess

from git import Repo
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)


def _generate_tag_pairs(tags: list) -> list[tuple[str, str, str, str]]:
    """Generate consecutive tag pairs with commit information.

    Args:
        tags: Sorted list of tag objects

    Returns:
        List of (prev_hexsha, next_hexsha, prev_name, next_name) tuples
    """
    return [
        (tags[i].commit.hexsha, tags[i + 1].commit.hexsha, tags[i].name, tags[i + 1].name)
        for i in range(len(tags) - 1)
    ]


def _process_tag_pair(
    pair: tuple[str, str, str, str],
    repo_path: Path,
    output_dir: Path,
) -> tuple[str, str, bool, str | None]:
    """Process a single tag pair with RefactoringMiner.

    Args:
        pair: Tuple of (prev_hexsha, next_hexsha, prev_name, next_name)
        repo_path: Path to repository
        output_dir: Directory for output JSON files

    Returns:
        Tuple of (prev_name, next_name, success, error_message)
    """
    prev_hexsha, next_hexsha, prev_name, next_name = pair
    output_file = f"pandas_{prev_name}_to_{next_name}.json"

    cmd = [
        "docker",
        "run",
        "-v",
        f"{repo_path}:/repo",
        "-v",
        f"{output_dir}:/output",
        "tsantalis/refactoringminer",
        "-bc",
        "/repo",
        prev_hexsha,
        next_hexsha,
        "-json",
        f"/output/{output_file}",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        if result.returncode == 0:
            return (prev_name, next_name, True, None)
        else:
            return (
                prev_name,
                next_name,
                False,
                f"Docker returned code {result.returncode}",
            )
    except subprocess.TimeoutExpired:
        return (prev_name, next_name, False, "Timeout (1 hour)")
    except Exception as e:
        return (prev_name, next_name, False, str(e))


# パス設定
repo_path = Path(__file__).parent.parent / "projects" / "pandas"
output_dir = Path(__file__).parent.parent / "output" / "refactoring_miner"
output_dir.mkdir(parents=True, exist_ok=True)

# リポジトリからタグを取得
repo = Repo(repo_path)
tags = [t for t in repo.tags if re.match(r"^v\d+\.\d+\.0$", t.name)]
tags.sort(key=lambda t: [int(x) for x in t.name[1:].split(".")])

# エッジケース処理
console = Console()

if len(tags) < 2:
    console.print("[yellow]At least 2 tags required[/yellow]")
    exit(0)

tag_pairs = _generate_tag_pairs(tags)

if not tag_pairs:
    console.print("[yellow]No tag pairs to process[/yellow]")
    exit(0)

# 並列処理でRefactoringMinerを実行
max_workers = os.cpu_count()
failed_analyses = []
successful_count = 0

with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    TaskProgressColumn(),
    console=console,
) as progress:
    task = progress.add_task(
        f"[cyan]Running RefactoringMiner on {len(tag_pairs)} tag pairs",
        total=len(tag_pairs),
    )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 全てのタスクを投入
        future_to_pair = {
            executor.submit(_process_tag_pair, pair, repo_path, output_dir): pair
            for pair in tag_pairs
        }

        # 完了順に処理
        for future in as_completed(future_to_pair):
            pair = future_to_pair[future]
            try:
                prev_name, next_name, success, error = future.result()

                if success:
                    successful_count += 1
                else:
                    failed_analyses.append((prev_name, next_name, error))
                    console.print(
                        f"[yellow]Warning: Failed {prev_name} -> {next_name}: {error}[/yellow]"
                    )
            except Exception as e:
                # スレッド実行エラーをキャッチ
                _, _, prev_name, next_name = pair
                failed_analyses.append((prev_name, next_name, str(e)))
                console.print(f"[red]Error: {prev_name} -> {next_name}: {e}[/red]")

            progress.update(task, advance=1)

# サマリー表示
console.print(f"\n[bold]Complete:[/bold] {successful_count}/{len(tag_pairs)} succeeded")

if failed_analyses:
    console.print("[yellow]Failed analyses:[/yellow]")
    for prev_name, next_name, error in failed_analyses:
        console.print(f"  - {prev_name} -> {next_name}: {error}")
