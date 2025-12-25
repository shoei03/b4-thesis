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


def ensure_repository(repo_path: Path, console: Console) -> None:
    """Ensure pandas repository exists and is properly cloned.

    Args:
        repo_path: Path to the repository
        console: Rich console for output
    """
    if not (repo_path / ".git").exists():
        console.print("[yellow]Pandas repository not found. Setting up...[/yellow]")

        setup_script = Path(__file__).parent / "setup_repository.sh"
        if not setup_script.exists():
            console.print(f"[red]Setup script not found at {setup_script}[/red]")
            exit(1)

        result = subprocess.run(["bash", str(setup_script)])
        if result.returncode != 0:
            console.print("[red]Failed to set up repository[/red]")
            exit(1)

        console.print("[green]Repository set up successfully[/green]")
    else:
        console.print("[dim]Repository found[/dim]")


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
    host_repo_path: Path,
    host_output_dir: Path,
) -> tuple[str, str, bool, str | None]:
    """Process a single tag pair with RefactoringMiner.

    Args:
        pair: Tuple of (prev_hexsha, next_hexsha, prev_name, next_name)
        repo_path: Path to repository (container path)
        output_dir: Directory for output JSON files (container path)
        host_repo_path: Path to repository (host path for Docker volume mount)
        host_output_dir: Directory for output JSON files (host path for Docker volume mount)

    Returns:
        Tuple of (prev_name, next_name, success, error_message)
    """
    prev_hexsha, next_hexsha, prev_name, next_name = pair
    output_file = f"pandas_{prev_name}_to_{next_name}.json"
    output_path = output_dir / output_file

    # Skip if output file already exists
    if output_path.exists():
        return (prev_name, next_name, True, "skipped (already exists)")

    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{host_repo_path}:/repo",
        "-v",
        f"{host_output_dir}:/output",
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
            error_msg = f"Docker returned code {result.returncode}"
            if result.stderr:
                error_msg += f"\nStderr: {result.stderr.strip()}"
            if result.stdout:
                error_msg += f"\nStdout: {result.stdout.strip()}"
            return (prev_name, next_name, False, error_msg)
    except subprocess.TimeoutExpired:
        return (prev_name, next_name, False, "Timeout (1 hour)")
    except Exception as e:
        return (prev_name, next_name, False, str(e))


# パス設定
base_dir = Path(__file__).parent.parent
repo_path = base_dir / "projects" / "pandas"
output_dir = base_dir / "output" / "refactoring_miner"
output_dir.mkdir(parents=True, exist_ok=True)

# ホスト側パス（Docker-in-Docker用のボリュームマウントに使用）
# デフォルトは親ディレクトリのprojects/outputを使用（ローカル実行想定）
host_repo_path = Path(os.getenv("HOST_PROJECTS_PATH", str(base_dir.parent / "projects"))) / "pandas"
host_output_dir = (
    Path(os.getenv("HOST_OUTPUT_PATH", str(base_dir / "output"))) / "refactoring_miner"
)

console = Console()

print(f"Repository path (container): {repo_path}")
print(f"Repository path (host): {host_repo_path}")
print(f"Output directory (container): {output_dir}")
print(f"Output directory (host): {host_output_dir}")

# リポジトリが存在することを確認（必要であればクローン）
ensure_repository(repo_path, console)

# リポジトリからタグを取得
repo = Repo(repo_path)
tags = [t for t in repo.tags if re.match(r"^v\d+\.\d+\.0$", t.name)]
tags.sort(key=lambda t: [int(x) for x in t.name[1:].split(".")])

# エッジケース処理

if len(tags) < 2:
    console.print("[yellow]At least 2 tags required[/yellow]")
    exit(0)

tag_pairs = _generate_tag_pairs(tags)

if not tag_pairs:
    console.print("[yellow]No tag pairs to process[/yellow]")
    exit(0)

# Docker可用性チェック
console.print("[dim]Checking Docker availability...[/dim]")
try:
    docker_version = subprocess.run(
        ["docker", "version", "--format", "{{.Server.Version}}"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    if docker_version.returncode == 0:
        console.print(f"[dim]Docker version: {docker_version.stdout.strip()}[/dim]")
    else:
        console.print("[yellow]Warning: Docker may not be available[/yellow]")
except Exception as e:
    console.print(f"[yellow]Warning: Could not check Docker: {e}[/yellow]")

# 並列処理でRefactoringMinerを実行
max_workers = 3
failed_analyses = []
successful_count = 0
skipped_count = 0

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
            executor.submit(
                _process_tag_pair, pair, repo_path, output_dir, host_repo_path, host_output_dir
            ): pair
            for pair in tag_pairs
        }

        # 完了順に処理
        for future in as_completed(future_to_pair):
            pair = future_to_pair[future]
            try:
                prev_name, next_name, success, error = future.result()

                if success:
                    if error and "skipped" in error:
                        skipped_count += 1
                    else:
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
console.print(
    f"\n[bold]Complete:[/bold] {successful_count}/{len(tag_pairs)} succeeded, "
    f"{skipped_count} skipped"
)

if failed_analyses:
    console.print("[yellow]Failed analyses:[/yellow]")
    for prev_name, next_name, error in failed_analyses:
        console.print(f"  - {prev_name} -> {next_name}: {error}")
