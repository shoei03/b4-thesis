#!/usr/bin/env python3
"""
NIL クローン検出実行スクリプト（バージョンバッチ実行専用）

v*.*.0 形式のバージョンタグごとにNILを実行する
"""

import argparse
from datetime import datetime
import logging
import re
import subprocess
import sys

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

DOCKER_CMD = ["docker", "compose", "run", "--rm", "nil"]


def run_docker(cmd: list[str], capture: bool = True) -> subprocess.CompletedProcess:
    """Dockerコンテナ内でコマンドを実行"""
    return subprocess.run(
        DOCKER_CMD + cmd,
        capture_output=capture,
        text=True,
        check=True,
    )


def run_git(source_dir: str, args: list[str]) -> str:
    """Gitコマンドを実行して出力を返す"""
    result = run_docker(["git", "-C", source_dir] + args)
    return result.stdout.strip()


def get_version_tags(source_dir: str) -> list[str]:
    """v*.*.0 形式のバージョンタグを取得（新しい順）"""
    output = run_git(source_dir, ["tag", "-l", "v*", "--sort=-v:refname"])
    pattern = re.compile(r"^v\d+\.\d+\.0$")
    return [tag for tag in output.split("\n") if tag and pattern.match(tag)]


def get_commit_info(source_dir: str) -> tuple[str, str, str]:
    """コミット情報を取得 (短縮ハッシュ, フォーマット済み日時, 表示用日時)"""
    full_hash = run_git(source_dir, ["rev-parse", "HEAD"])
    timestamp = int(run_git(source_dir, ["show", "-s", "--format=%ct", "HEAD"]))
    dt = datetime.fromtimestamp(timestamp)
    return full_hash[:8], dt.strftime("%Y%m%d_%H%M%S"), dt.strftime("%Y-%m-%d %H:%M:%S")


def checkout(source_dir: str, target: str) -> bool:
    """クリーンな状態でチェックアウト"""
    try:
        run_git(source_dir, ["reset", "--hard"])
        run_git(source_dir, ["clean", "-fd"])
        run_git(source_dir, ["checkout", target])
        return True
    except subprocess.CalledProcessError:
        return False


def run_nil(source_dir: str, language: str, short_commit: str, formatted_time: str, output_dir: str | None = None) -> bool:
    """NILを実行"""
    cmd = [
        "java", "-jar", "./build/libs/NIL-all.jar",
        "-s", source_dir,
        "-l", language,
        "-ch", short_commit,
        "-ct", formatted_time,
    ]
    if output_dir:
        cmd.extend(["-o", output_dir])
    try:
        run_docker(cmd, capture=False)
        return True
    except subprocess.CalledProcessError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="NIL バージョンバッチ実行")
    parser.add_argument("project", nargs="?", default="pandas", help="プロジェクト名 (デフォルト: pandas)")
    parser.add_argument("-s", "--source-dir", help="ソースディレクトリ (デフォルト: /app/Repos/{project})")
    parser.add_argument("-l", "--language", default="python", help="言語 (デフォルト: python)")
    parser.add_argument("-o", "--output", help="出力ディレクトリ (デフォルト: results/{project}/)")
    parser.add_argument("--dry-run", action="store_true", help="実行せずにバージョン一覧のみ表示")
    args = parser.parse_args()

    # projectに基づいてデフォルト値を設定
    source_dir = args.source_dir or f"/app/Repos/{args.project}"
    output_dir = args.output or f"results/{args.project}/"

    # JARファイル確認
    try:
        run_docker(["test", "-f", "./build/libs/NIL-all.jar"])
    except subprocess.CalledProcessError:
        logger.error("❌ NIL-all.jarが見つかりません。./scripts/build.sh を実行してください")
        return 1

    # バージョンタグ取得
    logger.info(f"📋 プロジェクト: {args.project}")
    logger.info(f"📁 ソースディレクトリ: {source_dir}")
    logger.info(f"📂 出力ディレクトリ: {output_dir}")
    logger.info("📋 バージョンタグを取得中...")
    tags = get_version_tags(source_dir)
    logger.info(f"📊 実行対象: {len(tags)} バージョン")

    # ドライラン
    if args.dry_run:
        for i, tag in enumerate(tags, 1):
            info = run_git(source_dir, ["log", "-1", "--format=%h %ai %s", tag])
            logger.info(f"  {i}. {tag} - {info}")
        return 0

    # 現在の状態を保存
    try:
        original = run_git(source_dir, ["branch", "--show-current"]) or \
                   run_git(source_dir, ["rev-parse", "HEAD"])
    except subprocess.CalledProcessError:
        original = None

    # バッチ実行
    successful, failed = [], []
    for i, tag in enumerate(tags, 1):
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"🔄 [{i}/{len(tags)}] {tag}")

        if not checkout(source_dir, tag):
            logger.error(f"❌ チェックアウト失敗: {tag}")
            failed.append(tag)
            continue

        short_commit, formatted_time, display_time = get_commit_info(source_dir)
        logger.info(f"📝 {output_dir}{formatted_time}_{short_commit}/ ({display_time})")

        if run_nil(source_dir, args.language, short_commit, formatted_time, output_dir):
            logger.info(f"✅ 完了: {tag}")
            successful.append(tag)
        else:
            logger.error(f"❌ 失敗: {tag}")
            failed.append(tag)

    # 元に戻す
    if original:
        logger.info("🔄 元の状態に戻しています...")
        checkout(source_dir, original)

    # サマリー
    logger.info(f"\n🎉 完了: {len(successful)}/{len(tags)} 成功")
    if failed:
        logger.info(f"❌ 失敗: {', '.join(failed)}")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())