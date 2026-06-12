"""Tests for Notifier, TelegramChannel, and WebhookChannel."""

import json
from unittest.mock import MagicMock, patch

import pytest

from ..notifications.notifier import NotificationEvent, Notifier
from ..notifications.telegram import TelegramChannel
from ..notifications.webhook import WebhookChannel


@pytest.fixture
def notifier_disabled(base_config):
    cfg = dict(base_config)
    cfg["notifications"] = {"enabled": False}
    return Notifier(cfg)


@pytest.fixture
def notifier_enabled(base_config):
    cfg = dict(base_config)
    cfg["notifications"] = {
        "enabled": True,
        "telegram": {"enabled": False},
        "webhook": {"enabled": False},
    }
    return Notifier(cfg)


class TestNotificationEvent:

    def test_format_text_contains_type(self):
        ev = NotificationEvent(
            "TRADE ENTRY", symbol="BTC/USDT", side="buy", price=50000.0
        )
        text = ev.format_text()
        assert "TRADE ENTRY" in text
        assert "BTC/USDT" in text
        assert "BUY" in text

    def test_format_text_with_pnl(self):
        ev = NotificationEvent("EXIT", pnl=125.50)
        text = ev.format_text()
        assert "125.50" in text

    def test_missing_fields_dont_crash(self):
        ev = NotificationEvent("TEST")
        text = ev.format_text()
        assert "TEST" in text

    def test_all_convenience_fields(self):
        ev = NotificationEvent(
            "X",
            symbol="ETH/USDT",
            side="sell",
            price=3000.0,
            sl=3100.0,
            tp=2800.0,
            pnl=-50.0,
        )
        text = ev.format_text()
        for s in ("ETH/USDT", "SELL", "3000", "3100", "2800", "-50"):
            assert s in text, f"'{s}' not found in: {text}"


class TestNotifierDisabled:

    def test_send_does_not_raise(self, notifier_disabled):
        ev = NotificationEvent("TEST")
        notifier_disabled.send(ev)  # Should silently do nothing

    def test_no_channels_when_disabled(self, notifier_disabled):
        assert len(notifier_disabled._channels) == 0

    def test_trade_entry_no_raise(self, notifier_disabled):
        notifier_disabled.trade_entry(
            "BTC/USDT", "buy", 50000, 49000, 51000, 0.1, 75, "1h"
        )

    def test_trade_exit_no_raise(self, notifier_disabled):
        notifier_disabled.trade_exit("BTC/USDT", "buy", 51000, 100.0, "tp")

    def test_trail_update_no_raise(self, notifier_disabled):
        notifier_disabled.trail_update("BTC/USDT", "buy", 49000, 49500)

    def test_anomaly_no_raise(self, notifier_disabled):
        notifier_disabled.anomaly_detected("Spread too wide")

    def test_bot_started_no_raise(self, notifier_disabled):
        notifier_disabled.bot_started("binance")

    def test_bot_stopped_no_raise(self, notifier_disabled):
        notifier_disabled.bot_stopped("Manual")


class TestTelegramChannel:

    def test_send_calls_requests_post(self):
        ch = TelegramChannel("fake_token", "fake_chat")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch.object(ch._session, "post", return_value=mock_resp) as mock_post:
            ev = NotificationEvent("ENTRY", symbol="BTC/USDT")
            ch.send(ev)
            assert mock_post.called
            args, kwargs = mock_post.call_args
            payload = kwargs.get("json", {})
            assert payload["chat_id"] == "fake_chat"
            assert "DeltaForge" in payload["text"]

    def test_rate_limit_handled(self):
        ch = TelegramChannel("tok", "cid", max_retries=2)
        rate_limit_resp = MagicMock()
        rate_limit_resp.status_code = 429
        rate_limit_resp.json.return_value = {"parameters": {"retry_after": 0}}
        ok_resp = MagicMock()
        ok_resp.status_code = 200
        with patch.object(
            ch._session, "post", side_effect=[rate_limit_resp, ok_resp]
        ) as mp:
            ch.send(NotificationEvent("TEST"))
            assert mp.call_count == 2

    def test_network_error_retries(self):
        import requests

        ch = TelegramChannel("tok", "cid", max_retries=3)
        with patch.object(
            ch._session, "post", side_effect=requests.ConnectionError("timeout")
        ) as mp:
            ch.send(NotificationEvent("TEST"))  # Should not raise
            assert mp.call_count == 3


class TestWebhookChannel:

    def test_send_posts_json(self):
        ch = WebhookChannel("https://example.com/hook")
        mock_resp = MagicMock()
        mock_resp.ok = True
        with patch.object(ch._session, "post", return_value=mock_resp) as mp:
            ch.send(NotificationEvent("EXIT", symbol="BTC/USDT", pnl=50.0))
            assert mp.called
            _, kwargs = mp.call_args
            body = json.loads(kwargs["data"])
            assert body["symbol"] == "BTC/USDT"
            assert body["pnl"] == 50.0

    def test_non_ok_response_does_not_raise(self):
        ch = WebhookChannel("https://example.com/hook")
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 500
        with patch.object(ch._session, "post", return_value=mock_resp):
            ch.send(NotificationEvent("TEST"))  # Should not raise

    def test_custom_headers_included(self):
        ch = WebhookChannel(
            "https://example.com/hook", headers={"Authorization": "Bearer token123"}
        )
        assert ch._session.headers.get("Authorization") == "Bearer token123"
