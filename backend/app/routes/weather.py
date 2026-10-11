"""Weather forecast route, served from the BMKG REST API (BMKG_API_URL)."""

from __future__ import annotations

import re

import httpx
import structlog
from fastapi import APIRouter, HTTPException

from app.cache import cache
from app.config import settings
from app.dependencies import get_bmkg_client

logger = structlog.get_logger()

router = APIRouter(prefix="/weather", tags=["weather"])

_ADM4_PATTERN = re.compile(r"^\d{2}\.\d{2}\.\d{2}\.\d{4}$")


@router.get("/{adm4_code}")
async def get_weather_forecast(adm4_code: str):
    """3-day forecast for a kelurahan/desa, e.g. `33.26.16.2005`."""
    if not _ADM4_PATTERN.match(adm4_code):
        raise HTTPException(
            status_code=400,
            detail="Kode wilayah harus tingkat kelurahan/desa, contoh 33.26.16.2005",
        )

    # Every visitor shares this server's upstream rate limit, so cache per location
    cache_key = f"alert:weather:{adm4_code}"
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    client = get_bmkg_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Klien API BMKG belum siap")

    try:
        payload = await client.get_weather(adm4_code)
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        logger.warning("weather_upstream_error", adm4=adm4_code, status=status)
        if status == 404:
            raise HTTPException(status_code=404, detail="BMKG tidak punya prakiraan untuk wilayah ini") from exc
        raise HTTPException(status_code=502, detail="API BMKG menolak permintaan prakiraan cuaca") from exc
    except httpx.HTTPError as exc:
        logger.warning("weather_upstream_unreachable", adm4=adm4_code, error=str(exc))
        raise HTTPException(status_code=502, detail="API BMKG tidak bisa dihubungi") from exc

    await cache.set(cache_key, payload, ttl=settings.cache_ttl_weather)
    return payload
