"""
DeltaForge - Volume strategies.
"""

from typing import Tuple

import pandas as pd

from ..indicators import (
    SIGNAL_BUY,
    SIGNAL_NONE,
    SIGNAL_SELL,
    _ad_line,
    _chaikin_mf,
    _ema,
)


class VolumeStrategies:
    """Mixin - composed into StrategyEngine."""

    def accum_dist(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        ad = _ad_line(df)
        ad_e = _ema(ad, 10)
        if ad_e.iloc[-1] > ad_e.iloc[-2] > ad_e.iloc[-3]:
            return SIGNAL_BUY, 65, "A/D rising - accumulation"
        if ad_e.iloc[-1] < ad_e.iloc[-2] < ad_e.iloc[-3]:
            return SIGNAL_SELL, 65, "A/D falling - distribution"
        return SIGNAL_NONE, 0, ""

    # ─────────────────────────────────────────────────────────────────
    # 12. CHAIKIN MONEY FLOW
    # ─────────────────────────────────────────────────────────────────

    def chaikin_mf(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        cmf = _chaikin_mf(df).iloc[-1]
        if cmf > 0.05:
            return SIGNAL_BUY, min(100, cmf * 500), f"CMF {cmf:.3f} bullish"
        if cmf < -0.05:
            return SIGNAL_SELL, min(100, abs(cmf) * 500), f"CMF {cmf:.3f} bearish"
        return SIGNAL_NONE, 0, f"CMF {cmf:.3f} neutral"

    # ─────────────────────────────────────────────────────────────────
    # 13. FIBONACCI RETRACEMENT
    # ─────────────────────────────────────────────────────────────────

    def volume_breakout(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        avg_vol = df["volume"].iloc[-21:-1].mean()
        cur_vol = df["volume"].iloc[-1]
        close = df["close"].iloc[-1]
        prev = df["close"].iloc[-2]
        ratio = cur_vol / avg_vol if avg_vol > 0 else 0
        if ratio >= 1.8:
            conf = min(100, ratio * 30)
            if close > prev:
                return SIGNAL_BUY, conf, f"Volume surge {ratio:.1f}x bullish"
            else:
                return SIGNAL_SELL, conf, f"Volume surge {ratio:.1f}x bearish"
        return SIGNAL_NONE, 0, f"Normal volume {ratio:.1f}x"

    # ─────────────────────────────────────────────────────────────────
    # 20. PULLBACK TRADING
    # ─────────────────────────────────────────────────────────────────

    def pullback(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        e50 = _ema(df["close"], 50).iloc[-1]
        e200 = _ema(df["close"], 200).iloc[-1] if len(df) >= 200 else e50
        close = df["close"].iloc[-1]
        tol = e50 * 0.002
        if e50 > e200 and abs(close - e50) < tol:
            return SIGNAL_BUY, 75, "Pullback to EMA50 in uptrend"
        if e50 < e200 and abs(close - e50) < tol:
            return SIGNAL_SELL, 75, "Pullback to EMA50 in downtrend"
        return SIGNAL_NONE, 0, ""

    # ─────────────────────────────────────────────────────────────────
    # 21. SMART MONEY CONCEPTS (Fair Value Gaps + Order Blocks)
    # ─────────────────────────────────────────────────────────────────
