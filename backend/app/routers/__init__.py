"""API routers for the BMKG API."""

from app.routers.earthquake import router as earthquake_router
from app.routers.health import router as health_router

__all__ = ["earthquake_router", "health_router"]
