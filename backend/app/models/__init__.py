"""Pydantic models for the BMKG API."""

from app.models.earthquake import (
    Earthquake,
    EarthquakeWithDistance,
    EarthquakeListMeta,
    NearbyEarthquakeMeta,
)
from app.models.weather import (
    Location as WeatherLocation,
    ForecastEntry,
    ForecastDay,
    WeatherForecast,
    CurrentWeather,
    WeatherForecastMeta,
)
from app.models.wilayah import (
    Wilayah,
    WilayahLevel,
    WilayahSearchResult,
    WilayahListResponse,
    WilayahSearchResponse,
)
from app.models.nowcast import (
    Area,
    Warning,
    ActiveProvince,
    NowcastDetailResponse,
    NowcastListResponse,
    LocationCheckResult,
    NowcastMeta,
)
from app.models.enums import (
    Severity,
    Urgency,
    Certainty,
    WeatherCode,
    WEATHER_CODE_NAMES,
)
from app.models.responses import (
    Meta,
    APIResponse,
    ErrorResponse,
    HealthResponse,
    ReadinessResponse,
)
from app.models.alert import (
    MonitoredLocation,
    MonitoredLocation as Location,  # alias used by engine files
    AlertRecord,
    AlertRecord as Alert,           # alias used by engine/state.py
    MatchResult,
    WarningInfo,
    LocationCreate,
    LocationUpdate,
    ChannelCreate,
    ChannelUpdate,
    ConfigUpdate,
)

__all__ = [
    # Earthquake
    "Earthquake",
    "EarthquakeWithDistance",
    "EarthquakeListMeta",
    "NearbyEarthquakeMeta",
    # Weather
    "WeatherLocation",
    "ForecastEntry",
    "ForecastDay",
    "WeatherForecast",
    "CurrentWeather",
    "WeatherForecastMeta",
    # Wilayah
    "Wilayah",
    "WilayahLevel",
    "WilayahSearchResult",
    "WilayahListResponse",
    "WilayahSearchResponse",
    # Nowcast
    "Area",
    "Warning",
    "ActiveProvince",
    "NowcastDetailResponse",
    "NowcastListResponse",
    "LocationCheckResult",
    "NowcastMeta",
    # Enums
    "Severity",
    "Urgency",
    "Certainty",
    "WeatherCode",
    "WEATHER_CODE_NAMES",
    # Responses
    "Meta",
    "APIResponse",
    "ErrorResponse",
    "HealthResponse",
    "ReadinessResponse",
    # Alert system models
    "MonitoredLocation",
    "Location",
    "AlertRecord",
    "Alert",
    "MatchResult",
    "WarningInfo",
    "LocationCreate",
    "LocationUpdate",
    "ChannelCreate",
    "ChannelUpdate",
    "ConfigUpdate",
]
