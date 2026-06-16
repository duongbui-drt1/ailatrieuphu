#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-all}"
VERSION="${2:-${AILTP_VERSION:-}}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
if [ -z "$VERSION" ]; then
  VERSION="$(python3 -c 'from app_info import APP_VERSION; print(APP_VERSION)')"
fi

python3 -m pip install -r requirements.txt
python3 -m pip install -r requirements-build.txt
python3 packaging/build_apps.py --target "$TARGET" --dmg --version "$VERSION"
