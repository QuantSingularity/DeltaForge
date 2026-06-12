"""
DeltaForge Strategy Engine
26 Strategy implementations for crypto spot/margin trading
Input: OHLCV DataFrame with columns [timestamp, open, high, low, close, volume]
Output: signal = 1 (BUY), -1 (SELL), 0 (NONE) per strategy
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger("DeltaForge.Strategies")

SIGNAL_BUY = 1
SIGNAL_SELL = -1
SIGNAL_NONE = 0


# ─────────────────────────────────────────────────────────────────────
# INDICATOR HELPERS
# ─────────────────────────────────────────────────────────────────────
def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift()).abs()
    lc = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _macd(close: pd.Series, fast=12, slow=26, signal=9):
    fast_ema = _ema(close, fast)
    slow_ema = _ema(close, slow)
    macd_line = fast_ema - slow_ema
    signal_line = _ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _bollinger(close: pd.Series, period=20, std_dev=2.0):
    mid = _sma(close, period)
    std = close.rolling(period).std()
    upper = mid + std_dev * std
    lower = mid - std_dev * std
    return upper, mid, lower


def _stochastic(df: pd.DataFrame, k=14, d=3, smooth=3):
    low_min = df["low"].rolling(k).min()
    high_max = df["high"].rolling(k).max()
    k_raw = 100 * (df["close"] - low_min) / (high_max - low_min).replace(0, np.nan)
    k_smooth = k_raw.rolling(smooth).mean()
    d_line = k_smooth.rolling(d).mean()
    return k_smooth, d_line


def _adx(df: pd.DataFrame, period: int = 14):
    atr_val = _atr(df, period)
    up_move = df["high"].diff()
    dn_move = -df["low"].diff()
    pos_dm = np.where((up_move > dn_move) & (up_move > 0), up_move, 0)
    neg_dm = np.where((dn_move > up_move) & (dn_move > 0), dn_move, 0)
    pos_di = 100 * pd.Series(pos_dm, index=df.index).rolling(period).mean() / atr_val
    neg_di = 100 * pd.Series(neg_dm, index=df.index).rolling(period).mean() / atr_val
    dx = 100 * (pos_di - neg_di).abs() / (pos_di + neg_di).replace(0, np.nan)
    adx = dx.rolling(period).mean()
    return adx, pos_di, neg_di


def _ichimoku(df: pd.DataFrame, t=9, k=26, s=52):
    tenkan = (df["high"].rolling(t).max() + df["low"].rolling(t).min()) / 2
    kijun = (df["high"].rolling(k).max() + df["low"].rolling(k).min()) / 2
    span_a = ((tenkan + kijun) / 2).shift(k)
    span_b = ((df["high"].rolling(s).max() + df["low"].rolling(s).min()) / 2).shift(k)
    return tenkan, kijun, span_a, span_b


def _pivot_points(df: pd.DataFrame):
    pivot = (df["high"].shift(1) + df["low"].shift(1) + df["close"].shift(1)) / 3
    r1 = 2 * pivot - df["low"].shift(1)
    s1 = 2 * pivot - df["high"].shift(1)
    r2 = pivot + (df["high"].shift(1) - df["low"].shift(1))
    s2 = pivot - (df["high"].shift(1) - df["low"].shift(1))
    return pivot, r1, s1, r2, s2


def _chaikin_mf(df: pd.DataFrame, period: int = 20):
    hl = (df["high"] - df["low"]).replace(0, np.nan)
    clv = ((df["close"] - df["low"]) - (df["high"] - df["close"])) / hl
    mfv = clv * df["volume"]
    cmf = mfv.rolling(period).sum() / df["volume"].rolling(period).sum()
    return cmf


def _ad_line(df: pd.DataFrame):
    hl = (df["high"] - df["low"]).replace(0, np.nan)
    clv = ((df["close"] - df["low"]) - (df["high"] - df["close"])) / hl
    return (clv * df["volume"]).cumsum()


def _pivot_swing_lows(series: pd.Series, lookback: int = 5) -> pd.Series:
    """Detect swing low pivot points."""
    pivots = pd.Series(False, index=series.index)
    for i in range(lookback, len(series) - lookback):
        if series.iloc[i] == series.iloc[i - lookback : i + lookback + 1].min():
            pivots.iloc[i] = True
    return pivots


def _pivot_swing_highs(series: pd.Series, lookback: int = 5) -> pd.Series:
    """Detect swing high pivot points."""
    pivots = pd.Series(False, index=series.index)
    for i in range(lookback, len(series) - lookback):
        if series.iloc[i] == series.iloc[i - lookback : i + lookback + 1].max():
            pivots.iloc[i] = True
    return pivots


# ─────────────────────────────────────────────────────────────────────
# STRATEGY CLASS
# ─────────────────────────────────────────────────────────────────────
