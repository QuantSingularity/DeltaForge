"""Tests for SignalScorer."""

import numpy as np
import pytest

from ..features.feature_extractor import N_FEATURES, FeatureExtractor
from ..scoring.signal_scorer import SignalScorer


@pytest.fixture
def scorer():
    return SignalScorer()


@pytest.fixture
def random_features():
    rng = np.random.default_rng(0)
    return rng.uniform(-1, 1, N_FEATURES).astype(np.float32)


@pytest.fixture
def trained_scorer():
    """Scorer trained on 100 synthetic samples."""
    sc = SignalScorer()
    rng = np.random.default_rng(42)
    X = rng.uniform(-1, 1, (100, N_FEATURES)).astype(np.float32)
    y = rng.integers(0, 2, 100)
    sc.train(X, y, lr=0.05, epochs=200)
    return sc


class TestSignalScorer:

    def test_score_range(self, scorer, random_features):
        for direction in (1, -1):
            s = scorer.score(random_features, direction, confluence=60.0)
            assert 0.0 <= s <= 100.0, f"Score {s} out of [0, 100]"

    def test_score_returns_float(self, scorer, random_features):
        s = scorer.score(random_features, 1, 60.0)
        assert isinstance(s, float)

    def test_higher_confluence_raises_score(self, scorer, random_features):
        low = scorer.score(random_features, 1, confluence=40.0)
        high = scorer.score(random_features, 1, confluence=90.0)
        assert high >= low, "Higher confluence should not lower score"

    def test_score_without_training(self, scorer, random_features):
        """Untrained scorer should still return a valid score."""
        s = scorer.score(random_features, 1, 60.0)
        assert 0.0 <= s <= 100.0

    def test_extract_features_from_df(self, scorer):
        df = _make_ohlcv(300)
        ext = FeatureExtractor()
        vec = ext.extract(df)
        s = scorer.score(vec, 1, 60.0)
        assert 0.0 <= s <= 100.0

    def test_train_improves_loss(self, scorer):
        rng = np.random.default_rng(7)
        X = rng.uniform(-1, 1, (80, N_FEATURES)).astype(np.float32)
        y = (X[:, 0] > 0).astype(int)  # learnable signal
        loss_before = scorer._compute_loss(X, y)
        scorer.train(X, y, lr=0.1, epochs=500)
        loss_after = scorer._compute_loss(X, y)
        assert (
            loss_after <= loss_before + 0.05
        ), f"Loss did not improve: {loss_before:.4f} → {loss_after:.4f}"

    def test_trained_scorer_buy_vs_sell(self, trained_scorer, random_features):
        buy_score = trained_scorer.score(random_features, 1, 70.0)
        sell_score = trained_scorer.score(random_features, -1, 70.0)
        assert 0.0 <= buy_score <= 100.0
        assert 0.0 <= sell_score <= 100.0

    def test_save_load_weights(self, trained_scorer, tmp_path):
        wf = str(tmp_path / "weights.json")
        trained_scorer.save_weights(wf)
        new_sc = SignalScorer()
        new_sc.load_weights(wf)
        rng = np.random.default_rng(99)
        feat = rng.uniform(-1, 1, N_FEATURES).astype(np.float32)
        s1 = trained_scorer.score(feat, 1, 60.0)
        s2 = new_sc.score(feat, 1, 60.0)
        assert abs(s1 - s2) < 1e-3, "Weights not restored correctly"

    def test_batch_score(self, scorer):
        rng = np.random.default_rng(3)
        X = rng.uniform(-1, 1, (20, N_FEATURES)).astype(np.float32)
        scores = [scorer.score(x, 1, 60.0) for x in X]
        assert all(0.0 <= s <= 100.0 for s in scores)

    def test_weights_shape(self, scorer):
        assert scorer.weights.shape == (N_FEATURES,)
        assert isinstance(float(scorer.bias), float)
