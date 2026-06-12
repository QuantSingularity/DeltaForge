"""
DeltaForge — Volatility strategies.
"""

from typing import Tuple

import pandas as pd

from ..indicators import SIGNAL_BUY, SIGNAL_NONE, SIGNAL_SELL, _atr


class VolatilityStrategies:
    """Mixin — composed into StrategyEngine."""

    def atr_breakout(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        atr = _atr(df).iloc[-1]
        close = df["close"].iloc[-1]
        high20 = df["high"].iloc[-21:-1].max()
        low20 = df["low"].iloc[-21:-1].min()
        if close > high20 + atr * 0.5:
            return SIGNAL_BUY, 78, f"ATR breakout above {high20:.4f}"
        if close < low20 - atr * 0.5:
            return SIGNAL_SELL, 78, f"ATR breakdown below {low20:.4f}"
        return SIGNAL_NONE, 0, ""

    # ─────────────────────────────────────────────────────────────────
    # 11. ACCUMULATION / DISTRIBUTION
    # ─────────────────────────────────────────────────────────────────

    def breakout(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        atr = _atr(df).iloc[-1]
        close = df["close"].iloc[-1]
        high20 = df["high"].iloc[-21:-1].max()
        low20 = df["low"].iloc[-21:-1].min()
        if close > high20 + atr * 0.3:
            return SIGNAL_BUY, 85, "20-bar range breakout up"
        if close < low20 - atr * 0.3:
            return SIGNAL_SELL, 85, "20-bar range breakdown"
        return SIGNAL_NONE, 0, ""

    # ─────────────────────────────────────────────────────────────────
    # 18. TRENDLINE (EMA50 as proxy)
    # ─────────────────────────────────────────────────────────────────
