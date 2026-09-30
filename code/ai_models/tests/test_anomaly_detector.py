"""Tests for AnomalyDetector."""

import pytest

from ..anomaly.anomaly_detector import AnomalyDetector


@pytest.fixture
def cfg():
    return {
        "ml": {
            "zscore_threshold": 3.5,
            "volume_spike_ratio": 10.0,
            "max_spread_pct": 0.5,
        }
    }


@pytest.fixture
def warmed_detector(cfg):
    """Detector with 100 normal-price updates."""
    det = AnomalyDetector(cfg)
    for i in range(100):
        det.update(50000.0 + i * 10, 1_000_000.0)
    return det


class TestAnomalyDetector:

    def test_no_anomaly_normal_market(self, warmed_detector):
        is_anom, reason = warmed_detector.is_anomaly(51000.0, 1_100_000.0, 0.05)
        assert not is_anom, f"False positive: {reason}"

    def test_anomaly_huge_price_spike(self, warmed_detector):
        """Price 5× normal should trigger Z-score anomaly."""
        is_anom, _ = warmed_detector.is_anomaly(500_000.0, 1_000_000.0, 0.05)
        assert is_anom

    def test_anomaly_wide_spread(self, cfg):
        det = AnomalyDetector(cfg)
        det.update(50000.0, 1_000_000.0)
        is_anom, reason = det.is_anomaly(50000.0, 1_000_000.0, spread_pct=2.5)
        assert is_anom
        assert "spread" in reason.lower()

    def test_anomaly_volume_spike(self, warmed_detector):
        is_anom, reason = warmed_detector.is_anomaly(50500.0, 50_000_000.0, 0.05)
        assert is_anom
        assert "volume" in reason.lower()

    def test_no_anomaly_before_warmup(self, cfg):
        det = AnomalyDetector(cfg)
        # Only 5 updates - not enough history
        for _ in range(5):
            det.update(50000.0, 1_000_000.0)
        is_anom, _ = det.is_anomaly(50000.0, 1_000_000.0, 0.05)
        assert not is_anom

    def test_update_increments_counter(self, cfg):
        det = AnomalyDetector(cfg)
        assert det._count == 0
        det.update(50000.0, 1_000_000.0)
        assert det._count == 1

    def test_reason_string_non_empty_on_anomaly(self, warmed_detector):
        is_anom, reason = warmed_detector.is_anomaly(500_000.0, 1_000_000.0, 0.05)
        if is_anom:
            assert isinstance(reason, str) and len(reason) > 0

    def test_zero_price_handled(self, warmed_detector):
        """Zero price should not raise."""
        try:
            warmed_detector.is_anomaly(0.0, 1_000_000.0, 0.05)
        except Exception as e:
            pytest.fail(f"Zero price raised: {e}")

    def test_returns_tuple(self, warmed_detector):
        result = warmed_detector.is_anomaly(50000.0, 1_000_000.0, 0.05)
        assert isinstance(result, tuple) and len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)
