"""Coordinates for monitored locations, used to tell same-named kecamatan apart.

BMKG warnings name kecamatan without a code, and names repeat across provinces
("Wonosobo" is in Lampung and in Jawa Tengah). A warning also carries a polygon,
so a location far from every polygon of that warning is a different place.
"""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

# Warning polygons trace the affected cells loosely and a kecamatan is
# represented by one of its villages, so the test is deliberately generous:
# it only has to separate different regions, not draw a boundary.
MAX_DISTANCE_KM = 100.0


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance (haversine)."""
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 6371.0 * 2 * asin(sqrt(a))


def is_near_warning(latitude: float | None, longitude: float | None, areas: list[Any]) -> bool:
    """False only when the point is known and clearly outside every polygon of the warning.

    Missing coordinates or a warning without polygons cannot rule a match out,
    so both count as near: a missed warning is worse than an extra one.
    """
    if latitude is None or longitude is None:
        return True
    vertices = [point for area in areas for point in (area.polygon or []) if len(point) >= 2]
    if not vertices:
        return True
    return any(
        distance_km(latitude, longitude, point[0], point[1]) <= MAX_DISTANCE_KM
        for point in vertices
    )


async def resolve_point(client: Any, region_code: str) -> tuple[float, float] | None:
    """Coordinates of one village inside a region, from the BMKG API; None if unavailable.

    Accepts a kabupaten/kota ("34.04"), kecamatan ("34.04.07") or village code.
    """
    try:
        code = region_code
        if code.count(".") == 1:
            code = await _first_child(client, "/v1/wilayah/subdistricts", "district", code)
        if code and code.count(".") == 2:
            code = await _first_child(client, "/v1/wilayah/villages", "subdistrict", code)
        if not code:
            return None
        forecast = await client.get_json(f"/v1/weather/{code}")
        location = forecast.get("data", {}).get("location", {})
        lat, lon = location.get("lat"), location.get("lon")
        if lat is None or lon is None:
            return None
        return float(lat), float(lon)
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        logger.warning("region_point_unresolved", code=region_code, error=str(exc))
        return None


async def _first_child(client: Any, path: str, param: str, code: str) -> str | None:
    children = (await client.get_json(path, {param: code})).get("data") or []
    return children[0]["code"] if children else None


async def kecamatan_names(client: Any, district_code: str) -> set[str]:
    """Lower-cased names of the kecamatan in a kabupaten/kota; empty if unavailable."""
    try:
        children = (await client.get_json("/v1/wilayah/subdistricts", {"district": district_code})).get("data") or []
    except httpx.HTTPError as exc:
        logger.warning("district_members_unresolved", code=district_code, error=str(exc))
        return set()
    return {" ".join(child["name"].lower().split()) for child in children if child.get("name")}
