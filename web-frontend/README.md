# DeltaForge - Web Frontend

> **Status: Planned**

A browser-based dashboard for monitoring DeltaForge in real time.

## Planned Features

- Live signal analysis across all timeframes and symbols
- Open trade table with unrealized PnL, SL, TP, trail status
- Risk dashboard (exposure, drawdown, session PnL)
- Strategy confluence heatmap (26 strategies × 4 TFs)
- Backtest results viewer (equity curve, trade log)
- Config editor with hot-reload

## Planned Tech Stack

- **Framework:** React + Vite
- **UI:** Tailwind CSS
- **Charts:** Recharts / Lightweight Charts
- **Backend API:** FastAPI (Python) served from `code/backend/`
- **Realtime:** WebSocket feed from the bot loop

## Development

```bash
cd web-frontend
npm install
npm run dev
```

> Until this is implemented, use the built-in Rich terminal dashboard
> by running `./scripts/run_bot.sh`.
