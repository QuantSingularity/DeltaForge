# DeltaForge - Web Frontend

A browser-based application for monitoring and controlling DeltaForge in real
time. Built with React 18, Vite 5, Tailwind CSS 3 and React Router 6. Live data
streams over WebSocket from the FastAPI backend (`code/backend/api`), with a REST
polling fallback.

## Application structure

The app opens on a public **Homepage**. From there a visitor signs up or signs
in, and is taken to the protected **Dashboard**. The authenticated area shares a
single live WebSocket subscription across all of its pages.

```
Routes
  /            Home               public landing (entry route)
  /signin      Sign in            public, redirects to /dashboard if signed in
  /signup      Sign up            public, redirects to /dashboard if signed in
  /dashboard   Dashboard          protected: signal matrix, open trades,
                                   confluence heatmap, equity, risk, event log
  /trades      Trades             protected: open positions + closed history
  /strategies  Strategies         protected: signal matrix + 26-strategy heatmap
  /backtest    Backtest           protected: on-demand walk-forward backtest
  /settings    Settings           protected: live config editor + account/runtime
  *            404                anything else
```

```
src/
  api/client.js          REST client: base URL, bearer-token auth, endpoints
  auth/
    AuthContext.jsx      session state: login, register, logout, restore
    ProtectedRoute.jsx   guards the authenticated area
    PublicOnlyRoute.jsx  keeps signed-in users out of sign-in / sign-up
  components/            AppLayout, Sidebar, TopBar, Brand, AuthShell, Field,
                         PageHeader, and the live panels (SignalMatrix, OpenTrades,
                         RiskPanel, EquityCurve, ConfluenceHeatmap, EventLog,
                         ConfigEditor, BacktestPanel)
  hooks/useLiveState.js  WebSocket snapshot stream with REST polling fallback
  lib/format.js          display formatting + trading color semantics
  pages/                 Home, SignIn, SignUp, Dashboard, Trades, Strategies,
                         Backtest, Settings, NotFound
```

## API contract consumed

REST base URL is `VITE_API_BASE` (default `/api`). The dashboard data and bot
control endpoints are served by the existing backend. Authentication uses a
bearer token stored client-side and sent as `Authorization: Bearer <token>`:

```
POST /api/auth/register   { name, email, password } -> { token, user }
POST /api/auth/login      { email, password }        -> { token, user }
GET  /api/auth/me         (Authorization header)     -> { user }
```

## Development

```bash
# Terminal 1: start the API (from project root, pythonpath = code)
PYTHONPATH=code uvicorn backend.api.server:app --reload --port 8000

# Terminal 2: start the dashboard (proxies /api and /ws to port 8000)
cd frontend
npm install
npm run dev          # http://localhost:5173
```

## Lint and build

```bash
cd frontend
npm install
npm run lint         # eslint (config in .eslintrc.cjs)
npm run build        # outputs ./dist (vendor-split: app / react / charts)
```

Once `dist/` exists, the FastAPI server can serve it directly. For client-side
routing to survive a hard refresh on a deep link in production, the server must
fall back to `index.html` for non-API routes. The Docker / nginx setup in
`infrastructure/docker` is wired for this during the integration phase.
