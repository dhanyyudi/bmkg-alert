"""BMKG REST API client — async HTTP with httpx."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import httpx
import structlog

from app.models import NowcastDetailResponse, NowcastListResponse

logger = structlog.get_logger()

REQUEST_TIMEOUT = 30.0


@runtime_checkable
class BMKGClient(Protocol):
    """Protocol for BMKG API client — enables test doubles."""

    async def get_nowcast_list(self) -> NowcastListResponse: ...
    async def get_nowcast_detail(self, code: str) -> NowcastDetailResponse: ...
    async def search_wilayah(self, query: str) -> dict[str, Any]: ...
    async def get_provinces(self) -> dict[str, Any]: ...
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

    async def get_nowcast_list(self) -> NowcastListResponse:
        """Fetch all active nowcast warnings."""
        client = await self._get_client()
        logger.info("bmkg_api_request", endpoint="/v1/nowcast")
        response = await client.get("/v1/nowcast")
        response.raise_for_status()
        data = response.json()
        logger.info(
            "bmkg_api_response",
            endpoint="/v1/nowcast",
            count=data.get("meta", {}).get("count", 0),
        )
        return NowcastListResponse(**data)

    async def get_nowcast_detail(self, code: str) -> NowcastDetailResponse:
        """Fetch detail for a specific nowcast warning."""
        client = await self._get_client()
        endpoint = f"/v1/nowcast/{code}"
        logger.debug("bmkg_api_request", endpoint=endpoint)
        response = await client.get(endpoint)
        response.raise_for_status()
        data = response.json()
        # The bmkg-api wraps the detail in a "data" key: {"data": {...}, "meta": {...}}
        inner = data.get("data", data)
        return NowcastDetailResponse(**inner)

    async def search_wilayah(self, query: str) -> dict[str, Any]:
        """Search for Indonesian administrative areas."""
        client = await self._get_client()
        response = await client.get("/v1/wilayah/search", params={"q": query})
        response.raise_for_status()
        return response.json()

    async def get_provinces(self) -> dict[str, Any]:
        """Get list of all provinces."""
        client = await self._get_client()
        response = await client.get("/v1/wilayah/provinces")
        response.raise_for_status()
        return response.json()

    async def check_health(self) -> bool:
        """Check if the BMKG API is reachable."""
        try:
            client = await self._get_client()
            response = await client.get("/v1/nowcast")
            return response.status_code == 200
        except (httpx.HTTPError, Exception):
            return False
