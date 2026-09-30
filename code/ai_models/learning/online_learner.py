"""DeltaForge - OnlineLearner: SGD online updates from trade outcomes."""

import json
import logging
import os
import time
from typing import List

import numpy as np

from ..scoring.signal_scorer import SignalScorer

logger = logging.getLogger("DeltaForge.AI.OnlineLearner")


class OnlineLearner:
    """
    Records trade outcomes and triggers online weight updates every
    ``update_every`` completed trades.

    Attributes:
        scorer:         the SignalScorer whose weights are updated online.
        _update_every:  flush threshold (number of pending records).
        _pending:       integer count of records buffered since the last flush.
    """

    OUTCOME_FILE = "trade_outcomes.jsonl"

    def __init__(self, scorer: SignalScorer, update_every: int = 10):
        self.scorer = scorer
        self._update_every = int(update_every)
        self._buffer: List[dict] = []
        self._pending: int = 0

    # Public alias retained for readability / external configuration.
    @property
    def update_every(self) -> int:
        return self._update_every

    @update_every.setter
    def update_every(self, value: int):
        self._update_every = int(value)

    def record(
        self, features: np.ndarray, direction: int, confluence: float, pnl: float
    ):
        """
        Record a completed trade.
        pnl > 0 = profitable (label=1), pnl <= 0 = loss (label=0)
        """
        label = 1 if pnl > 0 else 0
        entry = {
            "features": np.asarray(features).tolist(),
            "direction": direction,
            "confluence": confluence,
            "pnl": pnl,
            "label": label,
            "ts": time.time(),
        }
        self._buffer.append(entry)
        self._pending += 1

        # Persist
        try:
            with open(self.OUTCOME_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.debug(f"Outcome log error: {e}")

        # Trigger online update once the buffer reaches the threshold.
        if self._pending >= self._update_every:
            self._batch_update()
            self._buffer.clear()
            self._pending = 0

    def _batch_update(self):
        for entry in self._buffer:
            f = np.array(entry["features"])
            self.scorer.online_update(
                f, entry["label"], entry["direction"], entry["confluence"]
            )
        self.scorer.save_weights()
        logger.info(f"Online learning: updated on {len(self._buffer)} trades")

    def load_history_and_retrain(self):
        """Full retrain from saved trade outcomes file."""
        if not os.path.exists(self.OUTCOME_FILE):
            return
        records = []
        with open(self.OUTCOME_FILE) as f:
            for line in f:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        if len(records) < 50:
            logger.info(
                f"Not enough trade outcomes ({len(records)}) for retrain (min 50)"
            )
            return
        X = np.array([r["features"] for r in records])
        y = np.array([r["label"] for r in records], dtype=float)
        logger.info(f"Retraining on {len(records)} trades...")
        self.scorer.train(X, y)
        self.scorer.save_weights()
