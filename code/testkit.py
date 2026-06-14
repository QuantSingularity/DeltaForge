"""
DeltaForge — shared test utilities.

Importable from any test module (``pythonpath = code`` is set in
``pytest.ini``)::

    from testkit import make_ohlcv

``make_ohlcv`` is a plain importable function (not a pytest fixture) so it can
be called with arbitrary arguments inside fixtures and test bodies alike.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = ["make_ohlcv"]


def make_ohlcv(n: int, seed: int = 42) -> pd.DataFrame:
    """Return a synthetic OHLCV DataFrame with *n* hourly bars.

    A fixed ``seed`` keeps every run deterministic; pass distinct seeds to
    generate distinct series.
    """
    rng = np.random.default_rng(seed)
    close = np.cumprod(1 + rng.normal(0.0002, 0.01, n)) * 30_000
    spread = close * 0.001
    open_ = close - rng.uniform(0, spread)
    high = close + rng.uniform(0, spread)
    low = close - rng.uniform(0, spread)
    # Enforce OHLCV sanity: high >= close >= low
    high = np.maximum.reduce([high, open_, close])
    low = np.minimum.reduce([low, open_, close])
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
