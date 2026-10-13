"""BMKG data for the dashboard, served from the BMKG REST API (BMKG_API_URL).

Every visitor shares this server's upstream rate limit, so each response is
cached here and reused until its TTL passes.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, HTTPException, Query

from app.cache import cache
from app.config import settings
from app.dependencies import get_bmkg_client

logger = structlog.get_logger()

router = APIRouter(tags=["bmkg"])

_ADM3_PATTERN = re.compile(r"^\d{2}\.\d{2}\.\d{2}$")
_ADM4_PATTERN = re.compile(r"^\d{2}\.\d{2}\.\d{2}\.\d{4}$")


async def _cached(key: str, ttl: int, fetch: Callable[[Any], Awaitable[dict[str, Any]]]) -> dict[str, Any]:
    cached = await cache.get(key)
    if cached is not None:
        return cached

    client = get_bmkg_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Klien API BMKG belum siap")

    try:
        payload = await fetch(client)
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        logger.warning("bmkg_upstream_error", key=key, status=status)
        if status == 404:
            raise HTTPException(status_code=404, detail="Data tidak ditemukan di API BMKG") from exc
        if status == 429:
            raise HTTPException(status_code=503, detail="API BMKG sedang membatasi permintaan, coba lagi sebentar") from exc
        raise HTTPException(status_code=502, detail="API BMKG menolak permintaan") from exc
    except httpx.HTTPError as exc:
        logger.warning("bmkg_upstream_unreachable", key=key, error=str(exc))
        raise HTTPException(status_code=502, detail="API BMKG tidak bisa dihubungi") from exc

    await cache.set(key, payload, ttl=ttl)
    return payload


@router.get("/nowcast/active")
async def get_active_warnings():
    """Every active nowcast warning in Indonesia, with affected areas and polygons."""

    async def fetch(client: Any) -> dict[str, Any]:
        active = await client.get_warnings()
        return {
            "data": [item.warning.model_dump(mode="json") for item in active],
            "meta": {"count": len(active)},
        }

    return await _cached("alert:nowcast:active", settings.cache_ttl_nowcast, fetch)


@router.get("/earthquake/recent")
async def get_recent_earthquakes():
    """Recent M 5.0+ earthquakes."""
    return await _cached(
        "alert:earthquake:recent",
        settings.cache_ttl_earthquake,
        lambda client: client.get_json("/v1/earthquake/recent"),
    )


@router.get("/earthquake/felt")
async def get_felt_earthquakes():
    """Recent earthquakes that were felt."""
    return await _cached(
        "alert:earthquake:felt",
        settings.cache_ttl_earthquake,
        lambda client: client.get_json("/v1/earthquake/felt"),
    )


@router.get("/wilayah/search")
async def search_wilayah(
    q: str = Query(..., min_length=2, max_length=50),
    limit: int = Query(20, ge=1, le=50),
):
    """Search provinces, kabupaten, kecamatan and villages by name."""
    query = " ".join(q.lower().split())
    return await _cached(
        f"alert:wilayah:search:{limit}:{query}",
        settings.cache_ttl_wilayah,
        lambda client: client.get_json("/v1/wilayah/search", {"q": query, "limit": limit}),
    )


@router.get("/wilayah/villages")
async def get_villages(subdistrict: str = Query(...)):
    """Kelurahan/desa of a kecamatan, e.g. `33.26.16`."""
    if not _ADM3_PATTERN.match(subdistrict):
        raise HTTPException(status_code=400, detail="Kode kecamatan tidak valid, contoh 33.26.16")
    return await _cached(
        f"alert:wilayah:villages:{subdistrict}",
        settings.cache_ttl_wilayah,
        lambda client: client.get_json("/v1/wilayah/villages", {"subdistrict": subdistrict}),
    )


@router.get("/weather/{adm4_code}")
async def get_weather_forecast(adm4_code: str):
    """3-day forecast for a kelurahan/desa, e.g. `33.26.16.2005`."""
    if not _ADM4_PATTERN.match(adm4_code):
        raise HTTPException(
            status_code=400,
            detail="Kode wilayah harus tingkat kelurahan/desa, contoh 33.26.16.2005",
        )
    return await _cached(
        f"alert:weather:{adm4_code}",
        settings.cache_ttl_weather,
        lambda client: client.get_json(f"/v1/weather/{adm4_code}"),
    )
