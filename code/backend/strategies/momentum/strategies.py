"""
DeltaForge — Momentum strategies.
"""

from typing import Tuple

import pandas as pd

from ..indicators import (
    SIGNAL_BUY,
    SIGNAL_NONE,
    SIGNAL_SELL,
    _bollinger,
    _rsi,
    _stochastic,
)


class MomentumStrategies:
    """Mixin — composed into StrategyEngine."""

    def rsi_strategy(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        rsi = _rsi(df["close"])
        r1 = rsi.iloc[-1]
        r2 = rsi.iloc[-2]
        if r2 < 30 and r1 >= 30:
            return SIGNAL_BUY, 80, f"RSI {r1:.1f} oversold bounce"
        if r2 > 70 and r1 <= 70:
            return SIGNAL_SELL, 80, f"RSI {r1:.1f} overbought fade"
        return SIGNAL_NONE, 0, f"RSI {r1:.1f}"

    # ─────────────────────────────────────────────────────────────────
    # 7. STOCHASTIC
    # ─────────────────────────────────────────────────────────────────

    def stochastic(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        k, d = _stochastic(df)
        k1, k2 = k.iloc[-1], k.iloc[-2]
        d1, d2 = d.iloc[-1], d.iloc[-2]
        if k1 < 20 and d1 < 20 and k2 < d2 and k1 > d1:
            return SIGNAL_BUY, 75, f"Stoch {k1:.1f} oversold cross"
        if k1 > 80 and d1 > 80 and k2 > d2 and k1 < d1:
            return SIGNAL_SELL, 75, f"Stoch {k1:.1f} overbought cross"
        return SIGNAL_NONE, 0, ""

    # ─────────────────────────────────────────────────────────────────
    # 8. MOMENTUM
    # ─────────────────────────────────────────────────────────────────

    def momentum(self, df: pd.DataFrame, period: int = 14) -> Tuple[int, float, str]:
        mom = df["close"] / df["close"].shift(period) * 100
        m1, m2 = mom.iloc[-1], mom.iloc[-2]
        if m2 < 100 and m1 >= 100:
            return SIGNAL_BUY, 70, "Momentum crossed above 100"
        if m2 > 100 and m1 <= 100:
            return SIGNAL_SELL, 70, "Momentum crossed below 100"
        return SIGNAL_NONE, 0, ""

    # ─────────────────────────────────────────────────────────────────
    # 9. BOLLINGER BANDS REVERSAL
    # ─────────────────────────────────────────────────────────────────

    def bollinger_bands(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        upper, mid, lower = _bollinger(df["close"])
        c1 = df["close"].iloc[-1]
        c2 = df["close"].iloc[-2]
        u1 = upper.iloc[-1]
        l1 = lower.iloc[-1]
        if c2 <= lower.iloc[-2] and c1 > l1:
            return SIGNAL_BUY, 72, "BB oversold bounce"
        if c2 >= upper.iloc[-2] and c1 < u1:
            return SIGNAL_SELL, 72, "BB overbought fade"
        band_width = (u1 - l1) / mid.iloc[-1] * 100
        if band_width < 2.0:
            if c1 > mid.iloc[-1]:
                return SIGNAL_BUY, 60, "BB squeeze breakout up"
            elif c1 < mid.iloc[-1]:
                return SIGNAL_SELL, 60, "BB squeeze breakout down"
        return SIGNAL_NONE, 0, ""

    # ─────────────────────────────────────────────────────────────────
    # 10. ATR BREAKOUT
    # ─────────────────────────────────────────────────────────────────
