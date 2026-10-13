"""Earthquake announcements to the channels configured through environment variables."""

import asyncio
import logging
from datetime import timedelta, timezone

from app.config import settings
from app.models.earthquake import Earthquake
from app.services.notifications.base import NotificationMessage, NotificationProvider
from app.services.notifications.discord import DiscordProvider
from app.services.notifications.email import EmailProvider
from app.services.notifications.slack import SlackProvider
from app.services.notifications.telegram import TelegramProvider
from app.services.notifications.webhook import WebhookProvider

logger = logging.getLogger(__name__)

WIB = timezone(timedelta(hours=7))


class NotificationService:
    """Delivers a notification across every provider that has credentials."""

    def __init__(self):
        self.providers: list[NotificationProvider] = [
            DiscordProvider(),
            SlackProvider(),
            WebhookProvider(),
            EmailProvider(),
            TelegramProvider(),
        ]

    @staticmethod
    def has_targets() -> bool:
        """Whether any environment-configured channel exists to announce to."""
        return bool(
            settings.discord_webhook_url
            or settings.slack_webhook_url
            or settings.generic_webhook_url
            or (settings.smtp_host and settings.smtp_user)
            or (settings.telegram_bot_token and settings.telegram_chat_id)
        )

    async def dispatch(self, earthquake: Earthquake) -> None:
        """Announce an earthquake to all configured providers."""
        message = self._earthquake_message(earthquake)
        logger.info(f"Dispatching alert: {message.title}")

        results = await asyncio.gather(
            *(provider.send(message) for provider in self.providers),
            return_exceptions=True,
        )
        logger.info(f"Notification Results: {results}")

    def _earthquake_message(self, eq: Earthquake) -> NotificationMessage:
        severity = "Info"
        if eq.magnitude >= 6.0:
            severity = "Critical"
        elif eq.magnitude >= 5.0:
            severity = "High"
        elif eq.magnitude >= 4.0:
            severity = "Medium"

        # The API reports earthquake times in UTC without an offset
        occurred = eq.occurred_at
        if occurred.tzinfo is None:
            occurred = occurred.replace(tzinfo=timezone.utc)
        local = occurred.astimezone(WIB)

        body = (
            f"Waktu: {local:%d-%m-%Y %H:%M} WIB\n"
            f"Lokasi: {eq.lat_text}, {eq.lon_text}\n"
            f"Kedalaman: {eq.depth_km:g} km\n"
            f"Potensi: {eq.tsunami_potential or '-'}\n"
            f"Dirasakan: {eq.felt_report or '-'}"
        )

        return NotificationMessage(
            title=f"Gempa M {eq.magnitude:.1f}: {eq.region}",
            body=body,
            severity=severity,
            timestamp=occurred,
            url=eq.shakemap_url,
            original_data=eq.model_dump(mode="json"),
        )


# Global notification service
notification_service = NotificationService()
