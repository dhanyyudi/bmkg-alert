"""Admin authentication routes."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings


router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
async def admin_login(body: LoginRequest):
    """Verify admin password and return access confirmation.

    The frontend stores the password and sends it as
    ``X-Admin-Token`` on subsequent requests.
    """
    if not secrets.compare_digest(body.password, settings.admin_password):
        raise HTTPException(status_code=401, detail="Invalid password")
    return {"authenticated": True, "demo_mode": settings.demo_mode}
