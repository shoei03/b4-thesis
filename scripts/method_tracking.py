"""
メソッドバージョン追跡システム - 一意のIDを割り当て

CSVファイルからメソッドの変更履歴を読み込み、
バージョン間でメソッドを追跡して一意のIDを割り当てます。
"""

from pathlib import Path
import sys

import pandas as pd


def assign_method_ids(input_csv: str, output_csv: str) -> dict:
    """
    CSVファイルを読み込み、メソッドに一意のIDを割り当てる

    Args:
        input_csv: 入力CSVファイルパス
        output_csv: 出力CSVファイルパス

    Returns:
        処理統計を含む辞書
    """
    print(f"Reading CSV file: {input_csv}")
    df = pd.read_csv(input_csv)

    print(f"Total rows: {len(df)}")
    print(f"Columns: {df.columns.tolist()}")

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

    print("\nProcessing method tracking...")

    # メイン処理
    method_to_id = {}
    next_id = 1
    method_ids = []

    # 統計情報
    stats = {
        "matched": 0,
        "deleted": 0,
        "added": 0,
        "matched_with_existing_id": 0,
        "matched_with_new_id": 0,
        "deleted_with_existing_id": 0,
        "deleted_with_new_id": 0,
    }

    for row in df.itertuples(index=False):
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

        if row.is_matched:
            stats["matched"] += 1
            if prev_key in method_to_id:
                # 既存メソッドの継続：IDを継承
                method_id = method_to_id[prev_key]
                del method_to_id[prev_key]
                method_to_id[curr_key] = method_id
                stats["matched_with_existing_id"] += 1
            else:
                # 辞書にない場合：新規ID割り当て
                method_id = next_id
                next_id += 1
                method_to_id[curr_key] = method_id
                stats["matched_with_new_id"] += 1

        elif row.is_deleted:
            stats["deleted"] += 1
            if prev_key in method_to_id:
                # 既存メソッドの削除：IDを取得して辞書から削除
                method_id = method_to_id[prev_key]
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
            method_to_id[curr_key] = method_id

        else:
            # 想定外のケース（念のため）
            print(f"Warning: Unexpected case at row {len(method_ids)}")
            method_id = next_id
            next_id += 1

        method_ids.append(method_id)

    # 結果を追加
    df["method_id"] = method_ids

    # 出力
    print(f"\nWriting output to: {output_csv}")
    df.to_csv(output_csv, index=False)

    # 統計情報を追加
    stats["total_rows"] = len(df)
    stats["total_unique_ids"] = next_id - 1
    stats["active_methods_in_dict"] = len(method_to_id)

    return stats


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
    print()
    print(f"Deleted cases:               {stats['deleted']:,}")
    print(f"  - With existing ID:        {stats['deleted_with_existing_id']:,}")
    print(f"  - With new ID:             {stats['deleted_with_new_id']:,}")
    print()
    print(f"Added cases:                 {stats['added']:,}")
    print("=" * 60)


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print("Usage: python assign_method_ids.py <input_csv> [output_csv]")
        print("\nExample:")
        print("  python assign_method_ids.py input.csv output.csv")
        print("  python assign_method_ids.py input.csv")
        sys.exit(1)

    input_csv = sys.argv[1]

    # 出力ファイル名の決定
    if len(sys.argv) >= 3:
        output_csv = sys.argv[2]
    else:
        input_path = Path(input_csv)
        output_csv = str(input_path.parent / f"{input_path.stem}_with_ids{input_path.suffix}")

    # 入力ファイルの存在確認
    if not Path(input_csv).exists():
        print(f"Error: Input file not found: {input_csv}")
        sys.exit(1)

    try:
        # メイン処理実行
        stats = assign_method_ids(input_csv, output_csv)

        # 統計情報表示
        print_statistics(stats)

        print(f"\n✓ Successfully completed!")
        print(f"Output saved to: {output_csv}")

    except Exception as e:
        print(f"\n✗ Error occurred: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
