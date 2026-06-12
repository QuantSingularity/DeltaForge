"""Tests for DeltaForgeDisplay dashboard and EventLog."""

import pytest

from ..display.dashboard import DeltaForgeDisplay
from ..display.event_log import (
    EVT_ANOMALY,
    EVT_BUY_SIGNAL,
    EVT_ENTRY,
    EVT_EXIT_LOSS,
    EVT_EXIT_WIN,
    EVT_HTF_REJECT,
    EVT_INFO,
    EVT_ML_REJECT,
    EVT_SELL_SIGNAL,
    EVT_TRAIL,
    EVT_WARN,
    EventLog,
)


@pytest.fixture
def display(base_config):
    return DeltaForgeDisplay(base_config)


class TestEventLog:

    def test_add_event(self):
        log = EventLog()
        log.add(EVT_INFO, "test message")
        assert len(log._events) == 1

    def test_bounded_to_max(self):
        log = EventLog()
        for i in range(30):
            log.add(EVT_INFO, f"msg {i}")
        assert len(log._events) == EventLog.MAX

    def test_tail_returns_last_n(self):
        log = EventLog()
        for i in range(10):
            log.add(EVT_INFO, f"msg {i}")
        tail = log.tail(3)
        assert len(tail) == 3
        assert tail[-1]["msg"] == "msg 9"

    def test_clear_empties_log(self):
        log = EventLog()
        log.add(EVT_INFO, "x")
        log.clear()
        assert len(log._events) == 0

    def test_event_has_required_fields(self):
        log = EventLog()
        log.add(EVT_BUY_SIGNAL, "BUY signal")
        ev = log._events[0]
        assert "type" in ev and "msg" in ev and "ts" in ev

    def test_event_type_stored(self):
        log = EventLog()
        log.add(EVT_TRAIL, "trail moved")
        assert log._events[0]["type"] == EVT_TRAIL

    def test_color_override_stored(self):
        log = EventLog()
        log.add(EVT_INFO, "msg", color_override="cyan")
        assert log._events[0]["color_override"] == "cyan"

    @pytest.mark.parametrize(
        "evt_type",
        [
            EVT_BUY_SIGNAL,
            EVT_SELL_SIGNAL,
            EVT_ENTRY,
            EVT_EXIT_WIN,
            EVT_EXIT_LOSS,
            EVT_TRAIL,
            EVT_HTF_REJECT,
            EVT_ML_REJECT,
            EVT_ANOMALY,
            EVT_INFO,
            EVT_WARN,
        ],
    )
    def test_all_event_types_stored(self, evt_type):
        log = EventLog()
        log.add(evt_type, "test")
        assert log._events[0]["type"] == evt_type


class TestDeltaForgeDisplay:

    def test_instantiation(self, display):
        assert display is not None

    def test_set_bot_status_running(self, display):
        display.set_bot_status(True, "Started")
        assert display._bot_running is True

    def test_set_bot_status_stopped(self, display):
        display.set_bot_status(False, "Stopped")
        assert display._bot_running is False

    def test_update_signal(self, display):
        display.update_signal(
            symbol="BTC/USDT",
            timeframe="1h",
            direction=1,
            confluence=75.0,
            ml_score=80.0,
            probability=77.0,
            sl=49000.0,
            tp=52000.0,
            strategies=["macd(B)", "rsi(B)"],
        )
        assert "1h" in display._signals

    def test_update_signal_stores_all_fields(self, display):
        display.update_signal(
            "BTC/USDT", "4h", 1, 70.0, 75.0, 72.0, 49000.0, 52000.0, []
        )
        sig = display._signals["4h"]
        assert sig["symbol"] == "BTC/USDT"
        assert sig["direction"] == 1
        assert sig["confluence"] == 70.0
        assert sig["ml_score"] == 75.0
        assert sig["probability"] == 72.0

    def test_update_trades(self, display):
        trades = [
            {
                "symbol": "BTC/USDT",
                "side": "buy",
                "entry_price": 50000,
                "current_price": 51000,
                "sl": 49000,
                "tp": 53000,
                "amount": 0.1,
                "unrealized_pnl": 100.0,
                "timeframe": "1h",
                "ml_score": 78,
                "trail_updated": False,
            }
        ]
        display.update_trades(trades)
        assert len(display._trades) == 1

    def test_log_entry_adds_event(self, display):
        n_before = len(display._log._events)
        display.log_entry("BTC/USDT", "buy", 50000, 49000, 52000, 0.1, 78.0, "1h")
        assert len(display._log._events) == n_before + 1
        assert display._log._events[-1]["type"] == EVT_ENTRY

    def test_log_exit_win_adds_event(self, display):
        display.log_exit("BTC/USDT", "buy", 51000, 100.0, "tp")
        assert display._log._events[-1]["type"] == EVT_EXIT_WIN

    def test_log_exit_loss_adds_event(self, display):
        display.log_exit("BTC/USDT", "buy", 49000, -100.0, "sl")
        assert display._log._events[-1]["type"] == EVT_EXIT_LOSS

    def test_log_trail_update_adds_event(self, display):
        display.log_trail_update("BTC/USDT", "buy", 49000.0, 49500.0)
        assert display._log._events[-1]["type"] == EVT_TRAIL

    def test_buy_signal_adds_buy_event(self, display):
        display.update_signal("BTC/USDT", "15m", 1, 65.0, 70.0, 67.0, 49000, 52000, [])
        types = [e["type"] for e in display._log._events]
        assert EVT_BUY_SIGNAL in types

    def test_sell_signal_adds_sell_event(self, display):
        display.update_signal("BTC/USDT", "15m", -1, 65.0, 70.0, 67.0, 51000, 48000, [])
        types = [e["type"] for e in display._log._events]
        assert EVT_SELL_SIGNAL in types

    def test_render_does_not_raise(self, display):
        display.update_signal("BTC/USDT", "1h", 1, 70.0, 75.0, 72.0, 49000, 52000, [])
        display.update_trades([])
        display.update_stats({"total_pnl": 100.0, "total_trades": 5})
        try:
            display.render()
        except Exception as e:
            pytest.fail(f"render() raised: {e}")

    def test_config_colors_applied(self, display, base_config):
        assert display.c_buy == base_config["display"]["buy_color"]
        assert display.c_sell == base_config["display"]["sell_color"]
        assert display.c_sl == base_config["display"]["sl_color"]
        assert display.c_tp == base_config["display"]["tp_color"]
