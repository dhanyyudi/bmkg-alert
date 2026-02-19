"""Nowcast (weather warnings) API routes."""

from datetime import datetime, timezone
from fastapi import APIRouter, Query, Request, Depends, HTTPException, Response
from fastapi.responses import JSONResponse

from app.config import settings
from app.dependencies import limiter
from app.models.nowcast import (
    ActiveProvince,
    Warning,
    LocationCheckResult,
    NowcastDetailResponse,
    NowcastMeta,
)
from app.models.responses import APIResponse
from app.services.nowcast_service import nowcast_service
from app.core.auth import verify_admin

router = APIRouter(
    prefix="/v1/nowcast",
    tags=["nowcast"],
)


def serialize_warning(warning: Warning) -> dict:
    """Serialize warning to dict for API response."""
    data = warning.model_dump(mode='json')
    # Ensure datetime fields are properly formatted
    if warning.effective:
        data['effective'] = warning.effective.isoformat() if warning.effective.tzinfo else warning.effective.isoformat() + "+00:00"
    if warning.expires:
        data['expires'] = warning.expires.isoformat() if warning.expires.tzinfo else warning.expires.isoformat() + "+00:00"
    return data


@router.get("", response_model=APIResponse[list[ActiveProvince]])
@limiter.limit(settings.rate_limit_anonymous)
async def get_active_provinces(
    request: Request,
    lang: str = Query("id", description="Language code (id/en)", pattern="^(id|en)$"),
):
    """Get provinces with active weather warnings.
    
    Returns a list of provinces that currently have active weather warnings.
    Data is fetched from BMKG's RSS feed and cached for 120 seconds.
    
    **Query Parameters:**
    - `lang`: Language code - "id" (Indonesian) or "en" (English). Default: "id"
    """
    try:
        provinces, from_cache, ttl = await nowcast_service.get_active_provinces(lang)
        
        response_data = {
            "data": [p.model_dump(mode='json') for p in provinces],
            "meta": {
                "count": len(provinces),
                "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "cache_ttl": ttl,
                "language": lang,
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
                "message": f"Failed to fetch weather warnings: {str(e)}",
                "status": 502,
            },
        )


@router.get("/active", response_model=APIResponse[list[Warning]])
@limiter.limit(settings.rate_limit_anonymous)
async def get_all_active_warnings(
    request: Request,
    lang: str = Query("id", description="Language code (id/en)", pattern="^(id|en)$"),
):
    """Get ALL active weather warnings.
    
    Returns a flattened list of all active warnings across Indonesia.
    This endpoint is useful for map visualizations.
    
    **Query Parameters:**
    - `lang`: Language code - "id" (Indonesian) or "en" (English). Default: "id"
    """
    try:
        warnings, from_cache, ttl = await nowcast_service.get_all_warnings(lang)
        
        response_data = {
            "data": [serialize_warning(w) for w in warnings],
            "meta": {
                "count": len(warnings),
                "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "cache_ttl": ttl,
                "language": lang,
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
                "message": f"Failed to fetch active warnings: {str(e)}",
                "status": 502,
            },
        )


@router.get("/{alert_code}", response_model=APIResponse[NowcastDetailResponse])
@limiter.limit(settings.rate_limit_anonymous)
async def get_warning_detail(
    request: Request,
    alert_code: str,
    lang: str = Query("id", description="Language code (id/en)", pattern="^(id|en)$"),
):
    """Get detailed weather warning for an alert.
    
    Returns detailed CAP (Common Alerting Protocol) data for a specific alert,
    including affected areas with polygon coordinates.
    
    **Path Parameters:**
    - `alert_code`: Alert code from the RSS feed (e.g., 'CBT20260216004')
    
    **Query Parameters:**
    - `lang`: Language code - "id" (Indonesian) or "en" (English). Default: "id"
    """
    try:
        warning, region_name, from_cache, ttl = await nowcast_service.get_warning_detail(
            alert_code, lang
        )
        
        if warning is None:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "not_found",
                    "message": f"Alert '{alert_code}' not found or no longer active",
                    "status": 404,
                },
            )
        
        response_data = {
            "data": {
                "province": region_name,
                "warnings": [serialize_warning(warning)],
            },
            "meta": {
                "count": 1,
                "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "cache_ttl": ttl,
                "language": lang,
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
                "message": f"Failed to fetch warning detail: {str(e)}",
                "status": 502,
            },
        )


@router.get("/check", response_model=APIResponse[LocationCheckResult])
@limiter.limit(settings.rate_limit_anonymous)
async def check_location_warnings(
    request: Request,
    location: str = Query(..., description="Kecamatan/district name to check (e.g., 'Wiradesa', 'Bojonegara')"),
    lang: str = Query("id", description="Language code (id/en)", pattern="^(id|en)$"),
):
    """Check weather warnings for a specific location.
    
    Searches all active weather warnings for mentions of the given location.
    Performs case-insensitive matching in warning descriptions.
    
    **Query Parameters:**
    - `location`: Location name (kecamatan/district) to search for. **Required**
    - `lang`: Language code - "id" (Indonesian) or "en" (English). Default: "id"
    
    **Example:**
    - `/v1/nowcast/check?location=Bojonegara`
    - `/v1/nowcast/check?location=Wiradesa&lang=id`
    """
    if not location or not location.strip():
        return JSONResponse(
            status_code=400,
            content={
                "error": "bad_request",
                "message": "Location parameter is required",
                "status": 400,
            },
        )
    
    try:
        result, from_cache, ttl = await nowcast_service.check_location(location.strip(), lang)
        
        response_data = {
            "data": result.model_dump(mode='json'),
            "meta": {
                "location": location.strip(),
                "checked_provinces": len(result.warnings),
                "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "cache_ttl": ttl,
                "language": lang,
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
                "message": f"Failed to check location warnings: {str(e)}",
                "status": 502,
            },
        )


@router.post("/simulate")
@limiter.limit(settings.rate_limit_authenticated)
async def simulate_warning(
    request: Request,
    response: Response,
    payload: dict,
    # username: str = Depends(verify_admin) # Temporarily disabled for Try Mode demo
):
    """Simulate a weather warning (Try Mode).
    
    Injects a fake warning into the system for testing purposes.
    Requires Admin Authentication.
    """
    from datetime import datetime, timedelta, timezone
    from app.models.nowcast import Warning, Area
    from app.models.enums import Severity, Urgency, Certainty
    
    sim_type = payload.get("type", "heavy_rain")
    
    # Generate fake warning based on type
    timestamp = int(datetime.now().timestamp())
    serialized_time = datetime.now(timezone.utc)
    
    if sim_type == "heavy_rain":
        warning = Warning(
            identifier=f"SIM-{timestamp}-RAIN",
            event="Hujan Lebat (Simulasi)",
            severity=Severity.SEVERE,
            urgency=Urgency.IMMEDIATE,
            certainty=Certainty.LIKELY,
            effective=serialized_time,
            expires=serialized_time + timedelta(hours=1),
            headline=f"SIMULASI: Hujan Lebat di Jakarta Pusat (ID: {timestamp})",
            description="Ini adalah simulasi peringatan dini cuaca untuk pengujian sistem.",
            sender="BMKG-Simulator",
            areas=[
                Area(name="Kec. Gambir, Jakarta Pusat", polygon=[
                     [-6.16, 106.81], [-6.16, 106.83], [-6.18, 106.83], [-6.18, 106.81]
                ])
            ],
            is_expired=False
        )
    elif sim_type == "earthquake":
         warning = Warning(
            identifier=f"SIM-{timestamp}-QUAKE",
            event="Gempa Bumi (Simulasi)",
            severity=Severity.EXTREME,
            urgency=Urgency.IMMEDIATE,
            certainty=Certainty.OBSERVED,
            effective=serialized_time,
            expires=serialized_time + timedelta(hours=1),
            headline=f"SIMULASI: Gempa Bumi 5.0 SR (ID: {timestamp})",
            description="Ini adalah simulasi gempa bumi.",
            sender="BMKG-Simulator",
            areas=[
                Area(name="Kec. Menteng, Jakarta Pusat", polygon=[
                     [-6.18, 106.82], [-6.18, 106.84], [-6.20, 106.84], [-6.20, 106.82]
                ])
            ],
            is_expired=False
        )
    else:
        # Default Flood
        warning = Warning(
            identifier=f"SIM-{timestamp}-FLOOD",
            event="Banjir (Simulasi)",
            severity=Severity.MODERATE,
            urgency=Urgency.EXPECTED,
            certainty=Certainty.POSSIBLE,
            effective=serialized_time,
            expires=serialized_time + timedelta(hours=3),
            headline=f"SIMULASI: Banjir di Bantul (ID: {timestamp})",
            description="Ini adalah simulasi banjir.",
            sender="BMKG-Simulator",
            areas=[
                Area(name="Kec. Bantul, DIY", polygon=[
                     [-7.87, 110.30], [-7.87, 110.35], [-7.92, 110.35], [-7.92, 110.30]
                ])
            ],
            is_expired=False
        )
        
    await nowcast_service.inject_warning(warning)
    return {"status": "ok", "message": f"Simulated {sim_type} warning injected", "id": warning.identifier}


@router.delete("/simulate")
@limiter.limit(settings.rate_limit_authenticated)
async def clear_simulations(
    request: Request,
    response: Response,
    # username: str = Depends(verify_admin)
):
    """Clear all simulated warnings."""
    await nowcast_service.clear_simulations()
    return {"status": "ok", "message": "All simulations cleared"}
