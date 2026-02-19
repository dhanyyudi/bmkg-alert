"""Wilayah proxy routes — forwards to BMKG REST API."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.dependencies import get_bmkg_client

router = APIRouter(prefix="/wilayah", tags=["wilayah"])


@router.get("/search")
async def search_wilayah(q: str = Query(..., min_length=2)):
    """Search for administrative areas (kecamatan, kabupaten, provinsi)."""
    client = get_bmkg_client()
    return await client.search_wilayah(q)


@router.get("/provinces")
async def get_provinces():
    """Get list of all provinces."""
    client = get_bmkg_client()
    return await client.get_provinces()
