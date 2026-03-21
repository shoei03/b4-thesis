# NIL Docker 実行ガイド

このドキュメントでは、NIL を Docker コンテナ内で実行する方法について詳しく説明します。

## 目次

1. [Docker イメージについて](#dockerイメージについて)
2. [セットアップ手順](#セットアップ手順)
3. [実行方法](#実行方法)

---

## Docker イメージについて

### ベースイメージ

```dockerfile
FROM openjdk:21-jdk-slim
```

- **Java**: OpenJDK 21
- **OS**: Debian-based slim image
- **追加ツール**: git

### イメージサイズ

- ベースイメージ: 約 400MB
- ビルド後（NIL 含む）: 約 450MB

### 含まれているツール

- Java Development Kit 21
- Git
- Gradle（Gradle Wrapper 経由）
- NIL ソースコード

---

## セットアップ手順

### 前提条件

以下のソフトウェアがインストールされている必要があります：

- Docker Engine 20.10+
- Docker Compose 1.29+（方法 1 を使用する場合）

### インストール確認

```bash
# Dockerバージョン確認
docker --version

# Docker Composeバージョン確認
docker compose --version
```

### 初回セットアップ

```bash
# 1. リポジトリをクローン
git clone https://github.com/kusumotolab/NIL
cd NIL

# 2. Dockerイメージをビルド
docker compose build

# 3. コンテナを起動
docker compose up -d

# 4. コンテナに入る
docker compose exec nil bash

# 5. NILをビルド
./gradlew shadowJar

# 6. ビルド確認
ls -lh ./build/libs/NIL-all.jar
```

---

## 実行方法

### 基本的な実行フロー

```bash
# 1. コンテナを起動（まだ起動していない場合）
docker compose up -d

# 2. コンテナに入る
docker compose exec nil bash

# 3. NILを実行
java -jar ./build/libs/NIL-all.jar -s <ソースディレクトリ> [オプション]

# 4. 結果を確認
cat result_*.csv

# 5. コンテナから退出
exit

# 6. コンテナを停止（必要に応じて）
docker compose down
```
