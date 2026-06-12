"""
DeltaForge display — backward-compatibility shim.
Imports have moved to code.backend.display subpackage.
"""

from .display.dashboard import DeltaForgeDisplay  # noqa: F401
from .display.event_log import (
    EVT_ANOMALY,
    EVT_BUY_SIGNAL,  # noqa: F401
    EVT_ENTRY,
    EVT_EXIT_LOSS,
    EVT_EXIT_WIN,
    EVT_HTF_REJECT,
    EVT_INFO,
    EVT_ML_REJECT,
    EVT_SELL_SIGNAL,
    EVT_TRAIL,
    EVT_WARN,
    EventLog,
)

__all__ = ["DeltaForgeDisplay", "EventLog"]
