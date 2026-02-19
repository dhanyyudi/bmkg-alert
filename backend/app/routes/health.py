"""Health check routes."""

from __future__ import annotations

import time

from fastapi import APIRouter

from app.config import get_settings
from app.database import get_database
from app.dependencies import get_bmkg_client, get_engine

router = APIRouter(tags=["health"])

_start_time: float = time.time()


@router.get("/health")
async def health_check():
    """Full health check with component status."""
    settings = get_settings()
    db = get_database()

    # Engine status
    engine = get_engine()
    engine_status = engine.get_status() if engine else {"running": False}

    # BMKG API status
    bmkg_client = get_bmkg_client()
    bmkg_ok = False
    if bmkg_client:
        try:
            bmkg_ok = await bmkg_client.check_health()
        except Exception:
            bmkg_ok = False

    # Counts
    locations_row = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM locations WHERE enabled = 1"
    )
    channels_rows = await db.fetch_all(
        "SELECT channel_type FROM notification_channels WHERE enabled = 1"
    )
    active_row = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM alerts WHERE status = 'active'"
    )
    trials_row = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM trial_subscriptions WHERE expires_at > datetime('now')"
    )

    return {
        "status": "healthy",
        "engine": "running" if engine_status.get("running") else "stopped",
        "last_poll": engine_status.get("last_poll"),
        "last_poll_result": engine_status.get("last_poll_result"),
        "active_warnings": active_row["cnt"] if active_row else 0,
        "uptime_seconds": int(time.time() - _start_time),
        "version": "1.0.0",
        "demo_mode": settings.demo_mode,
        "bmkg_api_url": settings.bmkg_api_url,
        "bmkg_api_status": "connected" if bmkg_ok else "unreachable",
        "monitored_locations": locations_row["cnt"] if locations_row else 0,
        "active_channels": [dict(r)["channel_type"] for r in channels_rows],
        "active_trials": trials_row["cnt"] if trials_row else 0,
    }
