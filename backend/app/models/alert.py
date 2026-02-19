"""Pydantic models for BMKG Alert management system.

These models are used by the alert engine, state manager, notification
dispatcher, and CRUD routes — separate from the BMKG API data models.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# Re-export Warning as WarningInfo so engine/dispatcher can use the same type
# without importing directly from nowcast (avoids circular deps)
from app.models.nowcast import Warning as WarningInfo  # noqa: F401


class MonitoredLocation(BaseModel):
    """A monitored location stored in the `locations` table."""

    id: int = 0
    label: str | None = None
    province_code: str = ""
    province_name: str = ""
    district_code: str = ""
    district_name: str = ""
    subdistrict_code: str = ""
    subdistrict_name: str = ""
    latitude: float | None = None
    longitude: float | None = None
    enabled: bool = True
    created_at: str | None = None


class LocationCreate(BaseModel):
    """Payload for creating a new monitored location."""

    label: str | None = None
    province_code: str
    province_name: str
    district_code: str
    district_name: str
    subdistrict_code: str
    subdistrict_name: str
    latitude: float | None = None
    longitude: float | None = None


class LocationUpdate(BaseModel):
    """Payload for updating a monitored location (PATCH)."""

    label: str | None = None
    enabled: bool | None = None


class AlertRecord(BaseModel):
    """A matched alert stored in the `alerts` table."""

    id: int = 0
    bmkg_alert_code: str = ""
    event: str | None = None
    severity: str | None = None
    urgency: str | None = None
    certainty: str | None = None
    headline: str | None = None
    description: str | None = None
    effective: str | None = None
    expires: str | None = None
    infographic_url: str | None = None
    polygon_data: str | None = None
    matched_location_id: int | None = None
    match_type: str | None = None
    matched_text: str | None = None
    status: str = "active"
    expired_notified: bool = False
    created_at: str | None = None


class MatchResult(BaseModel):
    """Result of matching a BMKG warning against a monitored location."""

    location: MonitoredLocation
    match_type: str  # 'kecamatan' | 'kabupaten'
    matched_text: str


class ChannelCreate(BaseModel):
    """Payload for creating a notification channel."""

    channel_type: str
    enabled: bool = False
    config: dict[str, Any]


class ChannelUpdate(BaseModel):
    """Payload for updating a notification channel (PATCH)."""

    enabled: bool | None = None
    config: dict[str, Any] | None = None


class ConfigUpdate(BaseModel):
    """Payload for updating configuration key-value pairs."""

    settings: dict[str, str]
