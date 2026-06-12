"""DeltaForge — OnlineLearner: SGD online updates from trade outcomes."""

import json
import os
import time
from typing import List

import numpy as np

from ..scoring.signal_scorer import SignalScorer


class OnlineLearner:
    """
    Records trade outcomes and triggers online weight updates
    every N completed trades.
    """

    OUTCOME_FILE = "trade_outcomes.jsonl"

    def __init__(self, scorer: SignalScorer, update_every: int = 10):
        self.scorer = scorer
        self.update_every = update_every
        self._pending: List[dict] = []

    def record(
        self, features: np.ndarray, direction: int, confluence: float, pnl: float
    ):
        """
        Record a completed trade.
        pnl > 0 = profitable (label=1), pnl <= 0 = loss (label=0)
        """
        label = 1 if pnl > 0 else 0
        entry = {
            "features": features.tolist(),
            "direction": direction,
            "confluence": confluence,
            "pnl": pnl,
            "label": label,
            "ts": time.time(),
        }
        self._pending.append(entry)

        # Persist
        try:
            with open(self.OUTCOME_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.debug(f"Outcome log error: {e}")

        # Trigger online update
        if len(self._pending) >= self.update_every:
            self._batch_update()
            self._pending.clear()

    def _batch_update(self):
        for entry in self._pending:
            f = np.array(entry["features"])
            self.scorer.online_update(
                f, entry["label"], entry["direction"], entry["confluence"]
            )
        self.scorer.save_weights()
        logger.info(f"Online learning: updated on {len(self._pending)} trades")

    def load_history_and_retrain(self):
        """Full retrain from saved trade outcomes file."""
        if not os.path.exists(self.OUTCOME_FILE):
            return
        records = []
        with open(self.OUTCOME_FILE) as f:
            for line in f:
                try:
                    records.append(json.loads(line))
                except:
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
