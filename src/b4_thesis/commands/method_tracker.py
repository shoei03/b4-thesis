from typing import NamedTuple

import click
import pandas as pd
from rich.console import Console

console = Console()

# --- 型定義 ---

MethodKey = tuple[str, str, str, str]


class MethodEntry(NamedTuple):
    """method_to_id 辞書のエントリ"""

    method_id: int
    row_index: int
    is_identity: bool


# --- 定数 ---

_CATEGORICAL_COLUMNS = [
    "prev_file_path",
    "curr_file_path",
    "prev_method_name",
    "curr_method_name",
    "prev_return_type",
    "curr_return_type",
]


# --- ヘルパー関数 ---


def _make_method_key(row, prefix: str) -> MethodKey:
    """行データからメソッド識別キーを生成する"""
    return (
        getattr(row, f"{prefix}_file_path"),
        getattr(row, f"{prefix}_method_name"),
        getattr(row, f"{prefix}_return_type"),
        getattr(row, f"{prefix}_parameters"),
    )


def _load_and_preprocess(input_csv: str) -> pd.DataFrame:
    """CSVを読み込み、カテゴリ変換とソートを行う"""
    df = pd.read_csv(input_csv)

    for col in _CATEGORICAL_COLUMNS:
        if col in df.columns:
            df[col] = df[col].astype("category")

    # is_sig_matchedを優先処理するためのソート
    # sig_matchedの行を先に処理し、同じcurr_keyへのsim_matchedはマージとして扱う
    if "is_sig_matched" in df.columns:
        df = df.sort_values(
            ["prev_revision_id", "curr_revision_id", "is_sig_matched"],
            ascending=[True, True, False],
        )

    return df


def _handle_merge(
    curr_key: MethodKey,
    method_to_id: dict[MethodKey, MethodEntry],
    is_absorber_flags: list[bool],
    is_absorbed_flags: list[bool],
    stats: dict[str, int],
) -> None:
    """curr_keyが既に辞書に登録済みの場合のマージ処理

    A→A型（identity）: 既存行がabsorber
    A→B型（non-identity）: 既存行もabsorbed
    """
    existing = method_to_id[curr_key]
    if existing.is_identity:
        if not is_absorber_flags[existing.row_index]:
            is_absorber_flags[existing.row_index] = True
            stats["absorber_count"] += 1
    else:
        is_absorbed_flags[existing.row_index] = True
    stats["matched_absorbed"] += 1


def _assign_ids_core(
    df: pd.DataFrame,
) -> tuple[list[int], list[bool], list[bool], dict[str, int]]:
    """メソッドID割り当てのコアアルゴリズム

    Returns:
        (method_ids, is_absorbed_flags, is_absorber_flags, stats)
    """
    method_to_id: dict[MethodKey, MethodEntry] = {}
    next_id = 1
    method_ids: list[int] = []
    is_absorbed_flags = [False] * len(df)
    is_absorber_flags = [False] * len(df)

    stats: dict[str, int] = {
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
        prev_key = _make_method_key(row, "prev")
        curr_key = _make_method_key(row, "curr")
        is_absorbed = False

        if row.is_matched:
            stats["matched"] += 1

            # 判断1: method_idの決定（既存ID継承 or 新規割当）
            if prev_key in method_to_id:
                method_id = method_to_id.pop(prev_key).method_id
                id_source = "existing"
            else:
                method_id = next_id
                next_id += 1
                id_source = "new"

            # 判断2: curr_keyの登録 or マージ処理
            if curr_key not in method_to_id:
                method_to_id[curr_key] = MethodEntry(method_id, idx, prev_key == curr_key)
                stats[f"matched_with_{id_source}_id"] += 1
            else:
                is_absorbed = True
                _handle_merge(curr_key, method_to_id, is_absorber_flags, is_absorbed_flags, stats)

        elif row.is_deleted:
            stats["deleted"] += 1
            if prev_key in method_to_id:
                method_id = method_to_id.pop(prev_key).method_id
                stats["deleted_with_existing_id"] += 1
            else:
                method_id = next_id
                next_id += 1
                stats["deleted_with_new_id"] += 1

        elif row.is_added:
            stats["added"] += 1
            method_id = next_id
            next_id += 1
            method_to_id[curr_key] = MethodEntry(method_id, idx, True)

        else:
            print(f"Warning: Unexpected case at row {len(method_ids)}")
            method_id = next_id
            next_id += 1

        method_ids.append(method_id)
        is_absorbed_flags[idx] = is_absorbed

    stats["total_unique_ids"] = next_id - 1
    stats["active_methods_in_dict"] = len(method_to_id)
    return method_ids, is_absorbed_flags, is_absorber_flags, stats


# --- Click コマンド ---


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
def assign_method_ids(input_csv: str, output_csv: str) -> None:
    """CSVファイルを読み込み、メソッドに一意のIDを割り当てる"""
    print("\nProcessing method tracking...")

    df = _load_and_preprocess(input_csv)
    method_ids, is_absorbed_flags, is_absorber_flags, stats = _assign_ids_core(df)

    df["method_id"] = method_ids
    df["is_absorbed"] = is_absorbed_flags
    df["is_absorber"] = is_absorber_flags

    df.sort_values(["method_id", "prev_revision_id"]).to_csv(output_csv, index=False)

    stats["total_rows"] = len(df)
    _print_statistics(stats)
    print(f"Output saved to: {output_csv}")


# --- 表示ヘルパー ---


def _print_statistics(stats: dict) -> None:
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
