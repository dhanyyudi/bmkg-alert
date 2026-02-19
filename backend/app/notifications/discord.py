"""Discord webhook notification sender."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.models import MatchResult, WarningInfo

logger = structlog.get_logger()

SEVERITY_COLOR = {
    "Minor": 0x3B82F6,      # blue
    "Moderate": 0xEAB308,    # yellow
    "Severe": 0xEF4444,      # red
    "Extreme": 0x1F2937,     # dark
}

SEVERITY_EMOJI = {
    "Minor": "\U0001f535",
    "Moderate": "\U0001f7e1",
    "Severe": "\U0001f534",
    "Extreme": "\u26ab",
}


class DiscordSender:
    """Sends alert messages via Discord webhook."""

    async def send(
        self,
        warning: WarningInfo,
        match: MatchResult,
        channel_config: dict[str, Any],
        is_trial: bool = False,
    ) -> bool:
        webhook_url = channel_config.get("webhook_url", "")
        if not webhook_url:
            logger.error("discord_missing_webhook_url")
            return False

        payload = self._build_embed(warning, match, is_trial)
        return await self._post(webhook_url, payload)

    async def send_raw(self, webhook_url: str, message: str) -> bool:
        """Send a plain text message."""
        return await self._post(webhook_url, {"content": message})

    def _build_embed(
        self, warning: WarningInfo, match: MatchResult, is_trial: bool
    ) -> dict:
        emoji = SEVERITY_EMOJI.get(warning.severity, "\u26a0\ufe0f")
        loc = match.location
        color = SEVERITY_COLOR.get(warning.severity, 0x6B7280)

        description = warning.description or warning.headline or ""
        if len(description) > 300:
            description = description[:297] + "..."

        fields = [
            {"name": "Lokasi Terpantau", "value": loc.label or loc.subdistrict_name, "inline": True},
            {"name": "Tingkat", "value": warning.severity, "inline": True},
            {"name": "Berlaku", "value": warning.effective or "-", "inline": True},
            {"name": "Hingga", "value": warning.expires or "-", "inline": True},
        ]

        if match.matched_text:
            fields.append(
                {"name": "Match", "value": f"{match.match_type} — {match.matched_text}", "inline": False}
            )

        embed: dict[str, Any] = {
            "title": f"{emoji} Peringatan Cuaca — {warning.event}",
            "description": description,
            "color": color,
            "fields": fields,
            "footer": {"text": "BMKG Alert System v1.0 | Sumber: BMKG (bmkg.go.id)"},
        }

        if warning.infographic_url:
            embed["image"] = {"url": warning.infographic_url}

        payload: dict[str, Any] = {"embeds": [embed]}

        if is_trial:
            payload["content"] = "\u23f3 *Mode Trial — notifikasi aktif sementara.*"

        return payload

    async def _post(self, webhook_url: str, payload: dict) -> bool:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(webhook_url, json=payload)

            if response.status_code in (200, 204):
                logger.info("discord_message_sent")
                return True

            logger.error(
                "discord_api_error",
                status=response.status_code,
                body=response.text[:200],
            )
            return False
        except httpx.HTTPError as exc:
            logger.error("discord_send_error", error=str(exc))
            return False
