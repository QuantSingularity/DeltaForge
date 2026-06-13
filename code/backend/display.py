"""
DeltaForge display — backward-compatibility shim.
Imports have moved to code.backend.display subpackage.
"""

from .display.dashboard import DeltaForgeDisplay  # noqa: F401
from .display.event_log import EVT_BUY_SIGNAL  # noqa: F401
from .display.event_log import EventLog

__all__ = ["DeltaForgeDisplay", "EventLog"]
