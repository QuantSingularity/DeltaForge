#!/usr/bin/env bash
# DeltaForge — one-time setup: Python deps, API deps, config, and (optionally)
# the frontend dependencies.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "========================================"
echo "  DeltaForge Setup"
echo "========================================"

# 1. Python version check
python3 -c "import sys; assert sys.version_info >= (3,10), 'Python 3.10+ required'" \
  || { echo "ERROR: Python 3.10+ required"; exit 1; }

# 2. Backend + API dependencies
echo "Installing Python dependencies (engine + API)..."
pip install -r code/backend/requirements.txt --quiet
pip install -r infrastructure/docker/requirements-api.txt --quiet
pip install pytest --quiet

# 3. Default config
CONFIG="code/backend/config.json"
if [ ! -f "$CONFIG" ]; then
    cp code/backend/config.json.example "$CONFIG"
    echo "Created $CONFIG — edit API keys before live trading."
fi

# 4. Frontend dependencies (skipped if npm is unavailable)
if command -v npm >/dev/null 2>&1; then
    echo "Installing frontend dependencies..."
    (cd web-frontend && npm install --silent)
else
    echo "npm not found — skipping frontend deps (install Node 20+ for the dashboard)."
fi

echo ""
echo "Setup complete. Next steps:"
echo "  1. Edit code/backend/config.json with your API keys"
echo "  2. Sandbox bot:   ./scripts/run_sandbox.sh"
echo "  3. Dashboard:     ./scripts/dev.sh        (API + UI with hot reload)"
echo "  4. Tests:         ./scripts/test.sh"
