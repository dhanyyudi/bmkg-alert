"""Standard API response models."""

from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

T = TypeVar("T")


class Meta(BaseModel):
    """Metadata for API responses."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "fetched_at": "2026-02-16T15:30:00+07:00",
                "cache_ttl": 60,
                "count": 15,
            }
        }
    )
    
    fetched_at: datetime = Field(..., description="When the data was fetched")
    cache_ttl: int | None = Field(None, description="Cache TTL in seconds")
    count: int | None = Field(None, description="Number of items in data (for lists)")


class APIResponse(BaseModel, Generic[T]):
    """Standard API response envelope.
    
    All API responses follow this structure:
    - `data`: The actual response payload
    - `meta`: Metadata about the request and caching
    - `attribution`: Data source attribution (always BMKG)
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "data": {},
                "meta": {
                    "fetched_at": "2026-02-16T15:30:00+07:00",
                    "cache_ttl": 60,
                },
                "attribution": "BMKG (Badan Meteorologi, Klimatologi, dan Geofisika)",
            }
        }
    )
    
    data: T = Field(..., description="The response data")
    meta: Meta | dict[str, Any] = Field(default_factory=dict, description="Metadata")
    attribution: str = Field(
        default="BMKG (Badan Meteorologi, Klimatologi, dan Geofisika)",
        description="Data attribution"
    )


class ErrorResponse(BaseModel):
    """Standard error response.
    
    Returned when an error occurs. Common error codes:
    - `bad_request`: Missing or invalid parameters
    - `not_found`: Resource not found
    - `rate_limit_exceeded`: Too many requests
    - `upstream_error`: BMKG API unavailable
    - `internal_error`: Unexpected server error
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "not_found",
                "message": "Province code 'xyz' not found. Use GET /v1/nowcast to see active provinces.",
                "status": 404,
                "retry_after": None,
            }
        }
    )
    
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    status: int = Field(..., description="HTTP status code")
    retry_after: int | None = Field(None, description="Seconds to wait before retry (for 429)")


class HealthResponse(BaseModel):
    """Health check response."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "timestamp": "2026-02-16T15:30:00+07:00",
                "version": "1.0.0",
                "cache": "healthy (redis)",
            }
        }
    )
    
    status: str = Field(..., description="API status: healthy, degraded, or unhealthy")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the check")
    version: str = Field(..., description="API version")
    cache: str | None = Field(None, description="Cache status")


class ReadinessResponse(BaseModel):
    """Readiness check response for Kubernetes/Docker."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ready": True,
            }
        }
    )
    
    ready: bool = Field(..., description="Whether the API is ready to serve requests")
