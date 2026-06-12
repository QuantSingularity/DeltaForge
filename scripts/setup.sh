#!/usr/bin/env bash
# DeltaForge — initial setup
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo "  DeltaForge Setup"
echo "========================================"

cd "$PROJECT_ROOT"

# Python version check
python3 -c "import sys; assert sys.version_info >= (3,10), 'Python 3.10+ required'" \
  || { echo "ERROR: Python 3.10+ required"; exit 1; }

echo "Installing Python dependencies..."
pip install -r code/backend/requirements.txt --quiet

echo "Copying default config if not present..."
CONFIG="code/backend/config.json"
if [ ! -f "$CONFIG" ]; then
    cp code/backend/config.json.example "$CONFIG"
    echo "Created $CONFIG — edit API keys before running."
fi

echo ""
echo "Setup complete. Next steps:"
echo "  1. Edit code/backend/config.json with your API keys"
echo "  2. Run:  ./scripts/run_bot.sh"
echo "  3. Backtest: ./scripts/run_backtest.sh"
