# B4 Thesis - Software Engineering Research Analysis Tool

ソフトウェア工学研究のためのPython CLI分析ツール

## 概要

このツールは、コードクローン検出・追跡のためのPython CLI分析ツールです。ソフトウェアリポジトリのリビジョンデータを分析し、コードクローンの進化を追跡します。

## 機能

### 実装済み（Phase 1-3完了）

- **コア分析モジュール**:
  - `UnionFind`: グループ検出のためのUnion-Findデータ構造
  - `SimilarityCalculator`: N-gram/LCS類似度計算（2段階アプローチ）
  - `RevisionManager`: リビジョンデータの読み込み・管理
  - `MethodMatcher`: メソッド間マッチング（2段階アプローチ）
  - `GroupDetector`: クローングループ検出
  - `GroupMatcher`: グループ間マッチング
  - `StateClassifier`: 状態分類（メソッド・グループ）
  - `MethodTracker`: メソッド進化追跡
  - `CloneGroupTracker`: クローングループ進化追跡

### CLI コマンド

- **track**: ✅ メソッド・クローングループの進化追跡（主要機能・完全実装済み）
  - `track methods`: メソッド進化追跡
  - `track groups`: クローングループ進化追跡
  - `track all`: メソッド・グループ両方の追跡
- **convert**: ✅ データフォーマット変換（完全実装済み）
  - `convert methods`: メソッド追跡データの形式変換（lineageフォーマット対応）
- **analyze**: ⚠️ 基本実装のみ（ファイル/ディレクトリ情報表示）
- **stats**: ✅ 統計メトリクスの計算（完全実装済み）
  - `stats general`: 汎用統計計算
  - `stats methods`: メソッド追跡専用統計
  - `stats groups`: グループ追跡専用統計
- **visualize**: ✅ データの可視化（完全実装済み）
  - `visualize general`: 汎用プロット（散布図、折れ線、棒、ヒストグラム、ヒートマップ）
  - `visualize methods`: メソッド追跡専用ダッシュボード（7種類のプロット）
  - `visualize groups`: グループ追跡専用ダッシュボード（7種類のプロット）

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

# メソッド進化追跡（主要機能）
b4-thesis track methods /path/to/revision_data -o output_dir

# クローングループ進化追跡
b4-thesis track groups /path/to/revision_data -o output_dir

# メソッド・グループ両方の追跡
b4-thesis track all /path/to/revision_data -o output_dir --summary

# 追跡データのlineageフォーマット変換
b4-thesis convert methods method_tracking.csv --lineage -o method_lineage.csv

# データの分析
b4-thesis analyze <input_path> -o results.txt

# 統計情報の計算
b4-thesis stats data.csv -m mean -m std -m median

# 可視化の作成
b4-thesis visualize data.csv -o plot.png -t scatter --x-column x --y-column y
```

### コマンド詳細

#### track methods

メソッド単位の進化を追跡します。

```bash
b4-thesis track methods <DATA_DIR> [OPTIONS]

Options:
  -o, --output DIRECTORY          出力ディレクトリ（デフォルト: カレントディレクトリ）
  --start-date YYYY-MM-DD         リビジョンフィルタリングの開始日
  --end-date YYYY-MM-DD           リビジョンフィルタリングの終了日
  --similarity INTEGER            メソッドマッチングの類似度閾値 (0-100, デフォルト: 70)
  -p, --parallel                  類似度計算の並列処理を有効化（実験的機能）
  --max-workers INTEGER           並列処理のワーカープロセス数（デフォルト: CPU数）
  -s, --summary                   サマリー統計を表示
  -v, --verbose                   詳細な出力を表示

  Phase 5.3最適化オプション（大規模データセット推奨）:
  --optimize                      全Phase 5.3最適化を一括有効化（推奨）
  --use-lsh                       LSHインデックスを有効化（~100倍高速化）
  --lsh-threshold FLOAT           LSH類似度閾値 (0.0-1.0, デフォルト: 0.7)
  --lsh-num-perm INTEGER          LSH置換数 (32-256, デフォルト: 128)
  --top-k INTEGER                 候補数 (デフォルト: 20)
  --use-optimized-similarity      バンド付きLCSを使用（~2倍高速化）
  --progressive-thresholds TEXT   プログレッシブ閾値（例: "90,80,70"）
```

**DATA_DIR**: `code_blocks.csv`と`clone_pairs.csv`を含むリビジョンサブディレクトリを持つディレクトリ

**出力**:
- `method_tracking.csv`: メソッド追跡結果（状態分類含む）

**使用例**:
```bash
# 基本的な使用
b4-thesis track methods ./revision_data -o ./output

# 日付範囲を指定
b4-thesis track methods ./revision_data -o ./output --start-date 2024-01-01 --end-date 2024-12-31

# 類似度閾値を変更してサマリー表示
b4-thesis track methods ./revision_data -o ./output --similarity 80 --summary

# Phase 5.3最適化を有効化（大規模データセット推奨、20+リビジョンで50-100倍高速化）
b4-thesis track methods ./revision_data -o ./output --optimize

# カスタムプログレッシブ閾値を使用
b4-thesis track methods ./revision_data -o ./output --progressive-thresholds "95,85,75,70"

# LSHパラメータを調整
b4-thesis track methods ./revision_data -o ./output --use-lsh --lsh-num-perm 256 --top-k 30

# 並列処理を有効化（実験的機能 - 小規模データでは逆に遅くなる可能性あり）
b4-thesis track methods ./revision_data -o ./output --parallel --max-workers 4
```

**Phase 5.3最適化について**:
- `--optimize`フラグは全Phase 5.3最適化を一括有効化（LSH + バンド付きLCS + プログレッシブ閾値[90,80,70]）
- **予想高速化**: 小規模(<5リビジョン): 2-5倍、中規模(5-20リビジョン): 10-30倍、大規模(20+リビジョン): 50-100倍
- **トレードオフ**: LSHは近似マッチング（recall 90-95%）、バンド付きLCSは近似LCS（精度ロスは最小）
- **推奨**: 20+リビジョンの大規模データセットで使用。100%再現性が必要な場合は最適化なしで実行
- 詳細: [docs/PERFORMANCE.md](docs/PERFORMANCE.md)

**注意**: `--parallel`オプションは実験的機能です。小規模データセット（<10リビジョン）では、
プロセス間通信のオーバーヘッドにより逆に遅くなる場合があります。大規模データセット（20+リビジョン）
での使用を推奨します。詳細は[docs/PERFORMANCE.md](docs/PERFORMANCE.md)を参照してください。

```

#### track groups

クローングループ単位の進化を追跡します。

```bash
b4-thesis track groups <DATA_DIR> [OPTIONS]

Options:
  -o, --output DIRECTORY          出力ディレクトリ（デフォルト: カレントディレクトリ）
  --start-date YYYY-MM-DD         リビジョンフィルタリングの開始日
  --end-date YYYY-MM-DD           リビジョンフィルタリングの終了日
  --similarity INTEGER            グループ検出の類似度閾値 (0-100, デフォルト: 70)
  --overlap FLOAT                 グループマッチングの重複閾値 (0.0-1.0, デフォルト: 0.5)
  -s, --summary                   サマリー統計を表示
  -v, --verbose                   詳細な出力を表示

  Phase 5.3最適化オプション（大規模データセット推奨）:
  --optimize                      全Phase 5.3最適化を一括有効化（推奨）
  --use-lsh                       LSHインデックスを有効化（~100倍高速化）
  --lsh-threshold FLOAT           LSH類似度閾値 (0.0-1.0, デフォルト: 0.7)
  --lsh-num-perm INTEGER          LSH置換数 (32-256, デフォルト: 128)
  --top-k INTEGER                 候補数 (デフォルト: 20)
  --use-optimized-similarity      バンド付きLCSを使用（~2倍高速化）
  --progressive-thresholds TEXT   プログレッシブ閾値（例: "90,80,70"）
```

**DATA_DIR**: `code_blocks.csv`と`clone_pairs.csv`を含むリビジョンサブディレクトリを持つディレクトリ

**出力**:
- `group_tracking.csv`: グループ追跡結果（状態分類含む）
- `group_membership.csv`: 各リビジョンのグループメンバーシップスナップショット

**使用例**:
```bash
# 基本的な使用
b4-thesis track groups ./revision_data -o ./output

# カスタム閾値で実行
b4-thesis track groups ./revision_data -o ./output --similarity 75 --overlap 0.6 --verbose

# Phase 5.3最適化を有効化（大規模データセット推奨）
b4-thesis track groups ./revision_data -o ./output --optimize
```

**Phase 5.3最適化について**: track methodsと同様の最適化オプションが利用可能です。詳細は上記「track methods」セクションを参照してください。

#### track all

メソッドとクローングループ両方の進化を追跡します。

```bash
b4-thesis track all <DATA_DIR> [OPTIONS]

Options:
  -o, --output DIRECTORY      出力ディレクトリ（デフォルト: カレントディレクトリ）
  --start-date YYYY-MM-DD     リビジョンフィルタリングの開始日
  --end-date YYYY-MM-DD       リビジョンフィルタリングの終了日
  --similarity INTEGER        類似度閾値 (0-100, デフォルト: 70)
  --overlap FLOAT             グループマッチングの重複閾値 (0.0-1.0, デフォルト: 0.5)
  -s, --summary               サマリー統計を表示
  -v, --verbose               詳細な出力を表示
```

**DATA_DIR**: `code_blocks.csv`と`clone_pairs.csv`を含むリビジョンサブディレクトリを持つディレクトリ

**出力**:
- `method_tracking.csv`: メソッド追跡結果
- `group_tracking.csv`: グループ追跡結果
- `group_membership.csv`: グループメンバーシップスナップショット

**使用例**:
```bash
# すべての追跡を実行
b4-thesis track all ./revision_data -o ./output --summary

# 期間を指定して実行
b4-thesis track all ./revision_data -o ./output --start-date 2024-06-01 --end-date 2024-12-31
```

#### convert methods

✅ **完全実装済み**: メソッド追跡データを異なる形式に変換します。特に、lineageフォーマットへの変換をサポートしています。

メソッド追跡データ（`method_tracking.csv`）をlineageフォーマット（`method_lineage.csv`）に変換します。

```bash
b4-thesis convert methods <INPUT_FILE> [OPTIONS]

Options:
  --lineage / --no-lineage        Lineageフォーマットに変換（デフォルト: False）
  -o, --output PATH               出力ファイルパス
```

**使用例**:
```bash
# Step 1: 追跡データを生成
b4-thesis track methods ./data -o ./output

# Step 2: Lineageフォーマットに変換
b4-thesis convert methods ./output/method_tracking.csv --lineage -o ./output/method_lineage.csv
```

**Lineageフォーマットとは**:

Lineageフォーマットは、メソッドの進化系譜を追跡しやすくするためのフォーマットです。

| 特徴 | method_tracking.csv | method_lineage.csv |
|------|---------------------|---------------------|
| 列数 | 17列 | 16列 |
| ID | `block_id` (リビジョンごとに異なる) | `global_block_id` (リビジョン間で統一) |
| マッチング情報 | `matched_block_id` 列あり | `matched_block_id` 列なし |
| クエリの簡単さ | `matched_block_id` を辿る必要あり | `global_block_id` で直接取得可能 |

**利点**:
- **クエリが簡単**: 同じメソッドは同じ `global_block_id` を持つ
- **進化追跡が容易**: リビジョン間のマッチング関係を辿る必要なし
- **柔軟なパイプライン**: 既存の追跡データをいつでも変換可能
- **独立した処理**: 追跡とフォーマット変換が分離されている

**クエリ例**:
```sql
-- 特定メソッドの進化を追跡
SELECT * FROM method_lineage WHERE global_block_id = 'block_a';

-- 長寿命メソッドの分析
SELECT global_block_id, function_name, MAX(lifetime_days) as max_lifetime
FROM method_lineage
GROUP BY global_block_id
HAVING max_lifetime > 365;
```

#### analyze

⚠️ **注意**: このコマンドは基本実装のみです。現在はファイル/ディレクトリの基本情報（存在チェック、サイズなど）のみを表示します。

データファイルやディレクトリの基本情報を分析します。

```bash
b4-thesis analyze <input_path> [OPTIONS]

Options:
  -o, --output PATH               出力ファイルパス
  -f, --format [json|csv|txt]     出力フォーマット (デフォルト: txt)
  -v, --verbose                   詳細な出力を表示
```

**使用例**:
```bash
# ファイルの基本情報を表示
b4-thesis analyze ./data/method_tracking.csv

# ディレクトリ情報を表示
b4-thesis analyze ./revision_data --verbose
```

#### stats

✅ **完全実装済み**: CSVファイルから統計メトリクスを計算します。サブコマンドで汎用統計と専用統計を選択できます。

##### stats general

任意のCSVファイルから汎用的な統計メトリクスを計算します。

```bash
b4-thesis stats general <input_file> [OPTIONS]

Options:
  -m, --metrics [mean|median|std|min|max|count]  計算する統計メトリクス（複数指定可）
  -c, --column TEXT                              分析対象の列名
```

**使用例**:
```bash
# 基本統計（mean, std）を計算
b4-thesis stats general data.csv

# 複数のメトリクスを指定
b4-thesis stats general data.csv -m mean -m median -m std -m max

# 特定の列のみ分析
b4-thesis stats general data.csv -c lifetime_days -m mean -m median
```

##### stats methods

メソッド追跡結果（`method_tracking.csv`）の専用統計レポートを生成します。

```bash
b4-thesis stats methods <input_file> [OPTIONS]

Options:
  -o, --output PATH    詳細統計の出力ファイル（XLSX形式）
```

**表示される統計**:
- 概要: 総メソッド数、ユニークメソッド数、リビジョン数、平均メソッド数/リビジョン
- 状態分布: ADDED, SURVIVED, DELETED の分布
- クローン統計: クローン率、平均クローン数、最大クローン数
- ライフタイム統計: 平均/中央値/最大ライフタイム（日数・リビジョン数）

**使用例**:
```bash
# コンソールに統計レポートを表示
b4-thesis stats methods ./output/method_tracking.csv

# 詳細統計をExcelファイルに保存
b4-thesis stats methods ./output/method_tracking.csv -o ./stats_report.xlsx
```

##### stats groups

グループ追跡結果（`group_tracking.csv`）の専用統計レポートを生成します。

```bash
b4-thesis stats groups <input_file> [OPTIONS]

Options:
  -o, --output PATH    詳細統計の出力ファイル（XLSX形式）
```

**表示される統計**:
- 概要: 総グループ数、ユニークグループ数、リビジョン数、平均グループ数/リビジョン
- 状態分布: BORN, CONTINUED, GROWN, SHRUNK, SPLIT, MERGED, DISSOLVED の分布
- グループサイズ統計: 平均/中央値/最大/最小グループサイズ
- メンバー変更統計: 平均/最大追加数・削除数
- ライフタイム統計: 平均/中央値/最大ライフタイム（日数・リビジョン数）

**使用例**:
```bash
# コンソールに統計レポートを表示
b4-thesis stats groups ./output/group_tracking.csv

# 詳細統計をExcelファイルに保存
b4-thesis stats groups ./output/group_tracking.csv -o ./group_stats.xlsx
```

#### visualize

✅ **完全実装済み**: データから可視化（プロット）を作成します。サブコマンドで汎用プロットと専用ダッシュボードを選択できます。

##### visualize general

任意のCSVファイルから汎用的な可視化を作成します。

```bash
b4-thesis visualize general <input_file> -o <output> [OPTIONS]

Options:
  -o, --output PATH                               出力ファイルパス（必須）
  -t, --type [scatter|line|bar|histogram|heatmap] グラフの種類（デフォルト: scatter）
  --x-column TEXT                                 X軸の列名
  --y-column TEXT                                 Y軸の列名
  --title TEXT                                    グラフのタイトル
```

**サポートされるプロットタイプ**:
- `scatter`: 散布図（x-column, y-column必須）
- `line`: 折れ線グラフ（x-column, y-column必須）
- `bar`: 棒グラフ（x-column, y-column必須）
- `histogram`: ヒストグラム（x-column必須）
- `heatmap`: ヒートマップ（相関行列、数値列のみ）

**使用例**:
```bash
# 散布図を作成
b4-thesis visualize general data.csv -o scatter.png -t scatter --x-column x --y-column y

# ヒストグラムを作成
b4-thesis visualize general data.csv -o hist.png -t histogram --x-column lifetime_days

# 相関ヒートマップを作成
b4-thesis visualize general data.csv -o heatmap.png -t heatmap --title "Correlation Matrix"
```

##### visualize methods

メソッド追跡結果（`method_tracking.csv`）の専用可視化を作成します。

```bash
b4-thesis visualize methods <input_file> [OPTIONS]

Options:
  -o, --output-dir PATH                           出力ディレクトリ（デフォルト: ./plots）
  -t, --plot-type [dashboard|state|lifetime|timeline]  プロットタイプ（デフォルト: dashboard）
```

**プロットタイプ**:
- `dashboard`: 全7種類のプロットを一括生成（状態分布×2、ライフタイム分布×2、時系列×3）
- `state`: 状態分布の棒グラフ
- `lifetime`: ライフタイム分布のヒストグラム
- `timeline`: メソッド数・クローン数の時系列プロット

**使用例**:
```bash
# ダッシュボード（全プロット）を生成
b4-thesis visualize methods ./output/method_tracking.csv -o ./plots

# 状態分布のみを生成
b4-thesis visualize methods ./output/method_tracking.csv -o ./plots -t state

# カスタム出力ディレクトリを指定
b4-thesis visualize methods ./output/method_tracking.csv -o ./my_analysis/plots -t dashboard
```

##### visualize groups

グループ追跡結果（`group_tracking.csv`）の専用可視化を作成します。

```bash
b4-thesis visualize groups <input_file> [OPTIONS]

Options:
  -o, --output-dir PATH                                  出力ディレクトリ（デフォルト: ./plots）
  -t, --plot-type [dashboard|state|size|timeline|members] プロットタイプ（デフォルト: dashboard）
```

**プロットタイプ**:
- `dashboard`: 全7種類のプロットを一括生成（状態分布、サイズ分布×2、時系列×3、メンバー変更）
- `state`: 状態分布の棒グラフ
- `size`: グループサイズ分布（ヒストグラム＋箱ひげ図）
- `timeline`: グループ数・平均サイズの時系列プロット
- `members`: メンバー変更（追加・削除）の時系列プロット

**使用例**:
```bash
# ダッシュボード（全プロット）を生成
b4-thesis visualize groups ./output/group_tracking.csv -o ./plots

# グループサイズ分布のみを生成
b4-thesis visualize groups ./output/group_tracking.csv -o ./plots -t size

# メンバー変更の時系列を生成
b4-thesis visualize groups ./output/group_tracking.csv -o ./plots -t members
```

### 出力CSVフォーマット

#### method_tracking.csv

メソッド進化追跡の結果を含むCSVファイル。

| 列名 | 型 | 説明 |
|------|------|------|
| `revision` | str | リビジョン識別子 |
| `block_id` | str | ブロックID |
| `function_name` | str | 関数名 |
| `file_path` | str | ファイルパス |
| `start_line` | int | 開始行番号 |
| `end_line` | int | 終了行番号 |
| `loc` | int | コード行数 |
| `state` | str | 状態 (deleted/survived/added) |
| `state_detail` | str | 詳細状態 (deleted_isolated, survived_unchanged, added_to_group等) |
| `matched_block_id` | str/null | マッチしたブロックID（前リビジョン） |
| `match_type` | str | マッチタイプ (exact/fuzzy/none) |
| `match_similarity` | int/null | マッチ類似度 (0-100) |
| `clone_count` | int | このブロックのクローン数 |
| `clone_group_id` | str/null | 所属クローングループID |
| `clone_group_size` | int | クローングループのサイズ |
| `lifetime_revisions` | int | ライフタイム（リビジョン数） |
| `lifetime_days` | int | ライフタイム（日数） |

#### method_lineage.csv

メソッドのlineage（系譜）を追跡するためのCSVファイル。`convert methods`コマンドで`method_tracking.csv`から生成できます。

```bash
# trackingデータからlineageフォーマットに変換
b4-thesis convert methods ./output/method_tracking.csv --lineage -o ./output/method_lineage.csv
```

`method_tracking.csv`との違い：
- `block_id` → `global_block_id`: リビジョン間で統一されたID
- `matched_block_id`列を削除: lineageで自動的に紐付けられるため不要

| 列名 | 型 | 説明 |
|------|------|------|
| `global_block_id` | str | リビジョン全体で統一されたブロックID |
| `revision` | str | リビジョン識別子 |
| `function_name` | str | 関数名 |
| `file_path` | str | ファイルパス |
| `start_line` | int | 開始行番号 |
| `end_line` | int | 終了行番号 |
| `loc` | int | コード行数 |
| `state` | str | 状態 (deleted/survived/added) |
| `state_detail` | str | 詳細状態 |
| `match_type` | str | マッチタイプ (exact/fuzzy/none) |
| `match_similarity` | int/null | マッチ類似度 (0-100) |
| `clone_count` | int | このブロックのクローン数 |
| `clone_group_id` | str/null | 所属クローングループID |
| `clone_group_size` | int | クローングループのサイズ |
| `lifetime_revisions` | int | ライフタイム（リビジョン数） |
| `lifetime_days` | int | ライフタイム（日数） |

**使用例**:
```sql
-- 特定メソッドの進化を追跡
SELECT * FROM method_lineage WHERE global_block_id = 'block_a';

-- 長寿命メソッドの分析
SELECT global_block_id, function_name, lifetime_days
FROM method_lineage
GROUP BY global_block_id
HAVING MAX(lifetime_days) > 365;
```

**状態の説明**:
- `deleted`: 削除されたメソッド
  - `deleted_isolated`: 孤立メソッドとして削除
  - `deleted_from_group`: クローングループから削除
- `survived`: 存続しているメソッド
  - `survived_unchanged`: 変更なしで存続
  - `survived_modified`: 変更ありで存続
  - `survived_clone_unchanged`: クローンとして変更なしで存続
  - `survived_clone_modified`: クローンとして変更ありで存続
- `added`: 新規追加されたメソッド
  - `added_isolated`: 孤立メソッドとして追加
  - `added_to_group`: クローングループに追加

#### group_tracking.csv

クローングループ進化追跡の結果を含むCSVファイル。

| 列名 | 型 | 説明 |
|------|------|------|
| `revision` | str | リビジョン識別子 |
| `group_id` | str | グループID |
| `member_count` | int | メンバー数 |
| `avg_similarity` | float/null | 平均類似度 |
| `min_similarity` | int/null | 最小類似度 |
| `max_similarity` | int/null | 最大類似度 |
| `density` | float | グループ密度 (0.0-1.0) |
| `state` | str | 状態 (born/continued/grown/shrunk/split/merged/dissolved) |
| `matched_group_id` | str/null | マッチしたグループID（前リビジョン） |
| `overlap_ratio` | float/null | 重複率 (0.0-1.0) |
| `member_added` | int | 追加されたメンバー数 |
| `member_removed` | int | 削除されたメンバー数 |
| `lifetime_revisions` | int | ライフタイム（リビジョン数） |
| `lifetime_days` | int | ライフタイム（日数） |

**状態の説明**:
- `born`: 新規作成されたグループ
- `continued`: 変更なしで継続
- `grown`: メンバーが増加
- `shrunk`: メンバーが減少
- `split`: 複数のグループに分割
- `merged`: 他のグループと統合
- `dissolved`: 解散（すべてのメンバーが消失）

#### group_membership.csv

各リビジョンにおけるグループメンバーシップのスナップショット。

| 列名 | 型 | 説明 |
|------|------|------|
| `revision` | str | リビジョン識別子 |
| `group_id` | str | グループID |
| `block_id` | str | ブロックID |
| `function_name` | str | 関数名 |
| `is_clone` | bool | クローンかどうか |

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
│       │   ├── track.py        # trackコマンド（主要機能）
│       │   ├── convert.py      # convertコマンド
│       │   ├── analyze.py      # analyzeコマンド
│       │   ├── stats.py        # statsコマンド
│       │   └── visualize.py    # visualizeコマンド
│       ├── core/               # コアユーティリティ
│       │   ├── __init__.py
│       │   ├── config.py       # 設定管理
│       │   └── revision_manager.py  # リビジョン管理
│       └── analysis/           # 分析モジュール（Phase 1-3）
│           ├── __init__.py
│           ├── union_find.py   # Union-Findデータ構造
│           ├── similarity.py   # 類似度計算
│           ├── method_matcher.py      # メソッドマッチング
│           ├── group_detector.py      # グループ検出
│           ├── group_matcher.py       # グループマッチング
│           ├── state_classifier.py    # 状態分類
│           ├── method_tracker.py      # メソッド追跡
│           └── clone_group_tracker.py # グループ追跡
├── tests/                      # テストファイル（282 tests passing）
│   ├── analysis/               # 分析モジュールのテスト
│   ├── core/                   # コアモジュールのテスト
│   ├── commands/               # コマンドのテスト
│   ├── integration/            # 統合テスト
│   └── fixtures/               # テストフィクスチャ
├── docs/                       # 詳細設計ドキュメント
├── pyproject.toml              # プロジェクト設定
├── README.md                   # ユーザー向けドキュメント
└── CLAUDE.md                   # 開発者向けドキュメント
```

## 開発

### テストの実行

```bash
# すべてのテストを実行
uv run pytest tests/

# 詳細モードで実行
uv run pytest tests/ -v

# カバレッジレポート生成
uv run pytest tests/ --cov=b4_thesis --cov-report=html
```

### コードフォーマット

```bash
# リント + 自動修正
uv run ruff check --fix src/

# フォーマット
uv run ruff format src/

# まとめて実行
uv run ruff check --fix src/ && uv run ruff format src/ && uv run pytest tests/
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

**詳細なタスク管理と開発ロードマップは [task_breakdown.md](docs/task_breakdown.md) を参照してください。**

### 現在の状況

- **完了済み**: Phase 1-4, Phase 5.1-5.3, Phase 6
- **進行中**: Phase 5.4-5.5
- **計画中**: Phase 7

**テスト状況**: 282 tests passing (100% success rate)

**コード品質**: ruff checks passing (0 errors)
