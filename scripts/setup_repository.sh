#!/bin/bash
set -e

REPO_PATH="/app/projects/pandas"
REPO_URL="https://github.com/pandas-dev/pandas.git"

if [ -d "$REPO_PATH/.git" ]; then
    echo "Repository already exists. Updating tags..."
    cd "$REPO_PATH"
    git fetch --tags --quiet
    echo "Tags updated successfully"
else
    echo "Cloning pandas repository (this may take a while)..."
    mkdir -p /app/projects
    git clone --progress --no-single-branch "$REPO_URL" "$REPO_PATH"
    cd "$REPO_PATH"
    git fetch --tags
    echo "Repository cloned successfully"
fi
