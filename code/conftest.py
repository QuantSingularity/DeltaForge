"""
Shared pytest fixtures for all DeltaForge test suites.

The synthetic-data helper lives in :mod:`testkit` so it is importable from any
test module (``from testkit import make_ohlcv``). A ``make_ohlcv`` fixture is
also exposed here for tests that prefer dependency injection.
"""

import json
import pathlib

import pytest
from testkit import make_ohlcv as _make_ohlcv  # noqa: F401  (re-export)

_CONFIG_PATH = pathlib.Path(__file__).parent / "backend" / "config.json"


@pytest.fixture
def make_ohlcv():
    """Fixture returning the synthetic-OHLCV factory function."""
    return _make_ohlcv


@pytest.fixture(scope="session")
def base_config() -> dict:
    """Full config dict loaded from ``config.json`` (treat as read-only)."""
    with open(_CONFIG_PATH) as fh:
        return json.load(fh)
