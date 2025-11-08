# メソッド削除・クローングループ追跡分析

## 概要

このドキュメントでは、Gitリビジョン間でメソッドの削除・追加・存続を追跡し、クローングループの進化を分析するツールの設計と使用方法について説明します。

## 目的

従来のGit履歴分析では、メソッドの削除と追加を別々の操作として扱うため、「メソッドの移動」や「リファクタリング」といった実質的な変更を正確に捉えられません。本ツールは、**コードクローン類似度**を利用してリビジョン間でメソッドを追跡することで、以下を実現します：

1. **真の削除の検出**: 移動やリファクタリングではなく、本当に削除されたメソッドを特定
2. **メソッドの進化追跡**: リビジョン間での同一メソッドの変化を追跡
3. **クローングループの動態分析**: メソッド間のクローン関係の進化を可視化
4. **削除メソッドの特徴抽出**: クローン数、寿命、グループサイズなどの特徴量を計算

## アーキテクチャ

本ツールは**2層追跡アーキテクチャ**を採用しています：

```
Layer 1: メソッドレベル追跡
├── token_hashベース高速マッチング
├── 類似度ベース精密マッチング
└── メソッド状態分類（削除/存続/追加）

Layer 2: クローングループレベル追跡
├── UnionFindによる連結成分検出
├── メンバー重複ベースグループマッチング
└── グループ状態分類（継続/成長/縮小/分裂/統合/消滅/誕生）
```

## データフロー

```
入力: clone_NIL/YYYYMMDD_HHMMSS_*/
├── clone_pairs.csv (クローンペア情報)
└── code_blocks.csv (コードブロック詳細)

↓ Step 1: リビジョン選択・時系列ソート
↓ Step 2: 各リビジョンでクローングループ検出（UnionFind）
↓ Step 3: リビジョン間メソッドマッチング
↓ Step 4: メソッド状態分類・特徴抽出
↓ Step 5: クローングループマッチング
↓ Step 6: グループ状態分類・特徴抽出

出力: 3つのCSVファイル
├── method_tracking.csv (メソッド追跡結果)
├── group_tracking.csv (グループ進化結果)
└── group_membership.csv (グループメンバーシップ)
```

## アルゴリズム詳細

### 1. リビジョン間メソッドマッチング

**目的**: リビジョンN-1とリビジョンNの間で同一メソッドを特定

**課題**: `block_id`はリビジョンごとに異なるハッシュ値のため、直接比較不可

**解決策**: 2段階マッチング戦略

#### Phase 1: token_hashベース高速マッチング（O(n)）

```python
# リビジョンN-1のtoken_hashインデックス作成
token_hash_index_N_minus_1 = code_blocks_N_minus_1.set_index('token_hash')['block_id'].to_dict()

# リビジョンNの各ブロックをtoken_hashでマッチング
for block_id_N in code_blocks_N['block_id']:
    token_hash_N = code_blocks_N.loc[code_blocks_N['block_id'] == block_id_N, 'token_hash'].iloc[0]

    if token_hash_N in token_hash_index_N_minus_1:
        block_id_N_minus_1 = token_hash_index_N_minus_1[token_hash_N]
        matches_N_to_N_minus_1[block_id_N] = block_id_N_minus_1
```

**メリット**: ハッシュテーブル検索により、完全一致メソッドを高速検出（計算量：O(n)）

#### Phase 2: 類似度ベース精密マッチング（未マッチのみ）

**重要**: `clone_pairs.csv` は同一リビジョン内のペアのみ記録しているため、リビジョン間の類似度は**token_sequenceを使って動的に計算**します。

```python
from b4_thesis.analysis.similarity import calculate_similarity

# Phase 1で未マッチのブロックのみ対象
unmatched_N = [b for b in code_blocks_N['block_id'] if b not in matches_N_to_N_minus_1]
unmatched_N_minus_1 = [b for b in code_blocks_N_minus_1['block_id'] if b not in matches_N_minus_1_to_N.values()]

# リビジョン間の類似度を動的計算
for block_id_N in unmatched_N:
    candidates = []

    # リビジョンNのtoken_sequenceを取得
    token_seq_N = code_blocks_N.loc[
        code_blocks_N['block_id'] == block_id_N,
        'token_sequence'
    ].iloc[0]

    for block_id_N_minus_1 in unmatched_N_minus_1:
        # リビジョンN-1のtoken_sequenceを取得
        token_seq_N_minus_1 = code_blocks_N_minus_1.loc[
            code_blocks_N_minus_1['block_id'] == block_id_N_minus_1,
            'token_sequence'
        ].iloc[0]

        # 2つのトークンシーケンスから類似度を計算
        similarity = calculate_similarity(token_seq_N, token_seq_N_minus_1)

        if similarity >= SIMILARITY_THRESHOLD:  # 例: 70%
            candidates.append((block_id_N_minus_1, similarity))

    if candidates:
        # 最高類似度のブロックを採用
        best_match = max(candidates, key=lambda x: x[1])
        matches_N_to_N_minus_1[block_id_N] = best_match[0]
```

**calculate_similarity関数の実装**:
```python
def calculate_similarity(token_seq_1: str, token_seq_2: str) -> int:
    """
    2つのtoken_sequenceから類似度を計算

    Args:
        token_seq_1: トークンシーケンス（文字列形式: "[123;456;789]"）
        token_seq_2: トークンシーケンス（文字列形式: "[123;456;789]"）

    Returns:
        int: 類似度（0-100）
    """
    # トークンシーケンスをパース
    tokens_1 = parse_token_sequence(token_seq_1)
    tokens_2 = parse_token_sequence(token_seq_2)

    # N-gram類似度を計算
    ngram_sim = calculate_ngram_similarity(tokens_1, tokens_2)

    # N-gram類似度が70以上の場合はLCSをスキップ（計算効率化）
    if ngram_sim >= 70:
        return ngram_sim

    # N-gram類似度が70未満の場合、LCS類似度を計算
    lcs_sim = calculate_lcs_similarity(tokens_1, tokens_2)
    return lcs_sim
```

**メリット**:
- リビジョン間の類似度を正確に計算可能
- 既存の2段階アプローチ（N-gram ≥ 70ならLCSスキップ）を踏襲
- 未マッチブロックのみ計算するため、全体の計算量を削減

**デメリット**:
- `token_sequence`の読み込みが必須（メモリ消費大）
- 類似度計算アルゴリズムの実装が必要
- Phase 1に比べて計算コストが高い（O(m × k × s)、s: トークンシーケンス長）

**重要**: 複数の高類似度候補が存在する場合、**最高類似度のブロックを選択**

#### 双方向マッチング

```python
# N → N-1 方向のマッチング
matches_N_to_N_minus_1 = match_blocks(code_blocks_N, code_blocks_N_minus_1, clone_pairs)

# N-1 → N 方向のマッチング
matches_N_minus_1_to_N = match_blocks(code_blocks_N_minus_1, code_blocks_N, clone_pairs)

# 双方向の結果を統合
bidirectional_matches = integrate_matches(matches_N_to_N_minus_1, matches_N_minus_1_to_N)
```

**意義**: 双方向マッチングにより、削除・追加・存続の3状態を正確に分類可能

### 2. クローングループ検出（UnionFind）

**目的**: 各リビジョンで、類似度閾値以上で繋がったメソッドのグループ（連結成分）を検出

**アルゴリズム**: UnionFind（Disjoint Set Union）

#### UnionFind実装

```python
class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        """経路圧縮付きfind操作"""
        if x not in self.parent:
            self.parent[x] = x
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  # 経路圧縮
        return self.parent[x]

    def union(self, x, y):
        """union操作"""
        root_x = self.find(x)
        root_y = self.find(y)
        if root_x != root_y:
            self.parent[root_x] = root_y

    def get_groups(self):
        """全連結成分を辞書形式で取得"""
        groups = {}
        for node in self.parent.keys():
            root = self.find(node)
            if root not in groups:
                groups[root] = []
            groups[root].append(node)
        return groups
```

#### クローングループ構築

```python
def detect_clone_groups(code_blocks, clone_pairs, similarity_threshold=70):
    """
    指定リビジョンのクローングループを検出

    Args:
        code_blocks: リビジョンのcode_blocks DataFrame
        clone_pairs: リビジョンのclone_pairs DataFrame
        similarity_threshold: グループ形成の類似度閾値（デフォルト: 70）

    Returns:
        dict: {group_id: [block_ids]}
    """
    uf = UnionFind()

    # すべてのブロックを初期化
    for block_id in code_blocks['block_id']:
        uf.find(block_id)  # 自分自身をルートとして登録

    # 類似度閾値以上のペアを結合
    for _, row in clone_pairs.iterrows():
        block_id_1 = row['block_id_1']
        block_id_2 = row['block_id_2']

        # N-gram類似度が70以上の場合、LCSは空欄（未計算）
        # N-gram類似度が70未満の場合、LCS類似度を使用
        if row['ngram_similarity'] >= 70:
            similarity = row['ngram_similarity']
        elif pd.notna(row['lcs_similarity']):
            similarity = row['lcs_similarity']
        else:
            similarity = row['ngram_similarity']

        if similarity >= similarity_threshold:
            uf.union(block_id_1, block_id_2)

    return uf.get_groups()
```

**計算量**: O(n × α(n)) ≈ O(n)（αは逆アッカーマン関数で、実用上は定数）

**出力例**:
```python
{
    'group_1': ['block_a', 'block_b', 'block_c'],  # 3つのメソッドが相互に類似
    'group_2': ['block_d', 'block_e'],              # 2つのメソッドが類似
    'group_3': ['block_f']                          # 孤立メソッド（クローンなし）
}
```

### 3. クローングループマッチング

**目的**: リビジョンN-1とリビジョンNの間でクローングループを追跡

**アルゴリズム**: メンバー重複ベースマッチング

```python
def match_groups(groups_N_minus_1, groups_N, method_matches):
    """
    リビジョン間でクローングループをマッチング

    Args:
        groups_N_minus_1: リビジョンN-1のグループ {group_id: [block_ids]}
        groups_N: リビジョンNのグループ {group_id: [block_ids]}
        method_matches: メソッドマッチング結果 {block_id_N_minus_1: block_id_N}

    Returns:
        dict: {group_id_N_minus_1: group_id_N}
    """
    from collections import Counter

    group_matches = {}

    for group_id_old, members_old in groups_N_minus_1.items():
        new_group_candidates = Counter()

        # 旧グループの各メンバーが新リビジョンでどのグループに所属するか集計
        for block_id_old in members_old:
            if block_id_old in method_matches:
                block_id_new = method_matches[block_id_old]

                # 新リビジョンでのグループを特定
                group_id_new = find_group_of_block(block_id_new, groups_N)

                if group_id_new:
                    new_group_candidates[group_id_new] += 1

        if new_group_candidates:
            # 最も重複メンバーが多いグループを選択
            matched_group = new_group_candidates.most_common(1)[0][0]
            overlap_count = new_group_candidates[matched_group]
            overlap_ratio = overlap_count / len(members_old)

            # 閾値以上の重複があればマッチングとする
            if overlap_ratio >= 0.5:  # 50%以上のメンバーが一致
                group_matches[group_id_old] = matched_group

    return group_matches
```

**判定ロジック**:
- 旧グループの各メンバーがマッチングされた新メソッドを集計
- 新メソッドが所属する新グループをカウント
- **最多重複グループ**を継続グループとして採用
- 重複率が閾値（例: 50%）以上の場合のみマッチング成立

### 4. メソッド状態分類

各メソッドを以下の3つの主状態に分類：

#### 削除（Deleted）
- **定義**: リビジョンN-1に存在し、リビジョンNに存在しない
- **判定条件**: `block_id_N_minus_1 not in matches_N_minus_1_to_N`
- **サブタイプ**:
  - `deleted_isolated`: クローンなし（単独削除）
  - `deleted_from_group`: クローングループから削除
  - `deleted_last_member`: グループ最後のメンバーとして削除

#### 存続（Survived）
- **定義**: リビジョンN-1とリビジョンNの両方に存在
- **判定条件**: `block_id_N_minus_1 in matches_N_minus_1_to_N and block_id_N in matches_N_to_N_minus_1`
- **サブタイプ**:
  - `survived_unchanged`: token_hash完全一致
  - `survived_modified`: token_hashは異なるが類似度閾値以上
  - `survived_clone_gained`: クローン数増加
  - `survived_clone_lost`: クローン数減少

#### 追加（Added）
- **定義**: リビジョンNに新規登場
- **判定条件**: `block_id_N not in matches_N_to_N_minus_1`
- **サブタイプ**:
  - `added_isolated`: クローンなし（新規作成）
  - `added_to_group`: 既存グループに追加
  - `added_new_group`: 新グループ形成

### 5. グループ状態分類

各クローングループを以下の7つの状態に分類：

#### 継続（Continued）
- **定義**: グループがマッチングされ、メンバー数が±10%以内
- **判定条件**:
  ```python
  group_id_old in group_matches and
  0.9 * len(members_old) <= len(members_new) <= 1.1 * len(members_old)
  ```

#### 成長（Grown）
- **定義**: メンバー数が10%以上増加
- **判定条件**: `len(members_new) > 1.1 * len(members_old)`

#### 縮小（Shrunk）
- **定義**: メンバー数が10%以上減少
- **判定条件**: `len(members_new) < 0.9 * len(members_old)`

#### 分裂（Split）
- **定義**: 1つの旧グループが複数の新グループに分割
- **判定条件**: 複数の新グループが同一の旧グループに最もマッチ

#### 統合（Merged）
- **定義**: 複数の旧グループが1つの新グループに統合
- **判定条件**: 1つの新グループが複数の旧グループに最もマッチ

#### 消滅（Dissolved）
- **定義**: グループが完全に消滅（全メンバー削除）
- **判定条件**: `group_id_old not in group_matches`

#### 誕生（Born）
- **定義**: 新規グループ形成
- **判定条件**: `group_id_new not in reverse_group_matches`

## 特徴量定義

### メソッドレベル特徴量

| 特徴量 | 説明 | 計算方法 |
|--------|------|----------|
| `revision` | リビジョンタイムスタンプ | ディレクトリ名から抽出 |
| `block_id` | メソッドのブロックID | code_blocks.csvのblock_id |
| `function_name` | 関数名 | code_blocks.csvのfunction_name |
| `file_path` | ファイルパス | code_blocks.csvのfile_path |
| `start_line`, `end_line` | 行範囲 | code_blocks.csvの値 |
| `loc` | 行数 | `end_line - start_line + 1` |
| `state` | メソッド状態 | deleted/survived/added |
| `state_detail` | 状態詳細 | サブタイプ（前述） |
| `matched_block_id` | マッチング先block_id | 次/前リビジョンのblock_id |
| `match_type` | マッチングタイプ | token_hash/similarity/none |
| `match_similarity` | マッチング類似度 | 類似度値（0-100）|
| `clone_count` | クローン数 | 同グループのメンバー数 - 1 |
| `clone_group_id` | クローングループID | UnionFindのルートID |
| `clone_group_size` | グループサイズ | 同グループのメンバー数 |
| `lifetime_revisions` | 生存リビジョン数 | 累積追跡リビジョン数 |
| `lifetime_days` | 生存日数 | 最初と最後のリビジョン日時差 |

### グループレベル特徴量

| 特徴量 | 説明 | 計算方法 |
|--------|------|----------|
| `revision` | リビジョンタイムスタンプ | ディレクトリ名から抽出 |
| `group_id` | グループID | UnionFindのルートblock_id |
| `member_count` | メンバー数 | グループ内block_id数 |
| `avg_similarity` | 平均類似度 | グループ内ペアの平均類似度 |
| `min_similarity` | 最小類似度 | グループ内ペアの最小類似度 |
| `max_similarity` | 最大類似度 | グループ内ペアの最大類似度 |
| `density` | 密度 | 実際のエッジ数 / 可能なエッジ数 |
| `state` | グループ状態 | continued/grown/shrunk/split/merged/dissolved/born |
| `matched_group_id` | マッチング先group_id | 前/次リビジョンのgroup_id |
| `overlap_ratio` | 重複率 | マッチング時のメンバー重複割合 |
| `member_added` | 追加メンバー数 | 新規加入メンバー数 |
| `member_removed` | 削除メンバー数 | 離脱メンバー数 |
| `lifetime_revisions` | 生存リビジョン数 | 累積追跡リビジョン数 |
| `lifetime_days` | 生存日数 | 最初と最後のリビジョン日時差 |

## 出力CSVフォーマット

### 1. method_tracking.csv

メソッド単位の追跡結果

```csv
revision,block_id,function_name,file_path,start_line,end_line,loc,state,state_detail,matched_block_id,match_type,match_similarity,clone_count,clone_group_id,clone_group_size,lifetime_revisions,lifetime_days
20160729_092155,abc123,calculate_sum,src/math.py,10,25,16,survived,survived_unchanged,def456,token_hash,100,2,abc123,3,5,120
20160729_092155,def456,process_data,src/util.py,50,75,26,deleted,deleted_from_group,,none,,1,abc123,3,3,45
20160801_103045,ghi789,new_function,src/feature.py,100,120,21,added,added_new_group,,none,,0,ghi789,1,1,0
```

### 2. group_tracking.csv

クローングループ単位の追跡結果

```csv
revision,group_id,member_count,avg_similarity,min_similarity,max_similarity,density,state,matched_group_id,overlap_ratio,member_added,member_removed,lifetime_revisions,lifetime_days
20160729_092155,abc123,3,85.5,75,100,1.0,continued,abc123,0.67,0,1,5,120
20160729_092155,def456,5,92.3,80,100,0.8,grown,def456,0.8,2,0,3,60
20160801_103045,ghi789,1,,,,,born,,,1,0,1,0
```

### 3. group_membership.csv

各リビジョンにおけるグループメンバーシップのスナップショット

```csv
revision,group_id,block_id,function_name,is_clone
20160729_092155,abc123,abc123,calculate_sum,true
20160729_092155,abc123,def456,process_data,true
20160729_092155,abc123,jkl012,compute_total,true
20160801_103045,abc123,abc123,calculate_sum,true
20160801_103045,abc123,jkl012,compute_total,true
20160801_103045,ghi789,ghi789,new_function,false
```

**注意**: `is_clone`はグループサイズが2以上の場合に`true`

## 使用方法

### CLI コマンド

#### 1. メソッド追跡のみ実行

```bash
b4-thesis track-methods data/clone_NIL \
    --start-date 20160729 \
    --end-date 20160810 \
    --similarity-threshold 70 \
    --output method_tracking.csv
```

**オプション**:
- `--start-date`: 分析開始日（YYYYMMDD形式）
- `--end-date`: 分析終了日（YYYYMMDD形式）
- `--similarity-threshold`: 類似度閾値（デフォルト: 70）
- `--output`: 出力ファイル名

#### 2. グループ追跡のみ実行

```bash
b4-thesis track-groups data/clone_NIL \
    --start-date 20160729 \
    --end-date 20160810 \
    --similarity-threshold 70 \
    --output-tracking group_tracking.csv \
    --output-membership group_membership.csv
```

#### 3. 統合追跡（メソッド + グループ）

```bash
b4-thesis track-all data/clone_NIL \
    --start-date 20160729 \
    --end-date 20160810 \
    --similarity-threshold 70 \
    --output-dir results/tracking_analysis
```

**出力**:
- `results/tracking_analysis/method_tracking.csv`
- `results/tracking_analysis/group_tracking.csv`
- `results/tracking_analysis/group_membership.csv`

#### 4. 統計サマリー表示

```bash
b4-thesis track-all data/clone_NIL \
    --start-date 20160729 \
    --end-date 20160810 \
    --show-summary
```

**表示内容**:
```
=== Method Tracking Summary ===
Total methods tracked: 1,234
├─ Deleted: 123 (10.0%)
│  ├─ deleted_isolated: 45
│  ├─ deleted_from_group: 68
│  └─ deleted_last_member: 10
├─ Survived: 1,000 (81.0%)
│  ├─ survived_unchanged: 850
│  ├─ survived_modified: 100
│  ├─ survived_clone_gained: 30
│  └─ survived_clone_lost: 20
└─ Added: 111 (9.0%)
   ├─ added_isolated: 60
   ├─ added_to_group: 40
   └─ added_new_group: 11

=== Clone Group Summary ===
Total groups tracked: 56
├─ Continued: 30 (53.6%)
├─ Grown: 8 (14.3%)
├─ Shrunk: 5 (8.9%)
├─ Split: 2 (3.6%)
├─ Merged: 3 (5.4%)
├─ Dissolved: 4 (7.1%)
└─ Born: 4 (7.1%)

Average group size: 4.2 methods
Average group lifetime: 3.5 revisions (67 days)
```

### Python API 使用例

```python
from b4_thesis.analysis.method_tracker import MethodTracker
from b4_thesis.analysis.clone_group_tracker import CloneGroupTracker
from datetime import datetime

# メソッド追跡
tracker = MethodTracker(
    data_dir='data/clone_NIL',
    similarity_threshold=70
)

# 分析期間設定
start_date = datetime(2016, 7, 29)
end_date = datetime(2016, 8, 10)

# 追跡実行
method_results = tracker.track(start_date=start_date, end_date=end_date)

# 結果保存
method_results.to_csv('method_tracking.csv', index=False)

# グループ追跡
group_tracker = CloneGroupTracker(
    data_dir='data/clone_NIL',
    similarity_threshold=70
)

group_results, membership_results = group_tracker.track(
    start_date=start_date,
    end_date=end_date
)

# 結果保存
group_results.to_csv('group_tracking.csv', index=False)
membership_results.to_csv('group_membership.csv', index=False)
```

## 分析例

### 削除メソッドの特徴分析

```python
import pandas as pd
import matplotlib.pyplot as plt

# データ読み込み
methods = pd.read_csv('method_tracking.csv')

# 削除メソッドのみ抽出
deleted = methods[methods['state'] == 'deleted']

# クローン数による分析
print("削除メソッドのクローン数分布:")
print(deleted['clone_count'].describe())

# クローン数とLOCの関係
plt.scatter(deleted['clone_count'], deleted['loc'])
plt.xlabel('Clone Count')
plt.ylabel('Lines of Code')
plt.title('Deleted Methods: Clone Count vs LOC')
plt.show()

# 寿命による分析
print(f"平均寿命: {deleted['lifetime_days'].mean():.1f} 日")
print(f"平均生存リビジョン: {deleted['lifetime_revisions'].mean():.1f}")

# サブタイプ別集計
print("\n削除タイプ別統計:")
print(deleted['state_detail'].value_counts())
```

### クローングループ進化分析

```python
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

# データ読み込み
groups = pd.read_csv('group_tracking.csv')
membership = pd.read_csv('group_membership.csv')

# グループ状態の時系列変化
state_timeline = groups.groupby(['revision', 'state']).size().unstack(fill_value=0)

state_timeline.plot(kind='bar', stacked=True, figsize=(12, 6))
plt.xlabel('Revision')
plt.ylabel('Group Count')
plt.title('Clone Group State Evolution')
plt.legend(title='State')
plt.tight_layout()
plt.show()

# 特定グループの進化追跡
def trace_group_history(group_id):
    group_history = groups[groups['group_id'] == group_id].sort_values('revision')

    for _, row in group_history.iterrows():
        print(f"Revision: {row['revision']}")
        print(f"  Members: {row['member_count']}")
        print(f"  State: {row['state']}")
        print(f"  Avg Similarity: {row['avg_similarity']:.1f}")
        print()

# 最長寿命グループ
longest_group = groups.loc[groups['lifetime_days'].idxmax()]
print(f"最長寿命グループ: {longest_group['group_id']}")
print(f"寿命: {longest_group['lifetime_days']} 日 ({longest_group['lifetime_revisions']} リビジョン)")
```

## 性能考慮

### 計算量

- **token_hashマッチング**: O(n) - ハッシュテーブル検索
- **類似度マッチング（動的計算）**: O(m × k × s) - m: 未マッチ数、k: 候補数、s: トークンシーケンス平均長（m << n）
  - N-gram類似度計算: O(s)
  - LCS類似度計算: O(s²)（N-gram < 70の場合のみ）
- **UnionFind**: O(n × α(n)) ≈ O(n) - 実用上線形
- **グループマッチング**: O(g × m) - g: グループ数、m: 平均メンバー数

**注意**: Phase 2の類似度計算はリビジョン間で動的に行うため、token_sequenceの長さに依存します。

### メモリ最適化

**重要**: リビジョン間マッチングでは`token_sequence`を使った類似度計算が**必須**のため、メモリ最適化は限定的です。

```python
# token_sequenceは必須（リビジョン間の類似度計算に使用）
code_blocks = pd.read_csv(
    csv_path,
    names=['block_id', 'file_path', 'start_line', 'end_line',
           'function_name', 'return_type', 'parameters', 'token_hash', 'token_sequence']
)

# メモリ節約のために、不要な列のみ除外
# ただし、token_sequenceは除外できません
```

**メモリ削減のヒント**:
1. **リビジョン単位で処理**: 全リビジョンを一度に読み込まず、N-1とNの2つずつ処理
2. **チャンク処理**: pandas の `chunksize` パラメータで分割読み込み
3. **データ型最適化**: 整数列は`int32`、文字列は`category`型に変換
4. **処理後にメモリ解放**: 不要なDataFrameは`del`で削除し、`gc.collect()`を実行

### 並列処理

リビジョンごとのクローングループ検出は独立しているため、並列化可能：

```python
from concurrent.futures import ProcessPoolExecutor

def process_revision(revision_dir):
    # クローングループ検出
    groups = detect_clone_groups(...)
    return groups

with ProcessPoolExecutor(max_workers=4) as executor:
    results = executor.map(process_revision, revision_dirs)
```

## トラブルシューティング

### 問題1: マッチング率が低すぎる

**原因**: 類似度閾値が高すぎる

**解決策**: `--similarity-threshold` を下げる（例: 70 → 60）

### 問題2: グループが過剰に統合される

**原因**: グループマッチングの重複率閾値が低すぎる

**解決策**: コード内の `overlap_ratio` 閾値を上げる（例: 0.5 → 0.7）

### 問題3: メモリ不足エラー

**原因**: `token_sequence` 列が大きすぎる

**解決策**:
- `token_sequence`は必須のため除外不可
- リビジョンを2つずつ処理（全リビジョンを一度に読み込まない）
- データ型を最適化（`int32`、`category`型の使用）
- 処理後に明示的にメモリ解放（`del`、`gc.collect()`）

### 問題4: 処理時間が長すぎる

**原因**: 分析期間が広すぎる、または類似度閾値が低すぎる

**解決策**:
1. `--start-date` と `--end-date` で期間を絞る
2. 類似度閾値を上げて候補を減らす
3. 並列処理を有効化

## 今後の拡張

1. **機械学習統合**
   - 削除予測モデル（クローン数、寿命、LOCなどから予測）
   - グループ進化パターン分類

2. **可視化強化**
   - グループ進化のサンキーダイアグラム
   - メソッド追跡のタイムライン可視化

3. **インタラクティブ分析**
   - Web UIでの結果探索
   - フィルタリング・ソート機能

4. **詳細メトリクス**
   - Cyclomatic Complexity（循環的複雑度）
   - Halstead Metrics（ハルステッドメトリクス）
   - Code Churn（コード変更頻度）

## 参考文献

- UnionFind (Disjoint Set Union): [Wikipedia](https://en.wikipedia.org/wiki/Disjoint-set_data_structure)
- Clone Detection Techniques: Koschke, R. (2007). "Survey of Research on Software Clones"
- Token-based Clone Detection: Kamiya et al. (2002). "CCFinder: A Multilinguistic Token-Based Code Clone Detection System"

---

**最終更新**: 2025-11-08
**バージョン**: 1.0.0
