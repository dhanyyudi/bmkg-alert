"""Main FastAPI application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.cache import cache
from app.dependencies import limiter, set_engine, set_bmkg_client
from app.http_client import close_http_client
from app.routers import earthquake, health, nowcast, weather, wilayah

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # --- Startup ---
    logger.info("Starting up BMKG Alert API...")

    # 1. Connect cache (Redis with in-memory fallback)
    await cache.connect()
    if cache.is_using_fallback():
        logger.info("Using in-memory cache (Redis unavailable)")
    else:
        logger.info("Connected to Redis")

    # 2. Initialize SQLite database for alert management
    from app.database import init_database
    db = init_database(settings.db_path)
    await db.connect()
    await db.init_schema()
    logger.info("Database initialized: %s", settings.db_path)

    # 3. Create BMKG API client and store as singleton
    from app.engine.bmkg_client import HttpBMKGClient
    bmkg_client = HttpBMKGClient(base_url=settings.bmkg_api_url)
    set_bmkg_client(bmkg_client)
    logger.info("BMKG client configured: %s", settings.bmkg_api_url)

    # 4. Create and start AlertEngine
    from app.engine.state import StateManager
    from app.engine.worker import AlertEngine
    from app.notifications.dispatcher import NotificationDispatcher
    state = StateManager(db)
    dispatcher = NotificationDispatcher(state)
    engine = AlertEngine(
        bmkg_client=bmkg_client,
        state=state,
        notification_dispatcher=dispatcher,
    )
    set_engine(engine)
    await engine.start()
    logger.info("Alert engine started")

    # 5. Start earthquake/weather scheduler (BMKG API poller)
    from app.services.scheduler import scheduler
    await scheduler.start()

    yield

    # --- Shutdown ---
    logger.info("Shutting down BMKG Alert API...")
    await engine.stop()
    await scheduler.stop()
    await db.close()
    await cache.disconnect()
    await bmkg_client.close()
    await close_http_client()
    logger.info("Cleanup complete")


# OpenAPI tags metadata
TAGS_METADATA = [
    {"name": "earthquake", "description": "Earthquake data from BMKG seismic network"},
    {"name": "weather", "description": "Weather forecasts for Indonesian regions"},
    {"name": "nowcast", "description": "Weather warnings and early alerts (Peringatan Dini)"},
    {"name": "wilayah", "description": "Region lookup for Indonesian administrative areas"},
    {"name": "alerts", "description": "Matched alert history and stats"},
    {"name": "locations", "description": "Monitored locations management"},
    {"name": "channels", "description": "Notification channels management"},
    {"name": "config", "description": "Application configuration"},
    {"name": "activity", "description": "Activity log"},
    {"name": "engine", "description": "Alert engine control (start/stop/check-now/status)"},
    {"name": "health", "description": "Health and readiness checks"},
]

DESCRIPTION = """
REST API for Indonesian Weather Alerts & BMKG Data.

**Features:**
- Earthquake Data: Latest, recent (M 5.0+), felt earthquakes
- Weather Forecasts: 3-day forecasts for any kelurahan/desa in Indonesia
- Weather Warnings: Real-time severe weather alerts (Nowcast)
- Alert Management: Monitored locations, notification channels, alert history
- Alert Engine: Background polling and notification dispatch

**Attribution:** All BMKG data belongs to BMKG (Badan Meteorologi, Klimatologi, dan Geofisika).
"""

app = FastAPI(
    title="BMKG Alert API",
    description=DESCRIPTION,
    version="1.0.0",
    docs_url=None,
    redoc_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    openapi_tags=TAGS_METADATA,
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── BMKG API routes (routers/) ────────────────────────────────────────────────
app.include_router(health.router, prefix="/api")
app.include_router(nowcast.router, prefix="/api")
app.include_router(earthquake.router, prefix="/api")
app.include_router(weather.router, prefix="/api")
app.include_router(wilayah.router, prefix="/api")

# ── Alert management routes (routes/) ────────────────────────────────────────
from app.routes import (
    alerts as alerts_router,
    auth as auth_router,
    locations as locations_router,
    channels as channels_router,
    config as config_router,
    activity as activity_router,
    engine as engine_router,
    trial as trial_router,
)

app.include_router(auth_router.router, prefix="/api/v1")
app.include_router(alerts_router.router, prefix="/api/v1")
app.include_router(locations_router.router, prefix="/api/v1")
app.include_router(channels_router.router, prefix="/api/v1")
app.include_router(config_router.router, prefix="/api/v1")
app.include_router(activity_router.router, prefix="/api/v1")
app.include_router(engine_router.router, prefix="/api/v1")
app.include_router(trial_router.router, prefix="/api/v1")

# ── Admin endpoint ────────────────────────────────────────────────────────────
from fastapi import Depends
from app.core.auth import verify_admin


@app.get("/admin/status", dependencies=[Depends(verify_admin)], tags=["admin"])
async def admin_status():
    """Protected admin status endpoint."""
    return {"status": "ok", "message": "You are authenticated as admin"}


# Static landing page: only mount if the directory exists (not available in Docker).
import os
if os.path.isdir("landing"):
    app.mount("/static", StaticFiles(directory="landing"), name="static")
    app.mount("/", StaticFiles(directory="landing", html=True), name="landing")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "An unexpected error occurred",
            "status": 500,
        },
    )
