"""
DeltaForge Trade Manager
Handles live order lifecycle: placement, SL/TP attachment,
trail stop updates (with display events), manual trade detection,
position tracking, and backtest-informed SL/TP for manual trades.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import pandas as pd

from ..exchanges.exchange_manager import ExchangeManager
from ..risk.risk_manager import RiskManager

logger = logging.getLogger("DeltaForge.TradeManager")

BOT_TAG = "DELTAFORGE"


@dataclass
class LiveTrade:
    symbol: str
    side: str
    entry_price: float
    amount: float
    sl: float
    tp: float
    order_id: str
    sl_order_id: str = ""
    tp_order_id: str = ""
    entry_time: float = field(default_factory=time.time)
    is_manual: bool = False
    peak_price: float = 0.0
    current_sl: float = 0.0
    trail_updated: bool = False  # True if trail moved since last display refresh
    timeframe: str = ""
    confluence: float = 0.0
    ml_score: float = 0.0
    strategies: str = ""
    features: list = field(default_factory=list)


class TradeManager:
    """
    Central order lifecycle manager.
    Accepts optional trail_event_cb(symbol, side, old_sl, new_sl) callback
    so the display layer can log trailing stop update events.
    """

    def __init__(
        self,
        exchange: ExchangeManager,
        risk: RiskManager,
        config: dict,
        trail_event_cb: Optional[Callable] = None,
    ):
        self.exchange = exchange
        self.risk = risk
        self.cfg = config
        self.risk_cfg = config.get("risk", {})
        self.trail_cfg = config.get("trail_stop", {})
        self._trades: Dict[str, LiveTrade] = {}
        self._trail_cb = trail_event_cb  # display callback for trail events

    # ─────────────────────────────────────────────────────────────
    # OPEN A NEW TRADE
    # ─────────────────────────────────────────────────────────────
    def open_trade(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        sl: float,
        tp: float,
        df: pd.DataFrame,
        timeframe: str = "",
        confluence: float = 0.0,
        ml_score: float = 0.0,
        strategies: str = "",
        features: list = None,
    ) -> Optional[LiveTrade]:
        balance = self.exchange.get_free_balance("USDT")
        amount, dollar_risk = self.risk.calculate_position_size(
            balance, entry_price, sl, symbol
        )

        ok, dr = self.risk.validate_dollar_risk(entry_price, sl, amount)
        if not ok:
            max_loss = self.risk_cfg.get("max_loss_per_trade", 50.0)
            sl_dist = abs(entry_price - sl)
            if sl_dist > 0:
                amount = max_loss / sl_dist
                amount = self.exchange.normalize_amount(symbol, amount)

        if amount * entry_price < self.exchange.get_min_notional(symbol):
            logger.warning(f"Position too small: ${amount*entry_price:.2f}")
            return None

        max_usdt = self.risk.max_dollar_crypto()
        if amount * entry_price > max_usdt:
            amount = max_usdt / entry_price
            amount = self.exchange.normalize_amount(symbol, amount)

        order = self.exchange.place_order(
            symbol=symbol,
            side=side,
            amount=amount,
            order_type="market",
            params={"newClientOrderId": f"{BOT_TAG}_{int(time.time())}"},
        )
        if not order:
            return None

        order_id = order.get("id", str(time.time()))
        actual_entry = float(order.get("average", order.get("price", entry_price)))
        if actual_entry == 0:
            actual_entry = entry_price

        if actual_entry != entry_price:
            sl, tp = self.risk.calculate_sl_tp(df, side, actual_entry)

        sl = self.exchange.normalize_price(symbol, sl)
        tp = self.exchange.normalize_price(symbol, tp) if tp else 0

        sl_order_id = ""
        if sl:
            sl_order = self.exchange.place_stop_loss(symbol, side, amount, sl)
            if sl_order:
                sl_order_id = sl_order.get("id", "")

        tp_order_id = ""
        if tp and self.risk.tp_enabled():
            tp_order = self.exchange.place_take_profit(symbol, side, amount, tp)
            if tp_order:
                tp_order_id = tp_order.get("id", "")

        trade = LiveTrade(
            symbol=symbol,
            side=side,
            entry_price=actual_entry,
            amount=amount,
            sl=sl,
            tp=tp,
            order_id=order_id,
            sl_order_id=sl_order_id,
            tp_order_id=tp_order_id,
            peak_price=actual_entry,
            current_sl=sl,
            trail_updated=False,
            timeframe=timeframe,
            confluence=confluence,
            ml_score=ml_score,
            strategies=strategies,
            features=features or [],
        )
        self._trades[order_id] = trade
        self.risk.register_trade(symbol, side, actual_entry, sl, amount, sl_order_id)

        logger.info(
            f"Trade opened: {side.upper()} {symbol} @ {actual_entry:.6f} | "
            f"Amount:{amount:.6f} | SL:{sl:.6f} | TP:{tp:.6f} | "
            f"Risk:${dollar_risk:.2f} | ML:{ml_score:.1f}%"
        )
        return trade

    # ─────────────────────────────────────────────────────────────
    # CLOSE A TRADE
    # ─────────────────────────────────────────────────────────────
    def close_trade(self, trade: LiveTrade, reason: str = "manual") -> bool:
        close_side = "sell" if trade.side == "buy" else "buy"
        order = self.exchange.place_order(
            symbol=trade.symbol,
            side=close_side,
            amount=trade.amount,
            order_type="market",
        )
        if not order:
            return False

        if trade.sl_order_id:
            self.exchange.cancel_order(trade.sl_order_id, trade.symbol)
        if trade.tp_order_id:
            self.exchange.cancel_order(trade.tp_order_id, trade.symbol)

        exit_price = float(order.get("average", order.get("price", 0)))
        if exit_price == 0:
            ticker = self.exchange.fetch_ticker(trade.symbol)
            exit_price = ticker["last"] if ticker else trade.sl

        pnl = (
            (exit_price - trade.entry_price) * trade.amount
            if trade.side == "buy"
            else (trade.entry_price - exit_price) * trade.amount
        )

        logger.info(
            f"Trade closed ({reason}): {trade.symbol} {trade.side.upper()} | "
            f"Exit:{exit_price:.6f} | PnL:${pnl:.2f}"
        )

        self._trades.pop(trade.order_id, None)
        self.risk.remove_trade(f"{trade.symbol}_{trade.side}_{trade.entry_price}")
        return True

    # ─────────────────────────────────────────────────────────────
    # TRAIL STOP UPDATE CYCLE
    # ─────────────────────────────────────────────────────────────
    def update_trail_stops(
        self, current_prices: Dict[str, float], df_map: Dict[str, pd.DataFrame]
    ):
        """
        Called every tick. Fires trail_event_cb for each SL that moves so
        the display can log TRAIL events in real time.
        """
        if not self.risk.trail_enabled():
            return

        # Risk.update_trail_stops now returns {key: (old_sl, new_sl)}
        updates = self.risk.update_trail_stops(current_prices, df_map)

        # Reset all trail_updated flags first
        for t in self._trades.values():
            t.trail_updated = False

        for trade_key, (old_sl, new_sl) in updates.items():
            trade = self._find_trade_by_key(trade_key)
            if not trade:
                continue

            new_sl_norm = self.exchange.normalize_price(trade.symbol, new_sl)

            if trade.sl_order_id:
                ok = self.exchange.modify_stop_loss(
                    trade.sl_order_id, trade.symbol, new_sl_norm
                )
                if ok:
                    old_sl_prev = trade.current_sl
                    trade.current_sl = new_sl_norm
                    trade.sl = new_sl_norm
                    trade.trail_updated = True
                    logger.info(
                        f"Trail updated {trade.symbol}: "
                        f"SL {old_sl_prev:.6f} → {new_sl_norm:.6f}"
                    )
                    if self._trail_cb:
                        self._trail_cb(
                            trade.symbol, trade.side, old_sl_prev, new_sl_norm
                        )
            else:
                sl_ord = self.exchange.place_stop_loss(
                    trade.symbol, trade.side, trade.amount, new_sl_norm
                )
                if sl_ord:
                    old_sl_prev = trade.current_sl
                    trade.sl_order_id = sl_ord.get("id", "")
                    trade.current_sl = new_sl_norm
                    trade.sl = new_sl_norm
                    trade.trail_updated = True
                    if self._trail_cb:
                        self._trail_cb(
                            trade.symbol, trade.side, old_sl_prev, new_sl_norm
                        )

    # ─────────────────────────────────────────────────────────────
    # MANUAL TRADE DETECTION
    # ─────────────────────────────────────────────────────────────
    def detect_and_fix_manual_trades(
        self, df_map: Dict[str, pd.DataFrame], bt_win_rates: Dict[str, float] = None
    ):
        """
        Auto-apply SL/TP to manual (non-bot) trades using:
          1. Saved backtest win rates (bt_win_rates: symbol -> win_rate%) for
             smarter ATR multiplier selection.
          2. ATR-based S/R adjustment as fallback.
        bt_win_rates: optional dict of {symbol: win_rate_pct} from backtest files.
        """
        positions = self.exchange.get_positions()
        bt_wr = bt_win_rates or {}

        for pos in positions:
            sym = pos.get("symbol", "")
            side = pos.get("side", "")
            entry = float(pos.get("entryPrice", pos.get("entry_price", 0)))
            sl = float(pos.get("stopLoss", pos.get("stop_loss", 0)))
            tp = float(pos.get("takeProfit", pos.get("take_profit", 0)))
            info = pos.get("info", {})
            order_id = str(pos.get("id", ""))

            if BOT_TAG in str(info.get("clientOrderId", "")):
                continue
            if order_id in self._trades:
                continue

            df = df_map.get(sym)
            if df is None:
                continue

            if sl == 0 or tp == 0:
                wr = bt_wr.get(sym, 0.0)
                new_sl, new_tp = self.risk.calculate_sl_tp(
                    df, side, entry, bt_win_rate=wr
                )
                if sl == 0:
                    sl = new_sl
                if tp == 0 and self.risk.tp_enabled():
                    tp = new_tp

                logger.info(
                    f"Auto SL/TP on manual trade {sym}: "
                    f"SL={sl:.6f} TP={tp:.6f} (bt_wr={wr:.0f}%)"
                )

                amt = float(pos.get("contracts", 0.001))
                if sl:
                    self.exchange.place_stop_loss(sym, side, amt, sl)
                if tp:
                    self.exchange.place_take_profit(sym, side, amt, tp)

                self.risk.register_trade(sym, side, entry, sl, amt, "")

    # ─────────────────────────────────────────────────────────────
    # SYNC CLOSED POSITIONS
    # ─────────────────────────────────────────────────────────────
    def sync_positions(self) -> List[dict]:
        """Reconcile internal state with exchange. Returns just-closed trades."""
        closed = []
        try:
            positions = self.exchange.get_positions()
            open_syms = {p.get("symbol", "") for p in positions}

            for oid, trade in list(self._trades.items()):
                if trade.symbol not in open_syms:
                    history = self.exchange.get_trade_history(trade.symbol, limit=10)
                    exit_price = trade.entry_price
                    for h in history:
                        if (
                            str(h.get("orderId", "")) == trade.sl_order_id
                            or str(h.get("orderId", "")) == trade.tp_order_id
                        ):
                            exit_price = float(h.get("price", exit_price))
                            break

                    pnl = (
                        (exit_price - trade.entry_price) * trade.amount
                        if trade.side == "buy"
                        else (trade.entry_price - exit_price) * trade.amount
                    )
                    closed.append(
                        {
                            "symbol": trade.symbol,
                            "side": trade.side,
                            "entry_price": trade.entry_price,
                            "exit_price": exit_price,
                            "pnl": round(pnl, 4),
                            "features": trade.features,
                            "direction": 1 if trade.side == "buy" else -1,
                            "confluence": trade.confluence,
                        }
                    )
                    del self._trades[oid]
        except Exception as e:
            logger.error(f"Sync error: {e}")

        return closed

    # ─────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────
    def _find_trade_by_key(self, key: str) -> Optional[LiveTrade]:
        for trade in self._trades.values():
            if f"{trade.symbol}_{trade.side}_{trade.entry_price}" == key:
                return trade
        return None

    def get_all_trades(self) -> List[LiveTrade]:
        return list(self._trades.values())

    def get_open_count(self, symbol: str = None) -> int:
        if symbol:
            return sum(1 for t in self._trades.values() if t.symbol == symbol)
        return len(self._trades)
