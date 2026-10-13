"""Dependencies for FastAPI routes.

Rate limiting, access checks, and singleton accessors for the AlertEngine
and HttpBMKGClient instances initialized in the app lifespan.
"""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request
from slowapi import Limiter

from app.config import settings

if TYPE_CHECKING:
    from app.engine.bmkg_client import HttpBMKGClient
    from app.engine.worker import AlertEngine


def client_ip(request: Request) -> str:
    """Address of the visitor, for rate limits.

    A forwarding header is only believed when CLIENT_IP_HEADER names it:
    without a proxy in front, any header is whatever the client chose to send.
    """
    if settings.client_ip_header:
        value = request.headers.get(settings.client_ip_header, "")
        # X-Forwarded-For style lists: the proxy appends, so the last entry is the one it saw
        candidate = value.split(",")[-1].strip()
        if candidate:
            return candidate
    return request.client.host if request.client else "unknown"


# No default limits: only the routes that need one declare it
limiter = Limiter(key_func=client_ip, headers_enabled=False)

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


def password_matches(candidate: str) -> bool:
    """Constant-time check against the admin password; the default password never matches."""
    if not settings.admin_password_set:
        return False
    return secrets.compare_digest(candidate.encode("utf-8"), settings.admin_password.encode("utf-8"))


def _is_admin(request: Request) -> bool:
    """Check if the request carries valid admin credentials.

    Supports two schemes:
    - ``Authorization: Bearer <ADMIN_PASSWORD>``
    - ``X-Admin-Token: <ADMIN_PASSWORD>``
    """
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer ") and password_matches(auth[7:]):
        return True
    token = request.headers.get("x-admin-token", "")
    return bool(token) and password_matches(token)


def can_view_private(request: Request) -> bool:
    """Whether the caller may see personal identifiers (chat IDs, email addresses)."""
    return not settings.write_locked or _is_admin(request)


def require_write_allowed(request: Request) -> None:
    """Block write operations on a locked instance unless the caller is the admin.

    Use as a FastAPI dependency on any mutating endpoint.
    """
    if not settings.write_locked or _is_admin(request):
        return
    if settings.demo_mode:
        detail = "Aksi ini dimatikan di mode demo. Pasang instance sendiri untuk mengubah pengaturan."
    else:
        detail = "Masuk sebagai admin untuk mengubah pengaturan."
    raise HTTPException(status_code=403, detail=detail)
