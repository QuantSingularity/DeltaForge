# DeltaForge

A multi-strategy agentic trading system for crypto (direct exchange APIs) and forex
(MT4/MT5 Expert Advisors). A Python trading core runs 26 strategies through a
confluence-voting engine, scores each candidate with a machine-learning layer, and
manages risk with hot-reloadable limits. The same core is exposed through a FastAPI
service that drives a modern React dashboard, a terminal bot, and MetaTrader EAs.

The emphasis is on correct, well-tested trading logic and a clean architecture. Every
simplifying assumption is stated plainly in the Limitations table rather than hidden.

|                |                                                                               |
| -------------- | ----------------------------------------------------------------------------- |
| **Language**   | Python 3.12 (core + API), React + Vite (web), MQL4/MQL5 (forex)               |
| **Interfaces** | Web dashboard, REST API + WebSocket, terminal bot, MT4/MT5 EAs                |
| **Modules**    | Strategies, Risk, Backtest, Execution, Exchanges, AI scoring, Notifications   |
| **Strategies** | 26 across 6 categories, combined by a confluence-voting engine                |
| **Markets**    | 10 crypto exchanges via ccxt plus a native Bitflex adapter; forex via MT4/MT5 |
| **Auth**       | Token based (stdlib PBKDF2 hashing + HMAC-signed tokens), no extra deps       |
| **Tests**      | 424 tests, all passing via pytest                                             |
| **Build**      | pip + pytest (backend), Vite (frontend), Docker (full stack)                  |

## Capabilities

| Module      | What it does                                                                                                                                    |
| ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Market data | Fetches OHLCV via ccxt or the native Bitflex adapter; a sandbox feed drives the dashboard with a synthetic series when no exchange is connected |
| Strategies  | 26 strategies across 6 categories vote into a single direction and confluence score, with higher-timeframe trend confirmation before entry      |
| AI scoring  | Logistic-regression scorer rates each signal 0 to 100 percent, learns online from outcomes, and auto-stops on anomalies                         |
| Risk        | Per-trade loss caps, order and position limits, and five trailing-stop types (ATR, percentage, dollar, time, volatility), all hot-reloaded      |
| Execution   | Portfolio and trade manager track positions, average cost, and realized and unrealized PnL                                                      |
| Backtesting | Walk-forward engine with metrics: win rate, net PnL, max drawdown, Sharpe and profit factor                                                     |
| Interfaces  | Everything above over a REST API plus a live WebSocket stream, an authenticated web dashboard, a terminal bot, and MetaTrader EAs               |

## Architecture

```
                      +----------------------------+
                      |  React + Vite dashboard     |
                      |  (Tailwind, Recharts)       |
                      +-------------+--------------+
                                    | fetch /api/*  + WS /ws  (JSON)
                                    v
                      +----------------------------+
                      |  FastAPI service            |
                      |  (REST + WebSocket + auth)  |
                      +-------------+--------------+
                                    | direct calls
                                    v
   +------------------------------------------------------------------+
   |                    DeltaForge trading core (Python)               |
   |                                                                   |
   |  Strategies   Risk   Backtest   Execution   Exchanges   AI scorer |
   |  Core: hot-reload config, logging, notifications                  |
   +------------------------------------------------------------------+
                          ^                         ^
                          | same core               | shared strategy logic
                      +----------------+      +----------------------+
                      |  Terminal bot  |      |  MT4 / MT5 EAs (MQL)  |
                      +----------------+      +----------------------+
```

The trading core is one implementation. The API service, the terminal bot and the
test suite all use that single core, so there is one implementation of every
calculation. The MetaTrader EAs mirror the same strategy logic for forex venues.

## Project structure

```
DeltaForge/
├── code/
│   ├── backend/
│   │   ├── api/              # FastAPI server, auth, live feed, app state
│   │   ├── strategies/       # 26 strategies in 6 category packages + engine
│   │   ├── risk/             # Position sizing, trailing stops, risk manager
│   │   ├── backtest/         # Walk-forward engine and metrics
│   │   ├── exchanges/        # ccxt manager and the native Bitflex adapter
│   │   ├── trading/          # Portfolio and trade manager
│   │   ├── notifications/    # Telegram and webhook notifiers
│   │   ├── core/             # Hot-reloading config and logging
│   │   ├── tests/            # Backend unit tests
│   │   └── main.py           # Terminal bot entry point
│   └── ai_models/            # Signal scoring, anomaly detection, online learning
├── frontend/
│   └── src/
│       ├── pages/            # Home, SignIn, SignUp, Dashboard, Trades, ...
│       ├── auth/             # Auth context and route guards
│       ├── components/       # Layout, navigation, live panels, charts
│       ├── hooks/            # Live WebSocket state with REST fallback
│       └── api/              # REST client (bearer auth, configurable base)
├── infrastructure/
│   ├── docker/               # Dockerfiles, compose, nginx
│   ├── k8s/                  # Kubernetes manifests
│   ├── terraform/            # IaC (ECR, VPC, EKS)
│   └── mql4/ · mql5/         # MetaTrader Expert Advisors
├── scripts/                  # Run, backtest, dev, build, test and setup helpers
├── docs/                     # Architecture notes
├── .github/workflows/        # Continuous integration
└── README.md
```

## Web app

The dashboard opens on a public homepage. A user signs up or signs in and is taken
to the protected dashboard. Authentication uses a bearer token that the frontend
stores client-side and sends on every request; a 401 clears it and returns to sign-in.

| Route         | Page       | Access                                            |
| ------------- | ---------- | ------------------------------------------------- |
| `/`           | Home       | Public landing (entry route)                      |
| `/signin`     | Sign in    | Public, redirects to the dashboard if signed in   |
| `/signup`     | Sign up    | Public, redirects to the dashboard if signed in   |
| `/dashboard`  | Dashboard  | Protected                                         |
| `/trades`     | Trades     | Protected (open positions and closed history)     |
| `/strategies` | Strategies | Protected (signal matrix and 26-strategy heatmap) |
| `/backtest`   | Backtest   | Protected (on-demand walk-forward)                |
| `/settings`   | Settings   | Protected (live config and account)               |

When the frontend is built (`frontend/dist`), the FastAPI server serves it on the
same origin with a single-page-app fallback, so one process serves both the API and
the dashboard and a hard refresh on a deep link such as `/dashboard` resolves correctly.

## Strategies

All 26 strategies run every scan and vote. The engine aggregates the votes into a
single direction and a confluence score; a trade is only considered when confluence
clears the threshold and the higher-timeframe trend agrees. Signals at one bar are
acted on at the next, so there is no look-ahead bias.

| Category     | Count | Strategies                                                           |
| ------------ | ----- | -------------------------------------------------------------------- |
| Trend        | 7     | ma_cross, ema_trend, macd, adx, parabolic_sar, ichimoku, trendline   |
| Momentum     | 3     | rsi, stochastic, momentum                                            |
| Volatility   | 3     | bollinger_bands, atr_breakout, breakout                              |
| Volume       | 3     | accum_dist, chaikin_mf, volume_breakout                              |
| Price action | 4     | pullback, fibonacci, pivot_points, support_resist                    |
| Advanced     | 6     | smc, order_flow, market_profile, lux_algo, news_momentum, quant_algo |

## REST API

All routes are served under `/api`; the live feed is a WebSocket at `/ws`. Auth is
token based and adds no third-party dependencies (standard-library PBKDF2 password
hashing and HMAC-signed tokens, with a JSON-file user store).

### Authentication

| Method | Path                 | Body / header                   | Returns           |
| ------ | -------------------- | ------------------------------- | ----------------- |
| POST   | `/api/auth/register` | `{ name, email, password }`     | `{ token, user }` |
| POST   | `/api/auth/login`    | `{ email, password }`           | `{ token, user }` |
| GET    | `/api/auth/me`       | `Authorization: Bearer <token>` | `{ user }`        |

### Dashboard and control

| Method | Path              | Description                                 |
| ------ | ----------------- | ------------------------------------------- |
| GET    | `/api/health`     | Liveness probe and bot running state        |
| GET    | `/api/state`      | Full dashboard snapshot                     |
| GET    | `/api/signals`    | Signal matrix (symbol x timeframe)          |
| GET    | `/api/trades`     | Open and recent closed trades               |
| GET    | `/api/risk`       | Risk dashboard                              |
| GET    | `/api/strategies` | Confluence heatmap across the 26 strategies |
| GET    | `/api/config`     | Current configuration                       |
| PUT    | `/api/config`     | Patch and hot-reload configuration          |
| POST   | `/api/bot/start`  | Start the sandbox feed                      |
| POST   | `/api/bot/stop`   | Stop the feed                               |
| POST   | `/api/backtest`   | Run an on-demand walk-forward backtest      |
| WS     | `/ws`             | Live snapshot stream (about 1 Hz)           |

### Backtest request body

| Field             | Example      | Notes                      |
| ----------------- | ------------ | -------------------------- |
| `symbol`          | `"BTC/USDT"` | Trading pair               |
| `timeframe`       | `"1h"`       | One of 15m, 1h, 4h, 1d     |
| `bars`            | `600`        | Number of bars to simulate |
| `initial_capital` | `10000`      | Starting equity            |

## Prerequisites

| Tool          | Version  | Purpose                             |
| ------------- | -------- | ----------------------------------- |
| Python + pip  | 3.10+    | Run the trading core, API and tests |
| Node.js + npm | 20+      | Build and serve the dashboard       |
| Docker        | Optional | Run the full stack in containers    |

## Quick start

| Goal                 | Command                                                                                             |
| -------------------- | --------------------------------------------------------------------------------------------------- |
| Install backend deps | `pip install -r code/backend/requirements.txt -r infrastructure/docker/requirements-api.txt pytest` |
| Run the test suite   | `pytest`                                                                                            |
| Run the bot (paper)  | `PYTHONPATH=code python -m backend --sandbox`                                                       |
| Run a backtest       | `PYTHONPATH=code python -m backend --backtest`                                                      |

Development, with API and UI hot reload (two processes):

```
PYTHONPATH=code uvicorn backend.api.server:app --reload --port 8000
cd frontend && npm install && npm run dev      # http://localhost:5173
```

Single origin, where one process serves the API and the built dashboard:

```
cd frontend && npm install && npm run build && cd ..
PYTHONPATH=code uvicorn backend.api.server:app --port 8000   # http://localhost:8000
```

Full stack in containers:

```
docker compose -f infrastructure/docker/docker-compose.yml up --build
# Dashboard: http://localhost:8080   API docs: http://localhost:8000/docs
```

## Helper scripts

| Script                      | What it does                                      |
| --------------------------- | ------------------------------------------------- |
| `scripts/setup.sh`          | One-time dependency and config setup              |
| `scripts/dev.sh`            | API and Vite dev server together (hot reload)     |
| `scripts/run_sandbox.sh`    | Paper-trading bot                                 |
| `scripts/run_bot.sh`        | Live trading bot                                  |
| `scripts/run_backtest.sh`   | Walk-forward backtest                             |
| `scripts/run_dashboard.sh`  | Serve the dashboard API (and built UI if present) |
| `scripts/build_frontend.sh` | Production build of the dashboard                 |
| `scripts/retrain_ml.sh`     | Retrain the ML scorer from trade history          |
| `scripts/test.sh`           | Run the test suite                                |
| `scripts/lint.sh`           | Python and frontend lint                          |
| `scripts/docker_up.sh`      | Build and start the full stack in Docker          |
| `scripts/docker_down.sh`    | Stop and remove the Docker stack                  |

## Configuration

Bot behavior (strategies, risk, trailing stops, ML thresholds, symbols) lives in
`code/backend/config.json` and hot-reloads on save through the dashboard. Runtime
environment variables:

| Variable                 | Purpose                                                  | Default     |
| ------------------------ | -------------------------------------------------------- | ----------- |
| `DELTAFORGE_MODE`        | Runtime mode (sandbox or live)                           | `sandbox`   |
| `DELTAFORGE_EXCHANGE`    | Override the configured exchange for run scripts         | unset       |
| `DELTAFORGE_PORT`        | API and dashboard port for the dev and dashboard scripts | `8000`      |
| `DELTAFORGE_AUTH_SECRET` | Token signing secret (generated and persisted if unset)  | generated   |
| `DELTAFORGE_DATA_DIR`    | Directory for the auth user store                        | backend dir |

## Limitations and simplifications

| Area           | Simplification                                                                                                                                                 |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Sandbox feed   | The dashboard runs on a synthetic random-walk price series so it populates without an exchange; trades shown in sandbox are simulated, not live fills          |
| Backtest fills | Signals enter at the bar close with a simple model; no intrabar matching, partial fills or live order book                                                     |
| AI scorer      | Logistic regression over a 10-feature handcrafted vector, not a deep model; trained on outcomes rather than tick data                                          |
| Auth scope     | The dashboard data endpoints are gated by the UI rather than per-route; suitable for a same-origin internal tool, with per-route enforcement an easy follow-up |
| Live data      | Live mode needs exchange API access; on a restricted network the exchange hosts must be on the egress allowlist                                                |
| Forex EAs      | The MQL4/MQL5 EAs are delivered as source and compile in MetaEditor; they are reviewed statically here, not compiled in CI                                     |

## Testing and verification

The suite is 424 tests, run with `pytest` (pythonpath configured by `pytest.ini`).

| Area            | What is covered                                                                              |
| --------------- | -------------------------------------------------------------------------------------------- |
| Config          | Load, validate, hot-reload, and typed accessors                                              |
| Strategies      | The engine, indicator helpers, and confluence aggregation                                    |
| Risk            | Position sizing, stop and target calculation, trailing-stop engine                           |
| Portfolio       | Average-cost accounting, realized and unrealized PnL                                         |
| Backtest        | Walk-forward engine and every metric (win rate, drawdown, Sharpe, profit factor)             |
| Exchanges       | Exchange manager behavior and the Bitflex adapter                                            |
| AI layer        | Feature extraction, signal scoring, online learning, anomaly detection                       |
| Auth            | Registration, duplicate and weak-password rejection, login, token round-trip, tamper, expiry |
| API regressions | The scorer feature-vector crash and the strategies serialization fix are locked in           |

The REST API and WebSocket were exercised end to end against a live server, and the
built frontend is served by the same FastAPI process that answers the API.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
