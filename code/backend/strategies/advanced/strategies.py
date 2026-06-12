"""
DeltaForge — Advanced strategies.
"""

from typing import Tuple

import numpy as np
import pandas as pd

from ..indicators import SIGNAL_BUY, SIGNAL_NONE, SIGNAL_SELL, _atr, _ema, _rsi


class AdvancedStrategies:
    """Mixin — composed into StrategyEngine."""

    def smart_money_concepts(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        close = df["close"].iloc[-1]
        for i in range(3, min(12, len(df) - 1)):
            h_before = df["high"].iloc[-i - 1]
            l_after = df["low"].iloc[-i + 1]
            l_before = df["low"].iloc[-i - 1]
            h_after = df["high"].iloc[-i + 1]
            if l_after > h_before and h_before <= close <= l_after:
                return SIGNAL_BUY, 85, "Bullish FVG zone"
            if h_after < l_before and h_after <= close <= l_before:
                return SIGNAL_SELL, 85, "Bearish FVG zone"
        for i in range(3, min(15, len(df) - 1)):
            body_size = abs(df["close"].iloc[-i] - df["open"].iloc[-i])
            atr = _atr(df).iloc[-1]
            if body_size > atr * 1.5:
                ob_high = df["high"].iloc[-i]
                ob_low = df["low"].iloc[-i]
                if ob_low <= close <= ob_high:
                    if df["close"].iloc[-i] > df["open"].iloc[-i]:
                        return SIGNAL_BUY, 78, "Bullish order block"
                    else:
                        return SIGNAL_SELL, 78, "Bearish order block"
        return SIGNAL_NONE, 0, ""

    # ─────────────────────────────────────────────────────────────────
    # 22. ORDER FLOW / LIQUIDITY SWEEP
    # ─────────────────────────────────────────────────────────────────

    def order_flow(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        atr = _atr(df).iloc[-1]
        high5 = df["high"].iloc[-7:-1].max()
        low5 = df["low"].iloc[-7:-1].min()
        cur_h = df["high"].iloc[-1]
        cur_l = df["low"].iloc[-1]
        close = df["close"].iloc[-1]
        if cur_h > high5 + atr * 0.1 and close < high5:
            return SIGNAL_SELL, 82, f"Liquidity sweep above {high5:.4f}"
        if cur_l < low5 - atr * 0.1 and close > low5:
            return SIGNAL_BUY, 82, f"Liquidity sweep below {low5:.4f}"
        return SIGNAL_NONE, 0, ""

    # ─────────────────────────────────────────────────────────────────
    # 23. MARKET PROFILE (POC approximation)
    # ─────────────────────────────────────────────────────────────────

    def market_profile(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        atr = _atr(df).iloc[-1]
        close = df["close"].iloc[-1]
        last20 = df.iloc[-21:-1]
        poc_bar = last20.loc[last20["volume"].idxmax()]
        poc = (poc_bar["high"] + poc_bar["low"]) / 2
        if close > poc + atr * 0.3:
            return SIGNAL_BUY, 68, f"Price above POC {poc:.4f}"
        if close < poc - atr * 0.3:
            return SIGNAL_SELL, 68, f"Price below POC {poc:.4f}"
        return SIGNAL_NONE, 0, f"Price at POC {poc:.4f}"

    # ─────────────────────────────────────────────────────────────────
    # 24. LUXALGO — RSI Divergence + EMA Confirmation + Volume Filter
    # ─────────────────────────────────────────────────────────────────

    def lux_algo(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        """
        LuxAlgo-style signal: Detects bullish/bearish RSI divergence confirmed
        by EMA trend alignment and volume expansion.

        Bullish divergence: price makes lower low, RSI makes higher low
        Bearish divergence: price makes higher high, RSI makes lower high
        """
        if len(df) < 40:
            return SIGNAL_NONE, 0, "Insufficient data"

        close = df["close"]
        rsi = _rsi(close, 14)
        ema20 = _ema(close, 20)
        ema50 = _ema(close, 50)

        # Average volume for confirmation
        avg_vol = df["volume"].iloc[-21:-1].mean()
        cur_vol = float(df["volume"].iloc[-1])

        # Swing detection using rolling min/max over last 30 bars
        window = min(30, len(df) - 5)
        recent_close = close.iloc[-window:]
        recent_rsi = rsi.iloc[-window:]

        cur_close = float(close.iloc[-1])
        cur_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0

        # Bullish divergence: current price < previous swing low
        # but RSI is higher than it was at that swing low
        prev_price_low = float(recent_close.iloc[:-3].min())
        prev_rsi_low = (
            float(recent_rsi.iloc[:-3].min())
            if not recent_rsi.iloc[:-3].isna().all()
            else 50.0
        )

        # Bearish divergence: current price > previous swing high
        prev_price_high = float(recent_close.iloc[:-3].max())
        prev_rsi_high = (
            float(recent_rsi.iloc[:-3].max())
            if not recent_rsi.iloc[:-3].isna().all()
            else 50.0
        )

        e20_cur = float(ema20.iloc[-1])
        e50_cur = float(ema50.iloc[-1])
        vol_ok = cur_vol > avg_vol * 1.1

        # Bullish divergence: price at/below prior low, RSI higher than it was
        if (
            cur_close <= prev_price_low * 1.003
            and cur_rsi > prev_rsi_low + 3
            and cur_rsi < 45  # in oversold territory
            and e20_cur > e50_cur * 0.998  # not in strong downtrend
            and vol_ok
        ):
            conf = min(90, 55 + (cur_rsi - prev_rsi_low) * 1.5)
            return SIGNAL_BUY, conf, f"LuxAlgo bullish divergence RSI {cur_rsi:.1f}"

        # Bearish divergence: price at/above prior high, RSI lower than it was
        if (
            cur_close >= prev_price_high * 0.997
            and cur_rsi < prev_rsi_high - 3
            and cur_rsi > 55  # in overbought territory
            and e20_cur < e50_cur * 1.002  # not in strong uptrend
            and vol_ok
        ):
            conf = min(90, 55 + (prev_rsi_high - cur_rsi) * 1.5)
            return SIGNAL_SELL, conf, f"LuxAlgo bearish divergence RSI {cur_rsi:.1f}"

        # Secondary: LuxAlgo-style EMA ribbon momentum
        # All 3 EMAs (9, 21, 50) aligned with expanding separation
        e9 = _ema(close, 9)
        e21 = _ema(close, 21)
        if (
            float(e9.iloc[-1]) > float(e21.iloc[-1]) > e20_cur > e50_cur
            and float(e9.iloc[-1]) - float(e9.iloc[-3]) > 0
            and cur_rsi > 50
            and vol_ok
        ):
            return SIGNAL_BUY, 68, "LuxAlgo EMA ribbon bullish momentum"
        if (
            float(e9.iloc[-1]) < float(e21.iloc[-1]) < e20_cur < e50_cur
            and float(e9.iloc[-1]) - float(e9.iloc[-3]) < 0
            and cur_rsi < 50
            and vol_ok
        ):
            return SIGNAL_SELL, 68, "LuxAlgo EMA ribbon bearish momentum"

        return SIGNAL_NONE, 0, ""

    # ─────────────────────────────────────────────────────────────────
    # 25. NEWS MOMENTUM — Impulse + Continuation
    # ─────────────────────────────────────────────────────────────────

    def news_momentum(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        """
        News/event-driven momentum proxy.

        Detects sudden large price impulse candles (body > 1.8× ATR)
        accompanied by exceptional volume (> 2.2× average).
        Trades continuation of that impulse if price has not reversed.
        This approximates news-driven momentum without requiring a live feed.
        """
        if len(df) < 25:
            return SIGNAL_NONE, 0, "Insufficient data"

        atr = float(_atr(df, 14).iloc[-1])
        if atr == 0:
            return SIGNAL_NONE, 0, ""

        avg_vol = float(df["volume"].iloc[-21:-4].mean())
        cur_close = float(df["close"].iloc[-1])

        # Scan last 3 candles for an impulse event
        for offset in range(1, 4):
            idx = -(offset + 1)
            bar = df.iloc[idx]
            body = abs(float(bar["close"]) - float(bar["open"]))
            vol = float(bar["volume"])

            if body < atr * 1.8 or vol < avg_vol * 2.2:
                continue  # Not an impulse candle

            is_bull = float(bar["close"]) > float(bar["open"])
            imp_close = float(bar["close"])

            # Confirm price is still extending (not fully reversed)
            if is_bull:
                if cur_close >= imp_close * 0.995:
                    conf = min(
                        85, 60 + (body / atr - 1.8) * 20 + (vol / avg_vol - 2.2) * 5
                    )
                    return (
                        SIGNAL_BUY,
                        round(conf, 1),
                        f"News impulse BUY body={body/atr:.1f}×ATR vol={vol/avg_vol:.1f}×avg",
                    )
            else:
                if cur_close <= imp_close * 1.005:
                    conf = min(
                        85, 60 + (body / atr - 1.8) * 20 + (vol / avg_vol - 2.2) * 5
                    )
                    return (
                        SIGNAL_SELL,
                        round(conf, 1),
                        f"News impulse SELL body={body/atr:.1f}×ATR vol={vol/avg_vol:.1f}×avg",
                    )

        return SIGNAL_NONE, 0, ""

    # ─────────────────────────────────────────────────────────────────
    # 26. QUANTITATIVE / ALGO — Z-Score Mean Reversion + Half-Kelly
    # ─────────────────────────────────────────────────────────────────

    def quant_algo(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        """
        Quantitative mean-reversion strategy using statistical Z-score.

        Identifies statistically extreme price deviations from their
        rolling mean (Z-score beyond ±1.8σ) that show early signs of
        reversion (Z-score pulling back from extreme).

        Secondary confirmation: Hurst exponent proxy (autocorrelation)
        to ensure the pair exhibits mean-reverting behaviour, not trending.
        """
        if len(df) < 35:
            return SIGNAL_NONE, 0, "Insufficient data"

        close = df["close"]
        period = 20

        mean = close.rolling(period).mean()
        std = close.rolling(period).std().replace(0, np.nan)
        zscore = (close - mean) / std

        z_now = float(zscore.iloc[-1]) if not pd.isna(zscore.iloc[-1]) else 0.0
        z_prev = float(zscore.iloc[-2]) if not pd.isna(zscore.iloc[-2]) else 0.0
        z_prev2 = float(zscore.iloc[-3]) if not pd.isna(zscore.iloc[-3]) else 0.0

        if np.isnan(z_now) or np.isnan(z_prev):
            return SIGNAL_NONE, 0, ""

        # Hurst proxy: negative autocorrelation of returns over 10 bars
        # (mean-reverting series have negative lag-1 autocorrelation)
        returns = close.pct_change().dropna()
        if len(returns) >= 15:
            lag1_corr = returns.iloc[-15:].autocorr(lag=1)
        else:
            lag1_corr = 0.0
        is_mean_reverting = (not np.isnan(lag1_corr)) and lag1_corr < 0.05

        # Entry: Z-score was extreme (beyond ±1.8σ) and is now pulling back
        threshold = 1.8

        # Oversold reversion: Z was deeply negative, now rising back
        if (
            z_prev2 < -threshold
            and z_prev < -threshold
            and z_now > z_prev
            and is_mean_reverting
        ):
            conf = min(88, 50 + abs(z_prev) * 15)
            return (
                SIGNAL_BUY,
                round(conf, 1),
                f"Quant Z={z_prev:.2f}σ oversold reversion (HE={lag1_corr:.2f})",
            )

        # Overbought reversion: Z was deeply positive, now falling back
        if (
            z_prev2 > threshold
            and z_prev > threshold
            and z_now < z_prev
            and is_mean_reverting
        ):
            conf = min(88, 50 + abs(z_prev) * 15)
            return (
                SIGNAL_SELL,
                round(conf, 1),
                f"Quant Z={z_prev:.2f}σ overbought reversion (HE={lag1_corr:.2f})",
            )

        # Breakout mode: strongly trending (NOT mean-reverting), Z sustained high/low
        if not is_mean_reverting:
            if z_prev > 1.5 and z_now > z_prev:  # Momentum continuation
                return SIGNAL_BUY, 62, f"Quant momentum Z={z_now:.2f}σ"
            if z_prev < -1.5 and z_now < z_prev:
                return SIGNAL_SELL, 62, f"Quant momentum Z={z_now:.2f}σ"

        return SIGNAL_NONE, 0, ""
