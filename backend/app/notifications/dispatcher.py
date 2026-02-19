"""Notification dispatcher — routes alerts to the correct channel sender."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog

from app.engine.state import StateManager
from app.models import MatchResult, WarningInfo
from app.notifications.telegram import TelegramSender
from app.notifications.discord import DiscordSender
from app.notifications.slack import SlackSender
from app.notifications.email import EmailSender
from app.notifications.webhook import WebhookSender

logger = structlog.get_logger()


class NotificationDispatcher:
    """Routes alert notifications to configured channel senders."""

    def __init__(self, state: StateManager) -> None:
        self._state = state
        self._telegram = TelegramSender()
        self._discord = DiscordSender()
        self._slack = SlackSender()
        self._email = EmailSender()
        self._webhook = WebhookSender()

    async def send(
        self,
        alert_id: int,
        warning: WarningInfo,
        match: MatchResult,
        channel: dict[str, Any],
    ) -> bool:
        """Send a notification through the appropriate channel.

        Args:
            alert_id: ID of the stored alert.
            warning: The BMKG warning details.
            match: The matched location.
            channel: Channel dict with 'id', 'channel_type', 'config'.

        Returns:
            True if notification was sent successfully.
        """
        channel_id = channel.get("id", 0)
        channel_type = channel.get("channel_type", "")
        channel_config = channel.get("config", {})

        # Check quiet hours
        if await self._is_quiet_hours(warning.severity):
            logger.info(
                "notification_skipped_quiet_hours",
                channel_id=channel_id,
                alert_id=alert_id,
            )
            await self._state.log_delivery(
                alert_id, channel_id, "skipped_quiet_hours"
            )
            return False

        # Route to the appropriate sender
        success = False
        error_msg = ""

        try:
            sender_map = {
                "telegram": self._telegram,
                "discord": self._discord,
                "slack": self._slack,
                "email": self._email,
                "webhook": self._webhook,
            }
            sender = sender_map.get(channel_type)

            if sender:
                success = await sender.send(
                    warning=warning,
                    match=match,
                    channel_config=channel_config,
                )
            else:
                logger.warn(
                    "unsupported_channel_type",
                    channel_type=channel_type,
                    channel_id=channel_id,
                )
                error_msg = f"Unsupported channel type: {channel_type}"
        except Exception as exc:
            error_msg = str(exc)
            logger.error(
                "notification_dispatch_error",
                channel_id=channel_id,
                channel_type=channel_type,
                error=error_msg,
            )

        # Record delivery result
        status = "sent" if success else "failed"
        await self._state.log_delivery(alert_id, channel_id, status, error_msg)

        return success

    async def _is_quiet_hours(self, severity: str) -> bool:
        """Check if current time is within quiet hours.

        Severe/Extreme warnings bypass quiet hours if configured.
        """
        enabled = await self._state.get_config_value(
            "quiet_hours_enabled", "false"
        )
        if enabled != "true":
            return False

        override_severe = await self._state.get_config_value(
            "quiet_hours_override_severe", "true"
        )
        if override_severe == "true" and severity in ("Severe", "Extreme"):
            return False

        start_str = await self._state.get_config_value("quiet_hours_start", "22:00")
        end_str = await self._state.get_config_value("quiet_hours_end", "06:00")

        try:
            now = datetime.now(timezone.utc).hour
            # Convert to local Jakarta time (UTC+7)
            local_hour = (now + 7) % 24
            start_hour = int(start_str.split(":")[0])
            end_hour = int(end_str.split(":")[0])

            if start_hour > end_hour:
                # Overnight: e.g., 22:00 - 06:00
                return local_hour >= start_hour or local_hour < end_hour
            else:
                return start_hour <= local_hour < end_hour
        except (ValueError, IndexError):
            return False
