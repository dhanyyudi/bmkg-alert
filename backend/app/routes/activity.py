"""Activity log routes."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.database import get_database

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("")
async def get_activity(limit: int = Query(50, ge=1, le=200)):
    """Get recent activity log entries."""
    db = get_database()
    rows = await db.fetch_all(
        "SELECT * FROM activity_log ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    return {"data": [dict(row) for row in rows]}
