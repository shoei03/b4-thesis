# B4 Thesis - Software Engineering Research Analysis Tool

ソフトウェア工学研究のためのPython CLI分析ツール

## 概要

このツールは、コードクローン検出・追跡のためのPython CLI分析ツールです。ソフトウェアリポジトリのリビジョンデータを分析し、コードクローンの進化を追跡します。

## 機能

### 実装済み（Phase 1完了）

- **コア分析モジュール**:
  - `UnionFind`: グループ検出のためのUnion-Findデータ構造
  - `SimilarityCalculator`: N-gram/LCS類似度計算（2段階アプローチ）
  - `RevisionManager`: リビジョンデータの読み込み・管理

### CLI コマンド（基本実装）

- **analyze**: リポジトリやデータファイルの分析
- **stats**: 統計メトリクスの計算
- **visualize**: データの可視化（散布図、折れ線グラフ、ヒストグラムなど）

## インストール

```bash
# 依存関係のインストール
uv sync

# 開発用依存関係も含めてインストール
uv sync --all-groups
```

## 使い方

### 基本的な使い方

```bash
# ヘルプの表示
b4-thesis --help

# データの分析
b4-thesis analyze <input_path> -o results.txt

# 統計情報の計算
b4-thesis stats data.csv -m mean -m std -m median

# 可視化の作成
b4-thesis visualize data.csv -o plot.png -t scatter --x-column x --y-column y
```

### コマンド詳細

#### analyze

データファイルやディレクトリを分析します。

```bash
b4-thesis analyze <input_path> [OPTIONS]

Options:
  -o, --output PATH        出力ファイルパス
  -f, --format [json|csv|txt]  出力フォーマット (デフォルト: txt)
  -v, --verbose           詳細な出力を表示
```

#### stats

CSVファイルから統計メトリクスを計算します。

```bash
b4-thesis stats <input_file> [OPTIONS]

Options:
  -m, --metrics [mean|median|std|min|max|count]  計算する統計メトリクス（複数指定可）
  -c, --column TEXT       分析対象の列名
```

#### visualize

データから可視化を作成します。

```bash
b4-thesis visualize <input_file> -o <output> [OPTIONS]

Options:
  -o, --output PATH       出力ファイルパス（必須）
  -t, --type [scatter|line|bar|histogram|heatmap]  グラフの種類
  --x-column TEXT         X軸の列名
  --y-column TEXT         Y軸の列名
  --title TEXT            グラフのタイトル
```

## 設定ファイル

設定ファイルを使用して、デフォルトの動作をカスタマイズできます。

以下の場所に `config.json` を配置できます：
- `~/.config/b4-thesis/config.json`
- `./b4-thesis.json`（カレントディレクトリ）

設定例：

```json
{
  "analysis": {
    "output_dir": "./output",
    "default_format": "txt",
    "verbose": false,
    "parallel_jobs": 4
  },
  "visualization": {
    "dpi": 300,
    "figure_size": [10, 6],
    "style": "whitegrid",
    "color_palette": "deep"
  }
}
```

## プロジェクト構造

```
b4-thesis/
├── src/
│   └── b4_thesis/
│       ├── __init__.py
│       ├── cli.py              # CLIエントリーポイント
│       ├── commands/           # コマンド実装
│       │   ├── __init__.py
│       │   ├── analyze.py      # analyzeコマンド
│       │   ├── stats.py        # statsコマンド
│       │   └── visualize.py    # visualizeコマンド
│       ├── core/               # コアユーティリティ
│       │   ├── __init__.py
│       │   ├── config.py       # 設定管理
│       │   └── revision_manager.py  # リビジョン管理（Phase 1）
│       └── analysis/           # 分析モジュール（Phase 1）
│           ├── __init__.py
│           ├── union_find.py   # Union-Findデータ構造
│           └── similarity.py   # 類似度計算
├── tests/                      # テストファイル（56 tests passing）
├── docs/                       # 詳細設計ドキュメント
├── pyproject.toml              # プロジェクト設定
└── README.md
```

## 開発

### テストの実行

```bash
pytest tests/
```

### コードフォーマット

```bash
ruff check src/
ruff format src/
```

## 依存ライブラリ

- **click**: CLIフレームワーク
- **rich**: ターミナル出力の装飾
- **pandas**: データ分析
- **numpy**: 数値計算
- **matplotlib/seaborn**: データ可視化
- **networkx**: グラフ分析
- **scikit-learn**: 機械学習
- **pydantic**: 設定管理

## ライセンス

研究用途のみ

## 開発ロードマップ

### ✅ Phase 1: 基盤実装（完了）

- [x] UnionFind データ構造
- [x] Similarity 計算（N-gram/LCS、2段階アプローチ）
- [x] RevisionManager（リビジョンデータ管理）
- [x] テストフレームワーク構築（56 tests passing）

### 🔄 Phase 2: コア分析コンポーネント（次フェーズ）

- [ ] MethodMatcher: メソッド間マッチング
- [ ] GroupDetector: グループ検出
- [ ] GroupMatcher: グループ間マッチング
- [ ] StateClassifier: 状態分類

### 📅 Phase 3: 追跡エンジン

- [ ] CloneEvolutionTracker: クローン進化追跡
- [ ] LifetimeCalculator: ライフタイム計算
- [ ] PatternDetector: パターン検出

### 📅 Phase 4: CLIコマンド統合

- [ ] track コマンド実装
- [ ] 統計レポート生成
- [ ] 可視化機能拡張

### 📅 Phase 5: 高度な機能

- [ ] 並列処理最適化
- [ ] 大規模データセット対応
- [ ] レポート自動生成（Markdown/PDF）
