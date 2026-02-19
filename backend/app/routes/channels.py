"""Notification channels CRUD + test routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_database
from app.dependencies import require_write_allowed
from app.models import ChannelCreate, ChannelUpdate
from app.notifications.telegram import TelegramSender
from app.notifications.discord import DiscordSender
from app.notifications.slack import SlackSender
from app.notifications.email import EmailSender
from app.notifications.webhook import WebhookSender

router = APIRouter(prefix="/channels", tags=["channels"])


@router.get("")
async def list_channels():
    """List all notification channels."""
    db = get_database()
    rows = await db.fetch_all(
        "SELECT * FROM notification_channels ORDER BY created_at DESC"
    )
    result = []
    for row in rows:
        channel = dict(row)
        if isinstance(channel.get("config"), str):
            channel["config"] = json.loads(channel["config"])
        result.append(channel)
    return {"data": result}


@router.post("", status_code=201, dependencies=[Depends(require_write_allowed)])
async def create_channel(body: ChannelCreate):
    """Add a new notification channel."""
    db = get_database()
    config_json = json.dumps(body.config)

    cursor = await db.execute(
        """
        INSERT INTO notification_channels (channel_type, enabled, config)
        VALUES (?, ?, ?)
        """,
        (body.channel_type, 1 if body.enabled else 0, config_json),
    )
    channel_id = cursor.lastrowid
    row = await db.fetch_one(
        "SELECT * FROM notification_channels WHERE id = ?", (channel_id,)
    )
    channel = dict(row)
    channel["config"] = json.loads(channel["config"])
    return {"data": channel}


@router.get("/{channel_id}")
async def get_channel(channel_id: int):
    """Get a specific channel."""
    db = get_database()
    row = await db.fetch_one(
        "SELECT * FROM notification_channels WHERE id = ?", (channel_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Channel not found")
    channel = dict(row)
    if isinstance(channel.get("config"), str):
        channel["config"] = json.loads(channel["config"])
    return {"data": channel}


@router.patch("/{channel_id}", dependencies=[Depends(require_write_allowed)])
async def update_channel(channel_id: int, body: ChannelUpdate):
    """Update a channel's enabled status or config."""
    db = get_database()
    row = await db.fetch_one(
        "SELECT * FROM notification_channels WHERE id = ?", (channel_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Channel not found")

    updates = []
    params = []
    if body.enabled is not None:
        updates.append("enabled = ?")
        params.append(1 if body.enabled else 0)
    if body.config is not None:
        updates.append("config = ?")
        params.append(json.dumps(body.config))

    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(channel_id)
        set_clause = ", ".join(updates)
        await db.execute(
            f"UPDATE notification_channels SET {set_clause} WHERE id = ?",
            tuple(params),
        )

    row = await db.fetch_one(
        "SELECT * FROM notification_channels WHERE id = ?", (channel_id,)
    )
    channel = dict(row)
    if isinstance(channel.get("config"), str):
        channel["config"] = json.loads(channel["config"])
    return {"data": channel}


@router.delete("/{channel_id}", dependencies=[Depends(require_write_allowed)])
async def delete_channel(channel_id: int):
    """Delete a notification channel."""
    db = get_database()
    row = await db.fetch_one(
        "SELECT * FROM notification_channels WHERE id = ?", (channel_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Channel not found")
    await db.execute(
        "DELETE FROM notification_channels WHERE id = ?", (channel_id,)
    )
    return {"status": "deleted", "id": channel_id}


@router.post("/{channel_id}/test", dependencies=[Depends(require_write_allowed)])
async def test_channel(channel_id: int):
    """Send a test notification through a channel."""
    db = get_database()
    row = await db.fetch_one(
        "SELECT * FROM notification_channels WHERE id = ?", (channel_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Channel not found")

    channel = dict(row)
    if isinstance(channel.get("config"), str):
        channel["config"] = json.loads(channel["config"])

    channel_type = channel["channel_type"]
    config = channel["config"]

    success = False
    test_text = (
        "Test Notifikasi BMKG Alert\n\n"
        "Ini adalah pesan test. Jika Anda melihat pesan ini, "
        "konfigurasi berhasil!\n\n"
        "BMKG Alert System v1.0"
    )

    if channel_type == "telegram":
        sender = TelegramSender()
        telegram_msg = (
            "\U0001f9ea <b>Test Notifikasi BMKG Alert</b>\n\n"
            "Ini adalah pesan test. Jika Anda melihat pesan ini, "
            "konfigurasi Telegram berhasil!\n\n"
            "\U0001f4e1 BMKG Alert System v1.0"
        )
        success = await sender.send_raw(
            bot_token=config.get("bot_token", ""),
            chat_id=config.get("chat_id", ""),
            message=telegram_msg,
        )
    elif channel_type == "discord":
        sender = DiscordSender()
        success = await sender.send_raw(
            webhook_url=config.get("webhook_url", ""),
            message=f"\U0001f9ea **{test_text}**",
        )
    elif channel_type == "slack":
        sender = SlackSender()
        success = await sender.send_raw(
            webhook_url=config.get("webhook_url", ""),
            message=f"\U0001f9ea {test_text}",
        )
    elif channel_type == "email":
        sender = EmailSender()
        success = await sender.send_raw(
            to_email=config.get("to_email", ""),
            subject="[BMKG Alert] Test Notification",
            body=test_text,
            channel_config=config,
        )
    elif channel_type == "webhook":
        sender = WebhookSender()
        success = await sender.send_raw(
            webhook_url=config.get("webhook_url", ""),
            payload={"type": "test", "source": "bmkg-alert", "message": test_text},
            headers=config.get("headers", {}),
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported channel type: {channel_type}",
        )

    if success:
        await db.execute(
            "UPDATE notification_channels SET last_success_at = CURRENT_TIMESTAMP WHERE id = ?",
            (channel_id,),
        )
        return {"status": "sent", "channel_type": channel_type}
    else:
        raise HTTPException(
            status_code=502, detail="Failed to send test notification"
        )
