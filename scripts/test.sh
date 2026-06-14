#!/usr/bin/env bash
# DeltaForge — run the full backend + AI test suite (404 tests).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

command -v pytest >/dev/null 2>&1 || { echo "pytest not found. Run ./scripts/setup.sh first."; exit 1; }

# pytest.ini sets pythonpath = code automatically.
echo "[DeltaForge] Running test suite..."
pytest "$@"
