from pathlib import Path
import re
import subprocess

from git import Repo

# パス設定
repo_path = Path(__file__).parent.parent / "projects" / "pandas"
output_dir = Path(__file__).parent.parent / "output" / "refactoring_miner"
output_dir.mkdir(parents=True, exist_ok=True)

# リポジトリからタグを取得
repo = Repo(repo_path)
tags = [t for t in repo.tags if re.match(r"^v\d+\.\d+\.0$", t.name)]
tags.sort(key=lambda t: [int(x) for x in t.name[1:].split(".")])

# 連続するタグ間でRefactoringMinerを実行
for i in range(len(tags) - 1):
    prev_tag, next_tag = tags[i], tags[i + 1]
    output_file = f"pandas_{prev_tag.name}_to_{next_tag.name}.json"

    print(f"Analyzing {prev_tag.name} -> {next_tag.name}...")

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
        prev_tag.commit.hexsha,
        next_tag.commit.hexsha,
        "-json",
        f"/output/{output_file}",
    ]

    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"Error processing {prev_tag.name} -> {next_tag.name}")
