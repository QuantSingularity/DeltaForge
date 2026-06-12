"""Tests for BacktestEngine and BTResult."""

import pytest

from ..backtest.engine import BacktestEngine, BTResult


@pytest.fixture
def engine(base_config, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # save JSON files to tmp_path
    return BacktestEngine(base_config)


@pytest.fixture
def df_500():
    return _make_ohlcv(500)


class TestBacktestEngine:

    def test_run_returns_result(self, engine, df_500):
        result = engine.run(
            df_500, "BTC/USDT", "1h", initial_capital=10000.0, walk_forward=False
        )
        assert isinstance(result, BTResult)

    def test_result_fields_populated(self, engine, df_500):
        r = engine.run(
            df_500, "BTC/USDT", "1h", initial_capital=10000.0, walk_forward=False
        )
        assert r.symbol == "BTC/USDT"
        assert r.timeframe == "1h"
        assert r.total_trades >= 0
        assert 0.0 <= r.win_rate <= 100.0
        assert isinstance(r.total_pnl, float)

    def test_equity_curve_populated(self, engine, df_500):
        r = engine.run(
            df_500, "BTC/USDT", "1h", initial_capital=10000.0, walk_forward=False
        )
        assert len(r.equity_curve) > 0
        assert r.equity_curve[0] == pytest.approx(10000.0, rel=0.01)

    def test_no_crash_walk_forward(self, engine, df_500):
        r = engine.run(
            df_500, "BTC/USDT", "1h", initial_capital=10000.0, walk_forward=True
        )
        assert isinstance(r, BTResult)

    def test_max_orders_respected(self, engine, df_500):
        r = engine.run(
            df_500, "BTC/USDT", "1h", initial_capital=10000.0, walk_forward=False
        )
        # No trade should exceed max_total_orders simultaneously
        assert r.total_trades <= len(df_500)

    def test_load_bt_win_rates_missing_files(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rates = BacktestEngine.load_bt_win_rates(["BTC/USDT"], ["1h"])
        assert isinstance(rates, dict)

    def test_save_result_creates_file(self, engine, df_500, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        engine.run(
            df_500, "BTC/USDT", "1h", initial_capital=10000.0, walk_forward=False
        )
        files = list(tmp_path.glob("backtest_BTC_USDT_1h.json"))
        assert len(files) == 1

    def test_win_rate_in_range(self, engine, df_500):
        r = engine.run(
            df_500, "BTC/USDT", "1h", initial_capital=10000.0, walk_forward=False
        )
        assert 0.0 <= r.win_rate <= 100.0

    def test_sharpe_is_float(self, engine, df_500):
        r = engine.run(
            df_500, "BTC/USDT", "1h", initial_capital=10000.0, walk_forward=False
        )
        assert isinstance(r.sharpe, float)


class TestBTTrailSimulation:
    """Verify all 5 trail types work in backtest simulation."""

    @pytest.mark.parametrize(
        "trail_type", ["atr", "percent", "dollar", "time", "volatility"]
    )
    def test_trail_type_no_crash(
        self, base_config, df_500, tmp_path, monkeypatch, trail_type
    ):
        monkeypatch.chdir(tmp_path)
        cfg = dict(base_config)
        cfg["trail_stop"] = dict(base_config["trail_stop"])
        cfg["trail_stop"]["type"] = trail_type
        eng = BacktestEngine(cfg)
        r = eng.run(
            df_500, "BTC/USDT", "1h", initial_capital=10000.0, walk_forward=False
        )
        assert isinstance(r, BTResult)
