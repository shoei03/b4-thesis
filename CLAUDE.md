# CLAUDE.md - Claude Code 開発ガイド

このドキュメントは、Claude Codeでこのプロジェクトを開発する際の重要な情報をまとめています。

## プロジェクト概要

**プロジェクト名**: B4 Thesis - Software Engineering Research Analysis Tool
**目的**: ソフトウェア工学研究のためのPython CLI分析ツール
**Python バージョン**: 3.10以上

## プロジェクト構造

```
b4-thesis/
├── src/b4_thesis/          # メインパッケージ
│   ├── cli.py              # CLIエントリーポイント（Clickベース）
│   ├── commands/           # 各サブコマンドの実装
│   │   ├── analyze.py      # データ/リポジトリ分析コマンド
│   │   ├── stats.py        # 統計メトリクス計算コマンド
│   │   └── visualize.py    # データ可視化コマンド
│   ├── core/               # コアユーティリティ
│   │   ├── config.py       # Pydanticベースの設定管理
│   │   └── revision_manager.py  # リビジョンデータ管理（Phase 1 ✓）
│   └── analysis/           # 分析モジュール（Phase 1-3 ✓）
│       ├── union_find.py        # Union-Findデータ構造（Phase 1 ✓）
│       ├── similarity.py        # 類似度計算（N-gram/LCS）（Phase 1 ✓）
│       ├── method_matcher.py    # メソッドマッチング（Phase 2 ✓）
│       ├── group_detector.py    # グループ検出（Phase 2 ✓）
│       ├── group_matcher.py     # グループマッチング（Phase 2 ✓）
│       ├── state_classifier.py  # 状態分類（Phase 2 ✓）
│       ├── method_tracker.py    # メソッド追跡（Phase 3 ✓）
│       └── clone_group_tracker.py  # グループ追跡（Phase 3 ✓）
├── tests/                  # テストコード（pytest使用、162 tests passing）
│   ├── analysis/           # 分析モジュールのテスト
│   ├── core/               # コアモジュールのテスト
│   └── fixtures/           # テストフィクスチャ
├── docs/                   # 詳細設計ドキュメント
├── pyproject.toml          # プロジェクト設定・依存関係
├── README.md               # ユーザー向けドキュメント
└── CLAUDE.md               # このファイル（開発者向け）
```

## 技術スタック

### コア技術
- **CLI Framework**: Click 8.1+ (コマンドライン構築)
- **出力装飾**: Rich 13.0+ (美しいターミナル出力)
- **設定管理**: Pydantic 2.12+ (型安全な設定)

### データ分析・科学計算
- **pandas**: データ分析・操作
- **numpy**: 数値計算
- **scipy**: 科学計算
- **scikit-learn**: 機械学習

### 可視化
- **matplotlib**: 基本的なプロット作成
- **seaborn**: 統計的データ可視化
- **networkx**: グラフ・ネットワーク分析

### 開発ツール
- **ruff**: リンター・フォーマッター（importソート含む）
- **pytest**: テストフレームワーク
- **uv**: パッケージマネージャー

## 開発ワークフロー

### セットアップ

```bash
# 依存関係のインストール
uv sync --all-groups

# 開発モードでインストール
uv pip install -e .
```

### 依存関係の管理（重要）

**必ず `uv add` を使用して依存関係を追加すること**

```bash
# 本番依存関係の追加
uv add <package-name>

# 開発依存関係の追加
uv add --dev <package-name>

# 特定のバージョンを指定
uv add <package-name>>=1.0.0

# 依存関係の削除
uv remove <package-name>

# 依存関係の更新
uv sync
```

**例**:
```bash
# Gitリポジトリ分析用にGitPythonを追加
uv add gitpython

# テスト用にpytest-covを開発依存関係として追加
uv add --dev pytest-cov
```

**注意**:
- `pip install` は使用しない
- `pyproject.toml` を手動で編集した後は `uv sync` を実行
- `uv add` は自動的に `pyproject.toml` と `uv.lock` を更新

### コーディング規約

1. **フォーマット**: Ruffを使用（line-length: 100）
2. **Import順序**: 自動ソート有効（標準 → サードパーティ → ファーストパーティ）
3. **文字列**: ダブルクォート使用
4. **型ヒント**: 可能な限り使用（Python 3.10+ syntax）

### コード品質チェック

**重要**: このプロジェクトでは`uv`を使用しているため、必ず`uv run`を付けてコマンドを実行すること

```bash
# リント + 自動修正（importソート含む）
uv run ruff check --fix src/

# フォーマット
uv run ruff format src/

# テスト実行
uv run pytest tests/

# 詳細モードでテスト実行
uv run pytest tests/ -v

# まとめて実行（推奨）
uv run ruff check --fix src/ && uv run ruff format src/ && uv run pytest tests/
```

**注意**:
- ❌ `ruff check src/` → エラー（command not found）
- ✅ `uv run ruff check src/` → 正しい
- ❌ `pytest tests/` → エラー（command not found）
- ✅ `uv run pytest tests/` → 正しい

### 新しいコマンドの追加方法

1. `src/b4_thesis/commands/` に新しいファイルを作成（例: `new_command.py`）
2. Clickデコレータでコマンド定義：
   ```python
   import click
   from rich.console import Console

   console = Console()

   @click.command()
   @click.argument("input_path", type=click.Path(exists=True))
   @click.option("--verbose", "-v", is_flag=True, help="Verbose output")
   def new_command(input_path: str, verbose: bool):
       """コマンドの説明."""
       console.print(f"[bold blue]Processing:[/bold blue] {input_path}")
       # 実装...
   ```
3. `src/b4_thesis/cli.py` でコマンドを登録：
   ```python
   from b4_thesis.commands import new_command

   main.add_command(new_command.new_command)
   ```

## 重要な設計方針

### 1. エラーハンドリング
- ユーザー入力エラーは明確なメッセージで表示（Rich使用）
- 例外は適切にキャッチして、ユーザーフレンドリーなエラーメッセージに変換

### 2. 出力
- プログレスバー: `tqdm` 使用
- テーブル/装飾: `rich` 使用
- データ出力: JSON/CSV/TXT形式をサポート

### 3. 設定管理
- `core/config.py` のPydanticモデルを使用
- 設定ファイルの場所:
  - `~/.config/b4-thesis/config.json`
  - `./b4-thesis.json`（プロジェクトルート）

### 4. テスト
- 各コマンドに対応するテストを `tests/` に配置
- Click の `CliRunner` を使用してCLIテスト
- カバレッジ目標: 80%以上

## よくある開発タスク

### データ分析機能の追加
1. `commands/analyze.py` または新しいコマンドファイルに実装
2. pandas/numpyで処理
3. Rich tableで結果表示

### 可視化機能の追加
1. `commands/visualize.py` に新しいプロットタイプ追加
2. matplotlib/seabornで描画
3. 設定で DPI/サイズ/スタイルをカスタマイズ可能に

### 統計メトリクスの追加
1. `commands/stats.py` に新しいメトリクス追加
2. scipy/scikit-learnの関数を活用
3. `--metrics` オプションで選択可能に

## デバッグのヒント

### CLIのデバッグ
```python
# デバッグ用の詳細出力
console.print("[dim]Debug info here[/dim]")

# 例外の詳細表示
import traceback
console.print(f"[red]Error:[/red] {traceback.format_exc()}")
```

### データ分析のデバッグ
```python
# DataFrameの確認
console.print(df.head())
console.print(df.info())
console.print(df.describe())
```

## Git ワークフロー

### コミットの粒度（重要）

**適切な粒度で頻繁にコミットすること**

#### コミットのタイミング
以下のような単位で1つのコミットを作成：

1. **機能追加の場合**
   - 新しいコマンド追加 → 1コミット
   - コマンドにオプション追加 → 1コミット
   - テスト追加 → 1コミット（または機能と同時）

2. **リファクタリングの場合**
   - ファイル1つの整理 → 1コミット
   - 関数の抽出・移動 → 1コミット
   - Import整理 → 1コミット

3. **ドキュメント更新**
   - README更新 → 1コミット
   - CLAUDE.md更新 → 1コミット
   - コメント追加・修正 → 1コミット

4. **設定変更**
   - 依存関係追加 → 1コミット
   - Ruff設定変更 → 1コミット
   - .gitignore更新 → 1コミット

#### 悪い例（粒度が大きすぎる）
```bash
# ❌ 複数の変更をまとめてコミット
git add .
git commit -m "feat: いろいろ追加"
```

#### 良い例（適切な粒度）
```bash
# ✅ 新コマンド追加
git add src/b4_thesis/commands/git_analysis.py
git commit -m "feat: add git analysis command

Add basic git repository analysis functionality"

# ✅ テスト追加
git add tests/test_git_analysis.py
git commit -m "test: add tests for git analysis command"

# ✅ 依存関係追加
git add pyproject.toml uv.lock
git commit -m "chore: add gitpython dependency"

# ✅ ドキュメント更新
git add README.md
git commit -m "docs: update README with git analysis usage"
```

### コミット前のチェックリスト
- [ ] `ruff check --fix src/` でリント
- [ ] `ruff format src/` でフォーマット
- [ ] `pytest tests/` でテスト実行（関連テストのみでも可）
- [ ] 新機能には対応するテストを追加
- [ ] コミットメッセージは明確で具体的
- [ ] 1コミット = 1つの論理的な変更

### コミットメッセージ規約
```
<type>: <subject>

<body>

Types:
- feat: 新機能
- fix: バグ修正
- docs: ドキュメント更新
- style: コードスタイル修正
- refactor: リファクタリング
- test: テスト追加・修正
- chore: ビルド・設定変更
```

### 推奨される開発フロー

```bash
# 1. 新機能開発開始
# 2. 実装
# 3. リント・フォーマット
ruff check --fix src/ && ruff format src/

# 4. テスト実行
pytest tests/

# 5. 変更内容を確認
git status
git diff

# 6. 関連ファイルのみステージング
git add src/b4_thesis/commands/new_feature.py

# 7. コミット
git commit -m "feat: add new feature

Detailed description of what this commit does"

# 8. 次の変更（テスト追加など）に移る
git add tests/test_new_feature.py
git commit -m "test: add tests for new feature"

# 9. 必要に応じてドキュメント更新
git add README.md CLAUDE.md
git commit -m "docs: update documentation for new feature"
```

### コミットのベストプラクティス

1. **小さく、頻繁にコミット**
   - 1つの変更 = 1つのコミット
   - 作業を細かく区切る

2. **意味のある単位でコミット**
   - コンパイル/テストが通る状態でコミット
   - 中途半端な状態でコミットしない

3. **明確なメッセージ**
   - 何を変更したか（What）
   - なぜ変更したか（Why）

4. **関連ファイルのみコミット**
   - `git add .` は避ける
   - ファイル単位で慎重にステージング

## 開発ロードマップ

### ✅ Phase 1: 基盤実装（完了 - 2025-11-08）

**実装完了したコンポーネント**:
- ✅ **UnionFind** (`analysis/union_find.py`): グループ検出用データ構造
  - 経路圧縮付きfind操作
  - union、get_groups、is_connected等のAPI
  - 13テストケース全てパス

- ✅ **SimilarityCalculator** (`analysis/similarity.py`): 類似度計算
  - N-gram類似度計算
  - LCS類似度計算
  - 2段階アプローチ（N-gram >= threshold → N-gram返却、それ以外 → LCS計算）
  - 27テストケース全てパス

- ✅ **RevisionManager** (`core/revision_manager.py`): リビジョンデータ管理
  - リビジョンディレクトリ列挙・ソート
  - 日付範囲フィルタリング
  - code_blocks.csv/clone_pairs.csv読み込み
  - ヘッダーなしCSV対応、空ファイル処理
  - 11テストケース全てパス

**テスト状況**: 56 tests passing（100% success rate）

**設計変更点**:
- CSVファイルをヘッダーなしで読み込む仕様に変更（`header=None`）
- 空の`clone_pairs.csv`を適切に処理する実装を追加

### ✅ Phase 2: コア分析コンポーネント（完了 - 2025-11-08）

**実装完了したコンポーネント**:
- ✅ **MethodMatcher** (`analysis/method_matcher.py`)
  - メソッド間のマッチング（2段階アプローチ）
  - Phase 1: token_hash による高速完全一致 (O(n))
  - Phase 2: 類似度ベースのファジーマッチング (O(m × k × s))
  - 二重マッチング防止、最高類似度マッチ選択
  - 12テストケース全てパス

- ✅ **GroupDetector** (`analysis/group_detector.py`)
  - クローングループの検出
  - UnionFindを活用した効率的なグループ形成
  - CloneGroupデータクラス（avg_similarity, min_similarity, max_similarity, density等）
  - 閾値ベースのグループ形成、isolated blocks処理
  - 20テストケース全てパス

- ✅ **GroupMatcher** (`analysis/group_matcher.py`)
  - リビジョン間のグループマッチング
  - オーバーラップベースのマッチング判定
  - Split/Merge検出機能
  - 閾値ベースのマッチング（デフォルト50%）
  - 14テストケース全てパス

- ✅ **StateClassifier** (`analysis/state_classifier.py`)
  - メソッド状態分類（DELETED, SURVIVED, ADDED）
  - 詳細状態（DELETED_ISOLATED, SURVIVED_UNCHANGED, ADDED_TO_GROUP等）
  - グループ状態分類（CONTINUED, GROWN, SHRUNK, SPLIT, MERGED, DISSOLVED, BORN）
  - サイズ許容範囲による柔軟な分類（デフォルト10%）
  - 21テストケース全てパス

**テスト状況**: 123 tests passing（100% success rate）
- Phase 1: 56 tests
- Phase 2: 67 tests

**設計の特徴**:
- 2段階マッチング戦略による高速化（token_hash + 類似度）
- 包括的な状態分類（メソッド3状態 × 詳細10状態、グループ7状態）
- Split/Merge検出による複雑な進化パターンの追跡
- 全コンポーネントで堅牢なエラーハンドリングとエッジケース処理

**依存関係**:
```
Phase 1 (完了) ✓
    ↓
MethodMatcher ← SimilarityCalculator ✓
GroupDetector ← UnionFind ✓
    ↓
GroupMatcher ← MethodMatcher ✓
    ↓
StateClassifier ← MethodMatcher + GroupMatcher ✓
    ↓
MethodTracker ← MethodMatcher + GroupDetector + StateClassifier ✓
CloneGroupTracker ← GroupDetector + GroupMatcher + MethodMatcher + StateClassifier ✓
```

### ✅ Phase 3: 追跡エンジン（完了 - 2025-11-09）

**実装完了したコンポーネント**:
- ✅ **MethodTracker** (`analysis/method_tracker.py`)
  - メソッド単位の進化追跡（複数リビジョン対応）
  - MethodTrackingResult データクラス（17フィールド）
  - ライフタイム計算（リビジョン数・日数）
  - 状態分類統合（StateClassifier使用）
  - 20テストケース全てパス

- ✅ **CloneGroupTracker** (`analysis/clone_group_tracker.py`)
  - クローングループ単位の進化追跡
  - GroupTrackingResult データクラス（14フィールド）
  - GroupMembershipResult データクラス（5フィールド）
  - メンバー変更計算（追加・削除カウント）
  - 2つのDataFrame出力（グループ追跡 + メンバーシップ）
  - 19テストケース全てパス

**テスト状況**: 162 tests passing（100% success rate）
- Phase 1: 56 tests
- Phase 2: 67 tests
- Phase 3: 39 tests

**主要機能**:
- 複数リビジョンにわたるメソッド・グループ追跡
- ライフタイム計算（初出〜最終出現の日数・リビジョン数）
- メンバー変更追跡（グループへの追加・削除）
- CSV出力対応（method_tracking.csv, group_tracking.csv, group_membership.csv）

### ✅ Phase 4: CLIコマンド統合（完了 - 2025-11-09）

**実装完了したコンポーネント**:
- ✅ **track コマンド** (`commands/track.py`)
  - `track methods`: メソッド進化追跡
  - `track groups`: クローングループ進化追跡
  - `track all`: メソッド・グループ両方の追跡
  - 日付範囲フィルタリング、類似度閾値、重複閾値のカスタマイズ対応
  - サマリー統計表示機能
  - 19テストケース全てパス

- ✅ **stats コマンド拡張** (`commands/stats.py`)
  - `stats general`: 一般的な統計（既存機能）
  - `stats methods`: メソッド追跡結果の統計レポート
  - `stats groups`: グループ追跡結果の統計レポート
  - 詳細統計のExcel出力機能
  - 11テストケース全てパス

- ✅ **visualize コマンド拡張** (`commands/visualize.py`)
  - `visualize general`: 一般的な可視化（既存機能）
  - `visualize methods`: メソッド追跡結果の可視化（dashboard/state/lifetime/timeline）
  - `visualize groups`: グループ追跡結果の可視化（dashboard/state/size/timeline/members）
  - 12テストケース全てパス

- ✅ **tracking_stats モジュール** (`analysis/tracking_stats.py`)
  - メソッド追跡統計計算（MethodTrackingStats）
  - グループ追跡統計計算（GroupTrackingStats）
  - 状態分布、ライフタイム分布、時系列統計
  - 23テストケース全てパス

- ✅ **tracking_visualizer モジュール** (`analysis/tracking_visualizer.py`)
  - 状態分布プロット（バー/円グラフ）
  - ライフタイム分布ヒストグラム
  - 時系列プロット（メソッド数/グループ数/平均サイズ）
  - グループサイズ分布（ヒストグラム/箱ひげ図）
  - メンバー変更の時系列（積み上げバー）
  - ダッシュボード生成機能（methods: 7プロット、groups: 7プロット）

- ✅ **統合テスト** (`tests/integration/test_end_to_end.py`)
  - エンドツーエンド統合テスト（10テストケース）
  - 出力CSV検証（構造・内容・データ整合性）
  - データ整合性チェック（メソッド追跡 ↔ グループメンバーシップ）
  - 全テストパス

- ✅ **ドキュメント更新**
  - README.md: trackコマンド使用例、出力CSVフォーマット説明
  - CLAUDE.md: Phase 4完了状況の更新

**テスト状況**: 237 tests passing（100% success rate）
- Phase 1: 56 tests
- Phase 2: 67 tests
- Phase 3: 39 tests
- Phase 4: 75 tests (19 track CLI + 11 stats CLI + 12 visualize CLI + 23 tracking_stats + 10 integration)

**コード品質**: ruff チェック全てパス（0エラー）

**成果物**:
- `track methods` → `method_tracking.csv`（17列）
- `track groups` → `group_tracking.csv`（14列）, `group_membership.csv`（5列）
- `track all` → 上記3ファイル
- `stats methods/groups` → 詳細統計レポート（コンソール表示 + Excel出力）
- `visualize methods/groups` → 可視化ダッシュボード（7プロット/タイプ）

**主要機能**:
- 包括的な統計レポート生成（ライフタイム、状態分布、クローン統計）
- 多様な可視化オプション（状態分布、時系列、サイズ分布）
- Excel形式での詳細統計エクスポート
- PNG形式での高品質プロット出力（300 DPI）

### 📅 Phase 5: 高度な機能（計画中）

- [ ] 実データでの検証テスト
- [ ] 並列処理最適化
- [ ] 大規模データセット対応
- [ ] レポート自動生成（Markdown/PDF）

## 参考リンク

- [Click Documentation](https://click.palletsprojects.com/)
- [Rich Documentation](https://rich.readthedocs.io/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [pandas Documentation](https://pandas.pydata.org/docs/)

## トラブルシューティング

### よくある問題

**問題**: `ModuleNotFoundError: No module named 'b4_thesis'`
```bash
# 解決策: 開発モードで再インストール
uv pip install -e .
```

**問題**: Importの順序が正しくない
```bash
# 解決策: Ruffで自動修正
ruff check --fix src/
```

**問題**: テストが失敗する
```bash
# 解決策: 詳細モードで実行
pytest tests/ -v
```

## メモ・注意事項

- **文字コード**: すべてのファイルはUTF-8で保存
- **改行コード**: LF（Unix形式）を使用
- **データファイル**: Git管理外（.gitignoreに含まれる）
- **出力ファイル**: `output/`, `results/`, `plots/` ディレクトリを使用（Git管理外）

---

**最終更新**: 2025-11-09 (Phase 4 完了 - 統計・可視化機能実装)
**メンテナー**: Claude Code開発チーム
