"""DeltaForge — Abstract exchange interface."""

from abc import ABC, abstractmethod
from typing import List, Optional


class BaseExchange(ABC):
    """Minimal interface every exchange adapter must implement."""

    @abstractmethod
    def load_markets(self) -> dict: ...

    @abstractmethod
    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> list: ...

    @abstractmethod
    def fetch_ticker(self, symbol: str) -> Optional[dict]: ...

    @abstractmethod
    def fetch_balance(self) -> dict: ...

    @abstractmethod
    def create_market_order(
        self, symbol: str, side: str, amount: float, params: dict = None
    ) -> Optional[dict]: ...

    @abstractmethod
    def create_limit_order(
        self, symbol: str, side: str, amount: float, price: float, params: dict = None
    ) -> Optional[dict]: ...

    @abstractmethod
    def cancel_order(self, order_id: str, symbol: str) -> bool: ...

    @abstractmethod
    def fetch_open_orders(self, symbol: str = None) -> List[dict]: ...
