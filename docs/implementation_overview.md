# メソッド追跡分析 実装概要

## ドキュメント構成

このプロジェクトの実装計画は以下の4つのドキュメントで構成されています：

1. **[method_tracking_analysis.md](method_tracking_analysis.md)** - 要件定義・仕様書
2. **[implementation_design.md](implementation_design.md)** - 実装設計書
3. **[test_strategy.md](test_strategy.md)** - テスト戦略書
4. **[task_breakdown.md](task_breakdown.md)** - タスク分解と実装計画

## クイックサマリー

### 目的

Gitリビジョン間でメソッドの削除・追加・存続を追跡し、クローングループの進化を分析するツールの実装。

### 主要機能

1. **メソッドレベル追跡**
   - 2段階マッチング（token_hash → 類似度）
   - 状態分類（削除/存続/追加 × 詳細サブタイプ）
   - 寿命計算（リビジョン数・日数）

2. **クローングループレベル追跡**
   - UnionFindによるグループ検出
   - メンバー重複ベースマッチング
   - グループ進化分類（7状態）

### アーキテクチャ

```
CLI Layer (Click)
    ↓
Application Layer (MethodTracker, CloneGroupTracker)
    ↓
Core Analysis Layer (Matcher, Detector, Classifier)
    ↓
Utility Layer (UnionFind, Similarity, RevisionManager)
```

### 実装規模

- **新規ファイル数**: 15ファイル
  - 実装: 8ファイル
  - テスト: 7ファイル
- **見積もり工数**: 45-60時間
- **実装期間**: 12-14日（1日3-4時間作業想定）

### 主要コンポーネント

| コンポーネント | 責務 | 計算量 |
|---------------|------|--------|
| UnionFind | 連結成分検出 | O(n × α(n)) ≈ O(n) |
| MethodMatcher | リビジョン間メソッドマッチング | Phase1: O(n), Phase2: O(m×k×s) |
| GroupDetector | クローングループ検出 | O(n + p) |
| GroupMatcher | グループマッチング | O(g × m) |
| StateClassifier | 状態分類 | O(1) per item |

## 実装アプローチ

### テスト駆動開発（TDD）

すべてのコンポーネントで以下のサイクルを実施：

```
1. テスト作成（実装前）
   ↓
2. 最小実装（テストを通す）
   ↓
3. リファクタリング
   ↓
4. コミット（テストと実装を分けて）
```

### 段階的実装（5フェーズ）

#### Phase 1: 基礎コンポーネント (7-10時間)
- UnionFind
- SimilarityCalculator拡張
- RevisionManager

#### Phase 2: コア分析 (14-18時間)
- MethodMatcher
- GroupDetector
- GroupMatcher
- StateClassifier

#### Phase 3: 統合 (10-12時間)
- MethodTracker
- CloneGroupTracker

#### Phase 4: CLI・統合 (7-10時間)
- CLIコマンド
- 統合テスト
- ドキュメント更新

#### Phase 5: 検証・最適化 (7-10時間)
- 実データ検証
- パフォーマンス最適化
- エッジケース対応

## 重要な判定ロジック

### メソッドマッチング

**Phase 1: token_hash** (O(n))
- 完全一致の高速検出
- ハッシュテーブル使用

**Phase 2: 類似度** (O(m×k×s))
- N-gram類似度 ≥ 70 → LCSスキップ
- 複数候補から最高類似度選択
- 閾値（デフォルト: 70）以上でマッチ

### グループマッチング

- 旧グループの各メンバーがマッチした新メソッドを集計
- 新メソッドの所属グループをカウント
- **最多重複グループ**を継続先として採用
- 重複率 ≥ 50%の場合のみマッチング成立

### 状態分類

**メソッド状態**（3主状態 × 3サブタイプ = 9パターン）:
- deleted: isolated / from_group / last_member
- survived: unchanged / modified / clone_gained / clone_lost
- added: isolated / to_group / new_group

**グループ状態**（7状態）:
- continued, grown, shrunk, split, merged, dissolved, born

## テスト戦略

### テストピラミッド

- **ユニットテスト**: 70%（各関数・クラス）
- **統合テスト**: 25%（複数コンポーネント連携）
- **E2Eテスト**: 5%（実データでの全フロー）

### カバレッジ目標

- ユニットテスト: 90%以上
- 統合テスト: 80%以上
- **全体: 85%以上**

### テストデータ

`tests/fixtures/sample_revisions/` に以下のシナリオを用意：

1. 基本的なメソッド状態遷移
2. クローングループの形成と消滅
3. グループの成長
4. グループの分裂
5. グループの統合
6. 類似度マッチングのエッジケース

## 出力仕様

### method_tracking.csv
メソッド単位の追跡結果（17列）

### group_tracking.csv
グループ単位の追跡結果（14列）

### group_membership.csv
各リビジョンのグループメンバーシップ（5列）

## 依存関係

### 既存コンポーネント

- `b4_thesis.analysis.similarity` (拡張)
- Click, Rich, pandas (既存依存関係)

### 新規依存関係

なし（既存のパッケージで実装可能）

## リスク管理

### 高リスク項目

1. **Phase 2のMethodMatcher**
   - リスク: 類似度計算のパフォーマンス
   - 対策: token_sequenceの長さに依存するため、早めにプロファイリング

2. **Phase 3の統合**
   - リスク: コンポーネント間の複雑な依存関係
   - 対策: 詳細な統合テストで検証

3. **実データ検証**
   - リスク: 予期しないデータパターン
   - 対策: 段階的検証、充実したエラーログ

### 緩和戦略

- **TDD徹底**: テスト先行で後戻りを防ぐ
- **段階的レビュー**: 各Phaseごとに確認
- **早期プロファイリング**: Phase 2完了後すぐに実施

## マイルストーン

| マイルストーン | 完了条件 | 期限目安 |
|--------------|---------|----------|
| MS1: 基礎完了 | Phase 1完了 | 1-2日 |
| MS2: コア完了 | Phase 2完了、ユニットテスト全PASS | 4-5日 |
| MS3: 統合完了 | Phase 3完了、統合テスト全PASS | 7-8日 |
| MS4: CLI完成 | Phase 4完了、カバレッジ85%以上 | 9-10日 |
| MS5: リリース準備 | Phase 5完了、実データ検証完了 | 12-14日 |

## 次のステップ

### 実装開始前の準備

1. **ドキュメントレビュー**
   - [ ] implementation_design.md の確認
   - [ ] test_strategy.md の確認
   - [ ] task_breakdown.md の確認
   - [ ] 不明点・修正点の洗い出し

2. **環境準備**
   - [ ] 必要な依存関係の確認
   - [ ] テストフィクスチャディレクトリ作成
   - [ ] `.gitignore` にテストデータ除外設定追加

3. **実装開始**
   - [ ] Phase 1, Task 1.1 (UnionFind) から開始
   - [ ] TDDサイクルを厳守
   - [ ] 適切な粒度でコミット

### コミット戦略

CLAUDE.mdのガイドラインに従い、以下の粒度でコミット：

```bash
# テストコミット
git add tests/analysis/test_union_find.py
git commit -m "test: add tests for UnionFind data structure"

# 実装コミット
git add src/b4_thesis/analysis/union_find.py
git commit -m "feat: implement UnionFind data structure

Implement Union-Find (Disjoint Set Union) with path compression
for efficient connected component detection in clone groups."
```

## 参考ドキュメント

- **要件**: [method_tracking_analysis.md](method_tracking_analysis.md)
- **設計**: [implementation_design.md](implementation_design.md)
- **テスト**: [test_strategy.md](test_strategy.md)
- **タスク**: [task_breakdown.md](task_breakdown.md)
- **開発ガイド**: [../CLAUDE.md](../CLAUDE.md)

---

**作成日**: 2025-11-08
**バージョン**: 1.0.0
