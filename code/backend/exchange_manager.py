"""
DeltaForge exchange_manager - backward-compatibility shim.
Imports have moved to code.backend.exchanges subpackage.
"""

from .exchanges.base import BaseExchange  # noqa: F401
from .exchanges.bitflex_adapter import BitflexAdapter  # noqa: F401
from .exchanges.exchange_manager import SUPPORTED_EXCHANGES  # noqa: F401
from .exchanges.exchange_manager import ExchangeManager

__all__ = ["ExchangeManager", "BitflexAdapter", "BaseExchange", "SUPPORTED_EXCHANGES"]
