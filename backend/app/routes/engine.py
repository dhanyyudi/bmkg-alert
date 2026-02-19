"""Engine control routes — start, stop, check-now, status."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.dependencies import get_engine, require_write_allowed

router = APIRouter(prefix="/engine", tags=["engine"])


@router.post("/start", dependencies=[Depends(require_write_allowed)])
async def start_engine():
    """Start the alert polling engine."""
    engine = get_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    await engine.start()
    return {"status": "started", "engine": engine.get_status()}


@router.post("/stop", dependencies=[Depends(require_write_allowed)])
async def stop_engine():
    """Stop the alert polling engine."""
    engine = get_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    await engine.stop()
    return {"status": "stopped", "engine": engine.get_status()}


@router.post("/check-now", dependencies=[Depends(require_write_allowed)])
async def check_now():
    """Trigger a single poll cycle immediately."""
    engine = get_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    result = await engine.check_now()
    return {"status": "completed", "result": result, "engine": engine.get_status()}


@router.get("/status")
async def get_status():
    """Get the current engine status."""
    engine = get_engine()
    if engine is None:
        return {"running": False, "message": "Engine not initialized", "demo_mode": settings.demo_mode}
    return {**engine.get_status(), "demo_mode": settings.demo_mode}
