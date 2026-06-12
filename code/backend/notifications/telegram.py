"""DeltaForge — Telegram notification channel."""

import logging
import time

import requests

from .notifier import NotificationEvent

logger = logging.getLogger("DeltaForge.Notifications.Telegram")

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramChannel:
    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        parse_mode: str = "Markdown",
        max_retries: int = 3,
    ):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.parse_mode = parse_mode
        self.max_retries = max_retries
        self._session = requests.Session()

    def send(self, event: NotificationEvent):
        text = f"```\n{event.format_text()}\n```"
        url = TELEGRAM_API.format(token=self.bot_token)
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": self.parse_mode,
            "disable_notification": False,
        }
        for attempt in range(self.max_retries):
            try:
                r = self._session.post(url, json=payload, timeout=8)
                if r.status_code == 200:
                    return
                # Rate-limit: back off
                if r.status_code == 429:
                    retry_after = r.json().get("parameters", {}).get("retry_after", 5)
                    time.sleep(retry_after)
                    continue
                logger.warning(f"Telegram API error {r.status_code}: {r.text[:200]}")
                return
            except requests.RequestException as e:
                if attempt < self.max_retries - 1:
                    time.sleep(2**attempt)
                else:
                    logger.error(
                        f"Telegram send failed after {self.max_retries} attempts: {e}"
                    )
