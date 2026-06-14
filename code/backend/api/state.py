"""
DeltaForge — shared API application state.

A single thread-safe ``AppState`` instance is the source of truth for the
dashboard. The live feed (or a real bot loop) publishes into it; the REST and
WebSocket layers read snapshots out of it.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Deque, Dict, List


class AppState:
    """Thread-safe in-memory store of everything the dashboard renders."""

    MAX_EVENTS = 200
    MAX_EQUITY = 500

    def __init__(self, initial_capital: float = 10_000.0):
        self._lock = threading.RLock()
        self.started_at = time.time()
        self.bot_running = False
        self.mode = "sandbox"  # sandbox | live | backtest
        self.exchange = "binance"

        self.initial_capital = initial_capital
        self.balance = initial_capital

        # symbol -> timeframe -> signal dict
        self.signals: Dict[str, Dict[str, dict]] = {}
        self.open_trades: List[dict] = []
        self.closed_trades: List[dict] = []
        self.events: Deque[dict] = deque(maxlen=self.MAX_EVENTS)
        self.equity_curve: Deque[float] = deque(
            [initial_capital], maxlen=self.MAX_EQUITY
        )
        self.risk: dict = {}
        self.last_update = time.time()

    # ── writers ───────────────────────────────────────────────────────
    def set_status(
        self, *, running: bool = None, mode: str = None, exchange: str = None
    ):
        with self._lock:
            if running is not None:
                self.bot_running = running
            if mode is not None:
                self.mode = mode
            if exchange is not None:
                self.exchange = exchange
            self.last_update = time.time()

    def update_signal(self, symbol: str, timeframe: str, signal: dict):
        with self._lock:
            self.signals.setdefault(symbol, {})[timeframe] = signal
            self.last_update = time.time()

    def set_open_trades(self, trades: List[dict]):
        with self._lock:
            self.open_trades = list(trades)
            self.last_update = time.time()

    def add_closed_trade(self, trade: dict):
        with self._lock:
            self.closed_trades.append(trade)
            self.balance += float(trade.get("pnl", 0.0))
            self.equity_curve.append(round(self.balance, 2))
            self.last_update = time.time()

    def add_event(self, event: dict):
        with self._lock:
            event.setdefault("ts", time.time())
            self.events.appendleft(event)
            self.last_update = time.time()

    def set_risk(self, risk: dict):
        with self._lock:
            self.risk = dict(risk)
            self.last_update = time.time()

    # ── readers ───────────────────────────────────────────────────────
    def snapshot(self) -> dict:
        """Full immutable snapshot for REST / WebSocket broadcast."""
        with self._lock:
            session_pnl = round(self.balance - self.initial_capital, 2)
            return {
                "status": {
                    "bot_running": self.bot_running,
                    "mode": self.mode,
                    "exchange": self.exchange,
                    "uptime_sec": round(time.time() - self.started_at, 1),
                    "last_update": self.last_update,
                },
                "account": {
                    "initial_capital": self.initial_capital,
                    "balance": round(self.balance, 2),
                    "session_pnl": session_pnl,
                    "session_pnl_pct": round(
                        session_pnl / max(self.initial_capital, 1e-9) * 100, 2
                    ),
                },
                "signals": {s: dict(tfs) for s, tfs in self.signals.items()},
                "open_trades": list(self.open_trades),
                "closed_trades": list(self.closed_trades)[-50:],
                "events": list(self.events)[:50],
                "equity_curve": list(self.equity_curve),
                "risk": dict(self.risk),
            }
