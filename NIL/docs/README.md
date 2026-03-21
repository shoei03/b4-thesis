# NIL ドキュメント

このディレクトリには、NIL（N-gram, Inverted index, LCS）クローン検出ツールに関する詳細なドキュメントが含まれています。

## ドキュメント一覧

### 1. [使用ガイド](./NIL_USAGE_GUIDE.md)

**対象読者**: NIL を使い始めるすべてのユーザー

**内容**:

- NIL の動作原理の説明

### 2. [Docker 実行ガイド](./DOCKER_GUIDE.md)

**対象読者**: Docker を使って NIL を実行したいユーザー

**内容**:

- Docker イメージの詳細
- セットアップ手順（Docker Compose / Docker CLI）

### 3. [入出力フォーマット詳細](./IO_FORMAT.md)

**対象読者**: NIL の入出力仕様を詳しく知りたいユーザー

**内容**:

- すべてのコマンドライン引数の詳細
- 中間ファイルの説明
- 出力ファイルの解析方法

### 4. [アーキテクチャドキュメント](./ARCHITECTURE.md)

**対象読者**: NIL の内部実装を理解したい開発者・研究者

**内容**:

- システムアーキテクチャ（3 層構造）
- コアコンポーネントの詳細
- 処理フローとアルゴリズム
- データ構造の設計
- 並列処理戦略
- 最適化技法
- 拡張方法

**こんな時に読む**:

- NIL の仕組みを深く理解したい
- 新しい機能を追加したい
- 新しい言語サポートを追加したい
- 研究で実装詳細が必要
- パフォーマンス改善を検討したい

## ドキュメントの読み方

### 初めて NIL を使う場合

1. **[使用ガイド](./NIL_USAGE_GUIDE.md)** を読む

   - 動作原理を理解

2. **[Docker 実行ガイド](./DOCKER_GUIDE.md)** を読む（Docker を使う場合）

   - セットアップ手順に従う

3. **[入出力フォーマット詳細](./IO_FORMAT.md)** を参照する（必要に応じて）

   - パラメータの詳細を確認
   - 出力結果の解釈

## 関連リソース

### プロジェクトルートのドキュメント

- [README.md](../README.md) - プロジェクト概要
- [INSTALL.md](../INSTALL.md) - インストール手順
- [EXPERIMENT.md](../EXPERIMENT.md) - 実験方法
- [METHOD_TRACKING.md](../METHOD_TRACKING.md) - メソッド追跡機能
- [REQUIREMENTS.md](../REQUIREMENTS.md) - 要件定義

### 学術論文

- FSE '21 論文: [camera-ready.pdf](../camera-ready.pdf)
- DOI: [10.5281/zenodo.4492665](https://doi.org/10.5281/zenodo.4492665)

### リポジトリ

- GitHub: [https://github.com/kusumotolab/NIL](https://github.com/kusumotolab/NIL)

## フィードバック

ドキュメントに関するフィードバックや改善提案は、GitHub の Issue までお願いします。

## ライセンス

このドキュメントは、NIL プロジェクトと同じライセンス（[LICENSE](../LICENSE)参照）の下で提供されています。

---

**最終更新**: 2026 年 3 月 20 日
