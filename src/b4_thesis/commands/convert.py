"""Convert tracking data to different formats."""

from pathlib import Path

import click
import pandas as pd
from rich.console import Console

from b4_thesis.analysis.union_find import UnionFind

console = Console()


@click.group()
def convert():
    """Convert tracking data to different formats."""
    pass


@convert.command()
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--lineage",
    is_flag=True,
    help="Convert to lineage format with unified global_block_id",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output file path (default: method_lineage.csv)",
)
def methods(input_file: Path, lineage: bool, output: Path | None) -> None:
    """
    Convert method tracking data to different formats.

    INPUT_FILE: Path to method_tracking.csv file

    Examples:
        b4-thesis convert methods ./output/method_tracking.csv --lineage -o result.csv
    """
    # Validate input
    if not lineage:
        console.print("[red]Error:[/red] No conversion option specified. Use --lineage")
        raise click.Abort()

    # Set default output path
    if output is None:
        output = Path("method_lineage.csv")

    # Read input CSV
    try:
        df = pd.read_csv(input_file)
    except Exception as e:
        console.print(f"[red]Error reading input file:[/red] {e}")
        raise click.Abort()

    # Validate required columns
    required_columns = ["revision", "block_id", "matched_block_id"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        console.print(f"[red]Error:[/red] Missing required columns: {', '.join(missing_columns)}")
        raise click.Abort()

    console.print(f"[bold blue]Converting:[/bold blue] {input_file}")
    console.print(f"[dim]Input rows:[/dim] {len(df)}")

    # Convert to lineage format
    lineage_df = _convert_to_lineage_format(df)

    # Save output
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        lineage_df.to_csv(output, index=False)
        console.print(f"[bold green]Saved:[/bold green] {output}")
        console.print(f"[dim]Output rows:[/dim] {len(lineage_df)}")
    except Exception as e:
        console.print(f"[red]Error writing output file:[/red] {e}")
        raise click.Abort()


def _convert_to_lineage_format(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert method tracking DataFrame to lineage format.

    Adds global_block_id column and removes block_id and matched_block_id columns.
    The global_block_id is unified across revisions based on matched_block_id relationships.

    Args:
        df: Input DataFrame with tracking data (must have revision, block_id, matched_block_id)

    Returns:
        DataFrame with lineage format (16 columns with global_block_id)
    """
    # Build global_block_id mapping using Union-Find
    global_block_id_map = _build_global_block_id_map(df)

    # Add global_block_id column
    result_df = df.copy()
    result_df["global_block_id"] = result_df.apply(
        lambda row: global_block_id_map.get(
            (row["revision"], row["block_id"]),
            row["block_id"],  # Fallback to block_id if not found
        ),
        axis=1,
    )

    # Define column order: global_block_id first, others except block_id/matched_block_id
    columns = ["global_block_id", "revision", "function_name", "file_path"]
    columns.extend(
        [
            "start_line",
            "end_line",
            "loc",
            "state",
            "state_detail",
            "match_type",
            "match_similarity",
            "clone_count",
            "clone_group_id",
            "clone_group_size",
            "lifetime_revisions",
            "lifetime_days",
        ]
    )

    return result_df[columns]


def _build_global_block_id_map(df: pd.DataFrame) -> dict[tuple[str, str], str]:
    """
    Build a mapping from (revision, block_id) to global_block_id.

    Uses Union-Find to track lineage relationships through matched_block_id.

    Args:
        df: Input DataFrame with revision, block_id, matched_block_id columns

    Returns:
        Dictionary mapping (revision, block_id) to global_block_id

    各行の説明:
    1. 関数定義: pandasのDataFrameを受け取り、(revision, block_id)のタプルをキーとし、
       global_block_idを値とする辞書を返す関数を定義

    2-11. docstring: 関数の概要と引数、戻り値を説明

    12-13. Union-Find構造体の初期化: ブロック間の系統関係を追跡するためのデータ構造を作成

    14-17. encode_key関数の定義: (revision, block_id)のタプルを、"::"で区切った文字列に変換する
           ヘルパー関数。Union-Findで使用するために一意のキーを生成

    18-21. decode_key関数の定義: encode_keyの逆変換を行うヘルパー関数。
           "::"で区切られた文字列を(revision, block_id)のタプルに戻す

    22-23. DataFrameのソート: リビジョンの順序でデータフレームをソートし、
           時系列順にブロックを処理できるようにする

    24-25. 第1パス開始: マッチしたブロック同士をUnion-Find構造で結合していく処理のループ

    26-28. 各行の情報取得: DataFrameの各行から、現在のリビジョン、ブロックID、
           マッチしたブロックIDの情報を取り出す

    29. 現在のキー生成: 現在のブロックを表す一意のキーを生成

    30-31. マッチ情報の確認: matched_block_idがnullや空文字でないかチェック。
           値が存在する場合、前のリビジョンでマッチしたブロックとの結合を行う

    32. 前のリビジョン一覧を取得: 現在のリビジョンより前のリビジョンをすべて抽出

    33. 前のリビジョンの存在確認: 前のリビジョンが1つ以上存在するか確認

    34-35. 直前のリビジョンを取得: ソートされた前のリビジョンのリストから、
           最も新しい（最後の）リビジョンを取得

    36-40. マッチしたブロックの検索: 直前のリビジョンにおいて、
           matched_block_idと同じblock_idを持つ行を検索

    41. 検索結果の確認: マッチしたブロックが見つかったか確認

    42-44. ブロック同士の結合: 現在のブロックと前のリビジョンでマッチしたブロックを
           Union-Find構造で同じグループに結合

    45-47. マッチしていない場合の処理: matched_block_idが存在しない場合でも、
           ブロックがUnion-Find構造に登録されるよう、find操作を実行

    48-50. 第2パス開始: Union-Findで作成されたグループに対して、
           各グループ内の最も古いブロックのIDをglobal_block_idとして割り当てる

    51. 戻り値の辞書を初期化: (revision, block_id)からglobal_block_idへのマッピングを格納する辞書

    52-53. グループの取得: Union-Find構造から、すべてのグループ（連結成分）を取得

    54-55. 各グループの処理: 各グループに対して、最も古いメンバーのblock_idを
           global_block_idとして使用する処理を実行

    56-57. メンバーのデコード: グループ内のすべてのメンバー（文字列キー）を
           (revision, block_id)のタプルに変換

    58-59. リビジョン順でソート: デコードされたメンバーをリビジョンの順序でソート

    60-61. global_block_idの決定: ソートされたメンバーの最初（最も古い）ブロックの
           block_idをglobal_block_idとして採用

    62-64. 全メンバーにglobal_block_idを割り当て: グループ内のすべてのメンバー
           （異なるリビジョンの同一系統のブロック）に同じglobal_block_idを設定

    65. マッピング辞書を返す: 完成した(revision, block_id) -> global_block_idのマッピングを返す
    """
    # Union-Find構造体を作成
    uf = UnionFind()

    # ヘルパー関数: (revision, block_id)を文字列キーにエンコード
    def encode_key(revision: str, block_id: str) -> str:
        return f"{revision}::{block_id}"

    # ヘルパー関数: 文字列キーを(revision, block_id)にデコード
    def decode_key(key: str) -> tuple[str, str]:
        parts = key.split("::", 1)
        return (parts[0], parts[1])

    # リビジョン順にソートして時系列で処理
    sorted_df = df.sort_values("revision")

    # 第1パス: マッチしたブロック同士を結合
    for _, row in sorted_df.iterrows():
        revision = row["revision"]
        block_id = row["block_id"]
        matched_block_id = row["matched_block_id"]

        current_key = encode_key(revision, block_id)

        # matched_block_idが存在する場合、前のリビジョンのブロックと結合
        if pd.notna(matched_block_id) and matched_block_id != "":
            # 現在より前のリビジョンをすべて取得
            prev_revisions = sorted_df[sorted_df["revision"] < revision]["revision"].unique()

            if len(prev_revisions) > 0:
                # 直前のリビジョンを取得
                prev_revision = sorted(prev_revisions)[-1]

                # 直前のリビジョンでマッチするブロックを検索
                matched_rows = sorted_df[
                    (sorted_df["revision"] == prev_revision)
                    & (sorted_df["block_id"] == matched_block_id)
                ]

                if not matched_rows.empty:
                    # 現在のブロックと前のブロックを同じグループに結合
                    prev_key = encode_key(prev_revision, matched_block_id)
                    uf.union(current_key, prev_key)
        else:
            # マッチしていない場合もUnion-Find構造に要素を登録
            uf.find(current_key)

    # 第2パス: 各グループにglobal_block_idを割り当て
    # グループ内の最も古いリビジョンのblock_idをglobal_block_idとして使用
    global_block_id_map: dict[tuple[str, str], str] = {}

    # すべてのグループを取得
    groups = uf.get_groups()

    # 各グループについて、最も古いメンバーのblock_idをglobal_block_idとする
    for root, members in groups.items():
        # すべてのメンバーをデコード
        decoded_members = [decode_key(member) for member in members]

        # リビジョン順にソートして最も古いものを見つける
        decoded_members.sort(key=lambda x: x[0])

        # 最も古いメンバーのblock_idをglobal_block_idとして採用
        global_block_id = decoded_members[0][1]

        # グループ内のすべてのメンバーに同じglobal_block_idを割り当て
        for member in decoded_members:
            global_block_id_map[member] = global_block_id

    return global_block_id_map
