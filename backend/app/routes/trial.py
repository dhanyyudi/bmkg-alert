"""Trial subscription routes — 24h Telegram trial for demo visitors."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

import structlog

from app.config import settings
from app.database import get_database
from app.notifications.telegram import TelegramSender

logger = structlog.get_logger()

router = APIRouter(prefix="/trial", tags=["trial"])

TRIAL_DURATION_HOURS = 24
MAX_REGISTRATIONS_PER_IP = 5


# ── Models ────────────────────────────────────────────────────────────────────

class TrialRegister(BaseModel):
    chat_id: str
    location_code: str
    location_name: str
    district_name: str = ""
    province_name: str = ""
    severity_min: str = "all"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _send_trial_message(chat_id: str, text: str) -> bool:
    """Send a Telegram message using the system bot token."""
    bot_token = settings.telegram_bot_token
    if not bot_token:
        logger.warn("trial_telegram_no_bot_token")
        return False
    sender = TelegramSender()
    return await sender.send_raw(bot_token=bot_token, chat_id=chat_id, message=text)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register")
async def register_trial(body: TrialRegister, request: Request):
    """Register a 24-hour Telegram trial subscription."""
    db = get_database()

    if not body.chat_id.strip():
        raise HTTPException(status_code=400, detail="Chat ID tidak boleh kosong")

    if not body.location_code.strip():
        raise HTTPException(status_code=400, detail="Kode lokasi tidak boleh kosong")

    # Check for existing active trial for this chat_id
    existing = await db.fetch_one(
        """
        SELECT id FROM trial_subscriptions
        WHERE telegram_chat_id = ? AND expires_at > CURRENT_TIMESTAMP
        """,
        (body.chat_id,),
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Anda sudah memiliki trial aktif. Tunggu hingga berakhir atau hentikan terlebih dahulu.",
        )

    # Rate limit: max registrations per IP in the last hour
    ip = _client_ip(request)
    ip_count = await db.fetch_one(
        """
        SELECT COUNT(*) as cnt FROM trial_subscriptions
        WHERE ip_address = ? AND registered_at > datetime('now', '-1 hour')
        """,
        (ip,),
    )
    if ip_count and ip_count["cnt"] >= MAX_REGISTRATIONS_PER_IP:
        raise HTTPException(
            status_code=429,
            detail="Terlalu banyak registrasi dari IP ini. Coba lagi nanti.",
        )

    # Insert trial
    expires_at = datetime.now(timezone.utc) + timedelta(hours=TRIAL_DURATION_HOURS)
    expires_str = expires_at.strftime("%Y-%m-%d %H:%M:%S")

    cursor = await db.execute(
        """
        INSERT INTO trial_subscriptions
            (telegram_chat_id, subdistrict_code, subdistrict_name, district_name, province_name,
             severity_threshold, expires_at, ip_address)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            body.chat_id,
            body.location_code,
            body.location_name,
            body.district_name,
            body.province_name,
            body.severity_min,
            expires_str,
            ip,
        ),
    )
    trial_id = cursor.lastrowid

    # Send confirmation via Telegram
    location_label = body.location_name
    if body.district_name:
        location_label += f", {body.district_name}"

    confirm_msg = (
        "<b>Trial BMKG Alert Aktif!</b>\n\n"
        f"Lokasi: {location_label}\n"
        f"Severity: {body.severity_min}\n"
        f"Berlaku: {TRIAL_DURATION_HOURS} jam\n\n"
        "Anda akan menerima notifikasi peringatan cuaca BMKG "
        "untuk lokasi ini selama masa trial.\n\n"
        "<i>BMKG Alert System</i>"
    )
    await _send_trial_message(body.chat_id, confirm_msg)

    # Log activity
    await db.execute(
        "INSERT INTO activity_log (event_type, message) VALUES (?, ?)",
        ("trial_registered", f"Trial registered for chat {body.chat_id}: {location_label}"),
    )

    return {
        "success": True,
        "id": trial_id,
        "expires_at": expires_str,
    }


@router.get("/status/{chat_id}")
async def get_trial_status(chat_id: str):
    """Get active trial status for a chat ID."""
    db = get_database()

    row = await db.fetch_one(
        """
        SELECT id, telegram_chat_id, subdistrict_code, subdistrict_name,
               district_name, province_name, severity_threshold,
               registered_at, expires_at
        FROM trial_subscriptions
        WHERE telegram_chat_id = ? AND expires_at > CURRENT_TIMESTAMP
        ORDER BY registered_at DESC LIMIT 1
        """,
        (chat_id,),
    )

    if not row:
        return {"active": False}

    return {
        "active": True,
        "id": row["id"],
        "location_code": row["subdistrict_code"],
        "location_name": row["subdistrict_name"],
        "district_name": row["district_name"],
        "province_name": row["province_name"],
        "severity_min": row["severity_threshold"],
        "registered_at": row["registered_at"],
        "expires_at": row["expires_at"],
    }


@router.delete("/{trial_id}")
async def cancel_trial(trial_id: int):
    """Cancel an active trial subscription."""
    db = get_database()

    row = await db.fetch_one(
        "SELECT telegram_chat_id, subdistrict_name FROM trial_subscriptions WHERE id = ?",
        (trial_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Trial tidak ditemukan")

    # Expire the trial immediately
    await db.execute(
        "UPDATE trial_subscriptions SET expires_at = CURRENT_TIMESTAMP WHERE id = ?",
        (trial_id,),
    )

    # Send cancellation message
    cancel_msg = (
        "<b>Trial BMKG Alert Dihentikan</b>\n\n"
        "Trial Anda telah dihentikan. "
        "Terima kasih sudah mencoba BMKG Alert!\n\n"
        "<i>BMKG Alert System</i>"
    )
    await _send_trial_message(row["telegram_chat_id"], cancel_msg)

    # Log activity
    await db.execute(
        "INSERT INTO activity_log (event_type, message) VALUES (?, ?)",
        ("trial_cancelled", f"Trial cancelled for chat {row['telegram_chat_id']}"),
    )

    return {"success": True}


@router.get("/bot-info")
async def get_bot_info():
    """Return the Telegram bot username so the UI can tell users which bot to /start."""
    bot_token = settings.telegram_bot_token
    if not bot_token:
        return {"available": False}

    url = f"https://api.telegram.org/bot{bot_token}/getMe"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
        data = resp.json()
        if resp.status_code == 200 and data.get("ok"):
            result = data["result"]
            return {
                "available": True,
                "username": result.get("username", ""),
                "name": result.get("first_name", ""),
            }
    except Exception:
        pass
    return {"available": False}


@router.post("/{trial_id}/test-message")
async def send_test_message(trial_id: int):
    """Send a test Telegram message so the user can verify the bot can reach them."""
    db = get_database()

    row = await db.fetch_one(
        """
        SELECT telegram_chat_id FROM trial_subscriptions
        WHERE id = ? AND expires_at > CURRENT_TIMESTAMP
        """,
        (trial_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Trial tidak ditemukan atau sudah berakhir")

    test_msg = (
        "✅ <b>Pesan Tes — BMKG Alert</b>\n\n"
        "Bot berhasil menghubungi Anda! Anda akan menerima notifikasi peringatan "
        "cuaca BMKG secara otomatis ketika ada peringatan untuk lokasi yang dipilih.\n\n"
        "<i>BMKG Alert System</i>"
    )
    success = await _send_trial_message(row["telegram_chat_id"], test_msg)
    if not success:
        raise HTTPException(
            status_code=502,
            detail=(
                "Gagal mengirim pesan. Pastikan Anda sudah mengirim /start ke bot kami "
                "di Telegram sebelum mendaftar trial."
            ),
        )
    return {"success": True}
