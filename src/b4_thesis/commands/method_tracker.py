from pathlib import Path

import pandas as pd
import click
from rich.console import Console

console = Console()


@click.group()
def method_tracker():
    """Method Tracking Command Group."""
    pass


@method_tracker.command()
@click.option(
    "--input-csv",
    "-i",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    required=False,
    default="./output/versions/nil/3_sim_sig_match.csv",
    help="Input file containing tracked methods data",
)
@click.option(
    "--output-csv",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    required=False,
    default="./output/versions/method_tracker/methods_tracked.csv",
    help="Output file for classified results",
)
def assign_method_ids(input_csv: str, output_csv: str) -> dict:
    """
    CSVファイルを読み込み、メソッドに一意のIDを割り当てる

    Args:
        input_csv: 入力CSVファイルパス
        output_csv: 出力CSVファイルパス

    Returns:
        処理統計を含む辞書
    """
    df = pd.read_csv(input_csv)

    # カテゴリ型への変換でメモリ削減
    categorical_columns = [
        "prev_file_path",
        "curr_file_path",
        "prev_method_name",
        "curr_method_name",
        "prev_return_type",
        "curr_return_type",
    ]

    for col in categorical_columns:
        if col in df.columns:
            df[col] = df[col].astype("category")

    # is_sig_matchedを優先処理するためのソート
    # sig_matchedの行を先に処理し、同じcurr_keyへのsim_matchedはマージとして扱う
    if "is_sig_matched" in df.columns:
        df = df.sort_values(
            ["prev_revision_id", "curr_revision_id", "is_sig_matched"],
            ascending=[True, True, False],
        )

    print("\nProcessing method tracking...")

    # メイン処理
    method_to_id = {}  # key → (method_id, row_index, is_identity)
    next_id = 1
    method_ids = []
    is_absorbed_flags = [False] * len(df)
    is_absorber_flags = [False] * len(df)

    # 統計情報
    stats = {
        "matched": 0,
        "deleted": 0,
        "added": 0,
        "matched_with_existing_id": 0,
        "matched_with_new_id": 0,
        "deleted_with_existing_id": 0,
        "deleted_with_new_id": 0,
        "matched_absorbed": 0,
        "absorber_count": 0,
    }

    for idx, row in enumerate(df.itertuples(index=False)):
        # キー生成
        prev_key = (
            row.prev_file_path,
            row.prev_method_name,
            row.prev_return_type,
            row.prev_parameters,
        )
        curr_key = (
            row.curr_file_path,
            row.curr_method_name,
            row.curr_return_type,
            row.curr_parameters,
        )

        is_absorbed = False

        if row.is_matched:
            stats["matched"] += 1
            if prev_key in method_to_id:
                # 既存メソッドの継続：IDを継承
                method_id, _, _ = method_to_id[prev_key]
                del method_to_id[prev_key]
                if curr_key not in method_to_id:
                    method_to_id[curr_key] = (method_id, idx, prev_key == curr_key)
                    stats["matched_with_existing_id"] += 1
                else:
                    # マージ: curr_keyが既に登録済み
                    is_absorbed = True
                    _, receiver_idx, existing_is_identity = method_to_id[curr_key]
                    if existing_is_identity:
                        # A→A型: 既存行がabsorber（従来通り）
                        if not is_absorber_flags[receiver_idx]:
                            is_absorber_flags[receiver_idx] = True
                            stats["absorber_count"] += 1
                    else:
                        # A→B型: 既存行もabsorbed（absorberなし）
                        is_absorbed_flags[receiver_idx] = True
                    stats["matched_absorbed"] += 1
            else:
                # 辞書にない場合：新規ID割り当て
                method_id = next_id
                next_id += 1
                if curr_key not in method_to_id:
                    method_to_id[curr_key] = (method_id, idx, prev_key == curr_key)
                    stats["matched_with_new_id"] += 1
                else:
                    # マージ: curr_keyが既に登録済み
                    is_absorbed = True
                    _, receiver_idx, existing_is_identity = method_to_id[curr_key]
                    if existing_is_identity:
                        # A→A型: 既存行がabsorber（従来通り）
                        if not is_absorber_flags[receiver_idx]:
                            is_absorber_flags[receiver_idx] = True
                            stats["absorber_count"] += 1
                    else:
                        # A→B型: 既存行もabsorbed（absorberなし）
                        is_absorbed_flags[receiver_idx] = True
                    stats["matched_absorbed"] += 1

        elif row.is_deleted:
            stats["deleted"] += 1
            if prev_key in method_to_id:
                # 既存メソッドの削除：IDを取得して辞書から削除
                method_id, _, _ = method_to_id[prev_key]
                del method_to_id[prev_key]
                stats["deleted_with_existing_id"] += 1
            else:
                # 辞書にない場合：新規ID割り当て（この削除イベント用）
                method_id = next_id
                next_id += 1
                stats["deleted_with_new_id"] += 1

        elif row.is_added:
            stats["added"] += 1
            # 新規メソッドの追加：新規ID割り当て
            method_id = next_id
            next_id += 1
            method_to_id[curr_key] = (method_id, idx, True)

        else:
            # 想定外のケース（念のため）
            print(f"Warning: Unexpected case at row {len(method_ids)}")
            method_id = next_id
            next_id += 1

        method_ids.append(method_id)
        is_absorbed_flags[idx] = is_absorbed

    # 結果を追加
    df["method_id"] = method_ids
    df["is_absorbed"] = is_absorbed_flags
    df["is_absorber"] = is_absorber_flags

    # 出力
    df.sort_values(["method_id", "prev_revision_id"]).to_csv(output_csv, index=False)

    # 統計情報を追加
    stats["total_rows"] = len(df)
    stats["total_unique_ids"] = next_id - 1
    stats["active_methods_in_dict"] = len(method_to_id)

    # 統計情報表示
    print_statistics(stats)

    print(f"Output saved to: {output_csv}")


def print_statistics(stats: dict):
    """処理統計を表示"""
    print("\n" + "=" * 60)
    print("Processing Statistics")
    print("=" * 60)
    print(f"Total rows processed:        {stats['total_rows']:,}")
    print(f"Total unique method IDs:     {stats['total_unique_ids']:,}")
    print(f"Active methods (in dict):    {stats['active_methods_in_dict']:,}")
    print()
    print(f"Matched cases:               {stats['matched']:,}")
    print(f"  - With existing ID:        {stats['matched_with_existing_id']:,}")
    print(f"  - With new ID:             {stats['matched_with_new_id']:,}")
    print(f"  - Absorbed:                {stats['matched_absorbed']:,}")
    print(f"  - Absorber:                {stats['absorber_count']:,}")
    print()
    print(f"Deleted cases:               {stats['deleted']:,}")
    print(f"  - With existing ID:        {stats['deleted_with_existing_id']:,}")
    print(f"  - With new ID:             {stats['deleted_with_new_id']:,}")
    print()
    print(f"Added cases:                 {stats['added']:,}")
    print("=" * 60)
