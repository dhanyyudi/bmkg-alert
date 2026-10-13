"""Configuration routes — read/write app config."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends

from app.config import settings
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


@router.post("/export", dependencies=[Depends(require_write_allowed)])
async def export_config():
    """Export full configuration as JSON, channel credentials included."""
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


# Columns an import may set on a location; everything else in the file is ignored
_LOCATION_FIELDS = (
    "label", "province_code", "province_name", "district_code", "district_name",
    "subdistrict_code", "subdistrict_name", "latitude", "longitude", "enabled",
)
_MASK = "••••••••"


@router.post("/import", dependencies=[Depends(require_write_allowed)])
async def import_config(data: dict):
    """Restore an export: settings, plus any location or channel that is not there yet."""
    db = get_database()
    imported = {"config": 0, "locations": 0, "channels": 0, "channels_skipped": 0}

    for key, value in (data.get("config") or {}).items():
        await db.execute(
            """
            INSERT INTO config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = CURRENT_TIMESTAMP
            """,
            (key, str(value), str(value)),
        )
        imported["config"] += 1

    for location in data.get("locations") or []:
        code = location.get("subdistrict_code")
        if not code or not location.get("subdistrict_name"):
            continue
        if await db.fetch_one("SELECT id FROM locations WHERE subdistrict_code = ?", (code,)):
            continue
        values = [location.get(field) for field in _LOCATION_FIELDS]
        values[-1] = 1 if location.get("enabled", True) else 0
        for index in range(1, 7):  # NOT NULL text columns
            values[index] = values[index] or ""
        await db.execute(
            f"INSERT INTO locations ({', '.join(_LOCATION_FIELDS)}) VALUES ({', '.join('?' * len(_LOCATION_FIELDS))})",
            tuple(values),
        )
        imported["locations"] += 1

    existing = {
        (row["channel_type"], json.dumps(json.loads(row["config"]), sort_keys=True))
        for row in await db.fetch_all("SELECT channel_type, config FROM notification_channels")
    }
    for channel in data.get("channels") or []:
        channel_type, config = channel.get("channel_type"), channel.get("config")
        if not channel_type or not isinstance(config, dict):
            continue
        # An export made without admin rights carries masked credentials, which cannot send anything
        if _MASK in config.values():
            imported["channels_skipped"] += 1
            continue
        key = (channel_type, json.dumps(config, sort_keys=True))
        if key in existing:
            continue
        await db.execute(
            "INSERT INTO notification_channels (channel_type, enabled, config) VALUES (?, ?, ?)",
            (channel_type, 1 if channel.get("enabled") else 0, json.dumps(config)),
        )
        existing.add(key)
        imported["channels"] += 1

    return {"status": "imported", "imported": imported}


@router.post("/reset", dependencies=[Depends(require_write_allowed)])
async def reset_config():
    """Reset configuration to defaults."""
    db = get_database()
    defaults = {
        "setup_completed": "false",
        "bmkg_api_url": settings.bmkg_api_url,
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
