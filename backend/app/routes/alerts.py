"""Alert history and stats routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query

from app.database import get_database

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("")
async def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
):
    """List alerts with pagination."""
    db = get_database()

    where = ""
    params: list = []
    if status:
        where = "WHERE status = ?"
        params.append(status)

    # Get total count
    count_row = await db.fetch_one(
        f"SELECT COUNT(*) as cnt FROM alerts {where}", tuple(params)
    )
    total = count_row["cnt"] if count_row else 0

    # Get page
    offset = (page - 1) * page_size
    params.extend([page_size, offset])
    rows = await db.fetch_all(
        f"SELECT * FROM alerts {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        tuple(params),
    )

    alerts = []
    for row in rows:
        alert = dict(row)
        if alert.get("polygon_data"):
            try:
                alert["polygon_data"] = json.loads(alert["polygon_data"])
            except (json.JSONDecodeError, TypeError):
                pass
        alerts.append(alert)

    return {
        "data": alerts,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/active")
async def get_active_alerts():
    """Get all currently active alerts."""
    db = get_database()
    rows = await db.fetch_all(
        "SELECT * FROM alerts WHERE status = 'active' ORDER BY created_at DESC"
    )
    alerts = []
    for row in rows:
        alert = dict(row)
        if alert.get("polygon_data"):
            try:
                alert["polygon_data"] = json.loads(alert["polygon_data"])
            except (json.JSONDecodeError, TypeError):
                pass
        alerts.append(alert)
    return {"data": alerts, "count": len(alerts)}


@router.get("/stats")
async def get_alert_stats():
    """Get alert statistics."""
    db = get_database()

    total_row = await db.fetch_one("SELECT COUNT(*) as cnt FROM alerts")
    month_row = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM alerts WHERE created_at >= date('now', 'start of month')"
    )
    locations_row = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM locations WHERE enabled = 1"
    )
    channels_row = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM notification_channels WHERE enabled = 1"
    )

    return {
        "total_alerts": total_row["cnt"] if total_row else 0,
        "alerts_this_month": month_row["cnt"] if month_row else 0,
        "monitored_locations": locations_row["cnt"] if locations_row else 0,
        "active_channels": channels_row["cnt"] if channels_row else 0,
    }


@router.get("/{alert_id}")
async def get_alert(alert_id: int):
    """Get a specific alert with delivery log."""
    db = get_database()
    row = await db.fetch_one("SELECT * FROM alerts WHERE id = ?", (alert_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert = dict(row)
    if alert.get("polygon_data"):
        try:
            alert["polygon_data"] = json.loads(alert["polygon_data"])
        except (json.JSONDecodeError, TypeError):
            pass

    # Get deliveries
    deliveries = await db.fetch_all(
        "SELECT * FROM alert_deliveries WHERE alert_id = ? ORDER BY sent_at DESC",
        (alert_id,),
    )

    return {
        "data": alert,
        "deliveries": [dict(d) for d in deliveries],
    }
