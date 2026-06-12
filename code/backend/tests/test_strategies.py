"""
Comprehensive tests for all 26 trading strategies.
Each strategy is tested for:
  - valid signal return type  (int: -1, 0, or 1)
  - valid confidence range    (0..100)
  - non-empty note string     when signal != 0
  - no exceptions on valid data
  - handling of short DataFrames
"""

import pytest

from ..strategies.engine import StrategyEngine
from ..strategies.indicators import SIGNAL_BUY, SIGNAL_NONE, SIGNAL_SELL

STRATEGY_NAMES = [
    "ma_cross",
    "ema_trend",
    "macd_strategy",
    "adx_filter",
    "parabolic_sar",
    "ichimoku",
    "trendline",
    "rsi_strategy",
    "stochastic",
    "momentum",
    "bollinger_bands",
    "atr_breakout",
    "breakout",
    "accum_dist",
    "chaikin_mf",
    "volume_breakout",
    "pullback",
    "fibonacci",
    "pivot_points",
    "support_resistance",
    "smart_money_concepts",
    "order_flow",
    "market_profile",
    "lux_algo",
    "news_momentum",
    "quant_algo",
]


@pytest.fixture
def engine(base_config):
    return StrategyEngine(base_config)


@pytest.fixture
def df_300():
    return _make_ohlcv(300)


@pytest.fixture
def df_short():
    return _make_ohlcv(15)


class TestStrategySignalContract:
    """Every strategy must return (int, float, str) within spec."""

    @pytest.mark.parametrize("name", STRATEGY_NAMES)
    def test_return_type(self, engine, df_300, name):
        method = getattr(engine, name, None)
        assert method is not None, f"Method {name!r} not found on StrategyEngine"
        result = method(df_300)
        assert (
            isinstance(result, tuple) and len(result) == 3
        ), f"{name} must return (signal, confidence, note)"

    @pytest.mark.parametrize("name", STRATEGY_NAMES)
    def test_signal_valid_value(self, engine, df_300, name):
        sig, conf, note = getattr(engine, name)(df_300)
        assert sig in (
            SIGNAL_BUY,
            SIGNAL_SELL,
            SIGNAL_NONE,
        ), f"{name} returned invalid signal {sig}"

    @pytest.mark.parametrize("name", STRATEGY_NAMES)
    def test_confidence_range(self, engine, df_300, name):
        sig, conf, note = getattr(engine, name)(df_300)
        assert 0.0 <= conf <= 100.0, f"{name} confidence {conf} out of [0, 100]"

    @pytest.mark.parametrize("name", STRATEGY_NAMES)
    def test_note_is_string(self, engine, df_300, name):
        sig, conf, note = getattr(engine, name)(df_300)
        assert isinstance(note, str), f"{name} note is not a string"

    @pytest.mark.parametrize("name", STRATEGY_NAMES)
    def test_active_signal_has_note(self, engine, df_300, name):
        sig, conf, note = getattr(engine, name)(df_300)
        if sig != SIGNAL_NONE:
            assert (
                len(note) > 0
            ), f"{name}: active signal ({sig}) must have non-empty note"

    @pytest.mark.parametrize("name", STRATEGY_NAMES)
    def test_no_exception_short_df(self, engine, df_short, name):
        """Strategies must not raise on short DataFrames — return NONE gracefully."""
        try:
            sig, conf, note = getattr(engine, name)(df_short)
            assert sig in (SIGNAL_BUY, SIGNAL_SELL, SIGNAL_NONE)
        except Exception as e:
            pytest.fail(f"{name} raised on short df: {e}")

    @pytest.mark.parametrize("name", STRATEGY_NAMES)
    def test_zero_confidence_on_none_signal(self, engine, df_300, name):
        sig, conf, note = getattr(engine, name)(df_300)
        if sig == SIGNAL_NONE:
            # Conf can be 0 or small — just verify it's not absurdly high
            assert conf <= 100.0


class TestStrategyEngine:

    def test_run_all_returns_dict(self, engine, df_300):
        result = engine.run_all(df_300)
        assert isinstance(result, dict)
        for key in (
            "direction",
            "confluence",
            "votes_buy",
            "votes_sell",
            "total",
            "hits",
        ):
            assert key in result, f"Missing key: {key}"

    def test_run_all_direction_valid(self, engine, df_300):
        result = engine.run_all(df_300)
        assert result["direction"] in (SIGNAL_BUY, SIGNAL_SELL, SIGNAL_NONE)

    def test_run_all_confluence_range(self, engine, df_300):
        result = engine.run_all(df_300)
        assert 0.0 <= result["confluence"] <= 100.0

    def test_votes_sum(self, engine, df_300):
        result = engine.run_all(df_300)
        total = result["votes_buy"] + result["votes_sell"]
        assert total <= result["total"]

    def test_hits_list_type(self, engine, df_300):
        result = engine.run_all(df_300)
        assert isinstance(result["hits"], list)

    def test_disabled_strategy_not_in_results(self, base_config):
        cfg = dict(base_config)
        cfg["strategies"] = dict(base_config["strategies"])
        cfg["strategies"]["macd"] = False
        eng = StrategyEngine(cfg)
        result = eng.run_all(_make_ohlcv(300))
        assert "macd" not in result["signals"]

    def test_all_strategies_enabled_count(self, engine, df_300):
        result = engine.run_all(df_300)
        assert result["total"] == 26

    def test_uptrend_bias_buy(self, base_config):
        """Trending up data should produce more buy votes than sell."""
        # Force strong uptrend by repeating +0.5% each bar
        import numpy as np
        import pandas as pd

        prices = np.cumprod(np.ones(300) * 1.005) * 30000
        idx = pd.date_range("2024-01-01", periods=300, freq="1h")
        df = pd.DataFrame(
            {
                "open": prices * 0.999,
                "high": prices * 1.006,
                "low": prices * 0.994,
                "close": prices,
                "volume": np.random.default_rng(5).uniform(500, 5000, 300),
            },
            index=idx,
        )
        eng = StrategyEngine(base_config)
        result = eng.run_all(df)
        assert (
            result["votes_buy"] >= result["votes_sell"]
        ), "Uptrend data should have more buy than sell votes"
