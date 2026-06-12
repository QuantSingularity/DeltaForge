"""DeltaForge — HTTP Webhook notification channel."""

import json
import logging
import time
from typing import Dict

import requests

from .notifier import NotificationEvent

logger = logging.getLogger("DeltaForge.Notifications.Webhook")


class WebhookChannel:
    """Posts a JSON payload to a configurable URL on each event."""

    def __init__(self, url: str, headers: Dict[str, str] = None, max_retries: int = 3):
        self.url = url
        self.headers = {"Content-Type": "application/json", **(headers or {})}
        self.max_retries = max_retries
        self._session = requests.Session()
        self._session.headers.update(self.headers)

    def send(self, event: NotificationEvent):
        payload = {
            "event_type": event.event_type,
            "message": event.message,
            "symbol": event.symbol,
            "side": event.side,
            "price": event.price,
            "sl": event.sl,
            "tp": event.tp,
            "pnl": event.pnl,
        }
        for attempt in range(self.max_retries):
            try:
                r = self._session.post(self.url, data=json.dumps(payload), timeout=8)
                if r.ok:
                    return
                logger.warning(f"Webhook {self.url} returned {r.status_code}")
                return
            except requests.RequestException as e:
                if attempt < self.max_retries - 1:
                    time.sleep(2**attempt)
                else:
                    logger.error(f"Webhook send failed: {e}")
