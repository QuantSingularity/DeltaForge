"""
DeltaForge backtest - backward-compatibility shim.
Imports have moved to code.backend.backtest subpackage.
"""

from .backtest.engine import BacktestEngine, BTResult, BTTrade  # noqa: F401
from .backtest.metrics import BacktestMetrics  # noqa: F401

__all__ = ["BacktestEngine", "BTResult", "BTTrade", "BacktestMetrics"]
