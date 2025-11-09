# メソッド追跡分析 タスク分解

## 概要

このドキュメントでは、メソッド削除・クローングループ追跡分析の実装を段階的に進めるためのタスク分解と依存関係を定義します。

**実装方針**: テスト駆動開発（TDD）により、各タスクで「テスト作成 → 実装 → テスト通過」のサイクルを回します。

## タスク依存関係グラフ

```
Phase 1: 基礎コンポーネント ✅ 完了
├─ T1.1: UnionFind [テスト + 実装] ✅
├─ T1.2: SimilarityCalculator拡張 [テスト + 実装] ✅
└─ T1.3: RevisionManager [テスト + 実装] ✅
                ↓
Phase 2: コア分析コンポーネント ✅ 完了
├─ T2.1: MethodMatcher [テスト + 実装] (depends: T1.2) ✅
├─ T2.2: GroupDetector [テスト + 実装] (depends: T1.1) ✅
├─ T2.3: GroupMatcher [テスト + 実装] (depends: T2.2) ✅
└─ T2.4: StateClassifier [テスト + 実装] (depends: T2.1, T2.2, T2.3) ✅
                ↓
Phase 3: 統合コンポーネント ✅ 完了
├─ T3.1: MethodTracker [テスト + 実装] (depends: T1.3, T2.1, T2.2, T2.4) ✅
└─ T3.2: CloneGroupTracker [テスト + 実装] (depends: T1.3, T2.2, T2.3, T2.4) ✅
                ↓
Phase 4: CLI・統合 ⬅ 次のフェーズ
├─ T4.1: CLIコマンド [テスト + 実装] (depends: T3.1, T3.2)
├─ T4.2: 統合テスト (depends: T4.1)
└─ T4.3: ドキュメント更新 (depends: T4.2)
                ↓
Phase 5: 検証・最適化
├─ T5.1: 実データでの検証テスト
├─ T5.2: パフォーマンス最適化
└─ T5.3: エッジケース対応
```

## Phase 1: 基礎コンポーネント

### T1.1: UnionFind実装

**優先度**: 最高
**見積もり**: 2-3時間
**依存**: なし

**タスク内容**:
1. テストファイル作成: `tests/analysis/test_union_find.py`
   - [ ] 基本操作テスト（find, union）
   - [ ] 経路圧縮テスト
   - [ ] 複数グループ検出テスト
   - [ ] エッジケーステスト

2. 実装: `src/b4_thesis/analysis/union_find.py`
   - [ ] UnionFindクラス定義
   - [ ] find()メソッド（経路圧縮付き）
   - [ ] union()メソッド
   - [ ] get_groups()メソッド
   - [ ] is_connected()メソッド
   - [ ] size(), num_groups()メソッド

3. テスト実行・検証
   - [ ] `pytest tests/analysis/test_union_find.py -v`
   - [ ] すべてのテストがPASS

**成果物**:
- `src/b4_thesis/analysis/union_find.py`
- `tests/analysis/test_union_find.py`

**コミット**:
```bash
git add tests/analysis/test_union_find.py
git commit -m "test: add tests for UnionFind data structure"

git add src/b4_thesis/analysis/union_find.py
git commit -m "feat: implement UnionFind data structure

Implement Union-Find (Disjoint Set Union) with path compression
for efficient connected component detection in clone groups."
```

---

### T1.2: SimilarityCalculator拡張

**優先度**: 最高
**見積もり**: 2-3時間
**依存**: なし（既存のsimilarity.pyを拡張）

**タスク内容**:
1. テスト拡張: `tests/analysis/test_similarity.py`
   - [ ] calculate_similarity()テスト
   - [ ] 完全一致テスト
   - [ ] N-gram ≥ 70でLCSスキップテスト
   - [ ] 低類似度でLCS使用テスト
   - [ ] エッジケーステスト

2. 実装: `src/b4_thesis/analysis/similarity.py`への追加
   - [ ] calculate_similarity()関数
   - [ ] 2段階アプローチ（N-gram → LCS）
   - [ ] 異常入力処理

3. テスト実行
   - [ ] `pytest tests/analysis/test_similarity.py -v`

**成果物**:
- `src/b4_thesis/analysis/similarity.py` (更新)
- `tests/analysis/test_similarity.py` (更新)

**コミット**:
```bash
git add tests/analysis/test_similarity.py
git commit -m "test: add tests for cross-revision similarity calculation"

git add src/b4_thesis/analysis/similarity.py
git commit -m "feat: add calculate_similarity for cross-revision matching

Implement 2-phase similarity calculation (N-gram then LCS) for
matching methods across revisions with different block_ids."
```

---

### T1.3: RevisionManager実装

**優先度**: 高
**見積もり**: 3-4時間
**依存**: なし

**タスク内容**:
1. テストフィクスチャ作成
   - [ ] `tests/fixtures/sample_revisions/` ディレクトリ作成
   - [ ] サンプルリビジョンデータ（最低3つ）作成
   - [ ] README.md（フィクスチャの説明）

2. テスト作成: `tests/core/test_revision_manager.py`
   - [ ] リビジョン検出テスト
   - [ ] 時系列ソートテスト
   - [ ] 日付範囲フィルタリングテスト
   - [ ] データ読み込みテスト

3. 実装: `src/b4_thesis/core/revision_manager.py`
   - [ ] RevisionInfo dataclass
   - [ ] RevisionManager クラス
   - [ ] get_revisions()メソッド
   - [ ] load_revision_data()メソッド

4. テスト実行
   - [ ] `pytest tests/core/test_revision_manager.py -v`

**成果物**:
- `src/b4_thesis/core/revision_manager.py`
- `tests/core/test_revision_manager.py`
- `tests/fixtures/sample_revisions/`

**コミット**:
```bash
git add tests/fixtures/sample_revisions/
git commit -m "test: add sample revision test fixtures"

git add tests/core/test_revision_manager.py
git commit -m "test: add tests for RevisionManager"

git add src/b4_thesis/core/revision_manager.py
git commit -m "feat: implement RevisionManager for handling revision data

Provide sorted access to revision directories and loading of
clone_pairs and code_blocks data with date range filtering."
```

---

## Phase 2: コア分析コンポーネント

### T2.1: MethodMatcher実装

**優先度**: 最高
**見積もり**: 4-5時間
**依存**: T1.2（SimilarityCalculator）

**タスク内容**:
1. テスト作成: `tests/analysis/test_method_matcher.py`
   - [ ] Phase 1: token_hashマッチングテスト
   - [ ] Phase 2: 類似度マッチングテスト
   - [ ] 閾値未満ケーステスト
   - [ ] 複数候補から最高類似度選択テスト
   - [ ] 双方向マッチング整合性テスト

2. 実装: `src/b4_thesis/analysis/method_matcher.py`
   - [ ] MatchType enum
   - [ ] MethodMatch dataclass
   - [ ] MethodMatcher クラス
   - [ ] match_revisions()メソッド
   - [ ] _phase1_token_hash_matching()
   - [ ] _phase2_similarity_matching()
   - [ ] create_bidirectional_matches()

3. テスト実行
   - [ ] `pytest tests/analysis/test_method_matcher.py -v`

**成果物**:
- `src/b4_thesis/analysis/method_matcher.py`
- `tests/analysis/test_method_matcher.py`

**コミット**:
```bash
git add tests/analysis/test_method_matcher.py
git commit -m "test: add tests for MethodMatcher"

git add src/b4_thesis/analysis/method_matcher.py
git commit -m "feat: implement MethodMatcher for cross-revision matching

Implement 2-phase matching strategy (token_hash then similarity)
with bidirectional consistency checking."
```

---

### T2.2: GroupDetector実装

**優先度**: 最高
**見積もり**: 3-4時間
**依存**: T1.1（UnionFind）

**タスク内容**:
1. テスト作成: `tests/analysis/test_group_detector.py`
   - [ ] 単一グループ検出テスト
   - [ ] 複数グループ検出テスト
   - [ ] 孤立メソッドテスト
   - [ ] 閾値境界テスト
   - [ ] グループメトリクス計算テスト

2. 実装: `src/b4_thesis/analysis/group_detector.py`
   - [ ] CloneGroup dataclass
   - [ ] グループメトリクスプロパティ（avg_similarity, min, max, density）
   - [ ] GroupDetector クラス
   - [ ] detect_groups()メソッド
   - [ ] _get_effective_similarity()

3. テスト実行
   - [ ] `pytest tests/analysis/test_group_detector.py -v`

**成果物**:
- `src/b4_thesis/analysis/group_detector.py`
- `tests/analysis/test_group_detector.py`

**コミット**:
```bash
git add tests/analysis/test_group_detector.py
git commit -m "test: add tests for GroupDetector"

git add src/b4_thesis/analysis/group_detector.py
git commit -m "feat: implement GroupDetector for clone group detection

Use UnionFind to detect connected components of similar methods
within a single revision."
```

---

### T2.3: GroupMatcher実装

**優先度**: 高
**見積もり**: 4-5時間
**依存**: T2.2（GroupDetector）

**タスク内容**:
1. テスト作成: `tests/analysis/test_group_matcher.py`
   - [ ] 単純マッチング（1対1）テスト
   - [ ] 重複率計算テスト
   - [ ] 閾値未満ケーステスト
   - [ ] 分裂検出（1対多）テスト
   - [ ] 統合検出（多対1）テスト

2. 実装: `src/b4_thesis/analysis/group_matcher.py`
   - [ ] GroupMatch dataclass
   - [ ] GroupMatcher クラス
   - [ ] match_groups()メソッド
   - [ ] _find_group_of_block()
   - [ ] detect_splits()
   - [ ] detect_merges()

3. テスト実行
   - [ ] `pytest tests/analysis/test_group_matcher.py -v`

**成果物**:
- `src/b4_thesis/analysis/group_matcher.py`
- `tests/analysis/test_group_matcher.py`

**コミット**:
```bash
git add tests/analysis/test_group_matcher.py
git commit -m "test: add tests for GroupMatcher"

git add src/b4_thesis/analysis/group_matcher.py
git commit -m "feat: implement GroupMatcher for group evolution tracking

Match clone groups across revisions based on member overlap,
with split and merge detection."
```

---

### T2.4: StateClassifier実装

**優先度**: 高
**見積もり**: 3-4時間
**依存**: T2.1, T2.2, T2.3

**タスク内容**:
1. テスト作成: `tests/analysis/test_state_classifier.py`
   - [ ] 各メソッド状態分類テスト（9パターン）
   - [ ] 各グループ状態分類テスト（7パターン）
   - [ ] 境界ケーステスト
   - [ ] 複合条件テスト

2. 実装: `src/b4_thesis/analysis/state_classifier.py`
   - [ ] MethodState enum
   - [ ] MethodStateDetail enum
   - [ ] GroupState enum
   - [ ] StateClassifier クラス
   - [ ] classify_method_state()メソッド
   - [ ] classify_group_state()メソッド

3. テスト実行
   - [ ] `pytest tests/analysis/test_state_classifier.py -v`

**成果物**:
- `src/b4_thesis/analysis/state_classifier.py`
- `tests/analysis/test_state_classifier.py`

**コミット**:
```bash
git add tests/analysis/test_state_classifier.py
git commit -m "test: add tests for StateClassifier"

git add src/b4_thesis/analysis/state_classifier.py
git commit -m "feat: implement StateClassifier for state classification

Classify method states (deleted/survived/added with details) and
group states (continued/grown/shrunk/split/merged/dissolved/born)."
```

---

## Phase 3: 統合コンポーネント ✅ 完了（2025-11-09）

### T3.1: MethodTracker実装 ✅

**優先度**: 最高
**見積もり**: 5-6時間
**依存**: T1.3, T2.1, T2.2, T2.4
**ステータス**: ✅ 完了

**タスク内容**:
1. テスト作成: `tests/analysis/test_method_tracker.py`
   - [x] 単一リビジョンペア処理テスト
   - [x] 複数リビジョン追跡テスト
   - [x] 寿命計算テスト
   - [x] CSV出力フォーマット検証

2. 実装: `src/b4_thesis/analysis/method_tracker.py`
   - [x] MethodTrackingResult dataclass
   - [x] MethodTracker クラス
   - [x] track()メソッド
   - [x] _process_revision_pair()
   - [x] _calculate_lifetime()

3. テスト実行
   - [x] `pytest tests/analysis/test_method_tracker.py -v` - **20/20 tests passed**

**成果物**:
- `src/b4_thesis/analysis/method_tracker.py` ✅
- `tests/analysis/test_method_tracker.py` ✅

**コミット**:
```bash
git add tests/analysis/test_method_tracker.py
git commit -m "test: add tests for MethodTracker"

git add src/b4_thesis/analysis/method_tracker.py
git commit -m "feat: implement MethodTracker for method evolution tracking

Track methods across multiple revisions with state classification,
lifetime calculation, and CSV output generation."
```

---

### T3.2: CloneGroupTracker実装 ✅

**優先度**: 最高
**見積もり**: 5-6時間
**依存**: T1.3, T2.2, T2.3, T2.4
**ステータス**: ✅ 完了

**タスク内容**:
1. テスト作成: `tests/analysis/test_clone_group_tracker.py`
   - [x] グループ検出と追跡テスト
   - [x] メンバーシップ記録テスト
   - [x] グループ状態分類テスト
   - [x] 分裂・統合検出テスト
   - [x] CSV出力フォーマット検証

2. 実装: `src/b4_thesis/analysis/clone_group_tracker.py`
   - [x] GroupTrackingResult dataclass
   - [x] GroupMembershipResult dataclass
   - [x] CloneGroupTracker クラス
   - [x] track()メソッド
   - [x] _process_revision_pair()
   - [x] _calculate_member_changes()

3. テスト実行
   - [x] `pytest tests/analysis/test_clone_group_tracker.py -v` - **19/19 tests passed**

**成果物**:
- `src/b4_thesis/analysis/clone_group_tracker.py` ✅
- `tests/analysis/test_clone_group_tracker.py` ✅

**コミット**:
```bash
git add tests/analysis/test_clone_group_tracker.py
git commit -m "test: add tests for CloneGroupTracker"

git add src/b4_thesis/analysis/clone_group_tracker.py
git commit -m "feat: implement CloneGroupTracker for group evolution tracking

Track clone groups across multiple revisions with state classification,
membership tracking, and dual CSV output generation."
```

---

## Phase 4: CLI・統合

### T4.1: CLIコマンド実装

**優先度**: 高
**見積もり**: 3-4時間
**依存**: T3.1, T3.2

**タスク内容**:
1. テスト作成: `tests/commands/test_track.py`
   - [ ] track methods コマンドテスト
   - [ ] track groups コマンドテスト
   - [ ] track all コマンドテスト
   - [ ] サマリー表示テスト
   - [ ] エラーハンドリングテスト

2. 実装: `src/b4_thesis/commands/track.py`
   - [ ] track グループコマンド
   - [ ] track methods サブコマンド
   - [ ] track groups サブコマンド
   - [ ] track all サブコマンド
   - [ ] サマリー表示機能
   - [ ] エラーハンドリング

3. CLI登録: `src/b4_thesis/cli.py`への追加
   - [ ] track コマンドグループを登録

4. テスト実行
   - [ ] `pytest tests/commands/test_track.py -v`

**成果物**:
- `src/b4_thesis/commands/track.py`
- `tests/commands/test_track.py`
- `src/b4_thesis/cli.py` (更新)

**コミット**:
```bash
git add tests/commands/test_track.py
git commit -m "test: add tests for track CLI commands"

git add src/b4_thesis/commands/track.py
git commit -m "feat: implement track CLI commands

Add 'track methods', 'track groups', and 'track all' commands
with summary statistics display option."

git add src/b4_thesis/cli.py
git commit -m "feat: register track command group in CLI"
```

---

### T4.2: 統合テスト

**優先度**: 高
**見積もり**: 2-3時間
**依存**: T4.1

**タスク内容**:
1. エンドツーエンド統合テスト作成
   - [ ] `tests/integration/test_end_to_end.py`
   - [ ] 実データに近いフィクスチャで全フロー実行
   - [ ] 出力CSV検証

2. テスト実行
   - [ ] `pytest tests/integration/ -v`

3. カバレッジレポート確認
   - [ ] `pytest tests/ --cov=b4_thesis --cov-report=html`
   - [ ] カバレッジ85%以上を確認

**成果物**:
- `tests/integration/test_end_to_end.py`
- カバレッジレポート

**コミット**:
```bash
git add tests/integration/test_end_to_end.py
git commit -m "test: add end-to-end integration tests"
```

---

### T4.3: ドキュメント更新

**優先度**: 中
**見積もり**: 2-3時間
**依存**: T4.2

**タスク内容**:
1. README.md更新
   - [ ] track コマンドの使用例追加
   - [ ] 出力CSVフォーマット説明
   - [ ] 使用例・サンプルコード

2. CLAUDE.md更新
   - [ ] 新機能の説明追加
   - [ ] 今後の拡張予定更新

**成果物**:
- `README.md` (更新)
- `CLAUDE.md` (更新)

**コミット**:
```bash
git add README.md
git commit -m "docs: add track commands documentation to README"

git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with method tracking feature"
```

---

## Phase 5: 検証・最適化

### T5.1: 実データでの検証テスト

**優先度**: 中
**見積もり**: 3-4時間
**依存**: T4.2

**タスク内容**:
1. 実際のデータで動作確認
   - [ ] clone_NILディレクトリで実行
   - [ ] 結果の妥当性検証
   - [ ] エッジケース発見と対応

2. バグ修正・改善
   - [ ] 発見された問題の修正

**成果物**:
- バグ修正コミット（必要に応じて）

---

### T5.2: パフォーマンス最適化

**優先度**: 低
**見積もり**: 2-3時間
**依存**: T5.1

**タスク内容**:
1. パフォーマンス測定
   - [ ] 大規模データでの実行時間測定
   - [ ] メモリ使用量測定
   - [ ] ボトルネック特定

2. 最適化実装
   - [ ] 必要に応じてデータ型最適化
   - [ ] メモリ解放処理追加
   - [ ] 並列処理の検討（将来的）

**成果物**:
- パフォーマンス改善コミット（必要に応じて）

---

### T5.3: エッジケース対応

**優先度**: 低
**見積もり**: 2-3時間
**依存**: T5.1

**タスク内容**:
1. エッジケーステスト追加
   - [ ] 空データ
   - [ ] 単一リビジョン
   - [ ] 巨大グループ
   - [ ] 異常値処理

2. 堅牢性向上
   - [ ] エラーハンドリング強化
   - [ ] 警告メッセージ追加

**成果物**:
- エッジケース対応コミット

---

## タスク実行チェックリスト

### 各タスクの実行手順（TDDサイクル）

```
□ ステップ1: テスト作成（実装なし）
  - テストファイル作成
  - すべてのテストケース記述
  - pytest実行 → すべてFAIL（期待通り）

□ ステップ2: 最小実装
  - 最低限の実装でテストを通す
  - pytest実行 → PASS

□ ステップ3: リファクタリング
  - コード品質向上
  - ruff check --fix src/
  - ruff format src/
  - pytest実行 → 引き続きPASS

□ ステップ4: コミット
  - テストコミット
  - 実装コミット
  - 分けてコミットする（CLAUDE.mdのガイドライン）

□ ステップ5: 次のタスクへ
```

## 見積もりサマリー

| Phase | タスク数 | 合計見積もり時間 | ステータス |
|-------|----------|------------------|-----------|
| Phase 1 | 3 | 7-10時間 | ✅ 完了（56 tests） |
| Phase 2 | 4 | 14-18時間 | ✅ 完了（67 tests） |
| Phase 3 | 2 | 10-12時間 | ✅ 完了（39 tests） |
| Phase 4 | 3 | 7-10時間 | 🔜 次のフェーズ |
| Phase 5 | 3 | 7-10時間 | 📅 予定 |
| **合計** | **15** | **45-60時間** | **Phase 1-3完了（162 tests passing）** |

## マイルストーン

### マイルストーン1: 基礎完了（Phase 1完了）✅ 達成（2025-11-08）
- [x] UnionFind実装完了
- [x] SimilarityCalculator拡張完了
- [x] RevisionManager実装完了
- **期限目安**: 開始から1-2日
- **実績**: 56 tests passing

### マイルストーン2: コア分析完了（Phase 2完了）✅ 達成（2025-11-08）
- [x] すべてのコア分析コンポーネント実装完了
- [x] ユニットテスト全PASS
- **期限目安**: 開始から4-5日
- **実績**: 67 tests passing (Phase 2) / 123 tests total

### マイルストーン3: 統合完了（Phase 3完了）✅ 達成（2025-11-09）
- [x] MethodTracker, CloneGroupTracker実装完了
- [x] 統合テスト全PASS
- **期限目安**: 開始から7-8日
- **実績**: 39 tests passing (Phase 3) / 162 tests total

### マイルストーン4: CLI完成（Phase 4完了）
- [ ] CLIコマンド実装完了
- [ ] ドキュメント更新完了
- [ ] カバレッジ85%以上
- **期限目安**: 開始から9-10日

### マイルストーン5: リリース準備完了（Phase 5完了）
- [ ] 実データ検証完了
- [ ] 最適化完了
- [ ] エッジケース対応完了
- **期限目安**: 開始から12-14日

## リスク管理

### 高リスク項目

1. **Phase 2のMethodMatcher実装**
   - リスク: 類似度計算のパフォーマンス問題
   - 対策: 早めにプロファイリング実施

2. **Phase 3の統合**
   - リスク: コンポーネント間の複雑な依存関係
   - 対策: 詳細な統合テスト作成

3. **Phase 5の実データ検証**
   - リスク: 予期しないデータパターン
   - 対策: 段階的検証、エラーログ充実

### 緩和戦略

- **早期のフィードバックループ**: 各Phaseごとにレビュー
- **段階的リリース**: PhaseごとにPR作成可能
- **テスト優先**: TDDを徹底することで後戻りを防ぐ

## 進捗追跡

進捗は各タスクごとにチェックボックスで追跡し、以下のコマンドで確認：

```bash
# テスト実行状況確認
pytest tests/ -v --tb=short

# カバレッジ確認
pytest tests/ --cov=b4_thesis --cov-report=term-missing

# 完了したコミット確認
git log --oneline --graph
```

---

**作成日**: 2025-11-08
**最終更新**: 2025-11-09 (Phase 3 完了)
**バージョン**: 1.1.0
