"""
DeltaForge - FeatureExtractor
Centralised, versioned feature engineering for all ML models.
Produces a fixed-length numpy feature vector from an OHLCV DataFrame.
"""

from typing import List

import numpy as np
import pandas as pd

FEATURE_NAMES: List[str] = [
    "rsi_norm",  # RSI normalised to -1..1
    "macd_hist_norm",  # MACD histogram / close * 1e4
    "bb_pct",  # Price position in Bollinger band  0..1
    "atr_norm",  # ATR / close
    "volume_ratio",  # Current volume / 20-bar average
    "ema_slope_norm",  # EMA20 slope / close
    "adx_norm",  # ADX / 100
    "stoch_k_norm",  # Stochastic %K / 100
    "price_momentum",  # 10-bar return
    "confluence",  # Strategy vote confluence (filled externally)
]
N_FEATURES = len(FEATURE_NAMES)


class FeatureExtractor:
    """
    Stateless feature extractor.  Call extract(df) to get a normalised
    numpy array of shape (N_FEATURES,) ready for the SignalScorer.
    """

    def extract(self, df: pd.DataFrame) -> np.ndarray:
        """Return feature vector for the latest bar in df."""
        close = df["close"]
        vec = np.zeros(N_FEATURES, dtype=np.float32)

        if len(df) < 30:
            return vec

        try:
            # 0 - RSI normalised
            rsi = self._rsi(close)
            vec[0] = (float(rsi.iloc[-1]) - 50.0) / 50.0

            # 1 - MACD histogram normalised
            _, _, hist = self._macd(close)
            c = float(close.iloc[-1])
            vec[1] = float(hist.iloc[-1]) / c * 1e4 if c != 0 else 0.0

            # 2 - Bollinger %b
            upper, mid, lower = self._bollinger(close)
            bw = float(upper.iloc[-1]) - float(lower.iloc[-1])
            vec[2] = (c - float(lower.iloc[-1])) / bw if bw != 0 else 0.5

            # 3 - ATR / close
            atr = self._atr(df)
            vec[3] = float(atr.iloc[-1]) / c if c != 0 else 0.0

            # 4 - Volume ratio
            avg_vol = float(df["volume"].iloc[-21:-1].mean())
            cur_vol = float(df["volume"].iloc[-1])
            vec[4] = cur_vol / avg_vol if avg_vol != 0 else 1.0

            # 5 - EMA20 slope normalised
            ema20 = close.ewm(span=20, adjust=False).mean()
            slope = float(ema20.iloc[-1]) - float(ema20.iloc[-2])
            vec[5] = slope / c if c != 0 else 0.0

            # 6 - ADX
            adx, _, _ = self._adx(df)
            vec[6] = float(adx.iloc[-1]) / 100.0 if not pd.isna(adx.iloc[-1]) else 0.25

            # 7 - Stochastic %K
            k, _ = self._stochastic(df)
            vec[7] = float(k.iloc[-1]) / 100.0

            # 8 - 10-bar price momentum
            if len(close) >= 11:
                prev = float(close.iloc[-11])
                vec[8] = (c - prev) / prev if prev != 0 else 0.0

            # 9 - confluence placeholder (filled by SignalScorer.score())
            vec[9] = 0.0

        except Exception:
            pass

        return np.clip(vec, -5.0, 5.0)

    def extract_batch(self, df: pd.DataFrame, lookback: int = 200) -> np.ndarray:
        """
        Extract features for a rolling window - used during backtest training.
        Returns shape (N, N_FEATURES).
        """
        rows = []
        for i in range(lookback, len(df)):
            sub = df.iloc[: i + 1]
            rows.append(self.extract(sub))
        return np.array(rows, dtype=np.float32)

    # ── Indicator helpers ─────────────────────────────────────────────
    @staticmethod
    def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _macd(close: pd.Series, fast=12, slow=26, signal=9):
        f = close.ewm(span=fast, adjust=False).mean()
        s = close.ewm(span=slow, adjust=False).mean()
        m = f - s
        sig = m.ewm(span=signal, adjust=False).mean()
        return m, sig, m - sig

    @staticmethod
    def _bollinger(close: pd.Series, period=20, std_dev=2.0):
        mid = close.rolling(period).mean()
        std = close.rolling(period).std()
        return mid + std_dev * std, mid, mid - std_dev * std

    @staticmethod
    def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        hl = df["high"] - df["low"]
        hc = (df["high"] - df["close"].shift()).abs()
        lc = (df["low"] - df["close"].shift()).abs()
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    @staticmethod
    def _adx(df: pd.DataFrame, period: int = 14):
        atr = FeatureExtractor._atr(df, period)
        up = df["high"].diff()
        dn = -df["low"].diff()
        pdm = np.where((up > dn) & (up > 0), up, 0)
        ndm = np.where((dn > up) & (dn > 0), dn, 0)
        pdi = (
            100
            * pd.Series(pdm, index=df.index).rolling(period).mean()
            / atr.replace(0, np.nan)
        )
        ndi = (
            100
            * pd.Series(ndm, index=df.index).rolling(period).mean()
            / atr.replace(0, np.nan)
        )
        dx = 100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, np.nan)
        return dx.rolling(period).mean(), pdi, ndi

    @staticmethod
    def _stochastic(df: pd.DataFrame, k=14, smooth=3):
        low_min = df["low"].rolling(k).min()
        high_max = df["high"].rolling(k).max()
        k_raw = 100 * (df["close"] - low_min) / (high_max - low_min).replace(0, np.nan)
        return (
            k_raw.rolling(smooth).mean(),
            k_raw.rolling(smooth).mean().rolling(3).mean(),
        )
