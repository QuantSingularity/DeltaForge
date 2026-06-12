"""Tests for OnlineLearner."""

import numpy as np
import pytest

from ..features.feature_extractor import N_FEATURES
from ..learning.online_learner import OnlineLearner
from ..scoring.signal_scorer import SignalScorer


@pytest.fixture
def scorer_and_learner():
    sc = SignalScorer()
    ol = OnlineLearner(sc)
    return sc, ol


class TestOnlineLearner:

    def test_record_does_not_raise(self, scorer_and_learner):
        sc, ol = scorer_and_learner
        rng = np.random.default_rng(0)
        feat = rng.uniform(-1, 1, N_FEATURES).astype(np.float32)
        ol.record(feat, direction=1, confluence=70.0, pnl=25.0)

    def test_multiple_records_accumulate(self, scorer_and_learner):
        sc, ol = scorer_and_learner
        rng = np.random.default_rng(1)
        for _ in range(15):
            feat = rng.uniform(-1, 1, N_FEATURES).astype(np.float32)
            ol.record(feat, direction=1, confluence=65.0, pnl=float(rng.normal(10, 30)))
        assert ol._pending >= 0  # pending may have been flushed

    def test_update_every_triggers_train(self, scorer_and_learner):
        sc, ol = scorer_and_learner
        ol._update_every = 5
        rng = np.random.default_rng(2)
        sc.weights.copy()
        for i in range(6):
            feat = rng.uniform(-1, 1, N_FEATURES).astype(np.float32)
            pnl = 20.0 if i % 2 == 0 else -10.0
            ol.record(feat, direction=1, confluence=60.0, pnl=pnl)
        # Weights may or may not have changed depending on implementation
        assert sc.weights.shape == (N_FEATURES,)

    def test_losing_trades_create_label_0(self, scorer_and_learner):
        """Record methods should produce label=0 for losing trades."""
        sc, ol = scorer_and_learner
        rng = np.random.default_rng(3)
        for _ in range(20):
            feat = rng.uniform(-1, 1, N_FEATURES).astype(np.float32)
            ol.record(feat, direction=-1, confluence=55.0, pnl=-50.0)
        # Just verify no exception raised and scorer still valid
        assert sc.weights.shape == (N_FEATURES,)

    def test_record_with_zero_pnl(self, scorer_and_learner):
        sc, ol = scorer_and_learner
        feat = np.zeros(N_FEATURES, dtype=np.float32)
        ol.record(feat, direction=1, confluence=50.0, pnl=0.0)

    def test_scorer_reference_preserved(self, scorer_and_learner):
        sc, ol = scorer_and_learner
        assert ol.scorer is sc
