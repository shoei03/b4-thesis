# メソッド追跡分析 実装設計書

## 概要

このドキュメントでは、メソッド削除・クローングループ追跡分析の実装における詳細な設計を定義します。

## アーキテクチャ概要

```
┌─────────────────────────────────────────────────────────────┐
│                     CLI Layer (Click)                       │
│  track-methods / track-groups / track-all                   │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│                Application Layer                            │
│  ├─ MethodTracker                                           │
│  └─ CloneGroupTracker                                       │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│                 Core Analysis Layer                         │
│  ├─ MethodMatcher (2-phase matching)                        │
│  ├─ GroupDetector (UnionFind)                               │
│  ├─ GroupMatcher (overlap-based)                            │
│  └─ StateClassifier                                         │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│                  Utility Layer                              │
│  ├─ UnionFind (data structure)                              │
│  ├─ SimilarityCalculator                                    │
│  └─ RevisionManager                                         │
└─────────────────────────────────────────────────────────────┘
```

## モジュール構成

### 1. ディレクトリ構造

```
src/b4_thesis/
├── analysis/
│   ├── __init__.py
│   ├── similarity.py              # 既存（類似度計算）
│   ├── union_find.py              # NEW: UnionFindデータ構造
│   ├── method_matcher.py          # NEW: メソッドマッチング
│   ├── group_detector.py          # NEW: グループ検出
│   ├── group_matcher.py           # NEW: グループマッチング
│   ├── state_classifier.py        # NEW: 状態分類
│   ├── method_tracker.py          # NEW: メソッド追跡メインロジック
│   └── clone_group_tracker.py     # NEW: グループ追跡メインロジック
├── commands/
│   └── track.py                   # NEW: CLIコマンド
└── core/
    └── revision_manager.py        # NEW: リビジョン管理

tests/
├── analysis/
│   ├── test_union_find.py         # NEW
│   ├── test_method_matcher.py     # NEW
│   ├── test_group_detector.py     # NEW
│   ├── test_group_matcher.py      # NEW
│   ├── test_state_classifier.py   # NEW
│   ├── test_method_tracker.py     # NEW
│   └── test_clone_group_tracker.py # NEW
├── commands/
│   └── test_track.py              # NEW
└── fixtures/
    └── sample_revisions/          # NEW: テスト用データ
```

## コンポーネント詳細設計

### 1. UnionFind (union_find.py)

**責務**: 連結成分検出のためのデータ構造

**クラス設計**:
```python
class UnionFind:
    """Union-Find (Disjoint Set Union) data structure with path compression."""

    def __init__(self) -> None:
        """Initialize empty Union-Find structure."""

    def find(self, x: str) -> str:
        """Find root of element x with path compression."""

    def union(self, x: str, y: str) -> None:
        """Union two sets containing x and y."""

    def get_groups(self) -> dict[str, list[str]]:
        """Get all connected components as {root: [members]}."""

    def is_connected(self, x: str, y: str) -> bool:
        """Check if x and y are in the same set."""

    def size(self) -> int:
        """Get number of elements."""

    def num_groups(self) -> int:
        """Get number of distinct groups."""
```

**テストケース**:
- 基本操作（find, union）
- 経路圧縮の検証
- 複数グループの検出
- エッジケース（空集合、単一要素）

### 2. SimilarityCalculator (similarity.py への拡張)

**既存関数**:
- `calculate_ngram_similarity(tokens_1, tokens_2) -> int`
- `calculate_lcs_similarity(tokens_1, tokens_2) -> int`
- `parse_token_sequence(token_seq: str) -> list[int]`

**新規関数**:
```python
def calculate_similarity(token_seq_1: str, token_seq_2: str) -> int:
    """
    Calculate similarity between two token sequences.

    2-phase approach:
    1. N-gram similarity
    2. LCS similarity (only if N-gram < 70)

    Args:
        token_seq_1: Token sequence string (e.g., "[123;456;789]")
        token_seq_2: Token sequence string

    Returns:
        Similarity score (0-100)
    """
```

**テストケース**:
- 完全一致（similarity = 100）
- 部分一致（70 <= similarity < 100）
- 低類似度（similarity < 70）
- N-gram ≥ 70 でLCSスキップの検証
- 異常入力（空文字列、不正フォーマット）

### 3. RevisionManager (core/revision_manager.py)

**責務**: リビジョンディレクトリの管理と時系列ソート

**クラス設計**:
```python
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass

@dataclass
class RevisionInfo:
    """Information about a single revision."""
    timestamp: datetime
    directory: Path
    clone_pairs_path: Path
    code_blocks_path: Path

    @property
    def revision_id(self) -> str:
        """Get revision ID (directory name)."""

class RevisionManager:
    """Manages revision directories and provides sorted access."""

    def __init__(self, data_dir: Path) -> None:
        """Initialize with data directory containing revisions."""

    def get_revisions(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None
    ) -> list[RevisionInfo]:
        """Get sorted list of revisions in date range."""

    def load_revision_data(
        self,
        revision: RevisionInfo
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Load code_blocks and clone_pairs DataFrames for a revision."""
```

**テストケース**:
- リビジョン検出
- 時系列ソート
- 日付範囲フィルタリング
- データ読み込み
- 不正なディレクトリ処理

### 4. MethodMatcher (analysis/method_matcher.py)

**責務**: リビジョン間でメソッドをマッチング（2段階戦略）

**クラス設計**:
```python
from dataclasses import dataclass
from enum import Enum

class MatchType(Enum):
    """Type of match between methods."""
    TOKEN_HASH = "token_hash"
    SIMILARITY = "similarity"
    NONE = "none"

@dataclass
class MethodMatch:
    """Result of matching a method between revisions."""
    source_block_id: str
    target_block_id: str | None
    match_type: MatchType
    similarity: int | None  # 0-100, None for token_hash or no match

class MethodMatcher:
    """Matches methods between consecutive revisions."""

    def __init__(self, similarity_threshold: int = 70) -> None:
        """Initialize with similarity threshold."""

    def match_revisions(
        self,
        code_blocks_old: pd.DataFrame,
        code_blocks_new: pd.DataFrame
    ) -> dict[str, MethodMatch]:
        """
        Match methods from old revision to new revision.

        Returns:
            Dictionary mapping old_block_id -> MethodMatch
        """

    def _phase1_token_hash_matching(
        self,
        code_blocks_old: pd.DataFrame,
        code_blocks_new: pd.DataFrame
    ) -> dict[str, str]:
        """Phase 1: Fast token_hash based matching."""

    def _phase2_similarity_matching(
        self,
        unmatched_old: list[str],
        unmatched_new: list[str],
        code_blocks_old: pd.DataFrame,
        code_blocks_new: pd.DataFrame
    ) -> dict[str, MethodMatch]:
        """Phase 2: Similarity-based matching for unmatched blocks."""

    def create_bidirectional_matches(
        self,
        matches_old_to_new: dict[str, MethodMatch],
        matches_new_to_old: dict[str, MethodMatch]
    ) -> tuple[dict[str, MethodMatch], dict[str, MethodMatch]]:
        """Integrate forward and backward matches."""
```

**テストケース**:
- Phase 1: token_hash完全一致
- Phase 2: 類似度マッチング
- 複数候補から最高類似度選択
- 双方向マッチングの整合性
- 閾値未満のケース
- 1対多、多対1のケース検証

### 5. GroupDetector (analysis/group_detector.py)

**責務**: 単一リビジョン内でクローングループを検出

**クラス設計**:
```python
from dataclasses import dataclass

@dataclass
class CloneGroup:
    """A group of cloned methods."""
    group_id: str  # Root block_id
    members: list[str]  # Block IDs
    similarities: dict[tuple[str, str], int]  # Pair similarities

    @property
    def size(self) -> int:
        """Number of members in the group."""

    @property
    def avg_similarity(self) -> float | None:
        """Average similarity of all pairs."""

    @property
    def min_similarity(self) -> int | None:
        """Minimum similarity among pairs."""

    @property
    def max_similarity(self) -> int | None:
        """Maximum similarity among pairs."""

    @property
    def density(self) -> float:
        """Graph density: actual_edges / possible_edges."""

    @property
    def is_clone(self) -> bool:
        """True if group has 2+ members."""

class GroupDetector:
    """Detects clone groups within a single revision using UnionFind."""

    def __init__(self, similarity_threshold: int = 70) -> None:
        """Initialize with similarity threshold for group formation."""

    def detect_groups(
        self,
        code_blocks: pd.DataFrame,
        clone_pairs: pd.DataFrame
    ) -> dict[str, CloneGroup]:
        """
        Detect clone groups in a revision.

        Returns:
            Dictionary mapping group_id -> CloneGroup
        """

    def _get_effective_similarity(self, pair_row: pd.Series) -> int:
        """Get effective similarity from clone_pairs row."""
```

**テストケース**:
- 単一グループ検出
- 複数グループ検出
- 孤立メソッド（グループサイズ=1）
- 閾値境界ケース
- グループメトリクス計算（avg, min, max, density）
- 空データ処理

### 6. GroupMatcher (analysis/group_matcher.py)

**責務**: リビジョン間でクローングループをマッチング

**クラス設計**:
```python
from dataclasses import dataclass

@dataclass
class GroupMatch:
    """Result of matching a group between revisions."""
    source_group_id: str
    target_group_id: str | None
    overlap_count: int  # Number of matched members
    overlap_ratio: float  # overlap_count / source_group_size
    source_size: int
    target_size: int | None

class GroupMatcher:
    """Matches clone groups between consecutive revisions."""

    def __init__(self, overlap_threshold: float = 0.5) -> None:
        """Initialize with overlap ratio threshold."""

    def match_groups(
        self,
        groups_old: dict[str, CloneGroup],
        groups_new: dict[str, CloneGroup],
        method_matches: dict[str, MethodMatch]
    ) -> dict[str, GroupMatch]:
        """
        Match groups from old revision to new revision.

        Returns:
            Dictionary mapping old_group_id -> GroupMatch
        """

    def _find_group_of_block(
        self,
        block_id: str,
        groups: dict[str, CloneGroup]
    ) -> str | None:
        """Find which group a block belongs to."""

    def detect_splits(
        self,
        matches: dict[str, GroupMatch]
    ) -> list[tuple[str, list[str]]]:
        """
        Detect split groups (1 old -> multiple new).

        Returns:
            List of (old_group_id, [new_group_ids])
        """

    def detect_merges(
        self,
        matches: dict[str, GroupMatch]
    ) -> list[tuple[list[str], str]]:
        """
        Detect merged groups (multiple old -> 1 new).

        Returns:
            List of ([old_group_ids], new_group_id)
        """
```

**テストケース**:
- 単純マッチング（1対1）
- 重複率計算
- 閾値未満のケース
- 分裂検出（1対多）
- 統合検出（多対1）
- 複雑なパターン（分裂と統合の同時発生）

### 7. StateClassifier (analysis/state_classifier.py)

**責務**: メソッドとグループの状態を分類

**クラス設計**:
```python
from enum import Enum

class MethodState(Enum):
    """Main state of a method."""
    DELETED = "deleted"
    SURVIVED = "survived"
    ADDED = "added"

class MethodStateDetail(Enum):
    """Detailed state of a method."""
    # Deleted
    DELETED_ISOLATED = "deleted_isolated"
    DELETED_FROM_GROUP = "deleted_from_group"
    DELETED_LAST_MEMBER = "deleted_last_member"

    # Survived
    SURVIVED_UNCHANGED = "survived_unchanged"
    SURVIVED_MODIFIED = "survived_modified"
    SURVIVED_CLONE_GAINED = "survived_clone_gained"
    SURVIVED_CLONE_LOST = "survived_clone_lost"

    # Added
    ADDED_ISOLATED = "added_isolated"
    ADDED_TO_GROUP = "added_to_group"
    ADDED_NEW_GROUP = "added_new_group"

class GroupState(Enum):
    """State of a clone group."""
    CONTINUED = "continued"
    GROWN = "grown"
    SHRUNK = "shrunk"
    SPLIT = "split"
    MERGED = "merged"
    DISSOLVED = "dissolved"
    BORN = "born"

class StateClassifier:
    """Classifies method and group states."""

    def classify_method_state(
        self,
        block_id: str,
        match: MethodMatch,
        group_old: CloneGroup | None,
        group_new: CloneGroup | None,
        is_last_member: bool = False
    ) -> tuple[MethodState, MethodStateDetail]:
        """Classify a method's state and detail."""

    def classify_group_state(
        self,
        group_match: GroupMatch,
        is_split: bool = False,
        is_merged: bool = False
    ) -> GroupState:
        """Classify a group's state."""
```

**テストケース**:
- 各メソッド状態の分類（9パターン）
- 各グループ状態の分類（7パターン）
- 境界ケース（±10%のサイズ変化）
- 複合条件（分裂かつ縮小など）

### 8. MethodTracker (analysis/method_tracker.py)

**責務**: メソッド追跡の統合ワークフロー

**クラス設計**:
```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class MethodTrackingResult:
    """Result of method tracking analysis."""
    revision: str
    block_id: str
    function_name: str
    file_path: str
    start_line: int
    end_line: int
    loc: int
    state: str
    state_detail: str
    matched_block_id: str | None
    match_type: str
    match_similarity: int | None
    clone_count: int
    clone_group_id: str | None
    clone_group_size: int
    lifetime_revisions: int
    lifetime_days: int

class MethodTracker:
    """Tracks method evolution across revisions."""

    def __init__(
        self,
        data_dir: Path,
        similarity_threshold: int = 70
    ) -> None:
        """Initialize method tracker."""

    def track(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None
    ) -> pd.DataFrame:
        """
        Track methods across revisions.

        Returns:
            DataFrame with method tracking results
        """

    def _process_revision_pair(
        self,
        revision_old: RevisionInfo,
        revision_new: RevisionInfo,
        lifetime_tracker: dict[str, dict]
    ) -> list[MethodTrackingResult]:
        """Process a pair of consecutive revisions."""

    def _calculate_lifetime(
        self,
        block_id: str,
        current_revision: datetime,
        lifetime_tracker: dict[str, dict]
    ) -> tuple[int, int]:
        """Calculate lifetime_revisions and lifetime_days."""
```

**テストケース**:
- 単一リビジョンペア処理
- 複数リビジョン追跡
- 寿命計算
- CSV出力フォーマット検証
- 大規模データ処理

### 9. CloneGroupTracker (analysis/clone_group_tracker.py)

**責務**: クローングループ追跡の統合ワークフロー

**クラス設計**:
```python
from dataclasses import dataclass

@dataclass
class GroupTrackingResult:
    """Result of group tracking analysis."""
    revision: str
    group_id: str
    member_count: int
    avg_similarity: float | None
    min_similarity: int | None
    max_similarity: int | None
    density: float
    state: str
    matched_group_id: str | None
    overlap_ratio: float | None
    member_added: int
    member_removed: int
    lifetime_revisions: int
    lifetime_days: int

@dataclass
class GroupMembershipResult:
    """Group membership snapshot."""
    revision: str
    group_id: str
    block_id: str
    function_name: str
    is_clone: bool

class CloneGroupTracker:
    """Tracks clone group evolution across revisions."""

    def __init__(
        self,
        data_dir: Path,
        similarity_threshold: int = 70,
        overlap_threshold: float = 0.5
    ) -> None:
        """Initialize clone group tracker."""

    def track(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Track clone groups across revisions.

        Returns:
            Tuple of (group_tracking_df, membership_df)
        """

    def _process_revision_pair(
        self,
        revision_old: RevisionInfo,
        revision_new: RevisionInfo,
        lifetime_tracker: dict[str, dict]
    ) -> tuple[list[GroupTrackingResult], list[GroupMembershipResult]]:
        """Process a pair of consecutive revisions."""

    def _calculate_member_changes(
        self,
        group_old: CloneGroup,
        group_new: CloneGroup,
        method_matches: dict[str, MethodMatch]
    ) -> tuple[int, int]:
        """Calculate member_added and member_removed."""
```

**テストケース**:
- グループ検出と追跡
- メンバーシップ記録
- グループ状態分類
- 分裂・統合検出
- 寿命計算
- CSV出力フォーマット検証

### 10. CLI Commands (commands/track.py)

**責務**: CLIインターフェース提供

**コマンド設計**:
```python
import click
from rich.console import Console
from rich.table import Table

@click.group()
def track():
    """Track method and clone group evolution."""
    pass

@track.command("methods")
@click.argument("data_dir", type=click.Path(exists=True))
@click.option("--start-date", help="Start date (YYYYMMDD)")
@click.option("--end-date", help="End date (YYYYMMDD)")
@click.option("--similarity-threshold", default=70, help="Similarity threshold")
@click.option("--output", default="method_tracking.csv", help="Output file")
def track_methods(data_dir, start_date, end_date, similarity_threshold, output):
    """Track methods across revisions."""
    pass

@track.command("groups")
@click.argument("data_dir", type=click.Path(exists=True))
@click.option("--start-date", help="Start date (YYYYMMDD)")
@click.option("--end-date", help="End date (YYYYMMDD)")
@click.option("--similarity-threshold", default=70, help="Similarity threshold")
@click.option("--overlap-threshold", default=0.5, help="Group overlap threshold")
@click.option("--output-tracking", default="group_tracking.csv")
@click.option("--output-membership", default="group_membership.csv")
def track_groups(data_dir, start_date, end_date, similarity_threshold,
                 overlap_threshold, output_tracking, output_membership):
    """Track clone groups across revisions."""
    pass

@track.command("all")
@click.argument("data_dir", type=click.Path(exists=True))
@click.option("--start-date", help="Start date (YYYYMMDD)")
@click.option("--end-date", help="End date (YYYYMMDD)")
@click.option("--similarity-threshold", default=70)
@click.option("--overlap-threshold", default=0.5)
@click.option("--output-dir", default="results/tracking_analysis")
@click.option("--show-summary", is_flag=True, help="Show summary statistics")
def track_all(data_dir, start_date, end_date, similarity_threshold,
              overlap_threshold, output_dir, show_summary):
    """Track both methods and groups."""
    pass
```

**テストケース**:
- コマンド引数解析
- ファイル出力検証
- サマリー表示
- エラーハンドリング

## データフロー

```
1. RevisionManager
   ↓
   リビジョンリストを時系列ソート

2. For each consecutive pair (N-1, N):
   ↓
   2a. Load code_blocks and clone_pairs

   2b. GroupDetector
       - UnionFindでグループ検出（両リビジョン）

   2c. MethodMatcher
       - Phase 1: token_hash matching
       - Phase 2: similarity matching
       - 双方向マッチング統合

   2d. GroupMatcher
       - メンバー重複ベースマッチング
       - 分裂・統合検出

   2e. StateClassifier
       - メソッド状態分類
       - グループ状態分類

   2f. Lifetime Tracking
       - 寿命情報更新

3. 結果集約
   ↓
   CSV出力
```

## パフォーマンス考慮

### 計算量

| 処理 | 計算量 | 説明 |
|------|--------|------|
| UnionFind | O(n × α(n)) | 実用上 O(n) |
| token_hash matching | O(n) | ハッシュテーブル検索 |
| similarity matching | O(m × k × s) | m: 未マッチ数、k: 候補数、s: トークン長 |
| group detection | O(n + p) | n: ブロック数、p: ペア数 |
| group matching | O(g × m) | g: グループ数、m: 平均メンバー数 |

### メモリ最適化

1. **リビジョン単位処理**: 2リビジョンずつ読み込み
2. **データ型最適化**: int32, category型の活用
3. **明示的メモリ解放**: del + gc.collect()
4. **列選択**: 必要な列のみ読み込み（ただしtoken_sequenceは必須）

## エラーハンドリング戦略

### 1. データ検証

- リビジョンディレクトリ存在確認
- CSVファイル存在確認
- 必須列の存在確認
- データ型検証

### 2. 例外処理

```python
try:
    # 処理
except FileNotFoundError as e:
    console.print(f"[red]Error:[/red] File not found: {e}")
    sys.exit(1)
except pd.errors.EmptyDataError:
    console.print(f"[red]Error:[/red] Empty CSV file")
    sys.exit(1)
except Exception as e:
    console.print(f"[red]Unexpected error:[/red] {e}")
    import traceback
    console.print(traceback.format_exc())
    sys.exit(1)
```

### 3. 警告メッセージ

- 低いマッチング率
- 空のクローングループ
- 異常な寿命値

## ログ戦略

```python
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 使用例
logger.info(f"Processing revision pair: {rev_old.revision_id} -> {rev_new.revision_id}")
logger.debug(f"Phase 1 matched: {len(matches)}")
logger.warning(f"Low matching rate: {rate:.1%}")
```

## 出力フォーマット仕様

### method_tracking.csv

```
revision,block_id,function_name,file_path,start_line,end_line,loc,state,state_detail,matched_block_id,match_type,match_similarity,clone_count,clone_group_id,clone_group_size,lifetime_revisions,lifetime_days
```

### group_tracking.csv

```
revision,group_id,member_count,avg_similarity,min_similarity,max_similarity,density,state,matched_group_id,overlap_ratio,member_added,member_removed,lifetime_revisions,lifetime_days
```

### group_membership.csv

```
revision,group_id,block_id,function_name,is_clone
```

## 設定パラメータ

| パラメータ | デフォルト値 | 説明 |
|-----------|-------------|------|
| similarity_threshold | 70 | メソッドマッチング・グループ形成の類似度閾値 |
| overlap_threshold | 0.5 | グループマッチングの重複率閾値 |
| group_size_tolerance | 0.1 | グループサイズ変化の許容率（±10%） |

## 拡張ポイント

### 将来的な拡張

1. **並列処理**: リビジョンペア処理の並列化
2. **インクリメンタル処理**: 差分更新のサポート
3. **可視化**: サンキーダイアグラム、タイムライン
4. **機械学習**: 削除予測、パターン分類
5. **詳細メトリクス**: 複雑度、コードチャーンの統合

---

**作成日**: 2025-11-08
**バージョン**: 1.0.0
