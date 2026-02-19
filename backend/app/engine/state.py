"""State manager — deduplication, expiry tracking, and DB persistence for alerts."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import structlog

from app.database import DatabaseManager
from app.models import Alert, Location, MatchResult, WarningInfo

logger = structlog.get_logger()


class StateManager:
    """Manages alert state: dedup, insert, expiry, and active alert tracking."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def is_duplicate(self, alert_code: str, location_id: int) -> bool:
        """Check if we already have a non-expired alert for this code + location."""
        row = await self._db.fetch_one(
            "SELECT id FROM alerts WHERE bmkg_alert_code = ? AND matched_location_id = ?",
            (alert_code, location_id),
        )
        return row is not None

    async def store_alert(
        self,
        warning: WarningInfo,
        match: MatchResult,
        alert_code: str,
    ) -> int:
        """Store a new matched alert in the database. Returns the new alert ID."""
        polygon_json = json.dumps(
            [
                {"name": area.name, "polygon": area.polygon}
                for area in warning.areas
            ]
        )

        cursor = await self._db.execute(
            """
            INSERT INTO alerts (
                bmkg_alert_code, event, severity, urgency, certainty,
                headline, description, effective, expires, infographic_url,
                polygon_data, matched_location_id, match_type, matched_text, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
            """,
            (
                alert_code,
                warning.event,
                warning.severity,
                warning.urgency,
                warning.certainty,
                warning.headline,
                warning.description,
                warning.effective,
                warning.expires,
                warning.infographic_url,
                polygon_json,
                match.location.id,
                match.match_type,
                match.matched_text,
            ),
        )
        alert_id = cursor.lastrowid or 0
        logger.info(
            "alert_stored",
            alert_id=alert_id,
            code=alert_code,
            warning_event=warning.event,
            severity=warning.severity,
            location_id=match.location.id,
            match_type=match.match_type,
        )
        return alert_id

    async def mark_expired_alerts(self) -> list[Alert]:
        """Find and mark alerts whose expires timestamp is in the past.

        Returns list of newly-expired alerts for 'all clear' notifications.
        """
        now_utc = datetime.now(timezone.utc).isoformat()

        # Find alerts that should be expired
        rows = await self._db.fetch_all(
            """
            SELECT * FROM alerts
            WHERE status = 'active'
              AND expires != ''
              AND expires < ?
            """,
            (now_utc,),
        )

        expired_alerts: list[Alert] = []
        for row in rows:
            alert = Alert(**dict(row))
            expired_alerts.append(alert)

            await self._db.execute(
                "UPDATE alerts SET status = 'expired' WHERE id = ?",
                (alert.id,),
            )
            logger.info(
                "alert_expired",
                alert_id=alert.id,
                code=alert.bmkg_alert_code,
            )

        return expired_alerts

    async def get_active_alerts(self) -> list[Alert]:
        """Return all currently active alerts."""
        rows = await self._db.fetch_all(
            "SELECT * FROM alerts WHERE status = 'active' ORDER BY created_at DESC"
        )
        return [Alert(**dict(row)) for row in rows]

    async def get_alert_count(self) -> int:
        """Count active alerts."""
        row = await self._db.fetch_one(
            "SELECT COUNT(*) as cnt FROM alerts WHERE status = 'active'"
        )
        return row["cnt"] if row else 0

    async def log_activity(
        self, event_type: str, message: str, details: str = ""
    ) -> None:
        """Write an activity log entry."""
        await self._db.execute(
            "INSERT INTO activity_log (event_type, message, details) VALUES (?, ?, ?)",
            (event_type, message, details),
        )

    async def log_delivery(
        self, alert_id: int, channel_id: int, status: str, error_message: str = ""
    ) -> None:
        """Record a notification delivery attempt."""
        await self._db.execute(
            """
            INSERT INTO alert_deliveries (alert_id, channel_id, status, error_message)
            VALUES (?, ?, ?, ?)
            """,
            (alert_id, channel_id, status, error_message),
        )

    async def get_enabled_locations(self) -> list[Location]:
        """Fetch all enabled monitored locations."""
        rows = await self._db.fetch_all(
            "SELECT * FROM locations WHERE enabled = 1"
        )
        return [Location(**dict(row)) for row in rows]

    async def get_enabled_channels(self) -> list[dict]:
        """Fetch all enabled notification channels."""
        rows = await self._db.fetch_all(
            "SELECT * FROM notification_channels WHERE enabled = 1"
        )
        result = []
        for row in rows:
            channel = dict(row)
            # Parse JSON config
            if isinstance(channel.get("config"), str):
                channel["config"] = json.loads(channel["config"])
            result.append(channel)
        return result

    async def get_config_value(self, key: str, default: str = "") -> str:
        """Read a single config value."""
        row = await self._db.fetch_one(
            "SELECT value FROM config WHERE key = ?", (key,)
        )
        return row["value"] if row else default

    # ── Trial subscriptions ───────────────────────────────────────────────────

    async def get_active_trials(self) -> list[dict]:
        """Fetch all active (non-expired) trial subscriptions."""
        rows = await self._db.fetch_all(
            """
            SELECT * FROM trial_subscriptions
            WHERE expires_at > CURRENT_TIMESTAMP
            """
        )
        return [dict(row) for row in rows]

    async def expire_trials(self) -> list[dict]:
        """Find expired trials that haven't been notified yet.

        Returns list of trial dicts that just expired so caller can notify.
        """
        rows = await self._db.fetch_all(
            """
            SELECT * FROM trial_subscriptions
            WHERE expires_at <= CURRENT_TIMESTAMP
              AND expired_notified = 0
            """
        )
        expired = [dict(row) for row in rows]

        if expired:
            ids = [t["id"] for t in expired]
            placeholders = ",".join("?" * len(ids))
            await self._db.execute(
                f"UPDATE trial_subscriptions SET expired_notified = 1 WHERE id IN ({placeholders})",
                tuple(ids),
            )

        return expired
