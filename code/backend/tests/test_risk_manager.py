"""Comprehensive tests for RiskManager, TrailEngine, and PositionSizer."""

import pytest
from testkit import make_ohlcv as _make_ohlcv

from ..risk.risk_manager import RiskManager
from ..risk.trail_engine import TrailEngine


@pytest.fixture
def risk(base_config):
    return RiskManager(base_config)


@pytest.fixture
def df():
    return _make_ohlcv(300)


class TestPositionSizing:

    def test_basic_sizing(self, risk, df):
        amount, dollar_risk = risk.calculate_position_size(
            balance_usdt=10000.0,
            entry_price=50000.0,
            sl_price=49000.0,
            symbol="BTC/USDT",
        )
        assert amount > 0
        assert dollar_risk > 0

    def test_max_loss_respected(self, risk, df):
        amount, dollar_risk = risk.calculate_position_size(
            balance_usdt=100000.0,
            entry_price=50000.0,
            sl_price=40000.0,
            symbol="BTC/USDT",
        )
        max_loss = risk.risk_cfg.get("max_loss_per_trade", 50.0)
        assert dollar_risk <= max_loss + 0.01

    def test_max_crypto_position_respected(self, risk, df):
        amount, _ = risk.calculate_position_size(
            balance_usdt=1_000_000.0,
            entry_price=50000.0,
            sl_price=49000.0,
            symbol="BTC/USDT",
        )
        max_usdt = risk.max_dollar_crypto()
        assert amount * 50000.0 <= max_usdt + 1.0

    def test_zero_sl_distance_handled(self, risk):
        amount, _ = risk.calculate_position_size(
            balance_usdt=10000.0,
            entry_price=50000.0,
            sl_price=50000.0,
            symbol="BTC/USDT",
        )
        assert amount > 0  # Falls back to 1% SL distance

    def test_dollar_risk_validation_pass(self, risk):
        ok, dr = risk.validate_dollar_risk(50000.0, 49500.0, 0.005)
        assert ok  # 0.005 BTC × $500 SL = $2.50 risk — well under $50

    def test_dollar_risk_validation_fail(self, risk):
        ok, dr = risk.validate_dollar_risk(50000.0, 45000.0, 1.0)
        assert not ok  # 1 BTC × $5000 SL = $5000 — way over $50


class TestSLTPCalculation:

    def test_buy_sl_below_entry(self, risk, df):
        sl, tp = risk.calculate_sl_tp(df, "buy", 50000.0)
        assert sl < 50000.0, f"Buy SL {sl} must be below entry 50000"

    def test_sell_sl_above_entry(self, risk, df):
        sl, tp = risk.calculate_sl_tp(df, "sell", 50000.0)
        assert sl > 50000.0, f"Sell SL {sl} must be above entry 50000"

    def test_buy_tp_above_entry(self, risk, df):
        sl, tp = risk.calculate_sl_tp(df, "buy", 50000.0)
        assert tp > 50000.0, f"Buy TP {tp} must be above entry 50000"

    def test_sell_tp_below_entry(self, risk, df):
        sl, tp = risk.calculate_sl_tp(df, "sell", 50000.0)
        assert tp < 50000.0, f"Sell TP {tp} must be below entry 50000"

    def test_rr_ratio_respected(self, risk, df):
        sl, tp = risk.calculate_sl_tp(df, "buy", 50000.0)
        sl_dist = 50000.0 - sl
        tp_dist = tp - 50000.0
        rr = risk.risk_cfg.get("tp_rr_ratio", 2.0)
        assert tp_dist >= sl_dist * rr * 0.8, "TP does not respect R:R ratio"

    def test_high_bt_winrate_widens_sl(self, risk, df):
        sl_normal, _ = risk.calculate_sl_tp(df, "buy", 50000.0, bt_win_rate=0.0)
        sl_high, _ = risk.calculate_sl_tp(df, "buy", 50000.0, bt_win_rate=80.0)
        assert sl_high <= sl_normal, "High win-rate should widen (lower) buy SL"

    def test_sl_tp_non_zero(self, risk, df):
        sl, tp = risk.calculate_sl_tp(df, "buy", 50000.0)
        assert sl != 0 and tp != 0


class TestTrailEngine:

    def test_register_and_retrieve(self, base_config):
        engine = TrailEngine(base_config["trail_stop"])
        engine.register_trade("BTC/USDT", "buy", 50000.0, 49000.0, 0.1)
        states = engine.get_all_trail_states()
        assert len(states) == 1

    @pytest.mark.parametrize(
        "trail_type", ["atr", "percent", "dollar", "time", "volatility"]
    )
    def test_all_trail_types(self, base_config, trail_type, df):
        cfg = dict(base_config["trail_stop"])
        cfg["type"] = trail_type
        engine = TrailEngine(cfg)
        engine.register_trade("BTC/USDT", "buy", 50000.0, 49000.0, 0.1)
        prices = {"BTC/USDT": 51000.0}
        updates = engine.update_trail_stops(prices, {"BTC/USDT": df})
        # Should either move SL or stay — no exceptions
        assert isinstance(updates, dict)

    def test_trail_only_moves_favourably_buy(self, base_config, df):
        """Trail SL for BUY must only move UP."""
        cfg = dict(base_config["trail_stop"])
        cfg["type"] = "percent"
        cfg["percent"] = 1.0
        engine = TrailEngine(cfg)
        engine.register_trade("BTC/USDT", "buy", 50000.0, 49000.0, 0.1)
        key = "BTC/USDT_buy_50000.0"
        state = engine.get_all_trail_states().get(key)
        if state is None:
            key = list(engine.get_all_trail_states().keys())[0]
            state = engine.get_all_trail_states()[key]
        original_sl = state.current_sl
        # Price rises
        engine.update_trail_stops({"BTC/USDT": 52000.0}, {"BTC/USDT": df})
        new_sl = engine.get_all_trail_states()[key].current_sl
        assert new_sl >= original_sl, "Buy SL must never move down"

    def test_trail_only_moves_favourably_sell(self, base_config, df):
        """Trail SL for SELL must only move DOWN."""
        cfg = dict(base_config["trail_stop"])
        cfg["type"] = "percent"
        cfg["percent"] = 1.0
        engine = TrailEngine(cfg)
        engine.register_trade("BTC/USDT", "sell", 50000.0, 51000.0, 0.1)
        key = list(engine.get_all_trail_states().keys())[0]
        original_sl = engine.get_all_trail_states()[key].current_sl
        engine.update_trail_stops({"BTC/USDT": 48000.0}, {"BTC/USDT": df})
        new_sl = engine.get_all_trail_states()[key].current_sl
        assert new_sl <= original_sl, "Sell SL must never move up"

    def test_remove_trade(self, base_config):
        engine = TrailEngine(base_config["trail_stop"])
        engine.register_trade("BTC/USDT", "buy", 50000.0, 49000.0, 0.1)
        key = list(engine.get_all_trail_states().keys())[0]
        engine.remove_trade(key)
        assert len(engine.get_all_trail_states()) == 0


class TestOrderGating:

    def test_can_place_within_limits(self, risk):
        ok, msg = risk.can_place_order([], [], "BTC/USDT", "buy")
        assert ok

    def test_max_total_orders_blocks(self, risk, base_config):
        n = base_config["risk"]["max_total_orders"]
        fake = [{"symbol": "BTC/USDT", "side": "buy"}] * n
        ok, msg = risk.can_place_order(fake, [], "ETH/USDT", "buy")
        assert not ok
        assert "max total" in msg.lower()

    def test_max_pair_orders_blocks(self, risk, base_config):
        n = base_config["risk"]["max_orders_per_pair"]
        fake = [{"symbol": "BTC/USDT", "side": "buy"}] * n
        ok, msg = risk.can_place_order(fake, [], "BTC/USDT", "buy")
        assert not ok

    def test_max_buy_orders_blocks(self, risk, base_config):
        n = base_config["risk"]["max_buy_orders"]
        fake = [{"symbol": f"COIN{i}/USDT", "side": "buy"} for i in range(n)]
        ok, msg = risk.can_place_order(fake, [], "ETH/USDT", "buy")
        assert not ok

    def test_sell_order_allowed_when_buy_full(self, risk, base_config):
        n = base_config["risk"]["max_buy_orders"]
        fake = [{"symbol": f"COIN{i}/USDT", "side": "buy"} for i in range(n)]
        ok, msg = risk.can_place_order(fake, [], "ETH/USDT", "sell")
        assert ok
