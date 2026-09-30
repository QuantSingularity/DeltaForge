"""
DeltaForge ConfigManager
Typed config loader with JSON schema validation, hot-reload, and
runtime mutation helpers. Wraps config.json with change callbacks.
"""

import json
import logging
import os
import threading
from copy import deepcopy
from typing import Any, Callable, Dict, List

logger = logging.getLogger("DeltaForge.Config")

_DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "config.json"
)

REQUIRED_KEYS = [
    "exchange",
    "symbols",
    "risk",
    "trail_stop",
    "strategies",
    "ml",
    "display",
]

VALID_TIMEFRAMES = {"15m", "1h", "4h", "1d"}
VALID_TRAIL_TYPES = {"atr", "percent", "dollar", "time", "volatility"}
VALID_TRADE_TYPES = {"spot", "margin"}


class ConfigError(Exception):
    """Raised when config.json fails validation."""


class ConfigManager:
    """
    Thread-safe config manager. Features:
    - Loads and validates config.json on startup
    - Hot-reloads when file mtime changes
    - Fires registered callbacks on reload
    - Provides typed get helpers
    - Supports runtime set() with optional persistence
    """

    def __init__(self, path: str = _DEFAULT_CONFIG_PATH):
        self._path = path
        self._data: Dict[str, Any] = {}
        self._mtime: float = 0.0
        self._lock = threading.RLock()
        self._callbacks: List[Callable[[Dict], None]] = []
        self.load()

    # ── Load / Validate ───────────────────────────────────────────────
    def load(self) -> None:
        if not os.path.exists(self._path):
            raise ConfigError(f"Config file not found: {self._path}")
        with open(self._path) as f:
            raw = json.load(f)
        self._validate(raw)
        with self._lock:
            self._data = raw
            self._mtime = os.path.getmtime(self._path)
        logger.info(f"Config loaded from {self._path}")

    def check_reload(self) -> bool:
        """Call every tick. Returns True if config was reloaded."""
        try:
            mtime = os.path.getmtime(self._path)
            if mtime <= self._mtime:
                return False
            self.load()
            for cb in self._callbacks:
                try:
                    cb(self._data)
                except Exception as e:
                    logger.error(f"Config reload callback error: {e}")
            return True
        except Exception as e:
            logger.warning(f"Config reload check failed: {e}")
            return False

    def on_reload(self, callback: Callable[[Dict], None]) -> None:
        """Register a callback fired whenever config is reloaded."""
        self._callbacks.append(callback)

    # ── Validation ────────────────────────────────────────────────────
    @staticmethod
    def _validate(cfg: Dict) -> None:
        for key in REQUIRED_KEYS:
            if key not in cfg:
                raise ConfigError(f"Missing required config key: '{key}'")

        exc = cfg.get("exchange", {})
        if not exc.get("api_key") and not exc.get("sandbox", False):
            logger.warning("No API key set and sandbox=false - using placeholder keys")

        trail = cfg.get("trail_stop", {})
        tt = trail.get("type", "atr")
        if tt not in VALID_TRAIL_TYPES:
            raise ConfigError(
                f"Invalid trail_stop.type '{tt}'. Choose: {VALID_TRAIL_TYPES}"
            )

        trade_type = exc.get("trade_type", "spot")
        if trade_type not in VALID_TRADE_TYPES:
            raise ConfigError(
                f"Invalid trade_type '{trade_type}'. Choose: {VALID_TRADE_TYPES}"
            )

        risk = cfg.get("risk", {})
        if risk.get("risk_percent", 1.0) > 10:
            raise ConfigError("risk.risk_percent > 10% is not allowed (safety cap)")
        if risk.get("max_total_orders", 10) > 50:
            raise ConfigError("max_total_orders > 50 is not allowed (safety cap)")

        symbols = cfg.get("symbols", [])
        if not symbols:
            raise ConfigError("No symbols configured")

    # ── Typed accessors ───────────────────────────────────────────────
    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            keys = key.split(".")
            val = self._data
            for k in keys:
                if not isinstance(val, dict):
                    return default
                val = val.get(k, default)
            return val

    def set(self, key: str, value: Any, persist: bool = False) -> None:
        """Set a config value at runtime. Optionally persist to JSON."""
        with self._lock:
            keys = key.split(".")
            d = self._data
            for k in keys[:-1]:
                d = d.setdefault(k, {})
            d[keys[-1]] = value
        if persist:
            self.save()
        logger.info(f"Config set: {key} = {value!r}")

    def save(self) -> None:
        with self._lock:
            with open(self._path, "w") as f:
                json.dump(self._data, f, indent=2)
            self._mtime = os.path.getmtime(self._path)
        logger.info(f"Config saved to {self._path}")

    # ── Convenience properties ────────────────────────────────────────
    @property
    def bot_running(self) -> bool:
        return bool(self.get("bot_running", True))

    @property
    def exchange_id(self) -> str:
        return str(self.get("exchange.id", "binance"))

    @property
    def trade_type(self) -> str:
        return str(self.get("exchange.trade_type", "spot"))

    @property
    def sandbox(self) -> bool:
        return bool(self.get("exchange.sandbox", False))

    @property
    def symbols(self) -> List[str]:
        return list(self.get("symbols", []))

    @property
    def trail_type(self) -> str:
        return str(self.get("trail_stop.type", "atr"))

    @property
    def trail_enabled(self) -> bool:
        return bool(self.get("trail_stop.enabled", True))

    @property
    def tp_enabled(self) -> bool:
        return bool(self.get("risk.take_profit_enabled", True))

    @property
    def min_ml_score(self) -> float:
        return float(self.get("ml.min_score", 60.0))

    @property
    def risk_percent(self) -> float:
        return float(self.get("risk.risk_percent", 1.0))

    @property
    def max_loss_per_trade(self) -> float:
        return float(self.get("risk.max_loss_per_trade", 50.0))

    @property
    def initial_capital(self) -> float:
        return float(self.get("initial_capital", 10000.0))

    @property
    def htf_enabled(self) -> bool:
        return bool(self.get("htf_confirmation.enabled", True))

    @property
    def htf_require_both(self) -> bool:
        return bool(self.get("htf_confirmation.require_both", False))

    @property
    def auto_stop_anomaly(self) -> bool:
        return bool(self.get("auto_stop_on_anomaly", True))

    def as_dict(self) -> Dict:
        with self._lock:
            return deepcopy(self._data)

    def __repr__(self) -> str:
        return f"ConfigManager(path={self._path!r}, exchange={self.exchange_id!r})"
