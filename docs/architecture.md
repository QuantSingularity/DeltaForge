# DeltaForge Architecture

## Full Directory Map

```
DeltaForge/
├── README.md
├── pyproject.toml
├── pytest.ini
├── requirements-dev.txt
│
├── code/
│   ├── conftest.py                        ← shared pytest fixtures (OHLCV, base_config)
│   │
│   ├── ai_models/                         ← AI / ML layer
│   │   ├── __init__.py                    ← re-exports all public classes
│   │   ├── ml_engine.py                   ← backward-compat shim
│   │   ├── scoring/
│   │   │   ├── __init__.py
│   │   │   └── signal_scorer.py           ← logistic regression scorer (0–100%)
│   │   ├── anomaly/
│   │   │   ├── __init__.py
│   │   │   └── anomaly_detector.py        ← Z-score + spread + volume anomaly gate
│   │   ├── learning/
│   │   │   ├── __init__.py
│   │   │   └── online_learner.py          ← SGD online updates from trade outcomes
│   │   ├── features/
│   │   │   ├── __init__.py
│   │   │   └── feature_extractor.py       ← NEW: 10-feature engineering (RSI, MACD, BB…)
│   │   └── tests/
│   │       ├── test_signal_scorer.py      ← 11 tests
│   │       ├── test_anomaly_detector.py   ← 9 tests
│   │       ├── test_online_learner.py     ← 6 tests
│   │       └── test_feature_extractor.py  ← 13 tests
│   │
│   └── backend/                           ← Core trading engine
│       ├── __init__.py
│       ├── __main__.py                    ← python -m code.backend
│       ├── main.py                        ← bot lifecycle, scan loop, HTF validation
│       ├── config.json                    ← hot-reloadable configuration
│       ├── requirements.txt
│       │
│       ├── core/                          ← NEW: config + logging infrastructure
│       │   ├── __init__.py
│       │   ├── config.py                  ← ConfigManager: typed, validated, hot-reload
│       │   └── logger.py                  ← structured RotatingFileHandler + RichHandler
│       │
│       ├── exchanges/                     ← Exchange API layer
│       │   ├── __init__.py
│       │   ├── base.py                    ← BaseExchange abstract interface
│       │   ├── bitflex_adapter.py         ← Bitflex native REST adapter (not in ccxt)
│       │   └── exchange_manager.py        ← unified factory for all 10 exchanges
│       │
│       ├── strategies/                    ← 26 trading strategies
│       │   ├── __init__.py
│       │   ├── indicators.py              ← shared indicator helpers (_ema, _rsi…)
│       │   ├── engine.py                  ← StrategyEngine: run_all() voting compositor
│       │   ├── trend/strategies.py        ← MA Cross, EMA, MACD, ADX, SAR, Ichimoku, Trendline
│       │   ├── momentum/strategies.py     ← RSI, Stochastic, Momentum, Bollinger Bands
│       │   ├── volatility/strategies.py   ← ATR Breakout, Breakout
│       │   ├── volume/strategies.py       ← A/D, Chaikin MF, Volume Breakout, Pullback
│       │   ├── price_action/strategies.py ← Fibonacci, Pivot Points, S/R Zones
│       │   └── advanced/strategies.py     ← SMC, Order Flow, Market Profile, LuxAlgo, News, Quant
│       │
│       ├── risk/                          ← Risk management
│       │   ├── __init__.py
│       │   ├── position_sizer.py          ← lot sizing, dollar-risk validation
│       │   ├── trail_engine.py            ← TrailState + all 5 trail type computations
│       │   └── risk_manager.py            ← unified gate: order limits, SL/TP, risk summary
│       │
│       ├── trading/                       ← Order lifecycle
│       │   ├── __init__.py
│       │   ├── trade_manager.py           ← open/close/sync trades, trail callback
│       │   └── portfolio.py               ← NEW: capital allocation, P&L, drawdown, streaks
│       │
│       ├── backtest/                      ← Backtesting
│       │   ├── __init__.py
│       │   ├── engine.py                  ← walk-forward BacktestEngine (all 5 trail types)
│       │   └── metrics.py                 ← NEW: Sharpe, Sortino, Calmar, Ulcer, MDD…
│       │
│       ├── display/                       ← Terminal dashboard
│       │   ├── __init__.py
│       │   ├── event_log.py               ← EventLog store + all EVT_* type constants
│       │   └── dashboard.py               ← DeltaForgeDisplay: 5-panel Rich dashboard
│       │
│       ├── notifications/                 ← NEW: notification channels
│       │   ├── __init__.py
│       │   ├── notifier.py                ← Notifier dispatcher + NotificationEvent
│       │   ├── telegram.py                ← TelegramChannel (Bot API, rate-limit aware)
│       │   └── webhook.py                 ← WebhookChannel (HTTP POST, JSON payload)
│       │
│       └── tests/                         ← Backend test suite
│           ├── test_strategies.py         ← 26 × 7 strategy contract tests (182 total)
│           ├── test_risk_manager.py       ← sizing, SL/TP, trail, order-gate tests
│           ├── test_portfolio.py          ← P&L, drawdown, capital, symbol stats tests
│           ├── test_backtest_metrics.py   ← Sharpe, Sortino, Calmar, streaks tests
│           ├── test_backtest_engine.py    ← engine + 5 trail-type simulation tests
│           ├── test_config.py             ← load, validate, get/set, hot-reload tests
│           ├── test_display.py            ← EventLog + dashboard rendering tests
│           ├── test_exchange_manager.py   ← BitflexAdapter + ExchangeManager mock tests
│           └── test_notifications.py      ← Notifier + Telegram + Webhook mock tests
│
├── docs/
│   └── architecture.md                   ← this file
│
├── infrastructure/
│   ├── README.md
│   ├── mql4/DeltaForge_EA.mq4            ← MT4 EA (26 strategies, 5 trail types)
│   └── mql5/
│       ├── DeltaForge_EA.mq5             ← MT5 EA (26 strategies, 5 trail types)
│       └── Include/
│           ├── Strategies.mqh            ← strategy class (LuxAlgo, News, Quant + 23)
│           ├── RiskManager.mqh
│           ├── MLFilter.mqh
│           └── DisplayPanel.mqh
│
├── scripts/
│   ├── setup.sh          ← install deps, create config
│   ├── run_bot.sh        ← live trading
│   ├── run_sandbox.sh    ← paper trading
│   ├── run_backtest.sh   ← walk-forward backtest
│   └── retrain_ml.sh     ← retrain ML from trade history
│
└── frontend/
    └── README.md         ← planned React dashboard
```

---

## Module Dependency Graph

```
main.py
  ├── core/config.py          ← ConfigManager (no internal deps)
  ├── core/logger.py          ← setup_logging  (no internal deps)
  ├── exchanges/              ← ExchangeManager
  │     └── bitflex_adapter.py
  ├── strategies/engine.py    ← StrategyEngine (composes 6 category mixins)
  │     ├── trend/
  │     ├── momentum/
  │     ├── volatility/
  │     ├── volume/
  │     ├── price_action/
  │     └── advanced/
  ├── risk/risk_manager.py
  │     ├── risk/trail_engine.py
  │     └── risk/position_sizer.py
  ├── trading/trade_manager.py
  │     ├── exchanges/exchange_manager.py
  │     └── risk/risk_manager.py
  ├── trading/portfolio.py    ← (no internal deps)
  ├── backtest/engine.py
  │     ├── strategies/engine.py
  │     ├── risk/risk_manager.py
  │     └── ai_models/scoring/
  ├── backtest/metrics.py     ← (no internal deps)
  ├── display/dashboard.py
  │     └── display/event_log.py
  ├── notifications/notifier.py
  │     ├── notifications/telegram.py
  │     └── notifications/webhook.py
  └── ai_models/
        ├── scoring/signal_scorer.py     (no internal deps)
        ├── anomaly/anomaly_detector.py  (no internal deps)
        ├── learning/online_learner.py   → scoring/signal_scorer
        └── features/feature_extractor.py (no internal deps)
```

---

## Running Tests

```bash
# From project root:
pip install -r requirements-dev.txt

# All tests:
pytest

# Specific suites:
pytest code/ai_models/tests/
pytest code/backend/tests/

# With coverage:
pytest --cov=code --cov-report=term-missing

# Single test file:
pytest code/backend/tests/test_strategies.py -v
```

---

## Running the Bot

```bash
./scripts/run_bot.sh                    # live trading
./scripts/run_sandbox.sh               # paper trading
./scripts/run_backtest.sh              # backtest
python -m code.backend --exchange bybit
python -m code.backend --retrain
```
