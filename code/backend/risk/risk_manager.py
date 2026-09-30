"""DeltaForge - Unified RiskManager (re-exports sub-components)."""

import logging
import time
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

from .trail_engine import TrailState

logger = logging.getLogger("DeltaForge.Risk")


class RiskManager:
    """
    Central risk gate for all trade decisions.
    All limits dynamically configurable via config dict.
    """

    def __init__(self, config: dict):
        self.cfg = config
        self.risk_cfg = config.get("risk", {})
        self.trail_cfg = config.get("trail_stop", {})
        self._trail_states: Dict[str, TrailState] = {}

        # Session metrics for risk dashboard
        self._session_high_equity: float = config.get("initial_capital", 10000.0)
        self._session_equity: float = config.get("initial_capital", 10000.0)
        self._peak_equity: float = config.get("initial_capital", 10000.0)
        self._max_drawdown: float = 0.0

    # ─────────────────────────────────────────────────────────────
    # DYNAMIC CONFIG RELOAD
    # ─────────────────────────────────────────────────────────────
    def reload(self, new_config: dict):
        self.cfg = new_config
        self.risk_cfg = new_config.get("risk", {})
        self.trail_cfg = new_config.get("trail_stop", {})
        logger.info("RiskManager config reloaded")

    # ─────────────────────────────────────────────────────────────
    # GATE: CAN WE PLACE A NEW ORDER?
    # ─────────────────────────────────────────────────────────────
    def can_place_order(
        self, open_orders: list, open_positions: list, symbol: str, side: str
    ) -> Tuple[bool, str]:
        r = self.risk_cfg

        total = len(open_orders) + len(open_positions)
        max_total = r.get("max_total_orders", 10)
        if total >= max_total:
            return False, f"Max total orders reached ({max_total})"

        pair_orders = [
            o
            for o in open_orders + open_positions
            if o.get("symbol", "").replace("/", "").replace("-", "").upper()
            == symbol.replace("/", "").replace("-", "").upper()
        ]
        max_pair = r.get("max_orders_per_pair", 2)
        if len(pair_orders) >= max_pair:
            return False, f"Max orders on {symbol} reached ({max_pair})"

        if side == "buy":
            buy_orders = [
                o for o in open_orders + open_positions if o.get("side", "") == "buy"
            ]
            if len(buy_orders) >= r.get("max_buy_orders", 5):
                return False, f"Max buy orders reached ({r.get('max_buy_orders', 5)})"
        elif side == "sell":
            sell_orders = [
                o for o in open_orders + open_positions if o.get("side", "") == "sell"
            ]
            if len(sell_orders) >= r.get("max_sell_orders", 5):
                return False, f"Max sell orders reached ({r.get('max_sell_orders', 5)})"

        return True, "OK"

    # ─────────────────────────────────────────────────────────────
    # POSITION SIZE
    # ─────────────────────────────────────────────────────────────
    def calculate_position_size(
        self,
        balance_usdt: float,
        entry_price: float,
        sl_price: float,
        symbol: str = "BTC/USDT",
    ) -> Tuple[float, float]:
        r = self.risk_cfg
        risk_pct = r.get("risk_percent", 1.0) / 100.0
        max_dollar = r.get("max_loss_per_trade", 50.0)
        max_dollar_amt = r.get("max_dollar_amount_crypto", 10000.0)

        dollar_risk = min(balance_usdt * risk_pct, max_dollar)

        sl_dist_pct = abs(entry_price - sl_price) / entry_price
        if sl_dist_pct == 0:
            logger.warning("SL == entry price, using 1% SL distance")
            sl_dist_pct = 0.01

        position_usdt = min(dollar_risk / sl_dist_pct, max_dollar_amt)
        amount_base = position_usdt / entry_price

        logger.debug(
            f"Position size: ${position_usdt:.2f} | "
            f"{amount_base:.6f} base | Risk: ${dollar_risk:.2f}"
        )
        return amount_base, dollar_risk

    # ─────────────────────────────────────────────────────────────
    # SL / TP CALCULATION
    # ─────────────────────────────────────────────────────────────
    def calculate_sl_tp(
        self, df: pd.DataFrame, side: str, entry_price: float, bt_win_rate: float = 0.0
    ) -> Tuple[float, float]:
        """
        Calculate SL and TP from ATR + optional backtested win-rate adjustment.
        bt_win_rate: 0-100. If > 0, adjust ATR multiplier based on backtested edge.
        Returns (sl_price, tp_price)
        """
        atr_mult = self.trail_cfg.get("atr_multiplier", 2.0)
        rr_ratio = self.risk_cfg.get("tp_rr_ratio", 2.0)
        tp_on = self.risk_cfg.get("take_profit_enabled", True)

        # Widen SL when backtested win rate is high (trade has strong edge)
        if bt_win_rate >= 60:
            atr_mult *= 1 + (bt_win_rate - 60) / 200  # up to ~1.2× at 100%
        elif bt_win_rate > 0 and bt_win_rate < 50:
            atr_mult *= 0.85  # tighten on weak edge

        atr = self._compute_atr(df)

        if side == "buy":
            sl = entry_price - atr * atr_mult
            tp = entry_price + atr * atr_mult * rr_ratio if tp_on else 0
        else:
            sl = entry_price + atr * atr_mult
            tp = entry_price - atr * atr_mult * rr_ratio if tp_on else 0

        sl, tp = self._adjust_to_sr_levels(df, side, entry_price, sl, tp, atr)
        return round(sl, 8), round(tp, 8) if tp else 0

    def _adjust_to_sr_levels(self, df, side, entry, sl, tp, atr):
        highs = df["high"].iloc[-50:]
        lows = df["low"].iloc[-50:]

        if side == "buy":
            supports = lows[(lows < entry) & (lows > entry - 3 * atr)]
            if not supports.empty:
                best_sl = supports.max()
                if best_sl < entry:
                    sl = min(sl, best_sl - atr * 0.1)
            if tp > 0:
                resistances = highs[(highs > entry) & (highs < entry + 6 * atr)]
                if not resistances.empty:
                    best_tp = resistances.min()
                    if best_tp > entry:
                        tp = max(tp, best_tp - atr * 0.1)
        else:
            supports = highs[(highs > entry) & (highs < entry + 3 * atr)]
            if not supports.empty:
                best_sl = supports.min()
                if best_sl > entry:
                    sl = max(sl, best_sl + atr * 0.1)
            if tp > 0:
                resistances = lows[(lows < entry) & (lows > entry - 6 * atr)]
                if not resistances.empty:
                    best_tp = resistances.max()
                    if best_tp < entry:
                        tp = min(tp, best_tp + atr * 0.1)
        return sl, tp

    # ─────────────────────────────────────────────────────────────
    # TRAIL STOP ENGINE
    # ─────────────────────────────────────────────────────────────
    def register_trade(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        sl_price: float,
        amount: float,
        sl_order_id: str = "",
    ):
        state = TrailState(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            current_sl=sl_price,
            peak_price=entry_price,
            amount=amount,
            sl_order_id=sl_order_id,
        )
        key = f"{symbol}_{side}_{entry_price}"
        self._trail_states[key] = state
        logger.info(
            f"Trail registered: {symbol} {side} @ {entry_price} | SL {sl_price}"
        )

    def update_trail_stops(
        self, current_prices: Dict[str, float], df_map: Dict[str, pd.DataFrame]
    ) -> Dict[str, Tuple[float, float]]:
        """
        Returns dict of {trade_key: (old_sl, new_sl)} for trades needing SL update.
        """
        if not self.trail_cfg.get("enabled", True):
            return {}

        trail_type = self.trail_cfg.get("type", "atr")
        updates = {}

        for key, state in list(self._trail_states.items()):
            sym = state.symbol
            price = current_prices.get(sym)
            if price is None:
                continue

            df = df_map.get(sym)
            atr = self._compute_atr(df) if df is not None else 0

            if state.side == "buy" and price > state.peak_price:
                state.peak_price = price
            if state.side == "sell" and price < state.peak_price:
                state.peak_price = price

            new_sl = self._compute_new_sl(state, price, atr, trail_type)
            if new_sl is None:
                continue

            should_update = (
                state.side == "buy" and new_sl > state.current_sl and new_sl < price
            ) or (state.side == "sell" and new_sl < state.current_sl and new_sl > price)

            if should_update:
                old_sl = state.current_sl
                state.current_sl = new_sl
                updates[key] = (old_sl, new_sl)
                logger.debug(f"Trail update {sym}: SL {old_sl:.6f} → {new_sl:.6f}")

        return updates

    def _compute_new_sl(
        self, state: TrailState, price: float, atr: float, trail_type: str
    ) -> Optional[float]:
        t = self.trail_cfg

        if trail_type == "atr":
            mult = t.get("atr_multiplier", 2.0)
            if atr == 0:
                return None
            return price - atr * mult if state.side == "buy" else price + atr * mult

        elif trail_type == "percent":
            pct = t.get("percent", 1.5) / 100.0
            return price * (1 - pct) if state.side == "buy" else price * (1 + pct)

        elif trail_type == "dollar":
            dollar = t.get("dollar", 30.0)
            return price - dollar if state.side == "buy" else price + dollar

        elif trail_type == "time":
            elapsed = time.time() - state.entry_time
            max_time = t.get("time_minutes", 60) * 60
            tighten = min(1.0, elapsed / max_time)
            base_dist = atr * t.get("atr_multiplier", 2.0) * (1 - tighten * 0.5)
            if atr == 0:
                return None
            return price - base_dist if state.side == "buy" else price + base_dist

        elif trail_type == "volatility":
            if atr == 0:
                return None
            vol_mult = t.get("volatility_atr_mult", 1.5)
            return (
                price - atr * vol_mult
                if state.side == "buy"
                else price + atr * vol_mult
            )

        return None

    def remove_trade(self, key: str):
        self._trail_states.pop(key, None)

    def get_all_trail_states(self) -> Dict[str, TrailState]:
        return self._trail_states

    # ─────────────────────────────────────────────────────────────
    # DOLLAR RISK VALIDATION
    # ─────────────────────────────────────────────────────────────
    def validate_dollar_risk(
        self, entry_price: float, sl_price: float, amount: float
    ) -> Tuple[bool, float]:
        max_loss = self.risk_cfg.get("max_loss_per_trade", 50.0)
        sl_dist = abs(entry_price - sl_price)
        dollar_risk = sl_dist * amount
        ok = dollar_risk <= max_loss
        if not ok:
            logger.warning(
                f"Dollar risk ${dollar_risk:.2f} exceeds max ${max_loss:.2f}"
            )
        return ok, dollar_risk

    # ─────────────────────────────────────────────────────────────
    # RISK SUMMARY  (for display Risk Dashboard panel)
    # ─────────────────────────────────────────────────────────────
    def get_risk_summary(
        self, live_trades: list, current_prices: Dict[str, float], session_pnl: float
    ) -> dict:
        """
        Build a risk summary dict consumed by DeltaForgeDisplay.
        live_trades: list of LiveTrade dataclass instances.
        """
        open_count = len(live_trades)
        total_exposure = 0.0
        unrealized_pnl = 0.0
        max_single_risk = 0.0
        ml_scores = []

        for t in live_trades:
            sym = getattr(t, "symbol", "")
            price = current_prices.get(sym, getattr(t, "entry_price", 0))
            amt = getattr(t, "amount", 0)
            entry = getattr(t, "entry_price", 0)
            sl = getattr(t, "current_sl", getattr(t, "sl", 0))
            side = getattr(t, "side", "buy")
            ml = getattr(t, "ml_score", 0)

            total_exposure += price * amt
            if side == "buy":
                unrealized_pnl += (price - entry) * amt
                max_single_risk = max(max_single_risk, abs(entry - sl) * amt)
            else:
                unrealized_pnl += (entry - price) * amt
                max_single_risk = max(max_single_risk, abs(sl - entry) * amt)
            if ml > 0:
                ml_scores.append(ml)

        avg_ml = float(np.mean(ml_scores)) if ml_scores else 0.0

        # Update session drawdown tracker
        self._session_equity += session_pnl
        if self._session_equity > self._peak_equity:
            self._peak_equity = self._session_equity
        dd = (
            (self._peak_equity - self._session_equity) / max(self._peak_equity, 1) * 100
        )
        self._max_drawdown = max(self._max_drawdown, dd)

        return {
            "open_positions": open_count,
            "total_exposure": round(total_exposure, 2),
            "unrealized_pnl": round(unrealized_pnl, 4),
            "max_single_risk": round(max_single_risk, 2),
            "avg_ml_score": round(avg_ml, 1),
            "session_drawdown": round(self._max_drawdown, 2),
        }

    # ─────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────
    def _compute_atr(self, df: Optional[pd.DataFrame], period: int = 14) -> float:
        if df is None or len(df) < period + 1:
            return 0.0
        hl = df["high"] - df["low"]
        hc = (df["high"] - df["close"].shift()).abs()
        lc = (df["low"] - df["close"].shift()).abs()
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        return float(tr.rolling(period).mean().iloc[-1])

    def max_dollar_crypto(self) -> float:
        return self.risk_cfg.get("max_dollar_amount_crypto", 10000.0)

    def trail_enabled(self) -> bool:
        return self.trail_cfg.get("enabled", True)

    def tp_enabled(self) -> bool:
        return self.risk_cfg.get("take_profit_enabled", True)
