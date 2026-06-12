"""Comprehensive tests for Portfolio tracker."""

import time

import pytest

from ..trading.portfolio import Portfolio


@pytest.fixture
def portfolio():
    return Portfolio(initial_capital=10_000.0)


@pytest.fixture
def portfolio_with_trades(portfolio):
    trades = [
        ("BTC/USDT", "buy", 50000, 51000, 0.1, 100.0, "tp"),
        ("ETH/USDT", "sell", 3000, 2950, 1.0, 50.0, "tp"),
        ("BTC/USDT", "buy", 48000, 47000, 0.05, -50.0, "sl"),
        ("SOL/USDT", "buy", 100, 105, 10.0, 50.0, "tp"),
        ("ETH/USDT", "buy", 2900, 2800, 0.5, -50.0, "sl"),
    ]
    for sym, side, entry, ex, amt, pnl, reason in trades:
        portfolio.record_close(
            sym,
            side,
            entry,
            ex,
            amt,
            pnl,
            open_time=time.time() - 3600,
            exit_reason=reason,
        )
    return portfolio


class TestPortfolioBasics:

    def test_initial_state(self, portfolio):
        assert portfolio.initial_capital == 10_000.0
        assert portfolio.total_trades == 0
        assert portfolio.net_pnl == 0.0
        assert portfolio.current_equity == 10_000.0

    def test_record_win_updates_equity(self, portfolio):
        portfolio.record_close(
            "BTC/USDT",
            "buy",
            50000,
            51000,
            0.1,
            100.0,
            open_time=time.time(),
            exit_reason="tp",
        )
        assert portfolio.current_equity == 10_100.0
        assert portfolio.net_pnl == 100.0

    def test_record_loss_updates_equity(self, portfolio):
        portfolio.record_close(
            "BTC/USDT",
            "buy",
            50000,
            49000,
            0.1,
            -100.0,
            open_time=time.time(),
            exit_reason="sl",
        )
        assert portfolio.current_equity == 9_900.0
        assert portfolio.net_pnl == -100.0

    def test_total_trades_counts_all(self, portfolio_with_trades):
        assert portfolio_with_trades.total_trades == 5

    def test_win_loss_counts(self, portfolio_with_trades):
        assert portfolio_with_trades.winning_trades == 3
        assert portfolio_with_trades.losing_trades == 2

    def test_win_rate(self, portfolio_with_trades):
        assert abs(portfolio_with_trades.win_rate - 60.0) < 0.01

    def test_net_pnl_sum(self, portfolio_with_trades):
        assert abs(portfolio_with_trades.net_pnl - 100.0) < 0.01

    def test_gross_profit_positive(self, portfolio_with_trades):
        assert portfolio_with_trades.gross_profit > 0

    def test_gross_loss_negative(self, portfolio_with_trades):
        assert portfolio_with_trades.gross_loss < 0

    def test_profit_factor(self, portfolio_with_trades):
        pf = portfolio_with_trades.profit_factor
        assert pf > 1.0  # wins > losses in this fixture


class TestPortfolioDrawdown:

    def test_zero_drawdown_on_only_wins(self, portfolio):
        for i in range(5):
            portfolio.record_close(
                "BTC/USDT",
                "buy",
                50000,
                51000,
                0.1,
                100.0,
                open_time=time.time(),
                exit_reason="tp",
            )
        assert portfolio.current_drawdown == 0.0

    def test_drawdown_after_loss(self, portfolio):
        portfolio.record_close(
            "BTC/USDT",
            "buy",
            50000,
            51000,
            0.1,
            100.0,
            open_time=time.time(),
            exit_reason="tp",
        )
        portfolio.record_close(
            "BTC/USDT",
            "buy",
            51000,
            49000,
            0.1,
            -200.0,
            open_time=time.time(),
            exit_reason="sl",
        )
        dd = portfolio.current_drawdown
        assert dd > 0.0


class TestPortfolioCapital:

    def test_deployed_capital_tracking(self, portfolio):
        portfolio.add_deployed(5_000.0)
        assert portfolio.deployed_capital == 5_000.0
        assert portfolio.free_capital == 5_000.0

    def test_remove_deployed(self, portfolio):
        portfolio.add_deployed(3_000.0)
        portfolio.remove_deployed(1_000.0)
        assert portfolio.deployed_capital == 2_000.0

    def test_deployed_never_negative(self, portfolio):
        portfolio.remove_deployed(99_999.0)
        assert portfolio.deployed_capital == 0.0


class TestPortfolioSymbolStats:

    def test_symbol_stats_present(self, portfolio_with_trades):
        stats = portfolio_with_trades.get_symbol_stats("BTC/USDT")
        assert stats is not None
        assert stats.trades > 0

    def test_best_worst_symbol(self, portfolio_with_trades):
        best = portfolio_with_trades.best_symbol()
        worst = portfolio_with_trades.worst_symbol()
        assert best in ("BTC/USDT", "ETH/USDT", "SOL/USDT")
        assert worst in ("BTC/USDT", "ETH/USDT", "SOL/USDT")


class TestPortfolioSummary:

    def test_summary_dict_keys(self, portfolio_with_trades):
        summary = portfolio_with_trades.to_summary_dict()
        for key in (
            "initial_capital",
            "current_equity",
            "net_pnl",
            "win_rate",
            "profit_factor",
            "current_drawdown",
            "total_trades",
        ):
            assert key in summary, f"Missing key: {key}"

    def test_recent_trades_limited(self, portfolio_with_trades):
        recent = portfolio_with_trades.recent_trades(n=3)
        assert len(recent) <= 3

    def test_streak_tracking(self, portfolio):
        for _ in range(4):
            portfolio.record_close(
                "BTC/USDT",
                "buy",
                50000,
                51000,
                0.1,
                10.0,
                open_time=time.time(),
                exit_reason="tp",
            )
        assert portfolio._max_win_streak == 4
