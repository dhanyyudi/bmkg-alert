"""Main FastAPI application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app import APP_VERSION
from app.cache import cache
from app.config import settings
from app.dependencies import limiter, set_bmkg_client, set_engine
from app.routes import (
    activity as activity_router,
    alerts as alerts_router,
    auth as auth_router,
    bmkg as bmkg_router,
    channels as channels_router,
    config as config_router,
    engine as engine_router,
    health as health_router,
    locations as locations_router,
    trial as trial_router,
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
# httpx logs every request URL at INFO, and Telegram URLs embed the bot token.
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # --- Startup ---
    logger.info("Starting up BMKG Alert API...")

    if settings.demo_mode and not settings.admin_password_set:
        logger.warning("DEMO_MODE is on with the default ADMIN_PASSWORD: admin login stays disabled until it is changed")
    elif not settings.write_locked:
        logger.warning("ADMIN_PASSWORD is the default: anyone who can reach this instance can change its settings")

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
    # The client reads BMKG_API_URL from the environment; mirror it into the
    # config table so the Settings page never shows a stale URL.
    for key, value in (("bmkg_api_url", settings.bmkg_api_url), ("app_version", APP_VERSION)):
        await db.execute(
            """
            INSERT INTO config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            (key, value),
        )

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

    # 5. Start the earthquake announcer
    from app.services.scheduler import scheduler
    await scheduler.start(bmkg_client)

    yield

    # --- Shutdown ---
    logger.info("Shutting down BMKG Alert API...")
    await engine.stop()
    await scheduler.stop()
    await db.close()
    await cache.disconnect()
    await bmkg_client.close()
    logger.info("Cleanup complete")


# OpenAPI tags metadata
TAGS_METADATA = [
    {"name": "bmkg", "description": "BMKG warnings, earthquakes, forecasts and regions, served from BMKG_API_URL"},
    {"name": "alerts", "description": "Matched alert history and stats"},
    {"name": "locations", "description": "Monitored locations management"},
    {"name": "channels", "description": "Notification channels management"},
    {"name": "config", "description": "Application configuration"},
    {"name": "activity", "description": "Activity log"},
    {"name": "engine", "description": "Alert engine control (start/stop/check-now/status)"},
    {"name": "trial", "description": "24-hour Telegram trial for demo visitors"},
    {"name": "health", "description": "Health check"},
]

DESCRIPTION = """
API of BMKG Alert: monitored locations, notification channels, matched alerts
and the alert engine. BMKG data comes from the BMKG REST API configured as
`BMKG_API_URL`.

**Attribution:** All BMKG data belongs to BMKG (Badan Meteorologi, Klimatologi, dan Geofisika).
"""

app = FastAPI(
    title="BMKG Alert API",
    description=DESCRIPTION,
    version=APP_VERSION,
    docs_url=None,
    redoc_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    openapi_tags=TAGS_METADATA,
)

# Rate limiter (only routes that declare a limit are limited)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# The bundled frontend calls the API on its own origin, so cross-origin access
# is off unless CORS_ORIGINS lists who may call it.
if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

for route_module in (
    health_router,
    bmkg_router,
    auth_router,
    alerts_router,
    locations_router,
    channels_router,
    config_router,
    activity_router,
    engine_router,
    trial_router,
):
    app.include_router(route_module.router, prefix="/api/v1")


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
