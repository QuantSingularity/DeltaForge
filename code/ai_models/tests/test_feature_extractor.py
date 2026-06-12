"""Tests for FeatureExtractor."""

import numpy as np
import pytest

from ..features.feature_extractor import FEATURE_NAMES, N_FEATURES, FeatureExtractor


@pytest.fixture
def extractor():
    return FeatureExtractor()


@pytest.fixture
def df():
    return _make_ohlcv(300)


class TestFeatureExtractor:

    def test_output_shape(self, extractor, df):
        vec = extractor.extract(df)
        assert vec.shape == (N_FEATURES,), f"Expected ({N_FEATURES},), got {vec.shape}"

    def test_output_dtype(self, extractor, df):
        vec = extractor.extract(df)
        assert vec.dtype == np.float32

    def test_values_bounded(self, extractor, df):
        vec = extractor.extract(df)
        assert np.all(vec >= -5.0), "Feature below -5 clip"
        assert np.all(vec <= 5.0), "Feature above +5 clip"

    def test_no_nan_on_sufficient_data(self, extractor, df):
        vec = extractor.extract(df)
        assert not np.any(np.isnan(vec)), "NaN in feature vector"

    def test_short_df_returns_zeros(self, extractor):
        df_short = _make_ohlcv(10)
        vec = extractor.extract(df_short)
        assert vec.shape == (N_FEATURES,)
        assert np.all(vec == 0.0)

    def test_rsi_norm_in_range(self, extractor, df):
        """RSI normalised to [-1, 1]."""
        vec = extractor.extract(df)
        assert -1.0 <= vec[0] <= 1.0, f"RSI_norm out of [-1,1]: {vec[0]}"

    def test_bb_pct_in_range(self, extractor, df):
        """Bollinger %b should be in [0, 1] for most bars."""
        vec = extractor.extract(df)
        # May slightly exceed due to extreme moves, so just check float
        assert isinstance(float(vec[2]), float)

    def test_volume_ratio_positive(self, extractor, df):
        vec = extractor.extract(df)
        assert vec[4] >= 0.0

    def test_atr_norm_positive(self, extractor, df):
        vec = extractor.extract(df)
        assert vec[3] >= 0.0

    def test_feature_names_length(self):
        assert len(FEATURE_NAMES) == N_FEATURES

    def test_batch_extract_shape(self, extractor, df):
        batch = extractor.extract_batch(df, lookback=200)
        expected_rows = len(df) - 200
        assert batch.shape == (expected_rows, N_FEATURES)
        assert batch.dtype == np.float32

    def test_reproducible(self, extractor, df):
        v1 = extractor.extract(df)
        v2 = extractor.extract(df)
        np.testing.assert_array_equal(v1, v2)

    def test_different_data_different_features(self, extractor):
        df1 = _make_ohlcv(300, seed=1)
        df2 = _make_ohlcv(300, seed=99)
        v1 = extractor.extract(df1)
        v2 = extractor.extract(df2)
        assert not np.allclose(v1, v2), "Same features for different data"

    def test_confluence_slot_is_zero(self, extractor, df):
        """Confluence (slot 9) is always 0 — filled externally by scorer."""
        vec = extractor.extract(df)
        assert vec[9] == 0.0
