"""
DeltaForge — FastAPI server.

Exposes the live bot state to the React dashboard:

    GET  /api/health                 liveness probe
    GET  /api/state                  full dashboard snapshot
    GET  /api/signals                signal matrix (symbol x timeframe)
    GET  /api/trades                 open + recent closed trades
    GET  /api/risk                   risk dashboard
    GET  /api/strategies             confluence heatmap (26 strategies)
    GET  /api/config                 current config
    PUT  /api/config                 patch + hot-reload config
    POST /api/bot/start              start the sandbox feed
    POST /api/bot/stop               stop the feed
    POST /api/backtest               run an on-demand walk-forward backtest
    WS   /ws                         live snapshot stream (~1 Hz)

Run with:  uvicorn backend.api.server:app --reload   (pythonpath = code)
"""

from __future__ import annotations

import asyncio
import os
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..core.config import ConfigManager
from .auth import UserStore, _load_secret, build_auth_router
from .feed import FeedEngine
from .state import AppState

_HERE = os.path.dirname(os.path.abspath(__file__))
_CONFIG_PATH = os.path.join(os.path.dirname(_HERE), "config.json")


class ConfigPatch(BaseModel):
    updates: dict


class BacktestRequest(BaseModel):
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    bars: int = 600
    initial_capital: float = 10_000.0


class _WSManager:
    def __init__(self):
        self._clients: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._clients.append(ws)

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            if ws in self._clients:
                self._clients.remove(ws)

    async def broadcast(self, payload: dict):
        async with self._lock:
            dead = []
            for ws in self._clients:
                try:
                    await ws.send_json(payload)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self._clients.remove(ws)


def create_app() -> FastAPI:
    cfg_mgr = ConfigManager(_CONFIG_PATH)
    cfg_mgr.load()
    config = cfg_mgr.as_dict()

    state = AppState(initial_capital=float(config.get("initial_capital", 10_000.0)))
    feed = FeedEngine(state, config)
    ws_manager = _WSManager()

    app = FastAPI(title="DeltaForge API", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Authentication (register / login / me). Registered before the static
    # frontend mount so the API routes always take precedence.
    auth_store = UserStore()
    auth_secret = _load_secret()
    app.include_router(build_auth_router(auth_store, auth_secret))

    @app.on_event("startup")
    async def _startup():
        feed.start()
        # Hold a reference to the broadcaster task. Without one, the event
        # loop only keeps a weak reference and the task may be garbage
        # collected mid-flight.
        app.state.broadcaster_task = asyncio.create_task(_broadcaster())

    @app.on_event("shutdown")
    async def _shutdown():
        feed.stop()
        task = getattr(app.state, "broadcaster_task", None)
        if task is not None:
            task.cancel()

    async def _broadcaster():
        while True:
            await ws_manager.broadcast(state.snapshot())
            await asyncio.sleep(1.0)

    # ── REST ──────────────────────────────────────────────────────────
    @app.get("/api/health")
    def health():
        return {"status": "ok", "bot_running": state.bot_running}

    @app.get("/api/state")
    def get_state():
        return state.snapshot()

    @app.get("/api/signals")
    def signals():
        snap = state.snapshot()
        return {"signals": snap["signals"], "account": snap["account"]}

    @app.get("/api/trades")
    def trades():
        snap = state.snapshot()
        return {"open": snap["open_trades"], "closed": snap["closed_trades"]}

    @app.get("/api/risk")
    def risk():
        snap = state.snapshot()
        return {
            "risk": snap["risk"],
            "account": snap["account"],
            "equity_curve": snap["equity_curve"],
        }

    @app.get("/api/strategies")
    def strategies():
        return feed.confluence_matrix()

    @app.get("/api/config")
    def get_config():
        return cfg_mgr.as_dict()

    @app.put("/api/config")
    def put_config(patch: ConfigPatch):
        for key, value in patch.updates.items():
            cfg_mgr.set(key, value, persist=True)
        feed.cfg = cfg_mgr.as_dict()
        state.add_event(
            {"type": "INFO", "message": f"Config updated: {', '.join(patch.updates)}"}
        )
        return {"ok": True, "config": cfg_mgr.as_dict()}

    @app.post("/api/bot/start")
    def bot_start():
        feed.start()
        return {"ok": True, "bot_running": True}

    @app.post("/api/bot/stop")
    def bot_stop():
        feed.stop()
        return {"ok": True, "bot_running": False}

    @app.post("/api/backtest")
    def run_backtest(req: BacktestRequest):
        # Local import keeps server startup fast.
        from testkit import make_ohlcv  # type: ignore

        from ..backtest.engine import BacktestEngine

        df = make_ohlcv(req.bars)
        engine = BacktestEngine(cfg_mgr.as_dict())
        result = engine.run(
            df,
            req.symbol,
            req.timeframe,
            initial_capital=req.initial_capital,
            walk_forward=False,
        )
        return {
            "symbol": result.symbol,
            "timeframe": result.timeframe,
            "total_trades": result.total_trades,
            "win_rate": round(result.win_rate, 2),
            "total_pnl": round(result.total_pnl, 2),
            "max_drawdown": round(result.max_drawdown, 2),
            "sharpe": round(result.sharpe, 3),
            "profit_factor": (
                round(result.profit_factor, 3)
                if result.profit_factor != float("inf")
                else None
            ),
            "equity_curve": result.equity_curve,
            "trades": result.trades[-100:],
        }

    # ── WebSocket ─────────────────────────────────────────────────────
    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        await ws_manager.connect(ws)
        try:
            await ws.send_json(state.snapshot())
            while True:
                await ws.receive_text()  # keep-alive; client may ping
        except WebSocketDisconnect:
            await ws_manager.disconnect(ws)
        except Exception:
            await ws_manager.disconnect(ws)

    # ── static frontend (served when built) ───────────────────────────
    dist = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(_HERE))), "frontend", "dist"
    )
    if os.path.isdir(dist):
        # Serve hashed build assets directly.
        assets_dir = os.path.join(dist, "assets")
        if os.path.isdir(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
        index_file = os.path.join(dist, "index.html")

        # SPA fallback: any non-API GET path serves a real file when one exists
        # (favicon, etc.) and otherwise index.html, so a hard refresh on a deep
        # link such as /dashboard does not 404. Registered last, so the /api
        # routes and the /assets mount above take precedence.
        @app.get("/{full_path:path}")
        def spa(full_path: str):
            # Unknown API paths should 404 as API, not fall through to the SPA.
            if full_path.startswith("api/") or full_path == "api":
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            if full_path:
                candidate = os.path.join(dist, full_path)
                if os.path.isfile(candidate):
                    return FileResponse(candidate)
            return FileResponse(index_file)

    else:

        @app.get("/")
        def root():
            return JSONResponse(
                {
                    "service": "DeltaForge API",
                    "docs": "/docs",
                    "note": "Build the frontend (npm run build) to serve the dashboard here.",
                }
            )

    return app


app = create_app()
