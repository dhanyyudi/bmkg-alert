"""Pydantic models for nowcast (weather warning) data."""

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from app.models.enums import Severity, Urgency, Certainty


class Area(BaseModel):
    """Affected area within a weather warning.
    
    Represents a specific geographic area (kecamatan/village level)
    that is affected by the weather warning.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Kec. Wiradesa, Kab. Pekalongan",
                "polygon": [[-6.89, 109.67], [-6.88, 109.68], [-6.87, 109.67]],
            }
        }
    )
    
    name: str = Field(..., description="Area name (kecamatan/kabupaten)")
    polygon: list[list[float]] | None = Field(None, description="Polygon coordinates [lat, lon]")


class Warning(BaseModel):
    """Weather warning from BMKG.
    
    Parsed from CAP (Common Alerting Protocol) XML format.
    Contains all details about a severe weather warning.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "identifier": "BMKG-20260216-001",
                "event": "Hujan Lebat disertai Petir dan Angin Kencang",
                "severity": "Moderate",
                "urgency": "Expected",
                "certainty": "Likely",
                "effective": "2026-02-16T20:00:00+07:00",
                "expires": "2026-02-17T02:00:00+07:00",
                "headline": "Peringatan Dini Cuaca Jawa Tengah",
                "description": "Hujan lebat disertai petir dan angin kencang berpotensi terjadi di...",
                "sender": "BMKG",
                "infographic_url": "https://nowcasting.bmkg.go.id/infographic.png",
                "areas": [
                    {"name": "Kec. Wiradesa, Kab. Pekalongan", "polygon": None}
                ],
                "is_expired": False,
            }
        }
    )
    
    identifier: str = Field(..., description="Unique warning identifier")
    event: str = Field(..., description="Event type in Indonesian")
    severity: Severity = Field(..., description="Severity level (Extreme/Severe/Moderate/Minor/Unknown)")
    urgency: Urgency = Field(..., description="Urgency level (Immediate/Expected/Future/Past/Unknown)")
    certainty: Certainty = Field(..., description="Certainty level (Observed/Likely/Possible/Unlikely/Unknown)")
    effective: datetime = Field(..., description="When the warning takes effect")
    expires: datetime = Field(..., description="When the warning expires")
    headline: str = Field(..., description="Warning headline")
    description: str = Field(..., description="Detailed warning description")
    sender: str = Field(..., description="Warning sender (usually BMKG)")
    infographic_url: str | None = Field(None, description="URL to infographic image")
    areas: list[Area] = Field(default_factory=list, description="Affected areas")
    is_expired: bool = Field(..., description="Whether the warning has expired")


class ActiveProvince(BaseModel):
    """Province with active weather warnings.
    
    Listed in the RSS feed of active warnings.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "jateng",
                "province": "Jawa Tengah",
                "description": "Peringatan dini cuaca...",
                "published_at": "2026-02-16T20:00:00+07:00",
                "detail_url": "/v1/nowcast/jateng",
            }
        }
    )
    
    code: str = Field(..., description="Province code for API")
    province: str = Field(..., description="Province name")
    description: str = Field(..., description="Warning description")
    published_at: datetime = Field(..., description="When the warning was published")
    detail_url: str = Field(..., description="API URL to get full warning details")


class NowcastDetailResponse(BaseModel):
    """Detailed nowcast response for a province.
    
    Contains all active warnings for a specific province.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "province": "Jawa Tengah",
                "warnings": [],
            }
        }
    )
    
    province: str = Field(..., description="Province name")
    warnings: list[Warning] = Field(..., description="List of active warnings")


class LocationCheckResult(BaseModel):
    """Result of checking warnings for a specific location."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "location": "Wiradesa",
                "has_warnings": True,
                "warnings": [],
            }
        }
    )
    
    location: str = Field(..., description="Location name that was checked")
    has_warnings: bool = Field(..., description="Whether there are active warnings for this location")
    warnings: list[Warning] = Field(default_factory=list, description="Active warnings affecting this location")


class NowcastListResponse(BaseModel):
    """Response wrapper for list of active provinces (used by engine BMKG client)."""
    data: list[ActiveProvince] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)


class NowcastMeta(BaseModel):
    """Metadata for nowcast responses."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "count": 5,
                "fetched_at": "2026-02-16T20:05:00+07:00",
                "cache_ttl": 120,
                "language": "id",
            }
        }
    )
    
    count: int = Field(..., description="Number of items")
    fetched_at: datetime = Field(..., description="When the data was fetched")
    cache_ttl: int = Field(..., description="Cache TTL in seconds")
    language: str = Field(default="id", description="Language code (id/en)")
