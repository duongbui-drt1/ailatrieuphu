#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-all}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

python3 -m pip install -r requirements.txt
python3 -m pip install -r requirements-build.txt
python3 packaging/build_apps.py --target "$TARGET" --pkg
