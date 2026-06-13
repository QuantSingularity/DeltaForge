# DeltaForge — Code

## Structure

```
code/
├── conftest.py            # Shared pytest fixtures (base_config, _make_ohlcv)
│
├── ai_models/             # ML / AI layer
│   ├── ml_engine.py       # Backward-compat shim (re-exports all public classes)
│   ├── scoring/
│   │   └── signal_scorer.py       # Logistic regression scorer (0–100%)
│   ├── anomaly/
│   │   └── anomaly_detector.py    # Z-score + spread + volume anomaly gate
│   ├── learning/
│   │   └── online_learner.py      # SGD online updates from trade outcomes
│   ├── features/
│   │   └── feature_extractor.py   # 10-feature engineering (RSI, MACD, BB, …)
│   └── tests/                     # 39 AI/ML tests
│
└── backend/               # Core trading engine
    ├── main.py            # Bot lifecycle + main scan loop
    ├── config.json        # Hot-reloadable configuration
    ├── requirements.txt
    │
    ├── core/
    │   ├── config.py      # ConfigManager: typed, validated, hot-reload
    │   └── logger.py      # RotatingFileHandler + RichHandler
    │
    ├── strategies/        # 26 trading strategies across 6 categories
    │   ├── engine.py      # StrategyEngine (mixin composition + voting)
    │   ├── indicators.py  # Shared indicator helpers + signal constants
    │   ├── trend/         # MA Cross, EMA Trend, MACD, ADX, Parabolic SAR, Ichimoku, Trendline
    │   ├── momentum/      # RSI, Stochastic, Momentum
    │   ├── volatility/    # Bollinger Bands, ATR Breakout, Breakout
    │   ├── volume/        # Accum/Dist, Chaikin MF, Volume Breakout
    │   ├── price_action/  # Pullback, Fibonacci, Pivot Points, Support/Resistance
    │   └── advanced/      # SMC, Order Flow, Market Profile, Lux Algo, News Momentum, Quant Algo
    │
    ├── risk/
    │   ├── risk_manager.py    # Position sizing, SL/TP, dollar-risk validation
    │   ├── trail_engine.py    # 5 trail stop types (ATR/percent/dollar/time/volatility)
    │   └── position_sizer.py  # Pure sizing logic
    │
    ├── trading/
    │   ├── trade_manager.py   # Order lifecycle + trail event callbacks
    │   └── portfolio.py       # P&L, drawdown, per-symbol stats
    │
    ├── backtest/
    │   ├── engine.py      # Walk-forward backtester
    │   └── metrics.py     # Sharpe, Sortino, Calmar, Ulcer, MDD, profit factor
    │
    ├── exchanges/
    │   ├── exchange_manager.py    # 10 exchanges via ccxt
    │   ├── bitflex_adapter.py     # Custom Bitflex REST adapter
    │   └── base.py                # BaseExchange abstract interface
    │
    ├── display/
    │   ├── dashboard.py   # Rich terminal dashboard (5 panels)
    │   └── event_log.py   # Scrolling trade event log
    │
    ├── notifications/
    │   ├── notifier.py    # Central dispatcher (fire-and-forget, thread-safe)
    │   ├── telegram.py    # Telegram channel
    │   └── webhook.py     # HTTP POST webhook channel
    │
    └── tests/             # 250+ backend tests across 9 test files
```

## Quick Start

```bash
# From project root:
python -m backend               # Live trading  (pythonpath = code)
python -m backend --backtest    # Backtest all pairs
python -m backend --sandbox     # Paper trading
```

## Running Tests

```bash
# From project root (pytest.ini configures pythonpath = code automatically):
pytest
pytest -q                          # Quiet summary
pytest code/backend/tests/ -v      # Backend tests only
pytest code/ai_models/tests/ -v    # AI/ML tests only
```

## Package Imports

With `pythonpath = code` (set in `pytest.ini` and at runtime), both top-level packages are directly importable:

```python
from backend.strategies.engine import StrategyEngine
from ai_models.scoring.signal_scorer import SignalScorer
```
