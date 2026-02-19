"""Pydantic models for BMKG Alert — API, domain, and request/response types."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel

# ─── Enums ───────────────────────────────────────────────────────────────────


class Severity(str, Enum):
    MINOR = "Minor"
    MODERATE = "Moderate"
    SEVERE = "Severe"
    EXTREME = "Extreme"


class ChannelType(str, Enum):
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"
    EMAIL = "email"
    WEBHOOK = "webhook"


class AlertStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class DeliveryStatus(str, Enum):
    SENT = "sent"
    FAILED = "failed"
    SKIPPED_QUIET_HOURS = "skipped_quiet_hours"
    SKIPPED_SEVERITY = "skipped_severity"


# ─── BMKG API Response Models ───────────────────────────────────────────────


class NowcastListItem(BaseModel):
    """Single item from GET /v1/nowcast response."""

    code: str
    province: str
    description: str
    published_at: str
    detail_url: str


class NowcastListResponse(BaseModel):
    """Full response from GET /v1/nowcast."""

    data: list[NowcastListItem]
    meta: dict[str, Any] = {}
    attribution: str = ""


class WarningArea(BaseModel):
    """Area affected by a warning."""

    name: str
    polygon: list[list[float]] = []


class WarningInfo(BaseModel):
    """Single warning from GET /v1/nowcast/{code}."""

    identifier: str = ""
    event: str = ""
    severity: str = ""
    urgency: str = ""
    certainty: str = ""
    effective: str = ""
    expires: str = ""
    headline: str = ""
    description: str = ""
    sender: str = ""
    infographic_url: str = ""
    areas: list[WarningArea] = []
    is_expired: bool = False


class NowcastDetailData(BaseModel):
    """Data field from GET /v1/nowcast/{code}."""

    province: str
    warnings: list[WarningInfo] = []


class NowcastDetailResponse(BaseModel):
    """Full response from GET /v1/nowcast/{code}."""

    data: NowcastDetailData
    meta: dict[str, Any] = {}
    attribution: str = ""


# ─── Domain Models ───────────────────────────────────────────────────────────


class Location(BaseModel):
    """Monitored location from database."""

    id: int = 0
    label: str = ""
    province_code: str
    province_name: str
    district_code: str
    district_name: str
    subdistrict_code: str
    subdistrict_name: str
    latitude: float | None = None
    longitude: float | None = None
    enabled: bool = True
    created_at: str = ""


class NotificationChannel(BaseModel):
    """Notification channel from database."""

    id: int = 0
    channel_type: str
    enabled: bool = False
    config: dict[str, Any] = {}
    last_success_at: str | None = None
    last_error: str | None = None
    created_at: str = ""
    updated_at: str = ""


class Alert(BaseModel):
    """Stored alert from database."""

    id: int = 0
    bmkg_alert_code: str
    event: str = ""
    severity: str = ""
    urgency: str = ""
    certainty: str = ""
    headline: str = ""
    description: str = ""
    effective: str = ""
    expires: str = ""
    infographic_url: str = ""
    polygon_data: str = ""
    matched_location_id: int | None = None
    match_type: str = ""
    matched_text: str = ""
    status: str = "active"
    expired_notified: bool = False
    created_at: str = ""


class AlertDelivery(BaseModel):
    """Delivery log entry."""

    id: int = 0
    alert_id: int
    channel_id: int
    status: str
    error_message: str = ""
    sent_at: str = ""


class ActivityLogEntry(BaseModel):
    """Activity log entry."""

    id: int = 0
    event_type: str
    message: str = ""
    details: str = ""
    created_at: str = ""


# ─── Request Models ─────────────────────────────────────────────────────────


class LocationCreate(BaseModel):
    """Request to add a new monitored location."""

    label: str = ""
    province_code: str
    province_name: str
    district_code: str
    district_name: str
    subdistrict_code: str
    subdistrict_name: str
    latitude: float | None = None
    longitude: float | None = None


class LocationUpdate(BaseModel):
    """Request to update a location."""

    label: str | None = None
    enabled: bool | None = None


class ChannelCreate(BaseModel):
    """Request to add a notification channel."""

    channel_type: str
    enabled: bool = True
    config: dict[str, Any]


class ChannelUpdate(BaseModel):
    """Request to update a notification channel."""

    enabled: bool | None = None
    config: dict[str, Any] | None = None


class ConfigUpdate(BaseModel):
    """Request to update configuration."""

    settings: dict[str, str]


# ─── Response Models ─────────────────────────────────────────────────────────


class MatchResult(BaseModel):
    """Result of matching a warning against a location."""

    location: Location
    match_type: str  # "kecamatan" or "kabupaten"
    matched_text: str


class EngineStatus(BaseModel):
    """Engine runtime status."""

    running: bool = False
    last_poll: str | None = None
    last_poll_result: str | None = None
    next_poll: str | None = None
    poll_interval: int = 300
    active_warnings: int = 0


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    engine: str = "stopped"
    last_poll: str | None = None
    last_poll_result: str | None = None
    active_warnings: int = 0
    uptime_seconds: int = 0
    version: str = "1.0.0"
    demo_mode: bool = False
    bmkg_api_url: str = ""
    bmkg_api_status: str = "unknown"
    monitored_locations: int = 0
    active_channels: list[str] = []
    active_trials: int = 0


class AlertStats(BaseModel):
    """Dashboard statistics."""

    total_alerts: int = 0
    alerts_this_month: int = 0
    monitored_locations: int = 0
    active_channels: int = 0


class PaginatedResponse(BaseModel):
    """Wrapper for paginated responses."""

    data: list[Any] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
