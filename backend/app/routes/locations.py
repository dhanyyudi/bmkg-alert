"""Locations CRUD routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_database
from app.dependencies import require_write_allowed
from app.models import LocationCreate, LocationUpdate

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("")
async def list_locations():
    """List all monitored locations."""
    db = get_database()
    rows = await db.fetch_all("SELECT * FROM locations ORDER BY created_at DESC")
    return {"data": [dict(row) for row in rows]}


@router.post("", status_code=201, dependencies=[Depends(require_write_allowed)])
async def create_location(body: LocationCreate):
    """Add a new monitored location."""
    db = get_database()

    # Check for duplicate subdistrict_code
    existing = await db.fetch_one(
        "SELECT id FROM locations WHERE subdistrict_code = ?",
        (body.subdistrict_code,),
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Location with subdistrict_code {body.subdistrict_code} already exists",
        )

    cursor = await db.execute(
        """
        INSERT INTO locations (
            label, province_code, province_name, district_code,
            district_name, subdistrict_code, subdistrict_name,
            latitude, longitude
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            body.label,
            body.province_code,
            body.province_name,
            body.district_code,
            body.district_name,
            body.subdistrict_code,
            body.subdistrict_name,
            body.latitude,
            body.longitude,
        ),
    )
    location_id = cursor.lastrowid
    row = await db.fetch_one("SELECT * FROM locations WHERE id = ?", (location_id,))
    return {"data": dict(row)}


@router.get("/{location_id}")
async def get_location(location_id: int):
    """Get a specific location."""
    db = get_database()
    row = await db.fetch_one("SELECT * FROM locations WHERE id = ?", (location_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Location not found")
    return {"data": dict(row)}


@router.patch("/{location_id}", dependencies=[Depends(require_write_allowed)])
async def update_location(location_id: int, body: LocationUpdate):
    """Update a location's label or enabled status."""
    db = get_database()
    row = await db.fetch_one("SELECT * FROM locations WHERE id = ?", (location_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Location not found")

    updates = {}
    if body.label is not None:
        updates["label"] = body.label
    if body.enabled is not None:
        updates["enabled"] = 1 if body.enabled else 0

    if updates:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [location_id]
        await db.execute(
            f"UPDATE locations SET {set_clause} WHERE id = ?",
            tuple(values),
        )

    row = await db.fetch_one("SELECT * FROM locations WHERE id = ?", (location_id,))
    return {"data": dict(row)}


@router.delete("/{location_id}", dependencies=[Depends(require_write_allowed)])
async def delete_location(location_id: int):
    """Delete a monitored location."""
    db = get_database()
    row = await db.fetch_one("SELECT * FROM locations WHERE id = ?", (location_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Location not found")
    await db.execute("DELETE FROM locations WHERE id = ?", (location_id,))
    return {"status": "deleted", "id": location_id}
