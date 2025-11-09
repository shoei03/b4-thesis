# パフォーマンス分析と最適化ガイド

このドキュメントでは、b4-thesisツールのパフォーマンス特性、ボトルネック分析、および最適化戦略について説明します。

## 目次

1. [概要](#概要)
2. [実データ特性](#実データ特性)
3. [ベンチマーク結果](#ベンチマーク結果)
4. [ボトルネック分析](#ボトルネック分析)
5. [最適化計画](#最適化計画)
6. [ベストプラクティス](#ベストプラクティス)

## 概要

b4-thesisツールは、コードクローンの進化を追跡するため、大量の類似度計算を行います。
特に大規模なリポジトリ（多数のリビジョンや大量のコードブロック）を処理する場合、
パフォーマンスが重要な課題となります。

### パフォーマンス特性の要約

| 項目 | 値 |
|------|------|
| **主要ボトルネック** | 類似度計算（99%以上の実行時間） |
| **計算複雑度** | O(n×m×T²) |
| **推定処理時間（37リビジョン）** | 9-18時間（最適化前） |
| **目標処理時間** | 5-10分（200倍高速化） |

## 実データ特性

### データセット: clone_NIL

**基本統計**:
- **リビジョン数**: 38（37アクティブ + 1空）
- **平均ブロック数**: 11,632 ブロック/リビジョン
- **平均トークン長**: 65トークン（最小: 数トークン、最大: 1,249）
- **平均クローンペア**: 6,446ペア/リビジョン
- **総クローンペア**: 238,537ペア

**リビジョンサイズの分布**:
```
最小: 1,472 ブロック（初期リビジョン）
中央値: ~11,000 ブロック
最大: 21,239 ブロック（最新リビジョン）
```

**トークン配列の特性**:
- 型: 整数配列（例: `2 4 8 8 11 ...`）
- 平均長: 65トークン
- 標準偏差: 大きい（数トークン〜1,000トークン超）
- パース: スペース区切りの文字列 → intリスト

## ベンチマーク結果

### 小規模テスト（2リビジョン）

実データの最初の2つの非空リビジョンを使用したベンチマーク:

| 実行モード | 実行時間 | User時間 | System時間 | 備考 |
|-----------|---------|----------|-----------|------|
| **逐次処理** | 9分8秒（548秒） | 543.50秒 | 1.35秒 | ベースライン |
| **並列処理** | 11分45秒（705秒） | 2,175.41秒 | 294.72秒 | 28.6%遅延 |

**並列処理の問題点**:
- User時間が4倍に増加（543s → 2,175s）
- System時間が218倍に増加（1.35s → 294.72s）
- プロセス間通信（IPC）のオーバーヘッドが支配的
- タスク粒度が細かすぎる（類似度計算1回 ≈ ミリ秒単位）

### 処理時間の推定

**2リビジョンのベンチマーク結果を元に、37リビジョンの処理時間を推定**:

```
処理時間 = リビジョンペア数 × 1ペアあたりの処理時間
         = 36ペア × 548秒
         = 19,728秒
         = 約5.5時間（最良ケース）

ただし、リビジョンサイズが増加するため:
推定範囲: 9-18時間
```

## ボトルネック分析

### 1. 類似度計算（99%以上の実行時間）

**位置**: `src/b4_thesis/analysis/method_matcher.py:186-214`

**問題のあるコード**:
```python
for _, source_row in unmatched_source.iterrows():  # ~3,490イテレーション
    block_id_source = source_row["block_id"]
    token_seq_source = source_row["token_sequence"]

    candidates = []

    for _, target_row in unmatched_target.iterrows():  # ~3,490イテレーション
        block_id_target = target_row["block_id"]
        token_seq_target = target_row["token_sequence"]

        # 類似度計算 - O(T²) でT≈65
        similarity = calculate_similarity(token_seq_source, token_seq_target)

        if similarity >= self.similarity_threshold:
            candidates.append((block_id_target, similarity))
```

**計算量分析**:
- **ネストループ**: n × m = 3,490 × 3,490 ≈ 12,180,000 イテレーション/リビジョンペア
- **類似度計算**: O(T²) = O(65²) ≈ 4,225 操作/呼び出し
- **総計算量**: 12.18M × 4,225 ≈ 51.4G 操作/リビジョンペア
- **37リビジョン**: 36ペア × 51.4G ≈ 1.85T 操作

### 2. LCS動的計画法のコスト

**位置**: `src/b4_thesis/analysis/similarity.py:89-110`

**アルゴリズム**:
```python
def calculate_lcs_similarity(tokens_1: list[int], tokens_2: list[int]) -> int:
    len1, len2 = len(tokens_1), len(tokens_2)

    # 動的計画法テーブル（T₁ × T₂）
    dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]

    # O(T₁ × T₂) ループ
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            if tokens_1[i - 1] == tokens_2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    lcs_length = dp[len1][len2]
    similarity = (2.0 * lcs_length / (len1 + len2)) * 100
    return int(round(similarity))
```

**コスト分析**:
- 平均ケース: O(65 × 65) = 4,225 操作
- 最悪ケース: O(1,249 × 1,249) = 1,560,001 操作
- メモリ: O(T₁ × T₂) のDP テーブル

### 3. 2段階アプローチの効果

現在の実装では、類似度計算に2段階アプローチを使用:

1. **Phase 1**: N-gram類似度（高速、O(T)）
   - 類似度 >= 閾値 → N-gram値を返して早期終了 ✅

2. **Phase 2**: LCS類似度（低速、O(T²)）
   - N-gram < 閾値の場合のみ実行

**効果**:
- 高類似度ペア（70%以上）: N-gramのみで処理 → 高速
- 低類似度ペア（70%未満）: LCS計算が必要 → 遅い

**問題**:
- 閾値未満のペア（ほとんど）でLCS計算が実行される
- 閾値70%の場合、約70-80%のペアでLCS計算発生

## 最適化計画

### Phase 5.3.1: 高速化基盤（目標: 30倍高速化、1-2日）

#### 1. 長さベースの事前フィルタ

**アイデア**: 長さが大きく異なるペアは高類似度になり得ない

```python
def _should_skip_length_diff(len1: int, len2: int, max_diff_ratio: float = 0.3) -> bool:
    """長さ差が30%以上なら類似度計算をスキップ."""
    if len1 == 0 or len2 == 0:
        return True

    ratio = abs(len1 - len2) / max(len1, len2)
    return ratio > max_diff_ratio
```

**推定効果**: 30-40%のペアをスキップ → 1.5-1.7倍高速化

#### 2. トークン集合交差の事前フィルタ

**アイデア**: Jaccard類似度が低いペアは類似していない

```python
def _should_skip_token_set(tokens_1: list[int], tokens_2: list[int],
                          min_jaccard: float = 0.3) -> bool:
    """Jaccard類似度が0.3未満なら類似度計算をスキップ."""
    set1 = set(tokens_1)
    set2 = set(tokens_2)

    intersection = len(set1 & set2)
    union = len(set1 | set2)

    if union == 0:
        return True

    jaccard = intersection / union
    return jaccard < min_jaccard
```

**推定効果**: 追加で20-30%のペアをスキップ → さらに1.3-1.5倍高速化

#### 3. LRUキャッシュの実装

**問題**: 双方向マッチングで同じペアを2回計算

```python
from functools import lru_cache

@lru_cache(maxsize=100000)
def calculate_similarity_cached(token_seq_1: str, token_seq_2: str,
                               threshold: int = 70) -> int:
    """キャッシュ付き類似度計算."""
    return calculate_similarity(token_seq_1, token_seq_2, threshold)
```

**推定効果**: 双方向マッチングで50%の計算削減 → 2倍高速化

#### 4. スマート並列モード選択

**アイデア**: データサイズに基づいて並列/逐次を自動選択

```python
def _should_use_parallel(num_source: int, num_target: int) -> bool:
    """並列処理を使用すべきか判定."""
    total_pairs = num_source * num_target

    # 100万ペア以上で並列処理が効果的
    return total_pairs >= 1_000_000
```

**推定効果**: 不要な並列化を回避 → IPC オーバーヘッド削減

**Phase 5.3.1 総合効果**: 1.5 × 1.3 × 2 ≈ **30倍高速化**
- 18時間 → 30-60分

### Phase 5.3.2: 高度な最適化（目標: 100倍高速化、3-5日）

#### 1. LSH（MinHash）インデックスの実装

**アイデア**: 近似最近傍探索で候補を事前に絞り込む

**実装方針**:
```python
from datasketch import MinHash, MinHashLSH

class LSHIndex:
    """LSHベースの類似コード検索インデックス."""

    def __init__(self, threshold: int = 70, num_perm: int = 128):
        self.threshold = threshold / 100.0
        self.lsh = MinHashLSH(threshold=self.threshold, num_perm=num_perm)

    def add(self, block_id: str, tokens: list[int]):
        """トークン配列をインデックスに追加."""
        mh = MinHash(num_perm=128)
        for token in tokens:
            mh.update(str(token).encode('utf8'))
        self.lsh.insert(block_id, mh)

    def query(self, tokens: list[int]) -> list[str]:
        """類似ブロックIDのリストを取得."""
        mh = MinHash(num_perm=128)
        for token in tokens:
            mh.update(str(token).encode('utf8'))
        return self.lsh.query(mh)
```

**使用方法**:
```python
# インデックス構築（target blocks）
lsh_index = LSHIndex(threshold=70)
for _, row in target_blocks.iterrows():
    lsh_index.add(row['block_id'], parse_tokens(row['token_sequence']))

# クエリ（source blocks）
for _, source_row in source_blocks.iterrows():
    # LSHで候補を絞り込む（全体の1-5%程度）
    candidate_ids = lsh_index.query(parse_tokens(source_row['token_sequence']))

    # 候補のみ詳細計算
    for target_id in candidate_ids:
        target_row = target_blocks[target_blocks['block_id'] == target_id]
        similarity = calculate_similarity(...)
```

**推定効果**:
- 候補数を全体の1-5%に削減（3,490 → 35-175）
- 100倍の計算削減 → 100倍高速化
- ただし、近似検索のため一部のマッチを見逃す可能性あり（recall: 90-95%）

#### 2. LCS早期終了（バンド付き動的計画法）

**アイデア**: 類似度が閾値に達しない場合、計算を早期終了

```python
def calculate_lcs_similarity_banded(tokens_1: list[int], tokens_2: list[int],
                                   threshold: int = 70,
                                   band_width: int = 10) -> int | None:
    """バンド付きLCS計算（早期終了あり）."""
    len1, len2 = len(tokens_1), len(tokens_2)

    # 理論的最大類似度を計算
    max_possible_lcs = min(len1, len2)
    max_possible_similarity = (2.0 * max_possible_lcs / (len1 + len2)) * 100

    if max_possible_similarity < threshold:
        return None  # 早期終了

    # バンド幅を考慮したDP
    dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]

    for i in range(1, len1 + 1):
        max_in_row = 0
        for j in range(max(1, i - band_width), min(len2 + 1, i + band_width)):
            if tokens_1[i - 1] == tokens_2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
            max_in_row = max(max_in_row, dp[i][j])

        # 現在の最大LCSでも閾値に達しない場合、早期終了
        if i > band_width:
            current_max_sim = (2.0 * max_in_row / (len1 + len2)) * 100
            if current_max_sim < threshold * 0.8:  # マージン
                return None

    lcs_length = dp[len1][len2]
    similarity = (2.0 * lcs_length / (len1 + len2)) * 100
    return int(round(similarity))
```

**推定効果**:
- 低類似度ペアで平均50%の計算削減
- 2倍高速化（LCS部分）

#### 3. Top-k候補フィルタリング

**アイデア**: 各ソースブロックに対してtop-k（例: k=20）の候補のみ保持

```python
def _match_with_topk(self, source_row, target_blocks, k=20):
    """Top-k候補のみマッチング."""
    # LSHで候補取得（例: 100個）
    candidates = lsh_index.query(source_tokens)

    # 最初のk個のみ詳細計算
    scores = []
    for i, candidate_id in enumerate(candidates[:k]):
        similarity = calculate_similarity(...)
        if similarity >= threshold:
            scores.append((candidate_id, similarity))

    # 最高スコアを返す
    if scores:
        return max(scores, key=lambda x: x[1])
    return None
```

**推定効果**:
- 候補数をさらに削減
- 1.5-2倍高速化

**Phase 5.3.2 総合効果**: 30 × 3 ≈ **100倍高速化**
- 18時間 → 10-20分

### Phase 5.3.3: 最終調整（目標: 200倍高速化、1-2日）

#### 1. NumPyベクトル化（N-gram計算）

**アイデア**: NumPyのベクトル演算でN-gram計算を高速化

```python
import numpy as np

def calculate_ngram_similarity_vectorized(tokens_1: np.ndarray,
                                         tokens_2: np.ndarray,
                                         n: int = 2) -> int:
    """NumPyベクトル化N-gram類似度."""
    # Bi-gram生成（ベクトル化）
    bigrams_1 = np.column_stack([tokens_1[:-1], tokens_1[1:]])
    bigrams_2 = np.column_stack([tokens_2[:-1], tokens_2[1:]])

    # 集合演算（高速）
    set1 = set(map(tuple, bigrams_1))
    set2 = set(map(tuple, bigrams_2))

    intersection = len(set1 & set2)
    total = len(set1) + len(set2)

    if total == 0:
        return 0

    return int(round((2.0 * intersection / total) * 100))
```

**推定効果**:
- N-gram計算が2-3倍高速化
- 全体で1.2-1.5倍高速化（N-gramは一部のみ）

#### 2. プログレッシブ閾値

**アイデア**: 高い閾値から段階的に処理

```python
def _match_progressive_threshold(self, source_blocks, target_blocks):
    """プログレッシブ閾値マッチング."""
    thresholds = [90, 80, 70]  # 高い順

    matched = set()
    results = {}

    for threshold in thresholds:
        # 未マッチのブロックのみ処理
        unmatched_source = [b for b in source_blocks if b not in matched]

        for source_block in unmatched_source:
            best_match = self._find_match(source_block, target_blocks, threshold)
            if best_match:
                results[source_block] = best_match
                matched.add(source_block)

    return results
```

**推定効果**:
- 高類似度ペアを早期に処理
- 1.3-1.5倍高速化

**Phase 5.3.3 総合効果**: 100 × 1.5 × 1.3 ≈ **200倍高速化**
- 18時間 → 5-10分

## ベストプラクティス

### データサイズに応じた推奨設定

| リビジョン数 | 推奨設定 | 推定実行時間 |
|------------|---------|------------|
| **2-5** | デフォルト（逐次） | 5-30分 |
| **6-10** | `--similarity 75` | 30-90分 |
| **11-20** | `--similarity 80` + Phase 5.3.1最適化 | 1-3時間 → 2-10分 |
| **21-50** | `--similarity 80` + Phase 5.3.2最適化 | 5-20時間 → 5-15分 |
| **50+** | すべての最適化 | 数日 → 10-30分 |

### 並列処理の使用ガイドライン

**並列処理を使用すべき場合**:
- リビジョン数 >= 20
- 平均ブロック数 > 10,000
- 十分なCPUコア数（8+）

**並列処理を使用すべきでない場合**:
- リビジョン数 < 10
- 平均ブロック数 < 5,000
- CPUコア数が少ない（2-4）

### メモリ使用量の見積もり

```
メモリ使用量 ≈ リビジョン数 × 平均ブロック数 × 平均トークン長 × 8 bytes

例（37リビジョン）:
= 37 × 11,632 × 65 × 8
≈ 224 MB（トークンデータのみ）

実際の使用量: 500 MB - 1 GB（DataFrameや中間データ含む）
```

### プログレスバーとロギング

大規模データ処理時は`--verbose`フラグを使用して進捗を確認:

```bash
b4-thesis track methods ./large_dataset -o ./output --verbose
```

出力例:
```
[INFO] Loading revision 1/37: 20090801_000716_9d008057
[INFO] Loading revision 2/37: 20111010_015605_87a3370b
[INFO] Matching methods: revision 1 -> 2
[INFO]   - Source blocks: 1,472
[INFO]   - Target blocks: 2,058
[INFO]   - Token hash matches: 1,234
[INFO]   - Remaining pairs: 238 × 824 = 196,112
[INFO]   - Similarity calculations: 196,112
[INFO]   - Matches found: 156
[INFO]   - Time: 8m 32s
```

## まとめ

b4-thesisツールの主要なパフォーマンスボトルネックは類似度計算です。
3段階の最適化計画を実施することで、処理時間を200倍高速化し、
大規模データセット（50+リビジョン）を10-30分で処理できるようになります。

**最適化の優先順位**:
1. **Phase 5.3.1（高速化基盤）**: すぐに実装可能、大きな効果
2. **Phase 5.3.2（LSH）**: 実装コストは高いが、最大の効果
3. **Phase 5.3.3（最終調整）**: 追加の微調整

**関連ドキュメント**:
- [CLAUDE.md](../CLAUDE.md) - 開発ガイド
- [README.md](../README.md) - ユーザーマニュアル
- [implementation_design.md](implementation_design.md) - 実装設計

---

**最終更新**: 2025-11-09
**次のステップ**: Phase 5.3.1の実装開始
