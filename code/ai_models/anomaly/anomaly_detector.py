"""DeltaForge - AnomalyDetector: Z-score + spread + volume spike auto-stop."""

import logging
from typing import Tuple

import numpy as np

logger = logging.getLogger("DeltaForge.AI.Anomaly")


class AnomalyDetector:
    """
    Isolation Forest approximation via Z-score + spread/volume checks.
    Flags extreme market conditions that should pause the bot.
    """

    def __init__(self, config: dict):
        self.cfg = config.get("ml", {})
        self._px_buf = []
        self._vol_buf = []
        self.buf_size = 100
        self._count = 0

    def update(self, price: float, volume: float):
        self._px_buf.append(price)
        self._vol_buf.append(volume)
        self._count += 1
        if len(self._px_buf) > self.buf_size:
            self._px_buf.pop(0)
        if len(self._vol_buf) > self.buf_size:
            self._vol_buf.pop(0)

    def is_anomaly(
        self, price: float, volume: float, spread_pct: float = 0.0
    ) -> Tuple[bool, str]:
        """
        Returns (is_anomaly, reason).
        """
        reasons = []

        # 1. Price Z-score
        if len(self._px_buf) >= 20:
            arr = np.array(self._px_buf)
            mean = arr.mean()
            std = arr.std()
            if std > 0:
                z = abs(price - mean) / std
                if z > self.cfg.get("zscore_threshold", 3.5):
                    reasons.append(f"Price Z-score {z:.2f} > 3.5")

        # 2. Volume spike
        if len(self._vol_buf) >= 10:
            avg_vol = np.mean(self._vol_buf[:-1])
            vol_ratio = volume / avg_vol if avg_vol > 0 else 0
            if vol_ratio > self.cfg.get("volume_spike_ratio", 10.0):
                reasons.append(f"Volume spike {vol_ratio:.1f}x average")

        # 3. Spread anomaly
        if spread_pct > self.cfg.get("max_spread_pct", 0.5):
            reasons.append(f"Spread {spread_pct:.3f}% > max")

        if reasons:
            logger.warning(f"ANOMALY: {' | '.join(reasons)}")
            return True, " | ".join(reasons)
        return False, ""


# ─────────────────────────────────────────────────────────────────────
# ONLINE LEARNER (trade outcome recorder)
# ─────────────────────────────────────────────────────────────────────
