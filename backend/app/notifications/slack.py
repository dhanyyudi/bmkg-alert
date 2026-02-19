"""Slack webhook notification sender."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.models import MatchResult, WarningInfo

logger = structlog.get_logger()

SEVERITY_EMOJI = {
    "Minor": ":large_blue_circle:",
    "Moderate": ":large_yellow_circle:",
    "Severe": ":red_circle:",
    "Extreme": ":black_circle:",
}


class SlackSender:
    """Sends alert messages via Slack Incoming Webhook."""

    async def send(
        self,
        warning: WarningInfo,
        match: MatchResult,
        channel_config: dict[str, Any],
        is_trial: bool = False,
    ) -> bool:
        webhook_url = channel_config.get("webhook_url", "")
        if not webhook_url:
            logger.error("slack_missing_webhook_url")
            return False

        payload = self._build_blocks(warning, match, is_trial)
        return await self._post(webhook_url, payload)

    async def send_raw(self, webhook_url: str, message: str) -> bool:
        """Send a plain text message."""
        return await self._post(webhook_url, {"text": message})

    def _build_blocks(
        self, warning: WarningInfo, match: MatchResult, is_trial: bool
    ) -> dict:
        emoji = SEVERITY_EMOJI.get(warning.severity, ":warning:")
        loc = match.location

        description = warning.description or warning.headline or ""
        if len(description) > 300:
            description = description[:297] + "..."

        blocks: list[dict[str, Any]] = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} Peringatan Cuaca — {warning.event}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Lokasi:*\n{loc.label or loc.subdistrict_name}"},
                    {"type": "mrkdwn", "text": f"*Tingkat:*\n{warning.severity}"},
                    {"type": "mrkdwn", "text": f"*Berlaku:*\n{warning.effective or '-'}"},
                    {"type": "mrkdwn", "text": f"*Hingga:*\n{warning.expires or '-'}"},
                ],
            },
        ]

        if description:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": description},
            })

        if warning.infographic_url:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<{warning.infographic_url}|Lihat Infografis BMKG>",
                },
            })

        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"Match: {match.match_type} — {match.matched_text}"},
                {"type": "mrkdwn", "text": "Sumber: BMKG (bmkg.go.id) | BMKG Alert v1.0"},
            ],
        })

        if is_trial:
            blocks.append({
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": ":hourglass: _Mode Trial — notifikasi aktif sementara._"},
                ],
            })

        return {"blocks": blocks}

    async def _post(self, webhook_url: str, payload: dict) -> bool:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(webhook_url, json=payload)

            if response.status_code == 200:
                logger.info("slack_message_sent")
                return True

            logger.error(
                "slack_api_error",
                status=response.status_code,
                body=response.text[:200],
            )
            return False
        except httpx.HTTPError as exc:
            logger.error("slack_send_error", error=str(exc))
            return False
