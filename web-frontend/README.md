# DeltaForge — Web Frontend

A browser-based dashboard for monitoring and controlling DeltaForge in real time.
Built with React, Vite and Tailwind CSS; data streams live over WebSocket from
the FastAPI backend (`code/backend/api`).

## Features

- **Status bar** — bot running state, balance, session P&L, start/stop control.
- **Signal matrix** — direction, confluence and ML score for every symbol across
  the four timeframes (15m, 1h, 4h, 1d).
- **Open positions** — entry, live price, SL, TP, trail type, and unrealized P&L.
- **Strategy confluence heatmap** — all 26 strategies, color-coded buy/sell with
  opacity encoding confidence.
- **Equity curve** — live session equity with profit/loss tinting.
- **Risk dashboard** — open positions vs limit, drawdown, exposure, trail config.
- **Event log** — live stream of entries, exits, trails, anomalies and rejects.
- **Backtest** — run an on-demand walk-forward backtest and view the metrics.
- **Configuration** — edit risk, trail and ML settings; writes hot-reload the bot.

## Tech stack

- **Framework:** React 18 + Vite 5
- **Styling:** Tailwind CSS 3
- **Charts:** Recharts
- **Realtime:** native WebSocket (`/ws`) with REST polling fallback (`/api/state`)

## Development

The dashboard talks to the API via same-origin `/api` and `/ws`. In development,
`vite.config.js` proxies these to the FastAPI server on port 8000.

```bash
# Terminal 1 — start the API (from project root, pythonpath = code)
PYTHONPATH=code uvicorn backend.api.server:app --reload --port 8000

# Terminal 2 — start the dashboard
cd web-frontend
npm install
npm run dev          # http://localhost:5173
```

## Production build

```bash
cd web-frontend
npm install
npm run build        # outputs ./dist
```

Once `dist/` exists, the FastAPI server serves it directly at its root, so a
single `uvicorn backend.api.server:app` process serves both the API and the UI.
The provided Docker setup also builds and serves it behind nginx
(`infrastructure/docker`).

> A built-in Rich terminal dashboard is also available via `./scripts/run_bot.sh`
> for headless / SSH environments.
