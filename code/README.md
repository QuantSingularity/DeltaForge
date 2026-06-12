# DeltaForge — Code

## Structure

```
code/
├── ai_models/         # ML / AI layer
│   └── ml_engine.py   # SignalScorer, AnomalyDetector, OnlineLearner
└── backend/           # Core trading engine
    ├── main.py        # Bot lifecycle + main scan loop
    ├── strategies.py  # 26 trading strategies
    ├── exchange_manager.py  # 10 exchanges (ccxt + Bitflex REST adapter)
    ├── risk_manager.py      # Sizing, SL/TP, 5 trail stop types, risk summary
    ├── trade_manager.py     # Order lifecycle + trail event callbacks
    ├── backtest.py          # Walk-forward backtester
    ├── display.py           # Rich terminal dashboard (5 panels)
    └── config.json          # Hot-reloadable configuration
```

## Quick Start

```bash
# From project root:
python -m code.backend               # Live trading
python -m code.backend --backtest    # Backtest all pairs
python -m code.backend --sandbox     # Paper trading
```

## Package Imports

Internal modules use relative imports. If you import `code.backend`
from outside the package:

```python
from code.backend.strategies import StrategyEngine
from code.ai_models.ml_engine import SignalScorer
```
