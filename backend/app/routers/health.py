"""Health check endpoints."""

from datetime import datetime, timezone
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from app.cache import cache
from app.models.responses import HealthResponse, ReadinessResponse

router = APIRouter(
    tags=["health"],
)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="""
    Returns the API status and checks cache connectivity.
    
    ## Response Status
    
    - `healthy`: API and cache are operational
    - `degraded`: API is running but cache is unavailable (using in-memory fallback)
    
    ## Use Cases
    
    - Load balancer health checks
    - Monitoring dashboards
    - Uptime monitoring services
    
    ## Cache Status
    
    The `cache` field indicates:
    - `healthy (redis)`: Connected to Redis
    - `healthy (in-memory fallback)`: Using local cache (Redis unavailable)
    - `unhealthy`: Cache is not functional
    """,
    responses={
        200: {
            "description": "API is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "timestamp": "2026-02-16T15:30:00+07:00",
                        "version": "1.0.0",
                        "cache": "healthy (redis)",
                    }
                }
            },
        },
        503: {
            "description": "API is degraded (cache unhealthy)",
            "content": {
                "application/json": {
                    "example": {
                        "status": "degraded",
                        "timestamp": "2026-02-16T15:30:00+07:00",
                        "version": "1.0.0",
                        "cache": "unhealthy",
                    }
                }
            },
        },
    },
)
async def health_check(request: Request):
    """Health check endpoint."""
    status_data = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "version": "1.0.0",
    }
    
    # Check cache health
    cache_healthy = await cache.health_check()
    if not cache_healthy:
        status_data["status"] = "degraded"
        status_data["cache"] = "unhealthy"
        return JSONResponse(content=status_data, status_code=503)
    
    # Show if using fallback
    if cache.is_using_fallback():
        status_data["cache"] = "healthy (in-memory fallback)"
    else:
        status_data["cache"] = "healthy (redis)"
    
    return JSONResponse(content=status_data)


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness check",
    description="""
    Readiness check for Kubernetes/Docker orchestration.
    
    Returns 200 when the application is ready to serve requests.
    Unlike the `/health` endpoint, this only checks if the app
    has finished initialization, not external dependencies.
    
    ## Use Cases
    
    - Kubernetes readiness probes
    - Docker health checks
    - Rolling deployment validation
    """,
    responses={
        200: {
            "description": "Application is ready",
            "content": {
                "application/json": {
                    "example": {
                        "ready": True,
                    }
                }
            },
        },
    },
)
async def readiness_check(request: Request):
    """Readiness check for Kubernetes/Docker healthcheck."""
    return JSONResponse(content={"ready": True})
