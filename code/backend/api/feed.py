"""
DeltaForge — live dashboard feed.

Runs the real StrategyEngine, FeatureExtractor and SignalScorer on a rolling
synthetic price series (sandbox mode) so the dashboard is fully populated
without a live exchange connection. In live mode the same publishing contract
is used by the trading loop, so the frontend code is identical either way.
"""

from __future__ import annotations

import threading
import time
import uuid

import numpy as np
import pandas as pd
from ai_models.features.feature_extractor import FeatureExtractor
from ai_models.scoring.signal_scorer import SignalScorer

from ..strategies.engine import StrategyEngine
from ..strategies.indicators import SIGNAL_BUY, SIGNAL_NONE, SIGNAL_SELL
from .state import AppState

TIMEFRAMES = ["15m", "1h", "4h", "1d"]
_DIR_NAME = {SIGNAL_BUY: "BUY", SIGNAL_SELL: "SELL", SIGNAL_NONE: "FLAT"}


class _Walker:
    """Maintains an evolving synthetic OHLCV series per (symbol, timeframe)."""

    def __init__(self, seed: int, start: float):
        self._rng = np.random.default_rng(seed)
        self._closes = list(
            np.cumprod(1 + self._rng.normal(0.0002, 0.012, 320)) * start
        )

    def step(self) -> pd.DataFrame:
        nxt = self._closes[-1] * (1 + self._rng.normal(0.0002, 0.012))
        self._closes.append(nxt)
        self._closes = self._closes[-320:]
        close = np.array(self._closes)
        spread = close * 0.0015
        high = close + self._rng.uniform(0, spread)
        low = close - self._rng.uniform(0, spread)
        open_ = np.r_[close[0], close[:-1]]
        return pd.DataFrame(
            {
                "open": open_,
                "high": np.maximum.reduce([high, open_, close]),
                "low": np.minimum.reduce([low, open_, close]),
                "close": close,
                "volume": self._rng.uniform(500, 5000, len(close)),
            }
        )

    @property
    def price(self) -> float:
        return float(self._closes[-1])


class FeedEngine:
    """Background thread that publishes signals, trades and risk into AppState."""

    def __init__(self, state: AppState, config: dict, interval: float = 3.0):
        self.state = state
        self.cfg = config
        self.interval = interval
        self.symbols = config.get("symbols", ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
        self.min_ml = float(config.get("min_ml_score", 60.0))

        self.engine = StrategyEngine(config)
        self.extractor = FeatureExtractor()
        self.scorer = SignalScorer()

        starts = {"BTC/USDT": 65000, "ETH/USDT": 3400, "SOL/USDT": 150}
        self._walkers = {
            (sym, tf): _Walker(
                seed=abs(hash((sym, tf))) % 10_000, start=starts.get(sym, 100.0)
            )
            for sym in self.symbols
            for tf in TIMEFRAMES
        }
        self._open: list[dict] = []
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    # ── lifecycle ─────────────────────────────────────────────────────
    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self.state.set_status(
            running=True,
            mode="sandbox",
            exchange=self.cfg.get("exchange", {}).get("id", "binance"),
        )
        self.state.add_event(
            {"type": "INFO", "message": "Feed engine started (sandbox)"}
        )
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self.state.set_status(running=False)
        self.state.add_event({"type": "WARN", "message": "Feed engine stopped"})

    # ── main loop ─────────────────────────────────────────────────────
    def _loop(self):
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception as e:  # never let the feed thread die silently
                self.state.add_event({"type": "WARN", "message": f"Feed error: {e}"})
            self._stop.wait(self.interval)

    def _tick(self):
        for sym in self.symbols:
            price = self._walkers[(sym, "1h")].price
            for tf in TIMEFRAMES:
                df = self._walkers[(sym, tf)].step()
                res = self.engine.run_all(df)
                direction = res["direction"]
                conf = res["confluence"]
                ml = 0.0
                if direction != SIGNAL_NONE:
                    feats = self.extractor.extract(df)
                    ml = self.scorer.score(feats, direction, conf)
                self.state.update_signal(
                    sym,
                    tf,
                    {
                        "direction": _DIR_NAME[direction],
                        "confluence": round(conf, 1),
                        "ml_score": round(ml, 1),
                        "votes_buy": res["votes_buy"],
                        "votes_sell": res["votes_sell"],
                        "total": res["total"],
                        "probability": (
                            round(ml * 0.7 + res.get("win_rate", 55) * 0.3, 1)
                            if ml
                            else 0.0
                        ),
                        "price": round(price, 2),
                    },
                )
            self._maybe_open(sym, price)
        self._manage_open()
        self._publish_risk()

    # ── trade simulation ──────────────────────────────────────────────
    def _maybe_open(self, sym: str, price: float):
        sig = self.state.signals.get(sym, {}).get("1h", {})
        if sig.get("direction") not in ("BUY", "SELL"):
            return
        if sig.get("ml_score", 0) < self.min_ml:
            return
        if any(t["symbol"] == sym for t in self._open):
            return
        if len(self._open) >= self.cfg.get("risk", {}).get("max_total_orders", 10):
            return
        side = sig["direction"]
        sl_pct, tp_pct = 0.015, 0.03
        sl = price * (1 - sl_pct) if side == "BUY" else price * (1 + sl_pct)
        tp = price * (1 + tp_pct) if side == "BUY" else price * (1 - tp_pct)
        trade = {
            "id": uuid.uuid4().hex[:8],
            "symbol": sym,
            "side": side,
            "entry": round(price, 2),
            "sl": round(sl, 2),
            "tp": round(tp, 2),
            "lot": round(self.cfg.get("risk", {}).get("max_lot_size", 1.0) * 0.5, 4),
            "ml_score": sig["ml_score"],
            "confluence": sig["confluence"],
            "trail": self.cfg.get("trail_stop", {}).get("type", "atr"),
            "opened_at": time.time(),
        }
        self._open.append(trade)
        self.state.add_event(
            {
                "type": "ENTRY",
                "symbol": sym,
                "message": f"{side} {sym} @ {trade['entry']} (ML {sig['ml_score']}%)",
            }
        )

    def _manage_open(self):
        still: list[dict] = []
        for t in self._open:
            price = self._walkers[(t["symbol"], "1h")].price
            t["price"] = round(price, 2)
            if t["side"] == "BUY":
                t["pnl"] = round((price - t["entry"]) * t["lot"], 2)
                hit_tp, hit_sl = price >= t["tp"], price <= t["sl"]
                t["sl"] = round(max(t["sl"], price * 0.985), 2)  # percent trail
            else:
                t["pnl"] = round((t["entry"] - price) * t["lot"], 2)
                hit_tp, hit_sl = price <= t["tp"], price >= t["sl"]
                t["sl"] = round(min(t["sl"], price * 1.015), 2)
            if hit_tp or hit_sl:
                reason = "tp" if hit_tp else "sl"
                closed = {**t, "exit": round(price, 2), "reason": reason}
                self.state.add_closed_trade(closed)
                self.state.add_event(
                    {
                        "type": "EXIT_WIN" if t["pnl"] >= 0 else "EXIT_LOSS",
                        "symbol": t["symbol"],
                        "message": f"Closed {t['symbol']} ({reason.upper()}) PnL ${t['pnl']:+.2f}",
                    }
                )
            else:
                still.append(t)
        self._open = still
        self.state.set_open_trades(self._open)

    def _publish_risk(self):
        risk_cfg = self.cfg.get("risk", {})
        exposure = sum(abs(t.get("entry", 0) * t.get("lot", 0)) for t in self._open)
        eq = list(self.state.equity_curve)
        peak = max(eq) if eq else self.state.initial_capital
        dd = (peak - self.state.balance) / max(peak, 1e-9) * 100
        self.state.set_risk(
            {
                "open_positions": len(self._open),
                "max_total_orders": risk_cfg.get("max_total_orders", 10),
                "exposure_usd": round(exposure, 2),
                "max_loss_per_trade": risk_cfg.get("max_loss_per_trade", 50.0),
                "drawdown_pct": round(max(dd, 0.0), 2),
                "trail_type": self.cfg.get("trail_stop", {}).get("type", "atr"),
                "trail_enabled": self.cfg.get("trail_stop", {}).get("enabled", True),
            }
        )

    def confluence_matrix(self) -> dict:
        """26 strategies × symbols heatmap built from the latest tick."""
        rows = []
        for sym in self.symbols:
            df = self._walkers[(sym, "1h")].step()
            per = {}
            for cfg_key, method in self.engine.STRATEGY_MAP.items():
                fn = getattr(self.engine, method, None)
                if fn is None:
                    continue
                try:
                    sig, conf, _ = fn(df)
                    # Strategy methods may return numpy scalars; coerce to
                    # native Python types so the JSON encoder can serialize them.
                    per[cfg_key] = {
                        "signal": _DIR_NAME[int(sig)],
                        "confidence": round(float(conf), 1),
                    }
                except Exception:
                    per[cfg_key] = {"signal": "FLAT", "confidence": 0.0}
            rows.append({"symbol": sym, "strategies": per})
        return {"strategies": list(self.engine.STRATEGY_MAP.keys()), "rows": rows}
