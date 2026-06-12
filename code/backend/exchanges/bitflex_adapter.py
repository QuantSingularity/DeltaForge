"""DeltaForge — Bitflex native REST adapter."""

"""
DeltaForge Exchange Manager
Supports: Binance, Bybit, OKX, KuCoin, Bitflex, BingX, Bitget, Gate.io, MEXC, Kraken
Uses ccxt for unified API access (spot + margin).
Bitflex uses a direct REST adapter (not in ccxt) with the same interface.
"""
import hashlib
import hmac
import json
import logging
import time
from typing import Dict, List, Optional

import ccxt
import requests

logger = logging.getLogger("DeltaForge.Exchange")


# ─────────────────────────────────────────────────────────────────────
# BITFLEX DIRECT REST ADAPTER
# ─────────────────────────────────────────────────────────────────────
from .base import BaseExchange


class BitflexAdapter(BaseExchange):
    """
    Direct REST adapter for Bitflex exchange.
    Implements the same interface used by ccxt exchanges so
    ExchangeManager can treat it identically to ccxt instances.
    Base URL: https://api.bitflex.com
    """

    TIMEFRAME_MAP = {
        "15m": "15m",
        "1h": "1h",
        "4h": "4h",
        "1d": "1d",
    }

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://api.bitflex.com",
        sandbox: bool = False,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.sandbox = sandbox
        self.markets: Dict[str, dict] = {}
        self.id = "bitflex"
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Content-Type": "application/json",
                "X-BF-APIKEY": api_key,
            }
        )

    # ── Auth ──────────────────────────────────────────────────────
    def _sign(self, payload: str) -> str:
        return hmac.new(
            self.api_secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()

    def _get(self, path: str, params: dict = None) -> dict:
        url = f"{self.base_url}{path}"
        r = self._session.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, data: dict = None) -> dict:
        data = data or {}
        ts = str(int(time.time() * 1000))
        body = json.dumps(data, separators=(",", ":"))
        sig = self._sign(ts + "POST" + path + body)
        headers = {"X-BF-TIMESTAMP": ts, "X-BF-SIGNATURE": sig}
        url = f"{self.base_url}{path}"
        r = self._session.post(url, data=body, headers=headers, timeout=10)
        r.raise_for_status()
        return r.json()

    # ── Market data ───────────────────────────────────────────────
    def load_markets(self) -> dict:
        try:
            data = self._get("/v1/markets")
            self.markets = {
                m["symbol"]: {
                    "symbol": m["symbol"],
                    "base": m.get("baseAsset", ""),
                    "quote": m.get("quoteAsset", ""),
                    "precision": {
                        "price": m.get("pricePrecision", 8),
                        "amount": m.get("amountPrecision", 4),
                    },
                    "limits": {
                        "amount": {"min": float(m.get("minQty", 0.001))},
                        "cost": {"min": float(m.get("minNotional", 10))},
                    },
                }
                for m in data.get("data", [])
            }
        except Exception as e:
            logger.warning(
                f"[bitflex] load_markets error: {e} — using empty market list"
            )
            self.markets = {}
        return self.markets

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> list:
        tf = self.TIMEFRAME_MAP.get(timeframe, timeframe)
        sym = symbol.replace("/", "")
        try:
            data = self._get(
                "/v1/klines", {"symbol": sym, "interval": tf, "limit": limit}
            )
            raw = data.get("data", [])
            return [
                [
                    int(k[0]),
                    float(k[1]),
                    float(k[2]),
                    float(k[3]),
                    float(k[4]),
                    float(k[5]),
                ]
                for k in raw
            ]
        except Exception as e:
            logger.error(f"[bitflex] OHLCV error {symbol}: {e}")
            return []

    def fetch_ticker(self, symbol: str) -> Optional[dict]:
        sym = symbol.replace("/", "")
        try:
            data = self._get(f"/v1/ticker/24hr", {"symbol": sym})
            d = data.get("data", {})
            return {
                "symbol": symbol,
                "last": float(d.get("lastPrice", 0)),
                "bid": float(d.get("bidPrice", 0)),
                "ask": float(d.get("askPrice", 0)),
                "volume": float(d.get("volume", 0)),
                "quoteVolume": float(d.get("quoteVolume", 0)),
            }
        except Exception as e:
            logger.error(f"[bitflex] Ticker error {symbol}: {e}")
            return None

    def fetch_order_book(self, symbol: str, limit: int = 20) -> Optional[dict]:
        sym = symbol.replace("/", "")
        try:
            data = self._get("/v1/depth", {"symbol": sym, "limit": limit})
            d = data.get("data", {})
            return {
                "bids": [[float(p), float(q)] for p, q in d.get("bids", [])],
                "asks": [[float(p), float(q)] for p, q in d.get("asks", [])],
            }
        except Exception as e:
            logger.error(f"[bitflex] Orderbook error: {e}")
            return None

    def fetch_balance(self) -> dict:
        try:
            data = self._post("/v1/account/balance")
            total = {}
            free = {}
            for b in data.get("data", {}).get("balances", []):
                asset = b.get("asset", "")
                total[asset] = float(b.get("total", 0))
                free[asset] = float(b.get("available", 0))
            return {"total": total, "free": free}
        except Exception as e:
            logger.error(f"[bitflex] Balance error: {e}")
            return {"total": {}, "free": {}}

    def create_market_order(
        self, symbol: str, side: str, amount: float, params: dict = None
    ) -> Optional[dict]:
        sym = symbol.replace("/", "")
        body = {
            "symbol": sym,
            "side": side.upper(),
            "type": "MARKET",
            "quantity": str(amount),
        }
        if params:
            if "stopLoss" in params:
                body["stopLoss"] = params["stopLoss"]
            if "takeProfit" in params:
                body["takeProfit"] = params["takeProfit"]
        try:
            data = self._post("/v1/order", body)
            order = data.get("data", {})
            return {
                "id": str(order.get("orderId", "")),
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "average": float(order.get("avgPrice", 0)),
                "status": order.get("status", ""),
            }
        except Exception as e:
            logger.error(f"[bitflex] Market order error: {e}")
            return None

    def create_limit_order(
        self, symbol: str, side: str, amount: float, price: float, params: dict = None
    ) -> Optional[dict]:
        sym = symbol.replace("/", "")
        body = {
            "symbol": sym,
            "side": side.upper(),
            "type": "LIMIT",
            "quantity": str(amount),
            "price": str(price),
        }
        try:
            data = self._post("/v1/order", body)
            order = data.get("data", {})
            return {
                "id": str(order.get("orderId", "")),
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "price": price,
                "status": order.get("status", ""),
            }
        except Exception as e:
            logger.error(f"[bitflex] Limit order error: {e}")
            return None

    def create_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: float = None,
        params: dict = None,
    ):
        if order_type.upper() == "MARKET":
            return self.create_market_order(symbol, side, amount, params)
        return self.create_limit_order(symbol, side, amount, price or 0, params)

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        sym = symbol.replace("/", "")
        try:
            self._post("/v1/order/cancel", {"orderId": order_id, "symbol": sym})
            return True
        except Exception as e:
            logger.error(f"[bitflex] Cancel error: {e}")
            return False

    def fetch_order(self, order_id: str, symbol: str) -> Optional[dict]:
        sym = symbol.replace("/", "")
        try:
            data = self._get("/v1/order", {"orderId": order_id, "symbol": sym})
            order = data.get("data", {})
            return {
                "id": str(order.get("orderId", "")),
                "symbol": symbol,
                "side": order.get("side", "").lower(),
                "amount": float(order.get("quantity", 0)),
                "remaining": float(order.get("remaining", 0)),
                "status": order.get("status", ""),
            }
        except Exception as e:
            logger.error(f"[bitflex] Fetch order error: {e}")
            return None

    def fetch_open_orders(self, symbol: str = None) -> List[dict]:
        params = {}
        if symbol:
            params["symbol"] = symbol.replace("/", "")
        try:
            data = self._post("/v1/openOrders", params)
            return [
                {
                    "id": str(o.get("orderId", "")),
                    "symbol": o.get("symbol", ""),
                    "side": o.get("side", "").lower(),
                    "amount": float(o.get("quantity", 0)),
                    "price": float(o.get("price", 0)),
                    "status": o.get("status", ""),
                }
                for o in data.get("data", [])
            ]
        except Exception as e:
            logger.error(f"[bitflex] Open orders error: {e}")
            return []

    def fetch_positions(self, symbols=None) -> List[dict]:
        # Bitflex spot — no margin positions
        return []

    def fetch_my_trades(self, symbol: str, limit: int = 100) -> List[dict]:
        sym = symbol.replace("/", "")
        try:
            data = self._post("/v1/myTrades", {"symbol": sym, "limit": limit})
            return [
                {
                    "id": str(t.get("tradeId", "")),
                    "symbol": symbol,
                    "side": t.get("side", "").lower(),
                    "price": float(t.get("price", 0)),
                    "amount": float(t.get("quantity", 0)),
                    "orderId": str(t.get("orderId", "")),
                }
                for t in data.get("data", [])
            ]
        except Exception as e:
            logger.error(f"[bitflex] Trade history error: {e}")
            return []

    def fetch_time(self) -> int:
        try:
            data = self._get("/v1/time")
            return int(data.get("serverTime", int(time.time() * 1000)))
        except:
            return int(time.time() * 1000)

    # ccxt compatibility helpers
    def market(self, symbol: str) -> dict:
        return self.markets.get(symbol, {})

    def set_sandbox_mode(self, enabled: bool):
        if enabled:
            self.base_url = "https://testnet.bitflex.com"

    def amount_to_precision(self, symbol: str, amount: float) -> str:
        prec = self.markets.get(symbol, {}).get("precision", {}).get("amount", 4)
        return f"{amount:.{prec}f}"

    def price_to_precision(self, symbol: str, price: float) -> str:
        prec = self.markets.get(symbol, {}).get("precision", {}).get("price", 8)
        return f"{price:.{prec}f}"


# ─────────────────────────────────────────────────────────────────────
# EXCHANGE REGISTRY
# ─────────────────────────────────────────────────────────────────────
SUPPORTED_EXCHANGES = {
    "binance": ccxt.binance,
    "bybit": ccxt.bybit,
    "okx": ccxt.okx,
    "kucoin": ccxt.kucoin,
    "bingx": ccxt.bingx,
    "bitget": ccxt.bitget,
    "gateio": ccxt.gateio,
    "mexc": ccxt.mexc,
    "kraken": ccxt.kraken,
    # Bitflex handled via BitflexAdapter below
}
