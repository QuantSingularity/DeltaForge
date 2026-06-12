"""DeltaForge — ExchangeManager: unified factory for all 10 exchanges."""

"""
DeltaForge Exchange Manager
Supports: Binance, Bybit, OKX, KuCoin, Bitflex, BingX, Bitget, Gate.io, MEXC, Kraken
Uses ccxt for unified API access (spot + margin).
Bitflex uses a direct REST adapter (not in ccxt) with the same interface.
"""
import logging
import time
from typing import List, Optional

import ccxt

logger = logging.getLogger("DeltaForge.Exchange")


# ─────────────────────────────────────────────────────────────────────
# BITFLEX DIRECT REST ADAPTER
# ─────────────────────────────────────────────────────────────────────
from .bitflex_adapter import BitflexAdapter


class ExchangeManager:
    """
    Unified exchange interface for all 10 supported exchanges.
    Handles spot and margin trading, OHLCV fetching, order management.
    Bitflex uses a native REST adapter; all others use ccxt.
    """

    def __init__(
        self,
        exchange_id: str,
        api_key: str,
        api_secret: str,
        passphrase: str = "",
        trade_type: str = "spot",
        sandbox: bool = False,
        bitflex_base_url: str = "https://api.bitflex.com",
    ):
        self.exchange_id = exchange_id.lower()
        self.trade_type = trade_type
        self.sandbox = sandbox
        self._connected = False
        self.exchange = None
        self._init_exchange(api_key, api_secret, passphrase, bitflex_base_url)

    # ── INITIALISATION ────────────────────────────────────────────
    def _init_exchange(
        self, api_key: str, api_secret: str, passphrase: str, bitflex_base_url: str
    ):
        # ── Bitflex: native REST adapter ──────────────────────────
        if self.exchange_id == "bitflex":
            self.exchange = BitflexAdapter(
                api_key=api_key,
                api_secret=api_secret,
                base_url=bitflex_base_url,
                sandbox=self.sandbox,
            )
            if self.sandbox:
                self.exchange.set_sandbox_mode(True)
                logger.info("[bitflex] Sandbox mode ENABLED")
            try:
                self.exchange.load_markets()
                self._connected = True
                logger.info(
                    f"[bitflex] Connected | {len(self.exchange.markets)} markets loaded"
                )
            except Exception as e:
                logger.error(f"[bitflex] Connection failed: {e}")
            return

        # ── ccxt exchanges ────────────────────────────────────────
        if self.exchange_id not in SUPPORTED_EXCHANGES:
            raise ValueError(
                f"Unsupported exchange: {self.exchange_id}. "
                f"Choose from: {list(SUPPORTED_EXCHANGES.keys()) + ['bitflex']}"
            )

        cls = SUPPORTED_EXCHANGES[self.exchange_id]
        params = {
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {"defaultType": self.trade_type},
        }
        if passphrase:
            params["password"] = passphrase

        # Exchange-specific option overrides
        if self.exchange_id == "binance":
            params["options"]["defaultType"] = (
                "margin" if self.trade_type == "margin" else "spot"
            )
        if self.exchange_id == "bybit":
            params["options"]["defaultType"] = (
                "linear" if self.trade_type == "margin" else "spot"
            )
        if self.exchange_id == "okx":
            params["options"]["defaultType"] = (
                "margin" if self.trade_type == "margin" else "spot"
            )

        self.exchange = cls(params)

        if self.sandbox:
            self.exchange.set_sandbox_mode(True)
            logger.info(f"[{self.exchange_id}] Sandbox mode ENABLED")

        try:
            self.exchange.load_markets()
            self._connected = True
            logger.info(
                f"[{self.exchange_id}] Connected | "
                f"{len(self.exchange.markets)} markets loaded"
            )
        except Exception as e:
            logger.error(f"[{self.exchange_id}] Connection failed: {e}")
            self._connected = False

    # ── MARKET DATA ───────────────────────────────────────────────
    def fetch_ohlcv(
        self, symbol: str, timeframe: str, limit: int = 500
    ) -> Optional[list]:
        tf_map = {"15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}
        tf = tf_map.get(timeframe, timeframe)

        for attempt in range(3):
            try:
                return self.exchange.fetch_ohlcv(symbol, tf, limit=limit)
            except ccxt.RateLimitExceeded:
                time.sleep(2**attempt)
            except AttributeError:
                # BitflexAdapter fetch_ohlcv doesn't raise ccxt errors
                return self.exchange.fetch_ohlcv(symbol, tf, limit=limit)
            except Exception as e:
                logger.warning(f"[{self.exchange_id}] OHLCV error {symbol}/{tf}: {e}")
                return None
        return None

    def fetch_ticker(self, symbol: str) -> Optional[dict]:
        try:
            return self.exchange.fetch_ticker(symbol)
        except Exception as e:
            logger.error(f"[{self.exchange_id}] Ticker error {symbol}: {e}")
            return None

    def fetch_orderbook(self, symbol: str, limit: int = 20) -> Optional[dict]:
        try:
            return self.exchange.fetch_order_book(symbol, limit)
        except Exception as e:
            logger.error(f"[{self.exchange_id}] Orderbook error {symbol}: {e}")
            return None

    def get_balance(self) -> dict:
        try:
            bal = self.exchange.fetch_balance()
            return bal.get("total", {})
        except Exception as e:
            logger.error(f"[{self.exchange_id}] Balance error: {e}")
            return {}

    def get_free_balance(self, currency: str = "USDT") -> float:
        try:
            bal = self.exchange.fetch_balance()
            return float(bal.get("free", {}).get(currency, 0))
        except Exception as e:
            logger.error(f"Balance error: {e}")
            return 0.0

    # ── ORDER MANAGEMENT ──────────────────────────────────────────
    def place_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float = None,
        order_type: str = "market",
        sl: float = None,
        tp: float = None,
        params: dict = None,
    ) -> Optional[dict]:
        if not self._connected:
            logger.error("Exchange not connected")
            return None

        extra = params or {}
        if sl or tp:
            extra.update(self._build_sltp_params(symbol, side, sl, tp))

        for attempt in range(3):
            try:
                if order_type == "market":
                    order = self.exchange.create_market_order(
                        symbol, side, amount, params=extra
                    )
                else:
                    if price is None:
                        ticker = self.fetch_ticker(symbol)
                        price = ticker["last"] if ticker else 0
                    order = self.exchange.create_limit_order(
                        symbol, side, amount, price, params=extra
                    )

                logger.info(
                    f"[{self.exchange_id}] Order placed: {side.upper()} "
                    f"{amount} {symbol} | ID: {order.get('id','?')} | "
                    f"SL: {sl} TP: {tp}"
                )
                return order

            except Exception as e:
                if (
                    "InsufficientFunds" in type(e).__name__
                    or "insufficient" in str(e).lower()
                ):
                    logger.error(f"Insufficient funds: {e}")
                    return None
                if "RateLimitExceeded" in type(e).__name__:
                    time.sleep(2**attempt)
                    continue
                logger.error(f"[{self.exchange_id}] Order error: {e}")
                if attempt == 2:
                    return None

        return None

    def _build_sltp_params(self, symbol: str, side: str, sl: float, tp: float) -> dict:
        p = {}
        if self.exchange_id == "bybit":
            if sl:
                p["stopLoss"] = str(sl)
            if tp:
                p["takeProfit"] = str(tp)
        elif self.exchange_id == "okx":
            if sl:
                p["slTriggerPx"] = str(sl)
            if tp:
                p["tpTriggerPx"] = str(tp)
        elif self.exchange_id == "kucoin":
            if sl:
                p["stopPrice"] = str(sl)
        elif self.exchange_id == "bitflex":
            if sl:
                p["stopLoss"] = str(sl)
            if tp:
                p["takeProfit"] = str(tp)
        return p

    def place_stop_loss(
        self, symbol: str, side: str, amount: float, stop_price: float
    ) -> Optional[dict]:
        try:
            close_side = "sell" if side == "buy" else "buy"
            if self.exchange_id == "binance":
                return self.exchange.create_order(
                    symbol,
                    "STOP_LOSS_LIMIT",
                    close_side,
                    amount,
                    stop_price * 0.998,
                    params={"stopPrice": stop_price, "timeInForce": "GTC"},
                )
            elif self.exchange_id == "bitflex":
                return self.exchange.create_order(
                    symbol,
                    "STOP_LOSS",
                    close_side,
                    amount,
                    stop_price,
                    params={"stopPrice": stop_price},
                )
            else:
                return self.exchange.create_order(
                    symbol,
                    "stop",
                    close_side,
                    amount,
                    stop_price,
                    params={"stopPrice": stop_price},
                )
        except Exception as e:
            logger.error(f"SL order error: {e}")
            return None

    def place_take_profit(
        self, symbol: str, side: str, amount: float, tp_price: float
    ) -> Optional[dict]:
        try:
            close_side = "sell" if side == "buy" else "buy"
            return self.exchange.create_limit_order(
                symbol, close_side, amount, tp_price
            )
        except Exception as e:
            logger.error(f"TP order error: {e}")
            return None

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        try:
            self.exchange.cancel_order(order_id, symbol)
            logger.info(f"[{self.exchange_id}] Order {order_id} cancelled")
            return True
        except Exception as e:
            logger.error(f"Cancel error: {e}")
            return False

    def modify_stop_loss(self, order_id: str, symbol: str, new_sl: float) -> bool:
        try:
            order = self.exchange.fetch_order(order_id, symbol)
            if order:
                self.cancel_order(order_id, symbol)
                time.sleep(0.3)
                side = order.get("side", "sell")
                amnt = order.get("remaining", order.get("amount", 0))
                new_o = self.place_stop_loss(symbol, side, amnt, new_sl)
                return new_o is not None
        except Exception as e:
            logger.error(f"Modify SL error: {e}")
        return False

    def get_open_orders(self, symbol: str = None) -> List[dict]:
        try:
            return self.exchange.fetch_open_orders(symbol) or []
        except Exception as e:
            logger.error(f"Open orders error: {e}")
            return []

    def get_positions(self, symbol: str = None) -> List[dict]:
        try:
            if hasattr(self.exchange, "fetch_positions"):
                pos = self.exchange.fetch_positions([symbol] if symbol else None)
                return [p for p in pos if float(p.get("contracts", 0)) != 0]
            return []
        except Exception as e:
            logger.error(f"Positions error: {e}")
            return []

    def get_trade_history(self, symbol: str, limit: int = 100) -> List[dict]:
        try:
            return self.exchange.fetch_my_trades(symbol, limit=limit) or []
        except Exception as e:
            logger.error(f"Trade history error: {e}")
            return []

    # ── SYMBOL INFO ───────────────────────────────────────────────
    def get_min_notional(self, symbol: str) -> float:
        try:
            mkt = self.exchange.market(symbol)
            return float(mkt.get("limits", {}).get("cost", {}).get("min", 10))
        except:
            return 10.0

    def get_min_amount(self, symbol: str) -> float:
        try:
            mkt = self.exchange.market(symbol)
            return float(mkt.get("limits", {}).get("amount", {}).get("min", 0.001))
        except:
            return 0.001

    def get_price_precision(self, symbol: str) -> int:
        try:
            mkt = self.exchange.market(symbol)
            return int(mkt.get("precision", {}).get("price", 8))
        except:
            return 8

    def get_amount_precision(self, symbol: str) -> int:
        try:
            mkt = self.exchange.market(symbol)
            return int(mkt.get("precision", {}).get("amount", 4))
        except:
            return 4

    def normalize_amount(self, symbol: str, amount: float) -> float:
        try:
            return float(self.exchange.amount_to_precision(symbol, amount))
        except:
            return round(amount, 4)

    def normalize_price(self, symbol: str, price: float) -> float:
        try:
            return float(self.exchange.price_to_precision(symbol, price))
        except:
            return round(price, 8)

    @property
    def is_connected(self) -> bool:
        return self._connected

    def get_server_time(self) -> int:
        try:
            return self.exchange.fetch_time()
        except:
            return int(time.time() * 1000)
