"""Weather forecast API routes."""

from datetime import datetime, timezone
from fastapi import APIRouter, Path, Request, Depends
from fastapi.responses import JSONResponse

from app.config import settings
from app.dependencies import limiter
from app.models.weather import WeatherForecast, CurrentWeather, WeatherForecastMeta
from app.models.responses import APIResponse
from app.services.weather_service import weather_service
from app.services.wilayah_service import wilayah_service

router = APIRouter(
    prefix="/v1/weather",
    tags=["weather"],
)


def serialize_forecast(forecast: WeatherForecast) -> dict:
    """Serialize forecast to dict for API response."""
    data = forecast.model_dump(by_alias=True, mode='json')
    return data


def serialize_current(current: CurrentWeather) -> dict:
    """Serialize current weather to dict for API response."""
    data = current.model_dump(by_alias=True, mode='json')
    return data


def _validate_adm4_province(adm4_code: str) -> JSONResponse | None:
    """Validate that the province part of an ADM4 code exists.

    Returns a JSONResponse with 404 if province is invalid, None if valid.
    """
    parts = adm4_code.split(".")
    if len(parts) >= 1:
        province_code = parts[0]
        province = wilayah_service.get_by_code(province_code)
        if province is None:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "not_found",
                    "message": f"Province code '{province_code}' not found. ADM4 code '{adm4_code}' does not match any known province.",
                    "status": 404,
                    "hint": "Use /v1/wilayah/provinces to see valid province codes, or /v1/wilayah/search to find locations by name",
                },
            )
    return None


@router.get("/{adm4_code}", response_model=APIResponse[WeatherForecast])
@limiter.limit(settings.rate_limit_anonymous)
async def get_weather_forecast(
    request: Request,
    adm4_code: str = Path(..., description="ADM4 area code (e.g., '33.26.16.1001')"),
):
    """Get 3-day weather forecast for a location.

    Returns weather forecast for the specified kelurahan/desa.
    The ADM4 code can be obtained from the Wilayah endpoints.
    Data is cached for 15 minutes.

    Example: `33.26.16.1001` for Kadipaten, Wiradesa, Pekalongan
    """
    try:
        forecast, from_cache, ttl = await weather_service.get_forecast(adm4_code)

        # Calculate metadata
        forecast_days = len(forecast.forecast)
        entries_per_day = len(forecast.forecast[0].entries) if forecast.forecast else 0

        response_data = {
            "data": serialize_forecast(forecast),
            "meta": {
                "forecast_days": forecast_days,
                "entries_per_day": entries_per_day,
                "fetched_at": datetime.now(timezone.utc).isoformat() + "Z",
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

    except ValueError as e:
        # Format validation failed — check province before returning 400
        province_error = _validate_adm4_province(adm4_code)
        if province_error:
            return province_error
        return JSONResponse(
            status_code=400,
            content={
                "error": "bad_request",
                "message": str(e),
                "status": 400,
            },
        )
    except Exception as e:
        error_msg = str(e).lower()
        if "not found" in error_msg or "tidak ditemukan" in error_msg or "404" in error_msg:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "not_found",
                    "message": f"Weather data not available for ADM4 code '{adm4_code}'. BMKG may not provide forecast for this location. Try a nearby kelurahan/desa.",
                    "status": 404,
                    "hint": "Use /v1/wilayah/search to find valid locations with weather data",
                },
            )
        return JSONResponse(
            status_code=502,
            content={
                "error": "upstream_error",
                "message": f"Failed to fetch weather data: {str(e)}",
                "status": 502,
            },
        )


@router.get("/{adm4_code}/current", response_model=APIResponse[CurrentWeather])
@limiter.limit(settings.rate_limit_anonymous)
async def get_current_weather(
    request: Request,
    adm4_code: str = Path(..., description="ADM4 area code (e.g., '33.26.16.1001')"),
):
    """Get current weather for a location.

    Returns the nearest forecast entry to current time.
    The ADM4 code can be obtained from the Wilayah endpoints.
    Data is cached for 15 minutes.

    Example: `33.26.16.1001` for Kadipaten, Wiradesa, Pekalongan
    """
    try:
        current, from_cache, ttl = await weather_service.get_current(adm4_code)

        response_data = {
            "data": serialize_current(current),
            "meta": {
                "fetched_at": datetime.now(timezone.utc).isoformat() + "Z",
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

    except ValueError as e:
        error_msg = str(e).lower()
        if "no current forecast" in error_msg:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "not_found",
                    "message": "No current forecast entry found",
                    "status": 404,
                },
            )
        # Format validation failed — check province before returning 400
        province_error = _validate_adm4_province(adm4_code)
        if province_error:
            return province_error
        return JSONResponse(
            status_code=400,
            content={
                "error": "bad_request",
                "message": str(e),
                "status": 400,
            },
        )
    except Exception as e:
        error_msg = str(e).lower()
        if "not found" in error_msg or "tidak ditemukan" in error_msg or "404" in error_msg:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "not_found",
                    "message": f"Weather data not available for ADM4 code '{adm4_code}'. BMKG may not provide forecast for this location. Try a nearby kelurahan/desa.",
                    "status": 404,
                    "hint": "Use /v1/wilayah/search to find valid locations with weather data",
                },
            )
        return JSONResponse(
            status_code=502,
            content={
                "error": "upstream_error",
                "message": f"Failed to fetch weather data: {str(e)}",
                "status": 502,
            },
        )

