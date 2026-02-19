"""Generic webhook notification sender."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.models import MatchResult, WarningInfo

logger = structlog.get_logger()


class WebhookSender:
    """Sends alert data as JSON POST to a generic webhook URL."""

    async def send(
        self,
        warning: WarningInfo,
        match: MatchResult,
        channel_config: dict[str, Any],
        is_trial: bool = False,
    ) -> bool:
        webhook_url = channel_config.get("webhook_url", "")
        if not webhook_url:
            logger.error("webhook_missing_url")
            return False

        headers = channel_config.get("headers", {})
        payload = self._build_payload(warning, match, is_trial)
        return await self._post(webhook_url, payload, headers)

    async def send_raw(self, webhook_url: str, payload: dict, headers: dict | None = None) -> bool:
        """Send an arbitrary JSON payload."""
        return await self._post(webhook_url, payload, headers or {})

    def _build_payload(
        self, warning: WarningInfo, match: MatchResult, is_trial: bool
    ) -> dict:
        loc = match.location
        return {
            "source": "bmkg-alert",
            "version": "1.0",
            "is_trial": is_trial,
            "warning": {
                "event": warning.event,
                "severity": warning.severity,
                "headline": warning.headline,
                "description": warning.description,
                "effective": warning.effective,
                "expires": warning.expires,
                "infographic_url": warning.infographic_url,
            },
            "location": {
                "code": loc.adm_code,
                "label": loc.label,
                "subdistrict": loc.subdistrict_name,
                "district": loc.district_name,
                "province": loc.province_name,
            },
            "match": {
                "type": match.match_type,
                "text": match.matched_text,
            },
        }

    async def _post(
        self, webhook_url: str, payload: dict, headers: dict
    ) -> bool:
        try:
            request_headers = {"Content-Type": "application/json"}
            request_headers.update(headers)

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    webhook_url, json=payload, headers=request_headers
                )

            if 200 <= response.status_code < 300:
                logger.info("webhook_sent", url=webhook_url, status=response.status_code)
                return True

            logger.error(
                "webhook_error",
                url=webhook_url,
                status=response.status_code,
                body=response.text[:200],
            )
            return False
        except httpx.HTTPError as exc:
            logger.error("webhook_send_error", error=str(exc), url=webhook_url)
            return False
