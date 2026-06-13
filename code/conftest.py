"""
Shared pytest fixtures and helpers for all DeltaForge test suites.

Available everywhere under code/ (backend/tests/ and ai_models/tests/).
"""

import json
import pathlib

import numpy as np
import pandas as pd
import pytest

_CONFIG_PATH = pathlib.Path(__file__).parent / "backend" / "config.json"


# ── Shared helper (plain function, not a fixture) ─────────────────────────────


def _make_ohlcv(n: int) -> pd.DataFrame:
    """Return a synthetic OHLCV DataFrame with *n* hourly bars.

    Uses a fixed random seed so every test run is deterministic.
    """
    rng = np.random.default_rng(42)
    close = np.cumprod(1 + rng.normal(0.0002, 0.01, n)) * 30_000
    spread = close * 0.001
    open_ = close - rng.uniform(0, spread)
    high = close + rng.uniform(0, spread)
    low = close - rng.uniform(0, spread)
    # Enforce OHLCV sanity: high >= close >= low
    high = np.maximum(high, close)
    low = np.minimum(low, close)
    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": rng.uniform(500, 5_000, n),
        },
        index=pd.date_range("2024-01-01", periods=n, freq="1h"),
    )


# ── Session-scoped fixtures ───────────────────────────────────────────────────


@pytest.fixture(scope="session")
def base_config() -> dict:
    """Full config dict loaded from config.json.

    Treat as read-only — copy before mutating in individual tests::

        cfg = dict(base_config)
        cfg["strategies"] = dict(base_config["strategies"])
        cfg["strategies"]["macd"] = False
    """
    with open(_CONFIG_PATH) as fh:
        return json.load(fh)
