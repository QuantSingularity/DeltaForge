"""DeltaForge REST + WebSocket API package.

Serves live bot state to the web dashboard and exposes control endpoints
(start/stop, config edit, on-demand backtest).
"""

from .server import create_app

__all__ = ["create_app"]
