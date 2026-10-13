"""BMKG REST API client — async HTTP with httpx.

Every BMKG datum this app shows or acts on comes through here, from the API
at BMKG_API_URL (https://github.com/dhanyyudi/bmkg-api).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import httpx
import structlog

from app.models import ActiveWarning, NowcastDetailResponse, NowcastListResponse

logger = structlog.get_logger()

REQUEST_TIMEOUT = 30.0


@runtime_checkable
class BMKGClient(Protocol):
    """Protocol for BMKG API client — enables test doubles."""

    async def get_warnings(self) -> list[ActiveWarning]: ...
    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]: ...
    async def check_health(self) -> bool: ...


class HttpBMKGClient:
    """Production implementation — calls the live BMKG REST API."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(REQUEST_TIMEOUT),
                headers={"Accept": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """GET a JSON document from the API; raises httpx.HTTPError on failure."""
        client = await self._get_client()
        response = await client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    async def get_warnings(self) -> list[ActiveWarning]:
        """Every active nowcast warning with its areas, in one request.

        API 1.4.0 added /v1/nowcast/warnings. Older self-hosted APIs answer 404,
        in which case the list is assembled from the feed and one detail call each.
        """
        try:
            payload = await self.get_json("/v1/nowcast/warnings")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 404:
                raise
            return await self._get_warnings_legacy()

        missing = payload.get("meta", {}).get("missing") or []
        if missing:
            # BMKG did not return these details; they are retried on the next cycle
            logger.warning("bmkg_warnings_missing", codes=missing)
        warnings = [ActiveWarning(**entry) for entry in payload.get("data", [])]
        logger.info("bmkg_warnings_fetched", count=len(warnings), missing=len(missing))
        return warnings

    async def _get_warnings_legacy(self) -> list[ActiveWarning]:
        feed = NowcastListResponse(**await self.get_json("/v1/nowcast"))
        warnings: list[ActiveWarning] = []
        for item in feed.data:
            try:
                payload = await self.get_json(f"/v1/nowcast/{item.code}")
            except httpx.HTTPError as exc:
                logger.warning("bmkg_detail_failed", code=item.code, error=str(exc))
                continue
            detail = NowcastDetailResponse(**payload.get("data", payload))
            warnings.extend(
                ActiveWarning(
                    code=item.code,
                    province=detail.province or item.province,
                    published_at=item.published_at,
                    warning=warning,
                )
                for warning in detail.warnings
            )
        logger.info("bmkg_warnings_fetched", count=len(warnings), legacy=True)
        return warnings

    async def check_health(self) -> bool:
        """Check if the BMKG API is reachable."""
        try:
            client = await self._get_client()
            response = await client.get("/health")
            return response.status_code == 200
        except httpx.HTTPError:
            return False
