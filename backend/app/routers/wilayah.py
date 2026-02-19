"""Wilayah (region) API routes."""

from datetime import datetime, timezone
from fastapi import APIRouter, Query, Request, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.config import settings
from app.dependencies import limiter
from app.models.wilayah import Wilayah, WilayahSearchResult
from app.services.wilayah_service import wilayah_service

router = APIRouter(
    prefix="/v1/wilayah",
    tags=["wilayah"],
)


def _serialize_wilayah(w: Wilayah) -> dict:
    """Serialize wilayah to dict."""
    return {
        "code": w.code,
        "name": w.name,
    }


def _serialize_search_result(w: WilayahSearchResult) -> dict:
    """Serialize search result to dict."""
    return {
        "code": w.code,
        "name": w.name,
        "level": w.level.value,
        "full_path": w.full_path,
        "parent_code": w.parent_code,
    }


@router.get("/provinces")
@limiter.limit(settings.rate_limit_anonymous)
async def get_provinces(
    request: Request,
):
    """Get all 34 provinces in Indonesia.
    
    Returns a list of all Indonesian provinces based on Permendagri 72/2019.
    """
    try:
        provinces = wilayah_service.get_provinces()
        
        response_data = {
            "data": [_serialize_wilayah(p) for p in provinces],
            "meta": {
                "fetched_at": datetime.now(timezone.utc).isoformat() + "Z",
                "count": len(provinces),
            },
            "attribution": "Permendagri 72/2019",
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": f"Failed to load wilayah data: {str(e)}",
                "status": 500,
            },
        )


@router.get("/districts")
@limiter.limit(settings.rate_limit_anonymous)
async def get_districts(
    request: Request,
    province: str = Query(..., description="Province code (2 digits, e.g., '33')", min_length=2, max_length=2),
):
    """Get districts (kabupaten/kota) for a province.
    
    Returns all districts (kabupaten and kota) within the specified province.
    """
    try:
        # Validate province exists
        province_wilayah = wilayah_service.get_by_code(province)
        if not province_wilayah:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "not_found",
                    "message": f"Province with code '{province}' not found",
                    "status": 404,
                },
            )
        
        districts = wilayah_service.get_districts(province)
        
        response_data = {
            "data": [_serialize_wilayah(d) for d in districts],
            "meta": {
                "fetched_at": datetime.now(timezone.utc).isoformat() + "Z",
                "count": len(districts),
                "province_code": province,
                "province_name": province_wilayah.name,
            },
            "attribution": "Permendagri 72/2019",
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": f"Failed to load wilayah data: {str(e)}",
                "status": 500,
            },
        )


@router.get("/subdistricts")
@limiter.limit(settings.rate_limit_anonymous)
async def get_subdistricts(
    request: Request,
    district: str = Query(..., description="District code (e.g., '33.26')"),
):
    """Get subdistricts (kecamatan) for a district.
    
    Returns all subdistricts (kecamatan) within the specified district.
    """
    try:
        # Validate district exists
        district_wilayah = wilayah_service.get_by_code(district)
        if not district_wilayah:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "not_found",
                    "message": f"District with code '{district}' not found",
                    "status": 404,
                },
            )
        
        subdistricts = wilayah_service.get_subdistricts(district)
        
        response_data = {
            "data": [_serialize_wilayah(s) for s in subdistricts],
            "meta": {
                "fetched_at": datetime.now(timezone.utc).isoformat() + "Z",
                "count": len(subdistricts),
                "district_code": district,
                "district_name": district_wilayah.name,
            },
            "attribution": "Permendagri 72/2019",
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": f"Failed to load wilayah data: {str(e)}",
                "status": 500,
            },
        )


@router.get("/villages")
@limiter.limit(settings.rate_limit_anonymous)
async def get_villages(
    request: Request,
    subdistrict: str = Query(..., description="Subdistrict code (e.g., '33.26.16')"),
):
    """Get villages (kelurahan/desa) for a subdistrict.
    
    Returns all villages (kelurahan and desa) within the specified subdistrict.
    """
    try:
        # Validate subdistrict exists
        subdistrict_wilayah = wilayah_service.get_by_code(subdistrict)
        if not subdistrict_wilayah:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "not_found",
                    "message": f"Subdistrict with code '{subdistrict}' not found",
                    "status": 404,
                },
            )
        
        villages = wilayah_service.get_villages(subdistrict)
        
        response_data = {
            "data": [_serialize_wilayah(v) for v in villages],
            "meta": {
                "fetched_at": datetime.now(timezone.utc).isoformat() + "Z",
                "count": len(villages),
                "subdistrict_code": subdistrict,
                "subdistrict_name": subdistrict_wilayah.name,
            },
            "attribution": "Permendagri 72/2019",
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": f"Failed to load wilayah data: {str(e)}",
                "status": 500,
            },
        )


@router.get("/search")
@limiter.limit(settings.rate_limit_anonymous)
async def search_wilayah(
    request: Request,
    q: str = Query(..., description="Search query (min 2 characters)", min_length=2),
    limit: int = Query(50, description="Maximum results to return", ge=1, le=100),
):
    """Search wilayah by name.
    
    Case-insensitive search across all administrative levels.
    Returns results with full hierarchical paths.
    """
    try:
        results = wilayah_service.search(q, limit=limit)
        
        response_data = {
            "data": [_serialize_search_result(r) for r in results],
            "meta": {
                "fetched_at": datetime.now(timezone.utc).isoformat() + "Z",
                "count": len(results),
                "query": q,
                "limit": limit,
            },
            "attribution": "Permendagri 72/2019",
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": f"Failed to search wilayah data: {str(e)}",
                "status": 500,
            },
        )
