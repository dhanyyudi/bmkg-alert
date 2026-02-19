"""Dependencies for FastAPI routes.

This module provides rate limiting and singleton accessors for the
AlertEngine and HttpBMKGClient instances initialized in the app lifespan.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from slowapi import Limiter
from slowapi.util import get_remote_address

from fastapi import HTTPException, Request

from app.config import settings

if TYPE_CHECKING:
    from app.engine.worker import AlertEngine
    from app.engine.bmkg_client import HttpBMKGClient


# Initialize rate limiter with IP-based keying
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.rate_limit_anonymous],
    headers_enabled=True,
)

# Singleton holders — populated during app lifespan startup
_engine_instance: "AlertEngine | None" = None
_bmkg_client_instance: "HttpBMKGClient | None" = None


def set_engine(engine: "AlertEngine") -> None:
    """Store the global AlertEngine instance (called at startup)."""
    global _engine_instance
    _engine_instance = engine


def get_engine() -> "AlertEngine | None":
    """Return the global AlertEngine instance."""
    return _engine_instance


def set_bmkg_client(client: "HttpBMKGClient") -> None:
    """Store the global HttpBMKGClient instance (called at startup)."""
    global _bmkg_client_instance
    _bmkg_client_instance = client


def get_bmkg_client() -> "HttpBMKGClient | None":
    """Return the global HttpBMKGClient instance."""
    return _bmkg_client_instance


def _is_admin(request: Request) -> bool:
    """Check if the request carries valid admin credentials.

    Supports two schemes:
    - ``Authorization: Bearer <ADMIN_PASSWORD>``
    - ``X-Admin-Token: <ADMIN_PASSWORD>``
    """
    admin_pw = settings.admin_password
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer ") and auth[7:] == admin_pw:
        return True
    token = request.headers.get("x-admin-token", "")
    if token and token == admin_pw:
        return True
    return False


def require_write_allowed(request: Request) -> None:
    """Block write operations when demo_mode is enabled.

    Admins bypass the check by sending valid credentials.
    Use as a FastAPI dependency on any mutating endpoint.
    """
    if not settings.demo_mode:
        return
    if _is_admin(request):
        return
    raise HTTPException(
        status_code=403,
        detail="This action is disabled in demo mode. Deploy your own instance to configure.",
    )
