#!/usr/bin/env bash
# DeltaForge - format/lint checks for Python and the frontend.
# Pass --fix to auto-format instead of just checking.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

FIX="${1:-}"

# Python: black + autoflake (install on demand if missing)
if ! command -v black >/dev/null 2>&1; then
    echo "[DeltaForge] Installing black + autoflake..."
    pip install --quiet black autoflake
fi

if [ "$FIX" = "--fix" ]; then
    echo "[DeltaForge] Formatting Python (black + autoflake)..."
    autoflake --remove-all-unused-imports --remove-unused-variables --recursive --in-place code
    black code
else
    echo "[DeltaForge] Checking Python formatting..."
    black --check code
fi

# Frontend lint (if configured)
if command -v npm >/dev/null 2>&1 && [ -d frontend/node_modules ]; then
    echo "[DeltaForge] Linting frontend..."
    (cd frontend && npm run lint) || echo "(frontend lint reported issues)"
fi

echo "[DeltaForge] Lint complete."
