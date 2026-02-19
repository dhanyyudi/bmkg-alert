"""Engine API routes."""

from fastapi import APIRouter, Request
from datetime import datetime, timezone
from app.services.scheduler import scheduler
from app.core.auth import verify_admin
from app.config import settings
from app.dependencies import limiter

router = APIRouter(
    prefix="/v1/engine",
    tags=["engine"],
)

@router.get("/status")
# @limiter.limit(settings.rate_limit_anonymous)
async def get_engine_status():
    """Get engine (scheduler) status."""
    return {
        "engine": "running" if scheduler.running else "stopped",
        "last_poll": datetime.now(timezone.utc).isoformat(),
        "last_poll_result": f"{len(scheduler.jobs)} active jobs",
        "jobs": [f"task-{i}" for i, _ in enumerate(scheduler.jobs)]
    }

@router.post("/start")
# @limiter.limit(settings.rate_limit_authenticated)
async def start_engine():
    """Start the engine."""
    if not scheduler.running:
        await scheduler.start()
    return {"status": "started"}

@router.post("/stop")
# @limiter.limit(settings.rate_limit_authenticated)
async def stop_engine():
    """Stop the engine."""
    if scheduler.running:
        await scheduler.stop()
    return {"status": "stopped"}
