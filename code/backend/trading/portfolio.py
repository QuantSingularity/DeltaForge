"""
DeltaForge Portfolio Tracker
Tracks capital allocation, realised P&L, drawdown, win/loss metrics,
and per-symbol performance — all missing from the original codebase.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger("DeltaForge.Portfolio")


@dataclass
class ClosedTrade:
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    amount: float
    pnl: float
    open_time: float
    close_time: float
    exit_reason: str  # "sl" | "tp" | "trail" | "manual"
    timeframe: str = ""
    strategy: str = ""


@dataclass
class SymbolStats:
    symbol: str
    trades: int = 0
    wins: int = 0
    losses: int = 0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0

    @property
    def win_rate(self) -> float:
        return self.wins / self.trades * 100 if self.trades else 0

    @property
    def net_pnl(self) -> float:
        return self.gross_profit + self.gross_loss

    @property
    def profit_factor(self) -> float:
        return (
            self.gross_profit / abs(self.gross_loss)
            if self.gross_loss != 0
            else float("inf")
        )


class Portfolio:
    """
    Single source of truth for:
    - Session / all-time P&L
    - Capital allocation (total, deployed, free)
    - Per-symbol performance breakdowns
    - Drawdown tracking
    - Win/loss streak counters
    """

    def __init__(self, initial_capital: float = 10_000.0):
        self.initial_capital = initial_capital
        self._peak_equity = initial_capital
        self._current_equity = initial_capital
        self._session_start = time.time()

        self._closed: List[ClosedTrade] = []
        self._symbol_stats: Dict[str, SymbolStats] = defaultdict(
            lambda: SymbolStats(symbol="")
        )

        # Streak tracking
        self._current_streak: int = 0  # + = wins, - = losses
        self._max_win_streak: int = 0
        self._max_loss_streak: int = 0

        # Deployed capital (sum of open position values)
        self._deployed: float = 0.0

    # ── Record a closed trade ─────────────────────────────────────────
    def record_close(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        exit_price: float,
        amount: float,
        pnl: float,
        open_time: float,
        exit_reason: str = "manual",
        timeframe: str = "",
        strategy: str = "",
    ) -> ClosedTrade:
        ct = ClosedTrade(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            exit_price=exit_price,
            amount=amount,
            pnl=round(pnl, 6),
            open_time=open_time,
            close_time=time.time(),
            exit_reason=exit_reason,
            timeframe=timeframe,
            strategy=strategy,
        )
        self._closed.append(ct)

        # Equity update
        self._current_equity += pnl
        if self._current_equity > self._peak_equity:
            self._peak_equity = self._current_equity

        # Symbol stats
        ss = self._symbol_stats[symbol]
        ss.symbol = symbol
        ss.trades += 1
        if pnl > 0:
            ss.wins += 1
            ss.gross_profit += pnl
            ss.largest_win = max(ss.largest_win, pnl)
            self._current_streak = max(self._current_streak + 1, 1)
            self._max_win_streak = max(self._max_win_streak, self._current_streak)
        else:
            ss.losses += 1
            ss.gross_loss += pnl
            ss.largest_loss = min(ss.largest_loss, pnl)
            self._current_streak = min(self._current_streak - 1, -1)
            self._max_loss_streak = max(
                self._max_loss_streak, abs(self._current_streak)
            )

        logger.info(
            f"Trade closed [{exit_reason.upper()}] {symbol} {side.upper()} | "
            f"PnL ${pnl:+.4f} | Equity ${self._current_equity:,.2f}"
        )
        return ct

    # ── Deployed capital management ───────────────────────────────────
    def add_deployed(self, value_usdt: float):
        self._deployed = max(0.0, self._deployed + value_usdt)

    def remove_deployed(self, value_usdt: float):
        self._deployed = max(0.0, self._deployed - value_usdt)

    # ── Portfolio metrics ─────────────────────────────────────────────
    @property
    def total_trades(self) -> int:
        return len(self._closed)

    @property
    def winning_trades(self) -> int:
        return sum(1 for t in self._closed if t.pnl > 0)

    @property
    def losing_trades(self) -> int:
        return sum(1 for t in self._closed if t.pnl <= 0)

    @property
    def win_rate(self) -> float:
        return (
            self.winning_trades / self.total_trades * 100 if self.total_trades else 0.0
        )

    @property
    def gross_profit(self) -> float:
        return sum(t.pnl for t in self._closed if t.pnl > 0)

    @property
    def gross_loss(self) -> float:
        return sum(t.pnl for t in self._closed if t.pnl <= 0)

    @property
    def net_pnl(self) -> float:
        return self._current_equity - self.initial_capital

    @property
    def net_pnl_pct(self) -> float:
        return (
            self.net_pnl / self.initial_capital * 100 if self.initial_capital else 0.0
        )

    @property
    def profit_factor(self) -> float:
        return (
            self.gross_profit / abs(self.gross_loss)
            if self.gross_loss != 0
            else float("inf")
        )

    @property
    def current_drawdown(self) -> float:
        return (self._peak_equity - self._current_equity) / self._peak_equity * 100

    @property
    def free_capital(self) -> float:
        return max(0.0, self._current_equity - self._deployed)

    @property
    def deployed_capital(self) -> float:
        return self._deployed

    @property
    def current_equity(self) -> float:
        return self._current_equity

    def avg_pnl(self) -> float:
        return self.net_pnl / self.total_trades if self.total_trades else 0.0

    def get_symbol_stats(self, symbol: str) -> Optional[SymbolStats]:
        return self._symbol_stats.get(symbol)

    def best_symbol(self) -> Optional[str]:
        if not self._symbol_stats:
            return None
        return max(self._symbol_stats.values(), key=lambda s: s.net_pnl).symbol

    def worst_symbol(self) -> Optional[str]:
        if not self._symbol_stats:
            return None
        return min(self._symbol_stats.values(), key=lambda s: s.net_pnl).symbol

    def to_summary_dict(self) -> Dict:
        return {
            "initial_capital": self.initial_capital,
            "current_equity": round(self._current_equity, 2),
            "net_pnl": round(self.net_pnl, 4),
            "net_pnl_pct": round(self.net_pnl_pct, 2),
            "deployed": round(self._deployed, 2),
            "free_capital": round(self.free_capital, 2),
            "total_trades": self.total_trades,
            "win_rate": round(self.win_rate, 2),
            "profit_factor": round(self.profit_factor, 3),
            "current_drawdown": round(self.current_drawdown, 2),
            "gross_profit": round(self.gross_profit, 4),
            "gross_loss": round(self.gross_loss, 4),
            "max_win_streak": self._max_win_streak,
            "max_loss_streak": self._max_loss_streak,
            "best_symbol": self.best_symbol(),
            "worst_symbol": self.worst_symbol(),
        }

    def recent_trades(self, n: int = 10) -> List[ClosedTrade]:
        return self._closed[-n:]
