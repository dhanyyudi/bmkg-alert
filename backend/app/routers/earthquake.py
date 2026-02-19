"""Earthquake API routes."""

from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Query, Request, Depends, status, Response
from fastapi.responses import JSONResponse

from app.core.auth import verify_admin

from app.config import settings
from app.dependencies import limiter
from app.models.earthquake import Earthquake, EarthquakeWithDistance, EarthquakeListMeta, NearbyEarthquakeMeta
from app.models.responses import APIResponse, ErrorResponse
from app.services.earthquake_service import earthquake_service

router = APIRouter(
    prefix="/v1/earthquake",
    tags=["earthquake"],
)


def serialize_earthquake(eq: Earthquake) -> dict:
    """Serialize earthquake to dict with 'datetime' field name for API response."""
    data = eq.model_dump(by_alias=True, mode='json')
    return data


@router.get(
    "/latest",
    response_model=APIResponse[Earthquake],
    summary="Get latest earthquake",
    description="""
    Returns the most recent earthquake detected by BMKG's seismic network.
    
    **Cache:** 60 seconds  
    **Source:** https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json
    
    ## Response
    
    Returns a single earthquake object with details including:
    - Magnitude and depth
    - Coordinates (lat/lon)
    - Region description
    - Tsunami potential warning
    - Shakemap URL (if available)
    
    ## Error Responses
    
    - `502`: BMKG API unavailable
    - `429`: Rate limit exceeded
    """,
    responses={
        200: {
            "description": "Latest earthquake data",
            "content": {
                "application/json": {
                    "example": {
                        "data": {
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
                        },
                        "meta": {
                            "fetched_at": "2026-02-16T15:30:00+07:00",
                            "cache_ttl": 60,
                        },
                        "attribution": "BMKG (Badan Meteorologi, Klimatologi, dan Geofisika)",
                    }
                }
            },
        },
        429: {
            "description": "Rate limit exceeded",
            "model": ErrorResponse,
        },
        502: {
            "description": "BMKG API unavailable",
            "model": ErrorResponse,
        },
    },
)
@limiter.limit(settings.rate_limit_anonymous)
async def get_latest_earthquake(
    request: Request,
):
    """Get the latest earthquake from BMKG."""
    try:
        earthquake, from_cache, ttl = await earthquake_service.get_latest()
        
        response_data = {
            "data": serialize_earthquake(earthquake),
            "meta": {
                "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "cache_ttl": ttl,
            },
            "attribution": "BMKG (Badan Meteorologi, Klimatologi, dan Geofisika)",
        }
        
        # Add cache headers
        headers = {
            "X-Cache": "HIT" if from_cache else "MISS",
            "X-Cache-TTL": str(ttl),
        }
        
        return JSONResponse(content=response_data, headers=headers)
        
    except Exception as e:
        return JSONResponse(
            status_code=502,
            content={
                "error": "upstream_error",
                "message": f"Failed to fetch earthquake data: {str(e)}",
                "status": 502,
            },
        )


@router.get(
    "/recent",
    response_model=APIResponse[list[Earthquake]],
    summary="Get recent earthquakes (M 5.0+)",
    description="""
    Returns the last 15 earthquakes with magnitude 5.0 or higher.
    
    **Cache:** 5 minutes (300 seconds)  
    **Source:** https://data.bmkg.go.id/DataMKG/TEWS/gempaterkini.json
    
    ## Response
    
    Returns a list of earthquake objects sorted by time (newest first).
    Only includes significant earthquakes with M ≥ 5.0.
    
    ## Error Responses
    
    - `502`: BMKG API unavailable
    - `429`: Rate limit exceeded
    """,
    responses={
        200: {
            "description": "List of recent earthquakes",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "datetime": "2026-02-16T13:15:30+00:00",
                                "magnitude": 5.4,
                                "depth_km": 10.0,
                                "lat": -6.89,
                                "lon": 109.67,
                                "lat_text": "6.89 LS",
                                "lon_text": "109.67 BT",
                                "region": "18 km TimurLaut Pekalongan",
                                "tsunami_potential": "Tidak berpotensi tsunami",
                                "felt_report": None,
                                "shakemap_url": "https://data.bmkg.go.id/DataMKG/TEWS/20260216131530.mmi.jpg",
                            }
                        ],
                        "meta": {
                            "fetched_at": "2026-02-16T15:30:00+07:00",
                            "cache_ttl": 300,
                            "count": 15,
                        },
                        "attribution": "BMKG (Badan Meteorologi, Klimatologi, dan Geofisika)",
                    }
                }
            },
        },
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        502: {"description": "BMKG API unavailable", "model": ErrorResponse},
    },
)
@limiter.limit(settings.rate_limit_anonymous)
async def get_recent_earthquakes(
    request: Request,
):
    """Get recent earthquakes (M 5.0+)."""
    try:
        earthquakes, from_cache, ttl = await earthquake_service.get_recent()
        
        response_data = {
            "data": [serialize_earthquake(eq) for eq in earthquakes],
            "meta": {
                "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "cache_ttl": ttl,
                "count": len(earthquakes),
            },
            "attribution": "BMKG (Badan Meteorologi, Klimatologi, dan Geofisika)",
        }
        
        headers = {
            "X-Cache": "HIT" if from_cache else "MISS",
            "X-Cache-TTL": str(ttl),
        }
        
        return JSONResponse(content=response_data, headers=headers)
        
    except Exception as e:
        return JSONResponse(
            status_code=502,
            content={
                "error": "upstream_error",
                "message": f"Failed to fetch earthquake data: {str(e)}",
                "status": 502,
            },
        )


@router.get(
    "/felt",
    response_model=APIResponse[list[Earthquake]],
    summary="Get felt earthquakes",
    description="""
    Returns the last 15 earthquakes that were felt by people.
    
    **Cache:** 5 minutes (300 seconds)  
    **Source:** https://data.bmkg.go.id/DataMKG/TEWS/gempadirasakan.json
    
    ## Response
    
    Returns a list of earthquake objects sorted by time (newest first).
    These earthquakes include felt reports with intensity information.
    
    ## Error Responses
    
    - `502`: BMKG API unavailable
    - `429`: Rate limit exceeded
    """,
    responses={
        200: {
            "description": "List of felt earthquakes",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "datetime": "2026-02-16T13:15:30+00:00",
                                "magnitude": 4.2,
                                "depth_km": 5.0,
                                "lat": -6.89,
                                "lon": 109.67,
                                "lat_text": "6.89 LS",
                                "lon_text": "109.67 BT",
                                "region": "18 km TimurLaut Pekalongan",
                                "tsunami_potential": None,
                                "felt_report": "III Pekalongan",
                                "shakemap_url": None,
                            }
                        ],
                        "meta": {
                            "fetched_at": "2026-02-16T15:30:00+07:00",
                            "cache_ttl": 300,
                            "count": 15,
                        },
                        "attribution": "BMKG (Badan Meteorologi, Klimatologi, dan Geofisika)",
                    }
                }
            },
        },
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        502: {"description": "BMKG API unavailable", "model": ErrorResponse},
    },
)
@limiter.limit(settings.rate_limit_anonymous)
async def get_felt_earthquakes(
    request: Request,
):
    """Get felt earthquakes."""
    try:
        earthquakes, from_cache, ttl = await earthquake_service.get_felt()
        
        response_data = {
            "data": [serialize_earthquake(eq) for eq in earthquakes],
            "meta": {
                "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "cache_ttl": ttl,
                "count": len(earthquakes),
            },
            "attribution": "BMKG (Badan Meteorologi, Klimatologi, dan Geofisika)",
        }
        
        headers = {
            "X-Cache": "HIT" if from_cache else "MISS",
            "X-Cache-TTL": str(ttl),
        }
        
        return JSONResponse(content=response_data, headers=headers)
        
    except Exception as e:
        return JSONResponse(
            status_code=502,
            content={
                "error": "upstream_error",
                "message": f"Failed to fetch earthquake data: {str(e)}",
                "status": 502,
            },
        )


@router.get(
    "/nearby",
    response_model=APIResponse[list[EarthquakeWithDistance]],
    summary="Find earthquakes near a location",
    description="""
    Search for earthquakes within a radius from a given coordinate.
    
    Combines recent (M 5.0+) and felt earthquake data, calculates distance
    using the Haversine formula, and returns results sorted by distance.
    
    **Cache:** 5 minutes (300 seconds)  
    **Sources:** Recent + Felt earthquake endpoints
    
    ## Query Parameters
    
    - `lat`: Latitude (-90 to 90)
    - `lon`: Longitude (-180 to 180)
    - `radius_km`: Search radius in km (1 to 1000, default: 200)
    
    ## Response
    
    Returns earthquakes with an additional `distance_km` field showing
    distance from the query point.
    
    ## Error Responses
    
    - `400`: Invalid coordinates
    - `502`: BMKG API unavailable
    - `429`: Rate limit exceeded
    """,
    responses={
        200: {
            "description": "Earthquakes near the specified location",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
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
                                "distance_km": 45.2,
                            }
                        ],
                        "meta": {
                            "fetched_at": "2026-02-16T15:30:00+07:00",
                            "cache_ttl": 300,
                            "count": 3,
                            "center": {"lat": -6.89, "lon": 109.67},
                            "radius_km": 200.0,
                        },
                        "attribution": "BMKG (Badan Meteorologi, Klimatologi, dan Geofisika)",
                    }
                }
            },
        },
        400: {"description": "Invalid coordinates", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        502: {"description": "BMKG API unavailable", "model": ErrorResponse},
    },
)
@limiter.limit(settings.rate_limit_anonymous)
async def get_nearby_earthquakes(
    request: Request,
    lat: float = Query(
        ...,
        description="Latitude of the center point",
        ge=-90,
        le=90,
        examples=[-6.89],
    ),
    lon: float = Query(
        ...,
        description="Longitude of the center point",
        ge=-180,
        le=180,
        examples=[109.67],
    ),
    radius_km: float = Query(
        200,
        description="Search radius in kilometers (1-1000)",
        ge=1,
        le=1000,
        examples=[200],
    ),
):
    """Get earthquakes near a coordinate."""
    try:
        earthquakes, meta = await earthquake_service.get_nearby(lat, lon, radius_km)
        
        response_data = {
            "data": [serialize_earthquake(eq) for eq in earthquakes],
            "meta": meta,
            "attribution": "BMKG (Badan Meteorologi, Klimatologi, dan Geofisika)",
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        return JSONResponse(
            status_code=502,
            content={
                "error": "upstream_error",
                "message": f"Failed to fetch earthquake data: {str(e)}",
                "status": 502,
            },
        )

@router.post("/simulate")
@limiter.limit(settings.rate_limit_authenticated)
async def simulate_earthquake(
    request: Request,
    response: Response,
    payload: dict,
    # username: str = Depends(verify_admin) # Temporarily disabled
):
    """Simulate an earthquake (Try Mode)."""
    
    # Generate fake earthquake
    timestamp = int(datetime.now().timestamp())
    serialized_time = datetime.now(timezone.utc)
    
    magnitude = float(payload.get("magnitude", 6.5))
    
    earthquake = Earthquake(
        datetime=serialized_time,
        magnitude=magnitude,
        depth_km=10.0,
        lat=-6.20,
        lon=106.84,
        lat_text="6.20 LS",
        lon_text="106.84 BT",
        region="15 km BaratDaya JAKARTA",
        tsunami_potential="Berpotensi Tsunami" if magnitude >= 7.0 else "Tidak berpotensi tsunami",
        felt_report="IV-V Jakarta",
        shakemap_url="https://data.bmkg.go.id/DataMKG/TEWS/20240826101530.mmi.jpg"
    )
    
    await earthquake_service.inject_earthquake(earthquake)
    return {"status": "ok", "message": "Simulated earthquake injected", "data": serialize_earthquake(earthquake)}

@router.delete("/simulate")
@limiter.limit(settings.rate_limit_authenticated)
async def clear_simulations(
    request: Request,
    response: Response,
    # username: str = Depends(verify_admin)
):
    """Clear all simulated earthquakes."""
    await earthquake_service.clear_simulations()
    return {"status": "ok", "message": "All simulations cleared"}
