"""DeltaForge — Typed event constants and event log store."""

from typing import List

EVT_BUY_SIGNAL = "BUY_SIGNAL"
EVT_SELL_SIGNAL = "SELL_SIGNAL"
EVT_ENTRY = "ENTRY"
EVT_EXIT_WIN = "EXIT_WIN"
EVT_EXIT_LOSS = "EXIT_LOSS"
EVT_TRAIL = "TRAIL"
EVT_HTF_REJECT = "HTF_REJECT"
EVT_ML_REJECT = "ML_REJECT"
EVT_ANOMALY = "ANOMALY"
EVT_INFO = "INFO"
EVT_WARN = "WARN"


class EventLog:
    """Bounded typed event store for the dashboard."""

    MAX = 14

    def __init__(self):
        self._events: List[dict] = []

    def add(self, evt_type: str, message: str, color_override: str = ""):
        from datetime import datetime

        self._events.append(
            {
                "type": evt_type,
                "msg": message,
                "ts": datetime.now().strftime("%H:%M:%S"),
                "color_override": color_override,
            }
        )
        if len(self._events) > self.MAX:
            self._events.pop(0)

    def tail(self, n: int = 14):
        return self._events[-n:]

    def clear(self):
        self._events.clear()
