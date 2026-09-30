"""
DeltaForge - Price Action strategies.
"""

from typing import Tuple

import pandas as pd

from ..indicators import SIGNAL_BUY, SIGNAL_NONE, SIGNAL_SELL, _atr, _pivot_points


class PriceActionStrategies:
    """Mixin - composed into StrategyEngine."""

    def fibonacci(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        swing_h = df["high"].iloc[-50:].max()
        swing_l = df["low"].iloc[-50:].min()
        r = swing_h - swing_l
        if r == 0:
            return SIGNAL_NONE, 0, ""
        close = df["close"].iloc[-1]
        tol = r * 0.015
        f618 = swing_h - r * 0.618
        f500 = swing_h - r * 0.500
        f382 = swing_h - r * 0.382
        if abs(close - f618) < tol:
            return SIGNAL_BUY, 82, f"Fib 61.8% support at {f618:.4f}"
        if abs(close - f500) < tol and close < f618:
            return SIGNAL_BUY, 75, f"Fib 50% support at {f500:.4f}"
        if abs(close - f382) < tol and close > f500:
            return SIGNAL_SELL, 72, f"Fib 38.2% resistance at {f382:.4f}"
        return SIGNAL_NONE, 0, ""

    # ─────────────────────────────────────────────────────────────────
    # 14. PIVOT POINTS
    # ─────────────────────────────────────────────────────────────────

    def pivot_points(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        pivot, r1, s1, r2, s2 = _pivot_points(df)
        close = df["close"].iloc[-1]
        p = pivot.iloc[-1]
        r1v = r1.iloc[-1]
        s1v = s1.iloc[-1]
        atr = _atr(df).iloc[-1]
        tol = atr * 0.3
        if abs(close - s1v) < tol and close > s1v:
            return SIGNAL_BUY, 70, f"Bounced off S1 {s1v:.4f}"
        if abs(close - r1v) < tol and close < r1v:
            return SIGNAL_SELL, 70, f"Rejected at R1 {r1v:.4f}"
        if close > p and abs(close - p) < tol:
            return SIGNAL_BUY, 60, f"Crossed above Pivot {p:.4f}"
        if close < p and abs(close - p) < tol:
            return SIGNAL_SELL, 60, f"Crossed below Pivot {p:.4f}"
        return SIGNAL_NONE, 0, ""

    # ─────────────────────────────────────────────────────────────────
    # 15. SUPPORT & RESISTANCE ZONES
    # ─────────────────────────────────────────────────────────────────

    def support_resistance(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        close = df["close"].iloc[-1]
        atr = _atr(df).iloc[-1]
        highs = df["high"].iloc[-100:]
        lows = df["low"].iloc[-100:]
        support_touches = ((lows - close).abs() < atr * 0.5).sum()
        resistance_touches = ((highs - close).abs() < atr * 0.5).sum()
        if support_touches >= 3:
            return (
                SIGNAL_BUY,
                min(100, support_touches * 15),
                f"At support zone ({support_touches} touches)",
            )
        if resistance_touches >= 3:
            return (
                SIGNAL_SELL,
                min(100, resistance_touches * 15),
                f"At resistance zone ({resistance_touches} touches)",
            )
        return SIGNAL_NONE, 0, ""

    # ─────────────────────────────────────────────────────────────────
    # 16. ICHIMOKU
    # ─────────────────────────────────────────────────────────────────
