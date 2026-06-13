"""DeltaForge — Trail Stop Engine (ATR/percent/dollar/time/volatility)."""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import pandas as pd

logger = logging.getLogger("DeltaForge.TrailEngine")


@dataclass
class TrailState:
    symbol: str
    side: str  # 'buy' | 'sell'
    entry_price: float
    current_sl: float
    peak_price: float
    entry_time: float = field(default_factory=time.time)
    sl_order_id: str = ""
    amount: float = 0.0


class TrailEngine:
    """Manages trailing stop state for all open positions."""

    def __init__(self, trail_cfg: dict):
        self.trail_cfg = trail_cfg
        self._states: Dict[str, TrailState] = {}

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
        self._states[key] = state
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

        for key, state in list(self._states.items()):
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
                logger.debug(f"Trail update {sym}: SL {old_sl:.6f} -> {new_sl:.6f}")

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

    def _compute_atr(self, df: Optional[pd.DataFrame], period: int = 14) -> float:
        """Compute Average True Range over the given DataFrame."""
        if df is None or len(df) < period + 1:
            return 0.0
        hl = df["high"] - df["low"]
        hc = (df["high"] - df["close"].shift()).abs()
        lc = (df["low"] - df["close"].shift()).abs()
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        return float(tr.rolling(period).mean().iloc[-1])

    def remove_trade(self, key: str):
        self._states.pop(key, None)

    def get_all_trail_states(self) -> Dict[str, TrailState]:
        return self._states

    def trail_enabled(self) -> bool:
        return self.trail_cfg.get("enabled", True)
