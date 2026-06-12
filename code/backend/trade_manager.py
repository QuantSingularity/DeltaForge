"""
DeltaForge trade_manager — backward-compatibility shim.
Imports have moved to code.backend.trading subpackage.
"""

from .trading.portfolio import ClosedTrade, Portfolio  # noqa: F401
from .trading.trade_manager import LiveTrade, TradeManager  # noqa: F401

__all__ = ["TradeManager", "LiveTrade", "Portfolio", "ClosedTrade"]
