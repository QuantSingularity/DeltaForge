"""
Regression tests for two runtime bugs that the original suite did not cover
because neither code path was exercised by synthetic test data.

1. SignalScorer.extract_features referenced an undefined name (N_FEATURES),
   crashing any backtest in which a signal actually fired.
2. FeedEngine.confluence_matrix returned numpy float scalars, which FastAPI
   could not serialize, so GET /api/strategies returned HTTP 500.
"""

import json

import numpy as np
from ai_models.scoring.signal_scorer import N_FEATURES, SignalScorer
from backend.api.feed import FeedEngine
from backend.api.state import AppState
from testkit import make_ohlcv


class TestSignalScorerExtractFeatures:
    def test_extract_features_returns_correct_shape(self):
        scorer = SignalScorer()
        df = make_ohlcv(300)
        feat = scorer.extract_features(df)
        assert feat.shape == (N_FEATURES,)
        assert N_FEATURES == 10

    def test_extract_features_does_not_raise_on_short_frame(self):
        scorer = SignalScorer()
        df = make_ohlcv(30)
        feat = scorer.extract_features(df)
        assert feat.shape == (N_FEATURES,)

    def test_extracted_features_are_finite_or_zero(self):
        scorer = SignalScorer()
        feat = scorer.extract_features(make_ohlcv(300))
        assert np.all(np.isfinite(feat))


class TestConfluenceMatrixSerialization:
    def _feed(self):
        cfg = {
            "symbols": ["BTC/USDT", "ETH/USDT"],
            "min_ml_score": 60.0,
            "risk": {"max_total_orders": 10},
            "trail_stop": {"type": "atr", "enabled": True},
        }
        return FeedEngine(AppState(10_000.0), cfg)

    def test_confluence_matrix_is_json_serializable(self):
        # json.dumps raises TypeError on numpy scalar types, so a successful
        # dump is a precise guard against the original HTTP 500.
        payload = self._feed().confluence_matrix()
        json.dumps(payload)

    def test_confluence_matrix_has_no_numpy_scalars(self):
        payload = self._feed().confluence_matrix()

        def walk(obj):
            if isinstance(obj, dict):
                for value in obj.values():
                    walk(value)
            elif isinstance(obj, list):
                for value in obj:
                    walk(value)
            else:
                assert not isinstance(obj, np.generic), f"numpy scalar leaked: {obj!r}"

        walk(payload)

    def test_confluence_matrix_shape(self):
        payload = self._feed().confluence_matrix()
        assert "strategies" in payload and "rows" in payload
        assert len(payload["rows"]) == 2
        for row in payload["rows"]:
            assert "symbol" in row and "strategies" in row
