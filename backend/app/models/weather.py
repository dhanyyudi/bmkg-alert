"""Pydantic models for weather forecast data."""

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class Location(BaseModel):
    """Location information for weather forecast.
    
    ADM4 code represents kelurahan/desa (village) level in Indonesian
    administrative hierarchy.
    """
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "code": "33.26.16.1001",
                "province": "Jawa Tengah",
                "district": "Kab. Pekalongan",
                "subdistrict": "Wiradesa",
                "village": "Kadipaten",
                "lat": -6.89,
                "lon": 109.67,
                "timezone": "+0700",
            }
        }
    )
    
    code: str = Field(..., description="ADM4 area code (kelurahan/desa)")
    province: str = Field(..., description="Province name")
    district: str = Field(..., description="District/Kabupaten name")
    subdistrict: str = Field(..., description="Subdistrict/Kecamatan name")
    village: str = Field(..., description="Village/Kelurahan name")
    lat: float = Field(..., description="Latitude", ge=-90, le=90)
    lon: float = Field(..., description="Longitude", ge=-180, le=180)
    timezone: str = Field(..., description="Timezone offset (e.g., +0700)")


class ForecastEntry(BaseModel):
    """Single forecast entry for a specific time.
    
    Contains weather conditions at a specific time interval.
    BMKG provides forecasts in 3-hour intervals (00:00, 03:00, 06:00, etc.)
    """
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "local_datetime": "2026-02-16 13:00:00",
                "utc_datetime": "2026-02-16 06:00:00",
                "temperature_c": 31,
                "humidity_pct": 70,
                "weather": "Cerah Berawan",
                "weather_en": "Partly Cloudy",
                "weather_code": 1,
                "wind_speed_kmh": 7.3,
                "wind_direction": "SW",
                "wind_direction_deg": 225,
                "cloud_cover_pct": 40,
                "visibility_m": 10000,
                "visibility_text": "> 10 km",
                "icon_url": "https://api-apps.bmkg.go.id/storage/icon/cuaca/cerah-berawan-am.svg",
            }
        }
    )
    
    datetime_local: str = Field(
        ...,
        alias="local_datetime",
        description="Local datetime (YYYY-MM-DD HH:MM:SS)"
    )
    datetime_utc: str = Field(
        ...,
        alias="utc_datetime",
        description="UTC datetime (YYYY-MM-DD HH:MM:SS)"
    )
    temperature_c: int = Field(..., description="Temperature in Celsius", ge=-50, le=60)
    humidity_pct: int = Field(..., description="Humidity percentage", ge=0, le=100)
    weather: str = Field(..., description="Weather condition (Indonesian)")
    weather_en: str = Field(..., description="Weather condition (English)")
    weather_code: int = Field(..., description="BMKG weather code (0-97)")
    wind_speed_kmh: float = Field(..., description="Wind speed in km/h", ge=0)
    wind_direction: str = Field(..., description="Wind direction (e.g., SW, NNE)")
    wind_direction_deg: int = Field(..., description="Wind direction in degrees (0-360)", ge=0, le=360)
    cloud_cover_pct: int = Field(..., description="Cloud cover percentage", ge=0, le=100)
    visibility_m: int = Field(..., description="Visibility in meters", ge=0)
    visibility_text: str = Field(..., description="Visibility as text (e.g., '> 10 km')")
    icon_url: str = Field(..., description="URL to weather icon SVG")


class ForecastDay(BaseModel):
    """Forecast data for a single day.
    
    Contains all forecast entries for a specific date.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date": "2026-02-16",
                "entries": [],
            }
        }
    )
    
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    entries: list[ForecastEntry] = Field(..., description="Forecast entries for this day (typically 8 entries)")


class WeatherForecast(BaseModel):
    """Complete weather forecast response.
    
    Contains location information and 3-day forecast data.
    BMKG updates forecasts twice daily.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "location": {
                    "code": "33.26.16.1001",
                    "province": "Jawa Tengah",
                    "district": "Kab. Pekalongan",
                    "subdistrict": "Wiradesa",
                    "village": "Kadipaten",
                    "lat": -6.89,
                    "lon": 109.67,
                    "timezone": "+0700",
                },
                "forecast": [],
            }
        }
    )
    
    location: Location = Field(..., description="Location information")
    forecast: list[ForecastDay] = Field(..., description="3-day forecast data")


class CurrentWeather(BaseModel):
    """Current weather data (single forecast entry).
    
    Returns the forecast entry closest to current time.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "location": {
                    "code": "33.26.16.1001",
                    "province": "Jawa Tengah",
                    "district": "Kab. Pekalongan",
                    "subdistrict": "Wiradesa",
                    "village": "Kadipaten",
                    "lat": -6.89,
                    "lon": 109.67,
                    "timezone": "+0700",
                },
                "current": {
                    "local_datetime": "2026-02-16 13:00:00",
                    "utc_datetime": "2026-02-16 06:00:00",
                    "temperature_c": 31,
                    "humidity_pct": 70,
                    "weather": "Cerah Berawan",
                    "weather_en": "Partly Cloudy",
                    "weather_code": 1,
                    "wind_speed_kmh": 7.3,
                    "wind_direction": "SW",
                    "wind_direction_deg": 225,
                    "cloud_cover_pct": 40,
                    "visibility_m": 10000,
                    "visibility_text": "> 10 km",
                    "icon_url": "https://api-apps.bmkg.go.id/storage/icon/cuaca/cerah-berawan-am.svg",
                },
            }
        }
    )
    
    location: Location = Field(..., description="Location information")
    current: ForecastEntry = Field(..., description="Current forecast entry")


class WeatherForecastMeta(BaseModel):
    """Metadata for weather forecast responses."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "forecast_days": 3,
                "entries_per_day": 8,
                "fetched_at": "2026-02-16T15:30:00+07:00",
                "cache_ttl": 900,
            }
        }
    )
    
    forecast_days: int = Field(..., description="Number of forecast days")
    entries_per_day: int = Field(..., description="Number of entries per day")
    fetched_at: datetime = Field(..., description="When the data was fetched")
    cache_ttl: int = Field(..., description="Cache TTL in seconds")
