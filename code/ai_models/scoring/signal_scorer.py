"""DeltaForge - SignalScorer: logistic regression signal confidence (0-100%)."""

import json
import logging
import os
import time

import numpy as np
import pandas as pd

logger = logging.getLogger("DeltaForge.AI.SignalScorer")

WEIGHTS_FILE = "ml_weights.json"

FEATURE_NAMES = [
    "rsi_norm",  # RSI normalised -1..1
    "macd_hist_norm",  # MACD histogram / close * 10000
    "bb_pct",  # Price position within BB 0..1
    "atr_norm",  # ATR / close * 100
    "adx_norm",  # ADX / 100
    "stoch_k_norm",  # Stoch K normalised -1..1
    "vol_ratio",  # Current vol / avg vol (20) - 1
    "ema_slope",  # EMA20 slope normalised
    "momentum_norm",  # Momentum (14) - 100 / 10
    "confluence",  # Strategy confluence 0..1, strongest feature
]

# Number of features the scorer expects. extract_features() fills indices
# 0..9 and score()/train() operate on a vector of this length.
N_FEATURES = len(FEATURE_NAMES)


class SignalScorer:
    """Logistic regression signal scorer with offline + online learning."""

    # Default weights (good starting point; overwritten by train/load)
    DEFAULT_WEIGHTS = np.array(
        [
            0.45,  # rsi_norm
            0.62,  # macd_hist_norm
            -0.38,  # bb_pct  (high BB% often precedes reversal)
            -0.22,  # atr_norm (high ATR = uncertainty)
            0.58,  # adx_norm
            0.33,  # stoch_k_norm
            0.41,  # vol_ratio
            0.71,  # ema_slope
            0.49,  # momentum_norm
            0.85,  # confluence (strongest predictor)
        ]
    )
    DEFAULT_BIAS = -0.15

    def __init__(self, weights_path: str = WEIGHTS_FILE):
        self.weights = self.DEFAULT_WEIGHTS.copy()
        self.bias = self.DEFAULT_BIAS
        self.path = weights_path
        # Loading is explicit (call load_weights()) so constructing a scorer
        # never silently depends on a file in the working directory.

    def sigmoid(self, x: float) -> float:
        return 1.0 / (1.0 + np.exp(-np.clip(x, -20, 20)))

    def score(self, features: np.ndarray, direction: int, confluence: float) -> float:
        """
        Return probability 0-100 that this is a good trade.
        direction: 1=BUY, -1=SELL, 0=NONE
        """
        if direction == 0:
            return 0.0
        # For SELL signals, flip direction-sensitive features
        f = features.copy()
        dir_sensitive = [0, 1, 5, 7, 8]  # rsi, macd, stoch, slope, momentum
        f[dir_sensitive] *= direction

        # Inject confluence
        f[9] = confluence / 100.0

        z = self.bias + float(np.dot(self.weights, f))
        prob = self.sigmoid(z) * 100.0
        return round(prob, 2)

    # ── FEATURE EXTRACTION ──────────────────────────────────────────
    def extract_features(self, df: pd.DataFrame) -> np.ndarray:
        feat = np.zeros(N_FEATURES)
        try:
            close = df["close"]
            high = df["high"]
            low = df["low"]
            volume = df["volume"]
            c_last = float(close.iloc[-1])

            # 0. RSI
            delta = close.diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rs = gain / loss.replace(0, np.nan)
            rsi = float((100 - (100 / (1 + rs))).iloc[-1])
            feat[0] = (rsi - 50) / 50

            # 1. MACD histogram
            fast_ema = close.ewm(span=12, adjust=False).mean()
            slow_ema = close.ewm(span=26, adjust=False).mean()
            macd_line = fast_ema - slow_ema
            sig_line = macd_line.ewm(span=9, adjust=False).mean()
            hist = float((macd_line - sig_line).iloc[-1])
            feat[1] = np.clip(hist / c_last * 10000, -1, 1) if c_last > 0 else 0

            # 2. BB%
            mid = close.rolling(20).mean()
            std = close.rolling(20).std()
            upper = mid + 2 * std
            lower = mid - 2 * std
            bb_range = float((upper - lower).iloc[-1])
            feat[2] = (
                float((c_last - lower.iloc[-1]) / bb_range) if bb_range > 0 else 0.5
            )

            # 3. ATR norm
            hl = high - low
            hc = (high - close.shift()).abs()
            lc = (low - close.shift()).abs()
            atr = float(
                pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(14).mean().iloc[-1]
            )
            feat[3] = min(1.0, atr / c_last * 100) if c_last > 0 else 0

            # 4. ADX
            up_move = high.diff()
            dn_move = -low.diff()
            pos_dm = np.where((up_move > dn_move) & (up_move > 0), up_move, 0)
            neg_dm = np.where((dn_move > up_move) & (dn_move > 0), dn_move, 0)
            atr_s = pd.Series(hl.rolling(14).mean().values, index=close.index).replace(
                0, np.nan
            )
            pos_di = (
                100 * pd.Series(pos_dm, index=close.index).rolling(14).mean() / atr_s
            )
            neg_di = (
                100 * pd.Series(neg_dm, index=close.index).rolling(14).mean() / atr_s
            )
            dx = 100 * (pos_di - neg_di).abs() / (pos_di + neg_di).replace(0, np.nan)
            adx = float(dx.rolling(14).mean().iloc[-1])
            feat[4] = adx / 100 if not np.isnan(adx) else 0

            # 5. Stoch K
            low_min = low.rolling(14).min()
            high_max = high.rolling(14).max()
            stoch_k = float(
                100
                * (c_last - low_min.iloc[-1])
                / max(high_max.iloc[-1] - low_min.iloc[-1], 1e-10)
            )
            feat[5] = (stoch_k - 50) / 50

            # 6. Volume ratio
            avg_vol = float(volume.iloc[-21:-1].mean())
            cur_vol = float(volume.iloc[-1])
            feat[6] = (cur_vol / avg_vol - 1) if avg_vol > 0 else 0

            # 7. EMA slope
            ema20 = close.ewm(span=20, adjust=False).mean()
            slope = (
                float((ema20.iloc[-1] - ema20.iloc[-2]) / ema20.iloc[-2] * 100)
                if ema20.iloc[-2] > 0
                else 0
            )
            feat[7] = np.clip(slope * 10, -1, 1)

            # 8. Momentum
            mom_period = 14
            if len(close) > mom_period:
                mom = float(close.iloc[-1] / close.iloc[-1 - mom_period] * 100 - 100)
                feat[8] = np.clip(mom / 10, -1, 1)

            # 9. Confluence - injected externally via score()
            feat[9] = 0

        except Exception as e:
            logger.debug(f"Feature extraction error: {e}")
        return feat

    # ── OFFLINE TRAINING ────────────────────────────────────────────
    def _compute_loss(self, X: np.ndarray, y: np.ndarray) -> float:
        """Binary cross-entropy of the current model on raw feature matrix X.

        Uses the same linear form as :meth:`train` (``z = bias + X·weights``)
        so the value is directly comparable before and after training.
        """
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        z = self.bias + X.dot(self.weights)
        pred = 1.0 / (1.0 + np.exp(-np.clip(z, -20, 20)))
        return float(
            -np.mean(y * np.log(pred + 1e-9) + (1 - y) * np.log(1 - pred + 1e-9))
        )

    def train(
        self, X: np.ndarray, y: np.ndarray, lr: float = 0.01, epochs: int = 1000
    ) -> dict:
        """
        Logistic regression via gradient descent.
        X: (n_samples, N_FEATURES)
        y: (n_samples,) - 1 = profitable, 0 = not profitable
        """
        n = len(y)
        weights = self.weights.copy()
        bias = self.bias

        for epoch in range(epochs):
            z = bias + X.dot(weights)
            pred = 1.0 / (1.0 + np.exp(-np.clip(z, -20, 20)))
            err = pred - y
            dW = X.T.dot(err) / n
            dB = err.mean()
            weights -= lr * dW
            bias -= lr * dB

            if epoch % 100 == 0:
                loss = float(
                    -np.mean(
                        y * np.log(pred + 1e-9) + (1 - y) * np.log(1 - pred + 1e-9)
                    )
                )
                logger.info(f"Epoch {epoch} | Loss: {loss:.4f}")

        self.weights = weights
        self.bias = bias
        acc = float(((pred >= 0.5).astype(int) == y).mean())
        logger.info(f"Training complete | Accuracy: {acc:.2%}")
        return {"accuracy": acc, "epochs": epochs}

    # ── ONLINE LEARNING (SGD on single sample) ──────────────────────
    def online_update(
        self,
        features: np.ndarray,
        label: int,
        direction: int,
        confluence: float,
        lr: float = 0.005,
    ):
        """
        Update weights on a single completed trade outcome.
        label: 1 = profitable, 0 = loss
        """
        f = features.copy()
        dir_sensitive = [0, 1, 5, 7, 8]
        f[dir_sensitive] *= direction
        f[9] = confluence / 100.0

        z = self.bias + float(np.dot(self.weights, f))
        pred = self.sigmoid(z)
        err = pred - label

        self.weights -= lr * err * f
        self.bias -= lr * err
        logger.debug(f"Online update: label={label} pred={pred:.3f} err={err:.4f}")

    # ── PERSIST ─────────────────────────────────────────────────────
    def save_weights(self, path: str = None):
        target = path or self.path
        data = {
            "weights": self.weights.tolist(),
            "bias": self.bias,
            "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(target, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Weights saved to {target}")

    def load_weights(self, path: str = None):
        target = path or self.path
        if not os.path.exists(target):
            logger.info(f"No weights file found at {target}, using defaults")
            return
        try:
            with open(target) as f:
                data = json.load(f)
            self.weights = np.array(data["weights"])
            self.bias = float(data["bias"])
            logger.info(
                f"Weights loaded from {target} (updated {data.get('updated','')})"
            )
        except Exception as e:
            logger.warning(f"Could not load weights: {e}")


# ─────────────────────────────────────────────────────────────────────
# ANOMALY DETECTOR
# ─────────────────────────────────────────────────────────────────────
