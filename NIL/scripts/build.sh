#!/bin/bash

# プロジェクトビルドスクリプト
# Docker環境でGradleビルドを実行する

set -e

echo "🔨 プロジェクトをビルド中..."

# Docker コンテナでGradle ShadowJarビルドを実行
docker compose run --rm nil ./gradlew ShadowJar

echo "✅ ビルドが完了しました"
echo "📦 生成されたJARファイル: build/libs/NIL-all.jar"