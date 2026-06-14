"""
DeltaForge — BacktestMetrics
Standalone performance metric calculations:
Sharpe, Sortino, Calmar, MAR, Max Drawdown, Win Rate,
Profit Factor, Expectancy, Recovery Factor.
"""

from typing import List

import numpy as np


class BacktestMetrics:
    """
    Computes a full suite of performance metrics from a list of PnL values
    and equity curve.
    """

    def __init__(
        self,
        pnls: List[float],
        equity: List[float],
        initial_capital: float = 10_000.0,
        trading_days: int = 252,
    ):
        self.pnls = np.array(pnls, dtype=float)
        self.equity = np.array(equity, dtype=float)
        self.initial_capital = initial_capital
        self.trading_days = trading_days

    # ── Core metrics ─────────────────────────────────────────────────
    @property
    def total_pnl(self) -> float:
        return float(self.pnls.sum())

    @property
    def total_return_pct(self) -> float:
        return self.total_pnl / self.initial_capital * 100

    @property
    def total_trades(self) -> int:
        return len(self.pnls)

    @property
    def wins(self) -> np.ndarray:
        return self.pnls[self.pnls > 0]

    @property
    def losses(self) -> np.ndarray:
        return self.pnls[self.pnls <= 0]

    @property
    def win_rate(self) -> float:
        return len(self.wins) / max(self.total_trades, 1) * 100

    @property
    def avg_win(self) -> float:
        return float(self.wins.mean()) if len(self.wins) else 0.0

    @property
    def avg_loss(self) -> float:
        return float(abs(self.losses.mean())) if len(self.losses) else 0.0

    @property
    def profit_factor(self) -> float:
        loss_sum = abs(self.losses.sum())
        return self.wins.sum() / loss_sum if loss_sum > 0 else float("inf")

    @property
    def expectancy(self) -> float:
        """Average $ per trade."""
        return float(self.pnls.mean()) if len(self.pnls) else 0.0

    @property
    def max_drawdown(self) -> float:
        """Maximum peak-to-trough drawdown as %."""
        if len(self.equity) < 2:
            return 0.0
        peak = np.maximum.accumulate(self.equity)
        dd = (peak - self.equity) / np.maximum(peak, 1e-9)
        return float(dd.max() * 100)

    @property
    def max_drawdown_dollar(self) -> float:
        if len(self.equity) < 2:
            return 0.0
        peak = np.maximum.accumulate(self.equity)
        return float((peak - self.equity).max())

    # ── Risk-adjusted returns ─────────────────────────────────────────
    @property
    def sharpe_ratio(self) -> float:
        if len(self.equity) < 2:
            return 0.0
        returns = np.diff(self.equity) / np.maximum(self.equity[:-1], 1e-9)
        std = returns.std()
        return (
            float(returns.mean() / std * np.sqrt(self.trading_days)) if std > 0 else 0.0
        )

    @property
    def sortino_ratio(self) -> float:
        """Like Sharpe but only penalises downside volatility."""
        if len(self.equity) < 2:
            return 0.0
        returns = np.diff(self.equity) / np.maximum(self.equity[:-1], 1e-9)
        neg_returns = returns[returns < 0]
        down_std = neg_returns.std() if len(neg_returns) > 0 else 1e-9
        return float(returns.mean() / down_std * np.sqrt(self.trading_days))

    @property
    def calmar_ratio(self) -> float:
        """Annualised return / Max drawdown."""
        mdd = self.max_drawdown
        if mdd <= 0:
            return float("inf")
        annual_return = self.total_return_pct * (
            self.trading_days / max(self.total_trades, 1)
        )
        return annual_return / mdd

    @property
    def mar_ratio(self) -> float:
        """Minimum Acceptable Return ratio — same as Calmar here."""
        return self.calmar_ratio

    @property
    def recovery_factor(self) -> float:
        """Net profit / Max drawdown in $."""
        mdd_d = self.max_drawdown_dollar
        return self.total_pnl / mdd_d if mdd_d > 0 else float("inf")

    @property
    def ulcer_index(self) -> float:
        """Measures pain of drawdown duration and depth."""
        if len(self.equity) < 2:
            return 0.0
        peak = np.maximum.accumulate(self.equity)
        pct_dd = ((peak - self.equity) / np.maximum(peak, 1e-9)) * 100
        return float(np.sqrt(np.mean(pct_dd**2)))

    # ── Win/Loss streak ───────────────────────────────────────────────
    def max_consecutive_wins(self) -> int:
        best = cur = 0
        for p in self.pnls:
            cur = cur + 1 if p > 0 else 0
            best = max(best, cur)
        return best

    def max_consecutive_losses(self) -> int:
        best = cur = 0
        for p in self.pnls:
            cur = cur + 1 if p <= 0 else 0
            best = max(best, cur)
        return best

    # ── Full report ───────────────────────────────────────────────────
    def report(self) -> dict:
        return {
            "total_trades": self.total_trades,
            "win_rate": round(self.win_rate, 2),
            "total_pnl": round(self.total_pnl, 4),
            "total_return_pct": round(self.total_return_pct, 2),
            "avg_win": round(self.avg_win, 4),
            "avg_loss": round(self.avg_loss, 4),
            "profit_factor": round(self.profit_factor, 3),
            "expectancy": round(self.expectancy, 4),
            "max_drawdown_pct": round(self.max_drawdown, 2),
            "max_drawdown_dollar": round(self.max_drawdown_dollar, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 3),
            "sortino_ratio": round(self.sortino_ratio, 3),
            "calmar_ratio": round(self.calmar_ratio, 3),
            "recovery_factor": round(self.recovery_factor, 3),
            "ulcer_index": round(self.ulcer_index, 3),
            "max_consec_wins": self.max_consecutive_wins(),
            "max_consec_losses": self.max_consecutive_losses(),
        }
