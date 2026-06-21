# DeltaForge

An internal, multi-strategy agentic AI trading system for crypto (direct
exchange APIs) and forex (MT4/MT5 Expert Advisors), with a shared trading core,
a live web dashboard, and full deployment tooling.

## What's inside

```
DeltaForge/
├── code/                      # Python trading core + AI/ML + FastAPI API
│   ├── backend/               # Engine, strategies, risk, backtest, exchanges, api
│   └── ai_models/             # Signal scoring, anomaly detection, online learning
├── frontend/              # React + Vite + Tailwind dashboard
├── infrastructure/
│   ├── mql4/ · mql5/          # MetaTrader Expert Advisors (forex)
│   ├── docker/                # Dockerfiles, compose, nginx
│   ├── k8s/                   # Kubernetes manifests
│   └── terraform/             # IaC (ECR + VPC + EKS)
├── scripts/                   # run_bot / run_backtest / run_sandbox / retrain / setup
├── docs/                      # Architecture notes
└── .github/workflows/         # CI
```

## Capabilities

- **26 trading strategies** across trend, momentum, volatility, volume, price
  action and advanced categories, combined by a confluence-voting engine.
- **10 crypto exchanges** via ccxt plus a native Bitflex adapter; spot + margin.
- **Forex** through MT4 (MQL4) and MT5 (MQL5) EAs with the same strategy logic.
- **Four timeframes only** — 15m, 1h, 4h, 1d — with higher-timeframe trend
  confirmation before any entry.
- **Risk management** — dynamically configurable, hot-reloaded: per-trade loss
  caps, order/position limits, and five trailing-stop types (ATR, percentage,
  dollar, time, volatility).
- **AI layer** — logistic-regression signal scoring (0–100% probability of gain),
  anomaly auto-stop, and online learning from trade outcomes.
- **Live dashboard** — signal matrix, open positions, confluence heatmap, equity
  curve, risk panel, event log, on-demand backtest, and live config editing.

## Quick start

```bash
# 1. Backend tests (404 tests; pythonpath configured by pytest.ini)
pip install -r code/backend/requirements.txt -r infrastructure/docker/requirements-api.txt pytest
pytest

# 2. Run the bot
PYTHONPATH=code python -m backend --sandbox

# 3. Run the dashboard (API + UI)
PYTHONPATH=code uvicorn backend.api.server:app --reload     # http://localhost:8000
#   (or `cd frontend && npm install && npm run dev` for hot-reload UI)

# 4. Full stack in containers
docker compose -f infrastructure/docker/docker-compose.yml up --build
```

## Intended use

Internal, in-house trading operations only. No resale or commercial
redistribution. See `LICENSE`.
