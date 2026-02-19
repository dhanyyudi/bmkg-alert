"""Wilayah (region) models for the BMKG API."""

from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class WilayahLevel(str, Enum):
    """Hierarchy levels for Indonesian administrative regions.
    
    Based on Permendagri No. 72/2019 standard:
    - Province (Provinsi): 2 digits (e.g., "33")
    - District (Kabupaten/Kota): 5 digits (e.g., "33.26")
    - Subdistrict (Kecamatan): 8 digits (e.g., "33.26.16")
    - Village (Kelurahan/Desa): 13 digits (e.g., "33.26.16.1001")
    """
    
    PROVINCE = "province"
    DISTRICT = "district"
    SUBDISTRICT = "subdistrict"
    VILLAGE = "village"


class Wilayah(BaseModel):
    """Base wilayah model.
    
    Represents an administrative region in Indonesia using
    the standard Permendagri coding system.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "33.26",
                "name": "KAB. PEKALONGAN",
                "level": "district",
            }
        }
    )
    
    code: str = Field(..., description="Wilayah code (Permendagri format)")
    name: str = Field(..., description="Wilayah name")
    level: WilayahLevel = Field(..., description="Administrative level")


class WilayahSearchResult(Wilayah):
    """Wilayah search result with full path.
    
    Includes the complete hierarchy path for easier identification.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "33.26.16",
                "name": "Wiradesa",
                "level": "subdistrict",
                "full_path": "Jawa Tengah > Kab. Pekalongan > Wiradesa",
                "parent_code": "33.26",
            }
        }
    )
    
    full_path: str = Field(..., description="Full hierarchical path (e.g., 'Jawa Tengah > Kab. Pekalongan > Wiradesa')")
    parent_code: str | None = Field(None, description="Parent wilayah code")


class WilayahListResponse(BaseModel):
    """Response model for wilayah list endpoints.
    
    Used by endpoints that return lists of regions
    (provinces, districts, subdistricts, villages).
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "data": [
                    {"code": "33", "name": "JAWA TENGAH", "level": "province"},
                    {"code": "34", "name": "DAERAH ISTIMEWA YOGYAKARTA", "level": "province"},
                ],
                "meta": {"count": 34},
            }
        }
    )
    
    data: list[Wilayah]
    meta: dict = Field(default_factory=dict)


class WilayahSearchResponse(BaseModel):
    """Response model for wilayah search endpoint.
    
    Returns search results with full path information.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "data": [
                    {
                        "code": "33.26.16",
                        "name": "Wiradesa",
                        "level": "subdistrict",
                        "full_path": "Jawa Tengah > Kab. Pekalongan > Wiradesa",
                        "parent_code": "33.26",
                    }
                ],
                "meta": {"query": "wiradesa", "count": 1},
            }
        }
    )
    
    data: list[WilayahSearchResult]
    meta: dict = Field(default_factory=dict)
