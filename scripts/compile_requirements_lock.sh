#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

python3 -m pip install --upgrade pip pip-tools

pip-compile requirements.txt --output-file requirements-lock.txt

echo "Generated requirements-lock.txt"
