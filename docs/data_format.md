# データフォーマット仕様書

## 概要

このドキュメントでは、`data/clone_NIL`ディレクトリに格納されているCSVファイルのフォーマットと使用方法について説明します。

## ディレクトリ構造

```
data/clone_NIL/
├── YYYYMMDD_HHMMSS_<hash>/
│   ├── clone_pairs.csv          # クローンペア情報
│   └── code_blocks.csv          # コードブロック情報
```

各サブディレクトリは、分析実行のタイムスタンプとハッシュ値で命名されています。

## CSVファイル詳細

### 1. clone_pairs.csv

クローンコードのペア情報を格納したファイル。

#### カラム構成（4列）

| カラム番号 | カラム名 | 型 | 説明 |
|-----------|---------|-----|------|
| 1 | block_id_1 | string | 1つ目のコードブロックのMD5ハッシュID |
| 2 | block_id_2 | string | 2つ目のコードブロックのMD5ハッシュID |
| 3 | ngram_similarity | integer | N-gram類似度（パーセンテージ、0-100） |
| 4 | lcs_similarity | integer/empty | LCS（最長共通部分列）類似度。N-gram類似度が70以上の場合は計算をスキップして空欄 |

#### サンプルデータ

```csv
f84fbf5daf30057f489a5391b7bb8898,f84fbf5daf30057f489a5391b7bb8898,100,
92d5aa1e5aaf986fbe7ec2e701448032,7ba97139efffd6926bbbba6cc02c09eb,75,
8e7e2b36d01118cfd960fc06aef93840,f41991b1c62d04564cc9f42720e84c4b,18,76
```

**データの読み方:**
- 1行目: N-gram類似度が100%（完全一致）のため、LCSは未計算（空欄）
- 2行目: N-gram類似度が75%（70以上）のため、LCSは未計算（空欄）
- 3行目: N-gram類似度が18%（70未満）のため、LCS類似度を計算して76%

#### 使用例

```python
import pandas as pd

# クローンペアの読み込み
clone_pairs = pd.read_csv(
    'data/clone_NIL/20160729_092155_aa88215a/clone_pairs.csv',
    names=['block_id_1', 'block_id_2', 'ngram_similarity', 'lcs_similarity']
)

# N-gram類似度が高いペアを抽出（80%以上）
high_ngram = clone_pairs[clone_pairs['ngram_similarity'] >= 80]
print(f"高N-gram類似度クローンペア数: {len(high_ngram)}")

# N-gram類似度が70以上（LCS未計算）のペアをクローンと判定
auto_clones = clone_pairs[clone_pairs['ngram_similarity'] >= 70]
print(f"自動判定クローン数: {len(auto_clones)}")

# N-gram類似度が70未満で、LCS類似度が高いペアを抽出
clone_pairs['lcs_similarity'] = pd.to_numeric(clone_pairs['lcs_similarity'], errors='coerce')
lcs_clones = clone_pairs[
    (clone_pairs['ngram_similarity'] < 70) &
    (clone_pairs['lcs_similarity'] >= 70)
]
print(f"LCS判定クローン数: {len(lcs_clones)}")

# 完全一致のペアを抽出
exact_clones = clone_pairs[clone_pairs['ngram_similarity'] == 100]
```

### 2. code_blocks.csv

各コードブロックの詳細情報を格納したファイル。

#### カラム構成（9列）

| カラム番号 | カラム名 | 型 | 説明 |
|-----------|---------|-----|------|
| 1 | block_id | string | コードブロックのMD5ハッシュID |
| 2 | file_path | string | ファイルパス |
| 3 | start_line | integer | 開始行番号 |
| 4 | end_line | integer | 終了行番号 |
| 5 | function_name | string | 関数名 |
| 6 | return_type | string | 関数の戻り値の型（存在しない場合は"None"） |
| 7 | parameters | string | パラメータリスト（配列形式の文字列） |
| 8 | token_hash | string | N-gramトークンシーケンスのハッシュ値（短縮版） |
| 9 | token_sequence | string | トークンシーケンス（数値配列） |

#### サンプルデータ

```csv
3f6f11d0ca6aa1b8c6149ef9880ed351,/app/Repos/pandas/bench/test.py,14,31,groupby1,None,[lat:Any;lon:Any;data:Any],aa88215a,[99333;506364891;...]
```

**データの読み方:**
- 関数名: `groupby1`
- 戻り値の型: `None`（型情報なし）
- パラメータ: `lat`, `lon`, `data`（すべて`Any`型）
- トークンハッシュ: `aa88215a`（N-gramトークンシーケンスの識別子）
- トークンシーケンス: 数値配列（抽象構文木をトークン化したもの）

#### 使用例

```python
import pandas as pd
import ast

# コードブロックの読み込み
code_blocks = pd.read_csv(
    'data/clone_NIL/20160729_092155_aa88215a/code_blocks.csv',
    names=['block_id', 'file_path', 'start_line', 'end_line',
           'function_name', 'return_type', 'parameters', 'token_hash', 'token_sequence']
)

# 関数の行数を計算
code_blocks['loc'] = code_blocks['end_line'] - code_blocks['start_line'] + 1

# 平均関数サイズ
print(f"平均関数サイズ: {code_blocks['loc'].mean():.2f} 行")

# 最大の関数を特定
largest_function = code_blocks.loc[code_blocks['loc'].idxmax()]
print(f"最大関数: {largest_function['function_name']} ({largest_function['loc']} 行)")

# パラメータ数による分析（パースが必要）
def count_params(param_str):
    if param_str == '[]':
        return 0
    return len(param_str.strip('[]').split(';'))

code_blocks['param_count'] = code_blocks['parameters'].apply(count_params)

# 戻り値の型による分析
type_annotated = code_blocks[code_blocks['return_type'] != 'None']
print(f"型アノテーション付き関数: {len(type_annotated)} / {len(code_blocks)} ({len(type_annotated)/len(code_blocks)*100:.1f}%)")

# トークンハッシュでグループ化（同一のトークンシーケンスを持つコードブロックを検出）
duplicate_tokens = code_blocks.groupby('token_hash').size()
duplicates = duplicate_tokens[duplicate_tokens > 1]
print(f"重複トークンハッシュ数: {len(duplicates)}")
```

## 統計情報

### データセット概要

- **総ディレクトリ数**: 37個
- **総CSVファイル数**: 74個
  - clone_pairs.csv: 37個
  - code_blocks.csv: 37個

### データサイズ

各ディレクトリのサイズは分析対象のリポジトリとコミットによって異なります。

## データの使用方法

### 基本的なワークフロー

1. **クローンペアの分析**
   ```python
   # 複数のディレクトリからクローンペアを集約
   import glob
   import pandas as pd

   all_pairs = []
   for csv_file in glob.glob('data/clone_NIL/*/clone_pairs.csv'):
       df = pd.read_csv(csv_file, names=['block_id_1', 'block_id_2', 'ngram_similarity', 'lcs_similarity'])
       all_pairs.append(df)

   combined_pairs = pd.concat(all_pairs, ignore_index=True)
   ```

2. **コードブロック情報との結合**
   ```python
   # クローンペアとコードブロック情報を結合
   code_blocks = pd.read_csv(
       'data/clone_NIL/20160729_092155_aa88215a/code_blocks.csv',
       names=['block_id', 'file_path', 'start_line', 'end_line',
              'function_name', 'return_type', 'parameters', 'token_hash', 'token_sequence']
   )

   clone_pairs = pd.read_csv(
       'data/clone_NIL/20160729_092155_aa88215a/clone_pairs.csv',
       names=['block_id_1', 'block_id_2', 'ngram_similarity', 'lcs_similarity']
   )

   # 1つ目のブロックの情報を付加
   merged = clone_pairs.merge(
       code_blocks,
       left_on='block_id_1',
       right_on='block_id',
       suffixes=('', '_1')
   )

   # 2つ目のブロックの情報を付加
   merged = merged.merge(
       code_blocks,
       left_on='block_id_2',
       right_on='block_id',
       suffixes=('_1', '_2')
   )

   # クローンペアの関数名を確認
   print(merged[['function_name_1', 'function_name_2', 'ngram_similarity']].head())
   ```

3. **時系列分析**
   ```python
   import os
   import pandas as pd
   from datetime import datetime

   results = []
   for dirname in os.listdir('data/clone_NIL'):
       # ディレクトリ名からタイムスタンプを抽出
       timestamp_str = dirname.split('_')[0] + dirname.split('_')[1]
       timestamp = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')

       # クローンペア数をカウント
       csv_path = f'data/clone_NIL/{dirname}/clone_pairs.csv'
       if os.path.exists(csv_path):
           pairs = pd.read_csv(csv_path, names=['block_id_1', 'block_id_2', 'ngram_similarity', 'lcs_similarity'])
           results.append({
               'timestamp': timestamp,
               'clone_pair_count': len(pairs),
               'avg_ngram_similarity': pairs['ngram_similarity'].mean()
           })

   timeline_df = pd.DataFrame(results).sort_values('timestamp')
   ```

## 注意事項

1. **ヘッダー行なし**: すべてのCSVファイルにはヘッダー行がありません。pandas読み込み時は`names`パラメータを使用してください。

2. **クローン判定アルゴリズム**:
   - N-gram類似度が**70以上**の場合、無条件でクローンと判定し、LCS計算をスキップ（計算効率化）
   - N-gram類似度が**70未満**の場合、LCS類似度を計算して精密に判定
   - この2段階アプローチにより、計算コストを削減しながら高精度なクローン検出を実現

3. **token_sequenceの扱い**: トークンシーケンスは大きな配列で、メモリ使用量が多くなる可能性があります。必要ない場合は読み込み時に除外してください。
   ```python
   code_blocks = pd.read_csv(
       csv_path,
       names=['block_id', 'file_path', 'start_line', 'end_line',
              'function_name', 'return_type', 'parameters', 'token_hash', 'token_sequence'],
       usecols=[0, 1, 2, 3, 4, 5, 6, 7]  # token_sequenceを除外
   )
   ```

   **token_hashとtoken_sequenceの関係**:
   - `token_hash`: N-gramトークンシーケンスのハッシュ値（軽量な識別子）
   - `token_sequence`: 実際のトークン配列（詳細だが重い）
   - クローン検出では`token_hash`を使用して効率的に比較
   - 詳細分析が必要な場合のみ`token_sequence`を使用

4. **文字コード**: UTF-8エンコーディングを使用しています。

5. **NULL値の表現**: 戻り値の型がない場合は文字列`"None"`、パラメータがない場合は`"[]"`と表記されます。

## 関連ツール

このデータを分析するためのCLIツールについては、[README.md](../README.md)を参照してください。

```bash
# データ分析の例
b4-thesis analyze data/clone_NIL/20160729_092155_aa88215a

# 統計情報の取得
b4-thesis stats data/clone_NIL/20160729_092155_aa88215a --metrics clone_density

# 可視化
b4-thesis visualize data/clone_NIL --plot-type scatter --x similarity --y loc
```

## 更新履歴

- **2025-11-08**: 初版作成
