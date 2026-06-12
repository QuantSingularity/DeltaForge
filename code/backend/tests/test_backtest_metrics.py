"""Comprehensive tests for BacktestMetrics."""

import math

import pytest

from ..backtest.metrics import BacktestMetrics


@pytest.fixture
def balanced_metrics():
    """10 wins of $100, 5 losses of -$80 — PF > 1."""
    pnls = [100.0] * 10 + [-80.0] * 5
    equity = [10000.0]
    for p in pnls:
        equity.append(equity[-1] + p)
    return BacktestMetrics(pnls, equity, initial_capital=10000.0)


@pytest.fixture
def all_wins():
    pnls = [50.0] * 20
    equity = [10000.0 + i * 50 for i in range(21)]
    return BacktestMetrics(pnls, equity, initial_capital=10000.0)


@pytest.fixture
def all_losses():
    pnls = [-30.0] * 10
    equity = [10000.0 - i * 30 for i in range(11)]
    return BacktestMetrics(pnls, equity, initial_capital=10000.0)


@pytest.fixture
def empty_metrics():
    return BacktestMetrics([], [10000.0], initial_capital=10000.0)


class TestBasicMetrics:

    def test_total_trades(self, balanced_metrics):
        assert balanced_metrics.total_trades == 15

    def test_win_rate(self, balanced_metrics):
        assert abs(balanced_metrics.win_rate - 66.67) < 0.1

    def test_all_wins_win_rate(self, all_wins):
        assert all_wins.win_rate == 100.0

    def test_all_losses_win_rate(self, all_losses):
        assert all_losses.win_rate == 0.0

    def test_total_pnl(self, balanced_metrics):
        expected = 10 * 100 - 5 * 80
        assert abs(balanced_metrics.total_pnl - expected) < 0.01

    def test_profit_factor(self, balanced_metrics):
        pf = balanced_metrics.profit_factor
        assert pf > 1.0

    def test_profit_factor_all_wins(self, all_wins):
        assert math.isinf(all_wins.profit_factor)

    def test_avg_win(self, balanced_metrics):
        assert abs(balanced_metrics.avg_win - 100.0) < 0.01

    def test_avg_loss(self, balanced_metrics):
        assert abs(balanced_metrics.avg_loss - 80.0) < 0.01

    def test_expectancy(self, balanced_metrics):
        pnl = balanced_metrics.total_pnl
        n = balanced_metrics.total_trades
        assert abs(balanced_metrics.expectancy - pnl / n) < 0.01

    def test_empty_metrics_no_crash(self, empty_metrics):
        assert empty_metrics.total_trades == 0
        assert empty_metrics.win_rate == 0.0
        assert empty_metrics.total_pnl == 0.0


class TestRiskAdjustedMetrics:

    def test_sharpe_positive_for_winning(self, all_wins):
        assert all_wins.sharpe_ratio > 0.0

    def test_sharpe_negative_for_losses(self, all_losses):
        assert all_losses.sharpe_ratio < 0.0

    def test_sortino_positive_for_winning(self, all_wins):
        assert all_wins.sortino_ratio > 0.0

    def test_calmar_positive_for_winning(self, all_wins):
        assert all_wins.calmar_ratio > 0.0

    def test_max_drawdown_zero_all_wins(self, all_wins):
        assert all_wins.max_drawdown == 0.0

    def test_max_drawdown_positive_all_losses(self, all_losses):
        assert all_losses.max_drawdown > 0.0

    def test_max_drawdown_bounded(self, balanced_metrics):
        assert 0.0 <= balanced_metrics.max_drawdown <= 100.0

    def test_ulcer_index_non_negative(self, balanced_metrics):
        assert balanced_metrics.ulcer_index >= 0.0

    def test_recovery_factor_all_wins(self, all_wins):
        assert math.isinf(all_wins.recovery_factor)


class TestStreakMetrics:

    def test_max_consec_wins(self, all_wins):
        assert all_wins.max_consecutive_wins() == 20

    def test_max_consec_losses(self, all_losses):
        assert all_losses.max_consecutive_losses() == 10

    def test_alternating_streak(self):
        pnls = [10.0, -5.0, 10.0, -5.0, 10.0]
        eq = [10000.0]
        for p in pnls:
            eq.append(eq[-1] + p)
        m = BacktestMetrics(pnls, eq)
        assert m.max_consecutive_wins() == 1
        assert m.max_consecutive_losses() == 1


class TestReportDict:

    def test_report_has_all_keys(self, balanced_metrics):
        report = balanced_metrics.report()
        required = [
            "total_trades",
            "win_rate",
            "total_pnl",
            "total_return_pct",
            "avg_win",
            "avg_loss",
            "profit_factor",
            "expectancy",
            "max_drawdown_pct",
            "sharpe_ratio",
            "sortino_ratio",
            "calmar_ratio",
            "recovery_factor",
            "ulcer_index",
            "max_consec_wins",
            "max_consec_losses",
        ]
        for k in required:
            assert k in report, f"Missing report key: {k}"

    def test_report_values_are_finite(self, balanced_metrics):
        report = balanced_metrics.report()
        for k, v in report.items():
            if isinstance(v, float):
                assert not math.isnan(v), f"NaN in report[{k!r}]"
