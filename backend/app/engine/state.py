"""State manager — deduplication, expiry tracking, and DB persistence for alerts."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import structlog

from app.database import DatabaseManager
from app.models import Alert, Location, MatchResult, WarningInfo

logger = structlog.get_logger()


def _to_iso(value: datetime | str | None) -> str | None:
    """Store timestamps as ISO 8601 text instead of relying on sqlite3's deprecated datetime adapter."""
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _parse_timestamp(value: str | None) -> datetime | None:
    """Parse a stored timestamp ("T" or space separated); naive values are UTC."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


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
                _to_iso(warning.effective),
                _to_iso(warning.expires),
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
        now_utc = datetime.now(timezone.utc)

        # `expires` keeps BMKG's local offset (+07:00/+08:00/+09:00), so it has to be
        # parsed and compared as an instant; a string comparison in SQL gets it wrong.
        rows = await self._db.fetch_all(
            "SELECT * FROM alerts WHERE status = 'active' AND expires IS NOT NULL AND expires != ''"
        )

        expired_alerts: list[Alert] = []
        for row in rows:
            alert = Alert(**dict(row))
            expires_at = _parse_timestamp(alert.expires)
            if expires_at is None or expires_at > now_utc:
                continue
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

    async def get_locations_without_point(self, limit: int = 3) -> list[Location]:
        """Enabled locations whose coordinates have not been resolved yet."""
        rows = await self._db.fetch_all(
            "SELECT * FROM locations WHERE enabled = 1 AND (latitude IS NULL OR longitude IS NULL) LIMIT ?",
            (limit,),
        )
        return [Location(**dict(row)) for row in rows]

    async def set_location_point(self, location_id: int, latitude: float, longitude: float) -> None:
        await self._db.execute(
            "UPDATE locations SET latitude = ?, longitude = ? WHERE id = ?",
            (latitude, longitude, location_id),
        )

    async def prune_activity_log(self, keep_days: int = 30) -> None:
        """Drop activity entries older than `keep_days`; one row is written per poll, so it grows without bound."""
        await self._db.execute(
            "DELETE FROM activity_log WHERE created_at < datetime('now', ?)",
            (f"-{keep_days} days",),
        )

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

    async def claim_trial_notification(self, trial_id: int, alert_code: str) -> bool:
        """Record that a trial is being notified about a warning.

        Returns False when that pair was already recorded, so each subscriber
        hears about a given warning once instead of on every poll cycle.
        """
        cursor = await self._db.execute(
            "INSERT OR IGNORE INTO trial_notifications (trial_id, alert_code) VALUES (?, ?)",
            (trial_id, alert_code),
        )
        return cursor.rowcount > 0

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
