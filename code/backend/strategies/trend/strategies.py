"""
DeltaForge — Trend strategies.
"""

from typing import Tuple

import numpy as np
import pandas as pd

from ..indicators import (
    SIGNAL_BUY,
    SIGNAL_NONE,
    SIGNAL_SELL,
    _adx,
    _ema,
    _ichimoku,
    _macd,
    _sma,
)


class TrendStrategies:
    """Mixin — composed into StrategyEngine."""

    def ma_cross(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        fast = _sma(df["close"], 10)
        slow = _sma(df["close"], 50)
        if fast.iloc[-2] < slow.iloc[-2] and fast.iloc[-1] > slow.iloc[-1]:
            return SIGNAL_BUY, 80, "MA10 crossed above MA50"
        if fast.iloc[-2] > slow.iloc[-2] and fast.iloc[-1] < slow.iloc[-1]:
            return SIGNAL_SELL, 80, "MA10 crossed below MA50"
        return SIGNAL_NONE, 0, ""

    # ─────────────────────────────────────────────────────────────────
    # 2. EMA TREND (20/50/200 alignment)
    # ─────────────────────────────────────────────────────────────────

    def ema_trend(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        if len(df) < 200:
            return SIGNAL_NONE, 0, "Insufficient data"
        e20 = _ema(df["close"], 20).iloc[-1]
        e50 = _ema(df["close"], 50).iloc[-1]
        e200 = _ema(df["close"], 200).iloc[-1]
        p = df["close"].iloc[-1]
        if p > e20 > e50 > e200:
            return SIGNAL_BUY, 75, "Full bullish EMA stack"
        if p < e20 < e50 < e200:
            return SIGNAL_SELL, 75, "Full bearish EMA stack"
        return SIGNAL_NONE, 0, ""

    # ─────────────────────────────────────────────────────────────────
    # 3. MACD
    # ─────────────────────────────────────────────────────────────────

    def macd_strategy(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        macd, sig, hist = _macd(df["close"])
        if macd.iloc[-2] < sig.iloc[-2] and macd.iloc[-1] > sig.iloc[-1]:
            conf = min(100, abs(hist.iloc[-1]) / df["close"].iloc[-1] * 10000)
            return SIGNAL_BUY, conf, "MACD crossed above signal"
        if macd.iloc[-2] > sig.iloc[-2] and macd.iloc[-1] < sig.iloc[-1]:
            conf = min(100, abs(hist.iloc[-1]) / df["close"].iloc[-1] * 10000)
            return SIGNAL_SELL, conf, "MACD crossed below signal"
        return SIGNAL_NONE, 0, ""

    # ─────────────────────────────────────────────────────────────────
    # 4. ADX FILTER
    # ─────────────────────────────────────────────────────────────────

    def adx_filter(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        adx, pos_di, neg_di = _adx(df)
        a = adx.iloc[-1]
        p = pos_di.iloc[-1]
        n = neg_di.iloc[-1]
        if pd.isna(a):
            return SIGNAL_NONE, 0, ""
        if a > 25 and p > n:
            return SIGNAL_BUY, a, f"ADX {a:.1f} strong uptrend"
        if a > 25 and n > p:
            return SIGNAL_SELL, a, f"ADX {a:.1f} strong downtrend"
        return SIGNAL_NONE, 0, f"ADX {a:.1f} - no trend"

    # ─────────────────────────────────────────────────────────────────
    # 5. PARABOLIC SAR
    # ─────────────────────────────────────────────────────────────────

    def parabolic_sar(
        self, df: pd.DataFrame, af_start=0.02, af_max=0.2
    ) -> Tuple[int, float, str]:
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values
        n = len(close)
        sar = np.zeros(n)
        ep = np.zeros(n)
        bull = True
        af = af_start
        sar[0] = low[0]
        ep[0] = high[0]

        for i in range(1, n):
            sar[i] = sar[i - 1] + af * (ep[i - 1] - sar[i - 1])
            if bull:
                sar[i] = min(sar[i], low[i - 1], low[max(0, i - 2)])
                if low[i] < sar[i]:
                    bull = False
                    sar[i] = ep[i - 1]
                    ep[i] = low[i]
                    af = af_start
                else:
                    if high[i] > ep[i - 1]:
                        ep[i] = high[i]
                        af = min(af + af_start, af_max)
                    else:
                        ep[i] = ep[i - 1]
            else:
                sar[i] = max(sar[i], high[i - 1], high[max(0, i - 2)])
                if high[i] > sar[i]:
                    bull = True
                    sar[i] = ep[i - 1]
                    ep[i] = high[i]
                    af = af_start
                else:
                    if low[i] < ep[i - 1]:
                        ep[i] = low[i]
                        af = min(af + af_start, af_max)
                    else:
                        ep[i] = ep[i - 1]

        prev_bull = close[-2] > sar[-2]
        curr_bull = close[-1] > sar[-1]
        if not prev_bull and curr_bull:
            return SIGNAL_BUY, 78, "SAR flipped bullish"
        if prev_bull and not curr_bull:
            return SIGNAL_SELL, 78, "SAR flipped bearish"
        return SIGNAL_NONE, 0, ""

    # ─────────────────────────────────────────────────────────────────
    # 6. RSI
    # ─────────────────────────────────────────────────────────────────

    def ichimoku(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        if len(df) < 60:
            return SIGNAL_NONE, 0, "Insufficient data"
        ten, kij, spa, spb = _ichimoku(df)
        close = df["close"].iloc[-1]
        t1 = ten.iloc[-1]
        k1 = kij.iloc[-1]
        a1 = spa.iloc[-1]
        b1 = spb.iloc[-1]
        if pd.isna(a1) or pd.isna(b1):
            return SIGNAL_NONE, 0, ""
        cloud_top = max(a1, b1)
        cloud_bot = min(a1, b1)
        if close > cloud_top and t1 > k1:
            return SIGNAL_BUY, 82, "Price above cloud, TK bullish"
        if close < cloud_bot and t1 < k1:
            return SIGNAL_SELL, 82, "Price below cloud, TK bearish"
        return SIGNAL_NONE, 0, "Price inside cloud"

    # ─────────────────────────────────────────────────────────────────
    # 17. BREAKOUT (range high/low)
    # ─────────────────────────────────────────────────────────────────

    def trendline(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        e50 = _ema(df["close"], 50)
        close = df["close"]
        if close.iloc[-2] < e50.iloc[-2] and close.iloc[-1] > e50.iloc[-1]:
            return SIGNAL_BUY, 70, "Price crossed above EMA50 trendline"
        if close.iloc[-2] > e50.iloc[-2] and close.iloc[-1] < e50.iloc[-1]:
            return SIGNAL_SELL, 70, "Price crossed below EMA50 trendline"
        return SIGNAL_NONE, 0, ""

    # ─────────────────────────────────────────────────────────────────
    # 19. VOLUME BREAKOUT
    # ─────────────────────────────────────────────────────────────────
