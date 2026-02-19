"""Telegram notification sender — sends formatted alerts via Telegram Bot API."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.models import MatchResult, WarningInfo
from app.notifications.formatter import format_telegram_message

logger = structlog.get_logger()

TELEGRAM_API_BASE = "https://api.telegram.org"


class TelegramSender:
    """Sends alert messages via Telegram Bot API."""

    async def send(
        self,
        warning: WarningInfo,
        match: MatchResult,
        channel_config: dict[str, Any],
        is_trial: bool = False,
    ) -> bool:
        """Send a formatted alert message to a Telegram chat.

        Args:
            warning: The BMKG warning.
            match: The location match result.
            channel_config: Must contain 'bot_token' and 'chat_id'.
            is_trial: Whether this is a trial subscription.

        Returns:
            True if message was sent successfully.
        """
        bot_token = channel_config.get("bot_token", "")
        chat_id = channel_config.get("chat_id", "")

        if not bot_token or not chat_id:
            logger.error(
                "telegram_missing_config",
                has_token=bool(bot_token),
                has_chat_id=bool(chat_id),
            )
            return False

        message = format_telegram_message(warning, match, is_trial)

        return await self._send_message(bot_token, chat_id, message)

    async def send_raw(
        self,
        bot_token: str,
        chat_id: str,
        message: str,
    ) -> bool:
        """Send a raw text message to a Telegram chat."""
        return await self._send_message(bot_token, chat_id, message)

    async def _send_message(
        self,
        bot_token: str,
        chat_id: str,
        text: str,
    ) -> bool:
        """Call Telegram Bot API sendMessage endpoint."""
        url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, json=payload)

            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    logger.info(
                        "telegram_message_sent",
                        chat_id=chat_id,
                    )
                    return True

            logger.error(
                "telegram_api_error",
                status=response.status_code,
                body=response.text[:200],
                chat_id=chat_id,
            )
            return False

        except httpx.HTTPError as exc:
            logger.error(
                "telegram_send_error",
                error=str(exc),
                chat_id=chat_id,
            )
            return False
