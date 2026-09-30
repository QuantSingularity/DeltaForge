"""Tests for ExchangeManager and BitflexAdapter (fully mocked)."""

from unittest.mock import MagicMock, patch

import pytest

from ..exchanges.bitflex_adapter import BitflexAdapter
from ..exchanges.exchange_manager import SUPPORTED_EXCHANGES, ExchangeManager


class TestBitflexAdapter:

    @pytest.fixture
    def adapter(self):
        return BitflexAdapter("key", "secret", "https://api.bitflex.com", sandbox=False)

    def test_sign_returns_hex_string(self, adapter):
        sig = adapter._sign("test_payload")
        assert isinstance(sig, str)
        assert len(sig) == 64  # SHA-256 hex digest

    def test_sign_different_payloads_differ(self, adapter):
        s1 = adapter._sign("payload_a")
        s2 = adapter._sign("payload_b")
        assert s1 != s2

    def test_load_markets_on_error_returns_empty(self, adapter):
        with patch.object(adapter._session, "get", side_effect=Exception("network")):
            markets = adapter.load_markets()
        assert markets == {}

    def test_fetch_ticker_on_error_returns_none(self, adapter):
        with patch.object(adapter._session, "get", side_effect=Exception("timeout")):
            result = adapter.fetch_ticker("BTC/USDT")
        assert result is None

    def test_fetch_ohlcv_on_error_returns_empty(self, adapter):
        with patch.object(adapter._session, "get", side_effect=Exception("err")):
            result = adapter.fetch_ohlcv("BTC/USDT", "1h")
        assert result == []

    def test_fetch_ticker_parses_response(self, adapter):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "data": {
                "lastPrice": "50000",
                "bidPrice": "49990",
                "askPrice": "50010",
                "volume": "1234",
            }
        }
        with patch.object(adapter._session, "get", return_value=mock_resp):
            t = adapter.fetch_ticker("BTC/USDT")
        assert t["last"] == 50000.0
        assert t["bid"] == 49990.0

    def test_amount_to_precision(self, adapter):
        adapter.markets["BTC/USDT"] = {"precision": {"amount": 3}}
        result = adapter.amount_to_precision("BTC/USDT", 0.123456)
        assert result == "0.123"

    def test_sandbox_changes_base_url(self, adapter):
        adapter.set_sandbox_mode(True)
        assert "testnet" in adapter.base_url

    def test_id_attribute(self, adapter):
        assert adapter.id == "bitflex"


class TestSupportedExchanges:

    def test_all_required_exchanges_present(self):
        required = [
            "binance",
            "bybit",
            "okx",
            "kucoin",
            "bingx",
            "bitget",
            "gateio",
            "mexc",
            "kraken",
        ]
        for ex in required:
            assert ex in SUPPORTED_EXCHANGES, f"Missing exchange: {ex}"

    def test_exchanges_are_ccxt_classes(self):
        for name, cls in SUPPORTED_EXCHANGES.items():
            assert callable(cls), f"{name} is not callable"

    def test_bitflex_not_in_ccxt_map(self):
        assert "bitflex" not in SUPPORTED_EXCHANGES


class TestExchangeManagerInit:

    def test_invalid_exchange_raises(self):
        with pytest.raises(ValueError, match="Unsupported exchange"):
            ExchangeManager("unknown_exchange", "key", "secret")

    def test_bitflex_uses_adapter(self):
        with patch(
            "backend.exchanges.bitflex_adapter.BitflexAdapter.load_markets",
            return_value={},
        ):
            mgr = ExchangeManager("bitflex", "key", "secret", sandbox=True)
        assert isinstance(mgr.exchange, BitflexAdapter)

    def test_ccxt_exchange_created(self):
        mock_cls = MagicMock()
        mock_inst = MagicMock()
        mock_inst.load_markets.return_value = {}
        mock_cls.return_value = mock_inst
        with patch.dict(
            "backend.exchanges.exchange_manager.SUPPORTED_EXCHANGES",
            {"mockex": mock_cls},
        ):
            mgr = ExchangeManager("mockex", "key", "secret", sandbox=False)
        assert mgr.exchange is mock_inst

    def test_get_free_balance_fallback(self):
        with patch(
            "backend.exchanges.bitflex_adapter.BitflexAdapter.load_markets",
            return_value={},
        ):
            mgr = ExchangeManager("bitflex", "key", "secret", sandbox=True)
        with patch.object(mgr.exchange, "fetch_balance", side_effect=Exception("auth")):
            bal = mgr.get_free_balance("USDT")
        assert bal == 0.0

    def test_fetch_ohlcv_returns_none_on_failure(self):
        with patch(
            "backend.exchanges.bitflex_adapter.BitflexAdapter.load_markets",
            return_value={},
        ):
            mgr = ExchangeManager("bitflex", "key", "secret", sandbox=True)
        with patch.object(mgr.exchange, "fetch_ohlcv", return_value=[]):
            result = mgr.fetch_ohlcv("BTC/USDT", "1h")
        # empty list is falsy - ExchangeManager should return None or []
        assert result == [] or result is None
