"""Alert Engine worker — background polling loop.

Runs as an asyncio.Task in the FastAPI lifespan. On each cycle:
1. Fetch nowcast list from BMKG API
2. For each warning, fetch detail
3. Match against monitored locations
4. Deduplicate (skip if code+location already exists)
5. Store new alerts and send notifications
6. Mark expired alerts and send 'all clear'
7. Log activity
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

import structlog

from app.config import settings
from app.engine.bmkg_client import BMKGClient
from app.engine.matcher import match_locations
from app.engine.state import StateManager
from app.notifications.telegram import TelegramSender

logger = structlog.get_logger()

# Severity ordering for trial filtering
_SEVERITY_ORDER = {"minor": 0, "moderate": 1, "severe": 2, "extreme": 3}


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
                self._last_poll_result = f"error: {exc}"

            # Wait for the configured interval or until stopped
            poll_interval = int(
                await self._state.get_config_value("poll_interval", "300")
            )
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(), timeout=poll_interval
                )
                # If we get here, stop was called
                break
            except asyncio.TimeoutError:
                # Normal timeout — continue polling
                continue

    async def _run_poll_cycle(self) -> dict[str, Any]:
        """Execute a single poll cycle."""
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
            # 1. Fetch nowcast list
            nowcast = await self._bmkg.get_nowcast_list()
            summary["warnings_fetched"] = len(nowcast.data)

            if not nowcast.data:
                self._last_poll_result = "no warnings"
                logger.info("poll_cycle_no_warnings")
                await self._state.log_activity(
                    "poll_completed", "No active warnings found"
                )
                return summary

            # 2. Get monitored locations
            locations = await self._state.get_enabled_locations()
            if not locations:
                self._last_poll_result = "no locations configured"
                logger.info("poll_cycle_no_locations")
                return summary

            # 3. Get enabled channels
            channels = await self._state.get_enabled_channels()

            # 4. For each warning, get detail and match
            for item in nowcast.data:
                try:
                    detail = await self._bmkg.get_nowcast_detail(item.code)
                    summary["details_fetched"] += 1

                    for warning in detail.warnings:
                        if warning.is_expired:
                            continue

                        matches = match_locations(warning, locations)
                        summary["matches_found"] += len(matches)

                        for match in matches:
                            # Dedup check
                            if await self._state.is_duplicate(
                                item.code, match.location.id
                            ):
                                summary["duplicates_skipped"] += 1
                                continue

                            # Store alert
                            alert_id = await self._state.store_alert(
                                warning, match, item.code
                            )
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

                except Exception as detail_err:
                    logger.error(
                        "detail_fetch_error",
                        code=item.code,
                        error=str(detail_err),
                    )
                    summary["errors"].append(f"{item.code}: {detail_err}")

            # 5. Mark expired alerts
            expired = await self._state.mark_expired_alerts()
            summary["expired_alerts"] = len(expired)

            # 6. Send trial notifications
            summary["trial_notifications"] = await self._process_trials(nowcast, summary)

            # 7. Expire trial subscriptions
            summary["trials_expired"] = await self._expire_trials()

            # Build result
            duration_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )
            self._last_poll_result = (
                f"OK: {summary['new_alerts']} new, "
                f"{summary['duplicates_skipped']} dupes, "
                f"{summary['expired_alerts']} expired"
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
            self._last_poll_result = f"error: {exc}"
            logger.error("poll_cycle_error", error=str(exc), exc_info=True)
            await self._state.log_activity(
                "poll_error", f"Poll cycle failed: {exc}"
            )

        return summary

    async def _process_trials(self, nowcast: Any, summary: dict) -> int:
        """Send Telegram notifications to matching trial subscribers."""
        bot_token = settings.telegram_bot_token
        if not bot_token:
            return 0

        trials = await self._state.get_active_trials()
        if not trials:
            return 0

        sent_count = 0
        telegram = TelegramSender()

        for item in nowcast.data:
            try:
                detail = await self._bmkg.get_nowcast_detail(item.code)
            except Exception:
                continue

            for warning in detail.warnings:
                if warning.is_expired:
                    continue

                description_lower = warning.description.lower()
                area_names_lower = {a.name.lower() for a in warning.areas}
                warn_sev = _SEVERITY_ORDER.get(warning.severity.lower(), 0)

                for trial in trials:
                    # Severity filter
                    trial_threshold = trial.get("severity_threshold", "all")
                    if trial_threshold != "all":
                        trial_sev = _SEVERITY_ORDER.get(trial_threshold.lower(), 0)
                        if warn_sev < trial_sev:
                            continue

                    # Location matching
                    sub_name = trial.get("subdistrict_name", "").lower()
                    dist_name = trial.get("district_name", "").lower()
                    matched = False

                    if sub_name and sub_name in description_lower:
                        matched = True
                    elif dist_name and any(dist_name in a for a in area_names_lower):
                        matched = True

                    if not matched:
                        continue

                    # Build and send message
                    loc_label = trial.get("subdistrict_name", "")
                    if trial.get("district_name"):
                        loc_label += f", {trial['district_name']}"

                    msg = (
                        f"<b>Peringatan Cuaca — {warning.event}</b>\n"
                        f"Severity: {warning.severity}\n\n"
                        f"Lokasi Anda: {loc_label}\n"
                        f"Berlaku: {warning.effective or '-'}\n"
                        f"Hingga: {warning.expires or '-'}\n\n"
                        f"{(warning.description or '')[:300]}\n\n"
                        f"<i>BMKG Alert — Trial Mode</i>"
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
                        logger.error("trial_send_error", chat_id=trial["telegram_chat_id"], error=str(e))

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
