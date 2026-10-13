"""Activity log routes."""

from __future__ import annotations

import re

from fastapi import APIRouter, Query, Request

from app.database import get_database
from app.dependencies import can_view_private

router = APIRouter(prefix="/activity", tags=["activity"])

# Entries written before chat IDs were dropped from the log look like
# "Trial registered for chat 123456789: Wiradesa"
_CHAT_ID = re.compile(r"(for chat )-?\d+")


@router.get("")
async def get_activity(request: Request, limit: int = Query(50, ge=1, le=200)):
    """Get recent activity log entries."""
    db = get_database()
    rows = await db.fetch_all(
        "SELECT * FROM activity_log ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    entries = [dict(row) for row in rows]
    if not can_view_private(request):
        for entry in entries:
            if entry.get("message"):
                entry["message"] = _CHAT_ID.sub(r"\1••••••••", entry["message"])
    return {"data": entries}
