"""Configuration routes — read/write app config."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends

from app.database import get_database
from app.dependencies import require_write_allowed
from app.models import ConfigUpdate

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
async def get_config():
    """Get all configuration values."""
    db = get_database()
    rows = await db.fetch_all("SELECT key, value FROM config ORDER BY key")
    config = {row["key"]: row["value"] for row in rows}
    return {"data": config}


@router.put("", dependencies=[Depends(require_write_allowed)])
async def update_config(body: ConfigUpdate):
    """Update configuration values."""
    db = get_database()
    for key, value in body.settings.items():
        await db.execute(
            """
            INSERT INTO config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = CURRENT_TIMESTAMP
            """,
            (key, value, value),
        )
    # Return updated config
    rows = await db.fetch_all("SELECT key, value FROM config ORDER BY key")
    config = {row["key"]: row["value"] for row in rows}
    return {"data": config}


@router.post("/export")
async def export_config():
    """Export full configuration as JSON."""
    db = get_database()

    config_rows = await db.fetch_all("SELECT key, value FROM config")
    location_rows = await db.fetch_all("SELECT * FROM locations")
    channel_rows = await db.fetch_all("SELECT * FROM notification_channels")

    channels = []
    for row in channel_rows:
        channel = dict(row)
        if isinstance(channel.get("config"), str):
            channel["config"] = json.loads(channel["config"])
        channels.append(channel)

    return {
        "config": {row["key"]: row["value"] for row in config_rows},
        "locations": [dict(row) for row in location_rows],
        "channels": channels,
    }


@router.post("/import", dependencies=[Depends(require_write_allowed)])
async def import_config(data: dict):
    """Import configuration from JSON export."""
    db = get_database()

    if "config" in data:
        for key, value in data["config"].items():
            await db.execute(
                """
                INSERT INTO config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = CURRENT_TIMESTAMP
                """,
                (key, value, value),
            )

    return {"status": "imported"}


@router.post("/reset", dependencies=[Depends(require_write_allowed)])
async def reset_config():
    """Reset configuration to defaults."""
    db = get_database()
    defaults = {
        "setup_completed": "false",
        "bmkg_api_url": "https://bmkg-restapi.vercel.app",
        "poll_interval": "300",
        "severity_threshold": "all",
        "quiet_hours_enabled": "false",
        "quiet_hours_start": "22:00",
        "quiet_hours_end": "06:00",
        "quiet_hours_override_severe": "true",
        "notification_language": "id",
    }
    for key, value in defaults.items():
        await db.execute(
            """
            INSERT INTO config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = CURRENT_TIMESTAMP
            """,
            (key, value, value),
        )
    return {"data": defaults}
