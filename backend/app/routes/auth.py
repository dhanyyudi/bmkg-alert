"""Admin authentication routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.config import settings
from app.dependencies import limiter, password_matches

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
@limiter.limit("10/minute")
async def admin_login(request: Request, body: LoginRequest):
    """Verify admin password and return access confirmation.

    The frontend stores the password and sends it as
    ``X-Admin-Token`` on subsequent requests.
    """
    if not settings.admin_password_set:
        raise HTTPException(
            status_code=403,
            detail="Login admin dimatikan sampai ADMIN_PASSWORD diganti dari nilai bawaannya.",
        )
    if not password_matches(body.password):
        raise HTTPException(status_code=401, detail="Kata sandi salah")
    return {"authenticated": True, "demo_mode": settings.demo_mode}
