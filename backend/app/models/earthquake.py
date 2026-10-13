"""Pydantic models for earthquake data."""

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class Earthquake(BaseModel):
    """Earthquake data model.
    
    Represents a single earthquake event from BMKG's seismic network.
    All times are in UTC.
    """
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "datetime": "2026-02-16T13:15:30+00:00",
                "magnitude": 5.4,
                "depth_km": 10.0,
                "lat": -6.89,
                "lon": 109.67,
                "lat_text": "6.89 LS",
                "lon_text": "109.67 BT",
                "region": "18 km TimurLaut Pekalongan",
                "tsunami_potential": "Tidak berpotensi tsunami",
                "felt_report": "III Pekalongan, II Batang",
                "shakemap_url": "https://data.bmkg.go.id/DataMKG/TEWS/20260216131530.mmi.jpg",
            }
        }
    )
    
    occurred_at: datetime = Field(
        ...,
        alias="datetime",
        description="Earthquake occurrence time (UTC)"
    )
    magnitude: float = Field(..., description="Earthquake magnitude (Richter scale)", ge=0, le=12)
    depth_km: float = Field(..., description="Depth in kilometers", ge=0)
    lat: float = Field(..., description="Latitude", ge=-90, le=90)
    lon: float = Field(..., description="Longitude", ge=-180, le=180)
    lat_text: str = Field(..., description="Latitude in text format (e.g., '6.89 LS')")
    lon_text: str = Field(..., description="Longitude in text format (e.g., '109.67 BT')")
    region: str = Field(..., description="Region description relative to nearest city")
    tsunami_potential: str | None = Field(None, description="Tsunami potential warning in Indonesian")
    felt_report: str | None = Field(None, description="Felt report description with intensity scale")
    shakemap_url: str | None = Field(None, description="URL to shakemap image (if available)")
