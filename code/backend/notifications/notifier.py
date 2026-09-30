"""
DeltaForge Notifier
Dispatches trade/system events to configured notification channels.
Channels: Telegram, Webhook (HTTP POST), future: Email/Slack.
"""

import logging
import threading

logger = logging.getLogger("DeltaForge.Notifications")


class NotificationEvent:
    __slots__ = ("event_type", "symbol", "side", "price", "sl", "tp", "pnl", "message")

    def __init__(self, event_type: str, message: str = "", **kwargs):
        self.event_type = event_type
        self.message = message
        for k, v in kwargs.items():
            if k in self.__slots__:
                setattr(self, k, v)
        # fill missing slots with None
        for s in self.__slots__:
            if not hasattr(self, s):
                setattr(self, s, None)

    def format_text(self) -> str:
        parts = [f"[DeltaForge] {self.event_type}"]
        if self.symbol:
            parts.append(f"Symbol: {self.symbol}")
        if self.side:
            parts.append(f"Side:   {self.side.upper()}")
        if self.price:
            parts.append(f"Price:  {self.price}")
        if self.sl:
            parts.append(f"SL:     {self.sl}")
        if self.tp:
            parts.append(f"TP:     {self.tp}")
        if self.pnl is not None:
            parts.append(f"PnL:    ${self.pnl:+.4f}")
        if self.message:
            parts.append(self.message)
        return "\n".join(parts)


class Notifier:
    """
    Central notification dispatcher. Thread-safe.
    Channels are registered at startup and fire asynchronously.
    """

    def __init__(self, config: dict):
        self.cfg = config.get("notifications", {})
        self.enabled = self.cfg.get("enabled", False)
        self._channels: list = []
        self._setup_channels()

    def _setup_channels(self):
        if not self.enabled:
            logger.info("Notifications disabled")
            return

        # Telegram
        tg = self.cfg.get("telegram", {})
        if tg.get("enabled") and tg.get("bot_token") and tg.get("chat_id"):
            from .telegram import TelegramChannel

            self._channels.append(TelegramChannel(tg["bot_token"], tg["chat_id"]))
            logger.info("Telegram notifications enabled")

        # Webhook
        wh = self.cfg.get("webhook", {})
        if wh.get("enabled") and wh.get("url"):
            from .webhook import WebhookChannel

            self._channels.append(WebhookChannel(wh["url"], wh.get("headers", {})))
            logger.info("Webhook notifications enabled")

    def send(self, event: NotificationEvent):
        """Fire-and-forget: sends to all channels in background threads."""
        if not self.enabled or not self._channels:
            return
        for ch in self._channels:
            t = threading.Thread(target=self._safe_send, args=(ch, event), daemon=True)
            t.start()

    def _safe_send(self, channel, event: NotificationEvent):
        try:
            channel.send(event)
        except Exception as e:
            logger.error(
                f"Notification channel {channel.__class__.__name__} error: {e}"
            )

    # ── Convenience helpers ───────────────────────────────────────────
    def trade_entry(self, symbol, side, entry, sl, tp, amount, ml_score, tf):
        self.send(
            NotificationEvent(
                "TRADE ENTRY",
                symbol=symbol,
                side=side,
                price=entry,
                sl=sl,
                tp=tp,
                message=f"Amount: {amount:.6f}  ML: {ml_score:.0f}%  TF: {tf}",
            )
        )

    def trade_exit(self, symbol, side, exit_price, pnl, reason):
        self.send(
            NotificationEvent(
                f"TRADE EXIT ({reason.upper()})",
                symbol=symbol,
                side=side,
                price=exit_price,
                pnl=pnl,
            )
        )

    def trail_update(self, symbol, side, old_sl, new_sl):
        direction = "▲" if new_sl > old_sl else "▼"
        self.send(
            NotificationEvent(
                f"TRAIL {direction}",
                symbol=symbol,
                side=side,
                message=f"SL: {old_sl:.6f} → {new_sl:.6f}",
            )
        )

    def anomaly_detected(self, reason: str):
        self.send(NotificationEvent("⚠ ANOMALY - BOT STOPPED", message=reason))

    def bot_started(self, exchange: str):
        self.send(NotificationEvent("✅ BOT STARTED", message=f"Exchange: {exchange}"))

    def bot_stopped(self, reason: str = ""):
        self.send(NotificationEvent("🛑 BOT STOPPED", message=reason))
