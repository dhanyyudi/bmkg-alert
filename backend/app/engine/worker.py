"""Alert Engine worker — background polling loop.

Runs as an asyncio.Task in the FastAPI lifespan. On each cycle:
1. Fetch every active warning from the BMKG API
2. Skip expired warnings and those below the severity floor
3. Match against monitored locations
4. Deduplicate (skip if code+location already exists)
5. Store new alerts and send notifications
6. Mark expired alerts
7. Log activity
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from html import escape
from typing import Any

import structlog

from app.config import settings
from app.engine.bmkg_client import BMKGClient
from app.engine.geo import is_near_warning, kecamatan_names, resolve_point
from app.engine.matcher import is_district_level, match_locations, name_listed
from app.engine.state import StateManager
from app.notifications.formatter import format_time, severity_label
from app.notifications.telegram import TelegramSender

logger = structlog.get_logger()

# Severity floor: "all" (or an unknown level) lets everything through
_SEVERITY_ORDER = {"all": 0, "minor": 0, "moderate": 1, "severe": 2, "extreme": 3}

DEFAULT_POLL_INTERVAL = 300
MIN_POLL_INTERVAL = 60


def _has_expired(warning: Any, now: datetime) -> bool:
    """A warning is over once its own `expires` passes; `is_expired` from a cached upstream response can lag."""
    return bool(warning.is_expired) or warning.expires <= now


class AlertEngine:
    """Background alert engine with start/stop/check-now controls."""

    def __init__(
        self,
        bmkg_client: BMKGClient,
        state: StateManager,
        notification_dispatcher: Any,  # NotificationDispatcher
    ) -> None:
        self._bmkg = bmkg_client
        self._state = state
        self._dispatcher = notification_dispatcher
        self._task: asyncio.Task | None = None
        self._running = False
        self._last_poll: str | None = None
        self._last_poll_result: str | None = None
        self._stop_event = asyncio.Event()
        self._cycle_lock = asyncio.Lock()
        self._district_names: dict[str, set[str]] = {}

    @property
    def running(self) -> bool:
        return self._running

    @property
    def last_poll(self) -> str | None:
        return self._last_poll

    @property
    def last_poll_result(self) -> str | None:
        return self._last_poll_result

    async def start(self) -> None:
        """Start the background polling loop."""
        if self._running:
            logger.warn("engine_already_running")
            return

        self._running = True
        self._stop_event.clear()
        self._task = asyncio.create_task(self._poll_loop())
        await self._state.log_activity("engine_started", "Alert engine started")
        logger.info("engine_started")

    async def stop(self) -> None:
        """Stop the background polling loop gracefully."""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        await self._state.log_activity("engine_stopped", "Alert engine stopped")
        logger.info("engine_stopped")

    async def check_now(self) -> dict[str, Any]:
        """Trigger a single poll cycle immediately. Returns summary."""
        return await self._run_poll_cycle()

    def get_status(self) -> dict[str, Any]:
        """Return current engine status."""
        return {
            "running": self._running,
            "last_poll": self._last_poll,
            "last_poll_result": self._last_poll_result,
        }

    async def _poll_loop(self) -> None:
        """Main polling loop."""
        while self._running:
            try:
                await self._run_poll_cycle()
            except Exception as exc:
                logger.error("poll_cycle_error", error=str(exc), exc_info=True)
                self._last_poll_result = f"Galat: {exc}"

            # Wait for the configured interval or until stopped
            poll_interval = await self._poll_interval()
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(), timeout=poll_interval
                )
                # If we get here, stop was called
                break
            except asyncio.TimeoutError:
                # Normal timeout: poll again
                continue

    async def _poll_interval(self) -> int:
        """Configured poll interval in seconds; a bad or tiny value must not stall or spin the loop."""
        raw = await self._state.get_config_value("poll_interval", str(DEFAULT_POLL_INTERVAL))
        try:
            return max(MIN_POLL_INTERVAL, int(raw))
        except (TypeError, ValueError):
            logger.warning("invalid_poll_interval", value=raw)
            return DEFAULT_POLL_INTERVAL

    async def _run_poll_cycle(self) -> dict[str, Any]:
        """Execute a single poll cycle; a manual check waits for a running one instead of overlapping it."""
        async with self._cycle_lock:
            return await self._poll_once()

    async def _poll_once(self) -> dict[str, Any]:
        start_time = datetime.now(timezone.utc)
        self._last_poll = start_time.isoformat()
        summary = {
            "warnings_fetched": 0,
            "details_fetched": 0,
            "matches_found": 0,
            "new_alerts": 0,
            "duplicates_skipped": 0,
            "notifications_sent": 0,
            "expired_alerts": 0,
            "trial_notifications": 0,
            "trials_expired": 0,
            "errors": [],
        }

        logger.info("poll_cycle_start")

        try:
            # 1. Fetch every active warning (one upstream request)
            active = await self._bmkg.get_warnings()
            summary["warnings_fetched"] = len(active)
            summary["details_fetched"] = len(active)

            # 2. Monitored locations, channels and the severity floor
            await self._resolve_location_points()
            locations = await self._state.get_enabled_locations()
            district_members = await self._district_members(locations)
            channels = await self._state.get_enabled_channels()
            min_severity = _SEVERITY_ORDER.get(
                (await self._state.get_config_value("severity_threshold", "all")).lower(), 0
            )

            # 3. Match each warning against the monitored locations
            for item in active:
                warning = item.warning
                try:
                    if _has_expired(warning, start_time):
                        continue
                    if _SEVERITY_ORDER.get(str(warning.severity).lower(), 0) < min_severity:
                        continue

                    matches = match_locations(warning, locations, district_members)
                    summary["matches_found"] += len(matches)

                    for match in matches:
                        # Dedup check
                        if await self._state.is_duplicate(item.code, match.location.id):
                            summary["duplicates_skipped"] += 1
                            continue

                        # Store alert
                        alert_id = await self._state.store_alert(warning, match, item.code)
                        summary["new_alerts"] += 1

                        # Send notifications
                        if channels and self._dispatcher:
                            for channel in channels:
                                try:
                                    success = await self._dispatcher.send(
                                        alert_id=alert_id,
                                        warning=warning,
                                        match=match,
                                        channel=channel,
                                    )
                                    if success:
                                        summary["notifications_sent"] += 1
                                except Exception as send_err:
                                    logger.error(
                                        "notification_send_error",
                                        channel_id=channel.get("id"),
                                        error=str(send_err),
                                    )
                                    summary["errors"].append(str(send_err))

                except Exception as warning_err:
                    logger.error(
                        "warning_processing_error",
                        code=item.code,
                        error=str(warning_err),
                    )
                    summary["errors"].append(f"{item.code}: {warning_err}")

            # 4. Mark expired alerts
            expired = await self._state.mark_expired_alerts()
            summary["expired_alerts"] = len(expired)

            # 5. Send trial notifications
            summary["trial_notifications"] = await self._process_trials(active, start_time)

            # 6. Expire trial subscriptions
            summary["trials_expired"] = await self._expire_trials()

            # 7. Keep the activity log bounded
            await self._state.prune_activity_log()

            # Build result
            duration_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )
            if not active:
                self._last_poll_result = "BMKG tidak mengeluarkan peringatan"
            elif not locations:
                self._last_poll_result = "Belum ada lokasi yang dipantau"
            else:
                self._last_poll_result = (
                    f"{summary['new_alerts']} peringatan baru, "
                    f"{summary['duplicates_skipped']} sudah tercatat, "
                    f"{summary['expired_alerts']} berakhir"
                )

            logger.info(
                "poll_cycle_complete",
                duration_ms=duration_ms,
                **{k: v for k, v in summary.items() if k != "errors"},
            )

            # Log activity
            await self._state.log_activity(
                "poll_completed",
                self._last_poll_result,
                json.dumps(summary, default=str),
            )

        except Exception as exc:
            self._last_poll_result = f"Galat: {exc}"
            logger.error("poll_cycle_error", error=str(exc), exc_info=True)
            await self._state.log_activity(
                "poll_error", f"Poll cycle failed: {exc}"
            )

        return summary

    async def _district_members(self, locations: list[Any]) -> dict[str, set[str]]:
        """Kecamatan names for each monitored kabupaten/kota, looked up once and kept."""
        for location in locations:
            code = location.subdistrict_code
            if is_district_level(location) and code not in self._district_names:
                names = await kecamatan_names(self._bmkg, code)
                if names:
                    self._district_names[code] = names
        return self._district_names

    async def _resolve_location_points(self) -> None:
        """Fill in coordinates for locations added before they were stored, a few per cycle."""
        for location in await self._state.get_locations_without_point():
            point = await resolve_point(self._bmkg, location.subdistrict_code)
            if point:
                await self._state.set_location_point(location.id, *point)

    async def _process_trials(self, active: list[Any], now: datetime) -> int:
        """Send Telegram notifications to matching trial subscribers, once per warning."""
        bot_token = settings.telegram_bot_token
        if not bot_token:
            return 0

        trials = await self._state.get_active_trials()
        if not trials:
            return 0

        sent_count = 0
        telegram = TelegramSender()

        for item in active:
            warning = item.warning
            if _has_expired(warning, now):
                continue

            area_names_lower = {a.name.lower() for a in warning.areas}
            warn_sev = _SEVERITY_ORDER.get(str(warning.severity).lower(), 0)

            for trial in trials:
                # Severity filter
                trial_threshold = trial.get("severity_threshold", "all")
                if warn_sev < _SEVERITY_ORDER.get(trial_threshold.lower(), 0):
                    continue

                # Location matching
                sub_name = trial.get("subdistrict_name", "")
                dist_name = trial.get("district_name", "").lower()
                by_name = name_listed(sub_name, warning.description) and is_near_warning(
                    trial.get("latitude"), trial.get("longitude"), warning.areas
                )
                by_district = bool(dist_name and any(dist_name in a for a in area_names_lower))
                if not (by_name or by_district):
                    continue

                if not await self._state.claim_trial_notification(trial["id"], item.code):
                    continue

                loc_label = trial.get("subdistrict_name", "")
                if trial.get("district_name"):
                    loc_label += f", {trial['district_name']}"

                msg = (
                    f"<b>Peringatan Cuaca: {escape(warning.event)}</b>\n"
                    f"Tingkat: {severity_label(warning.severity)}\n\n"
                    f"Lokasi Anda: {escape(loc_label)}\n"
                    f"Berlaku: {format_time(warning.effective)}\n"
                    f"Hingga: {format_time(warning.expires)}\n\n"
                    f"{escape((warning.description or '')[:300])}\n\n"
                    f"<i>BMKG Alert, mode trial</i>"
                )

                try:
                    ok = await telegram.send_raw(
                        bot_token=bot_token,
                        chat_id=trial["telegram_chat_id"],
                        message=msg,
                    )
                    if ok:
                        sent_count += 1
                except Exception as e:
                    logger.error("trial_send_error", trial_id=trial["id"], error=str(e))

        return sent_count

    async def _expire_trials(self) -> int:
        """Expire trial subscriptions and notify via Telegram."""
        expired_trials = await self._state.expire_trials()
        if not expired_trials:
            return 0

        bot_token = settings.telegram_bot_token
        if not bot_token:
            return len(expired_trials)

        telegram = TelegramSender()
        for trial in expired_trials:
            msg = (
                "<b>Trial BMKG Alert Berakhir</b>\n\n"
                "Trial 24 jam Anda telah berakhir. "
                "Terima kasih sudah mencoba BMKG Alert!\n\n"
                "Untuk mendapatkan notifikasi secara permanen, silakan cek di "
                "<a href=\"https://github.com/dhanyyudi/bmkg-alert\">github.com/dhanyyudi/bmkg-alert</a> "
                "atau hubungi <a href=\"https://dhanypedia.com\">dhanypedia.com</a>\n\n"
                "<i>BMKG Alert System</i>"
            )
            try:
                await telegram.send_raw(
                    bot_token=bot_token,
                    chat_id=trial["telegram_chat_id"],
                    message=msg,
                )
            except Exception as e:
                logger.error("trial_expire_notify_error", chat_id=trial["telegram_chat_id"], error=str(e))

        logger.info("trials_expired", count=len(expired_trials))
        return len(expired_trials)
