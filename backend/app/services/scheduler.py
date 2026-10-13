"""Background poller that announces new earthquakes."""

import asyncio
import logging
from typing import Any

from app.cache import cache
from app.models.earthquake import Earthquake
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)

POLL_SECONDS = 60
_LAST_SEEN_KEY = "scheduler:last_processed_eq"


class SchedulerService:
    """Background scheduler for periodic tasks."""

    def __init__(self):
        self._tasks: list[asyncio.Task] = []
        self._running = False
        self._baseline_taken = False
        self._client: Any = None

    @property
    def running(self) -> bool:
        return self._running

    async def start(self, bmkg_client: Any) -> None:
        """Start the earthquake poller, unless there is nowhere to announce to."""
        if not notification_service.has_targets():
            logger.info("Earthquake announcements off: no channel configured in the environment")
            return
        self._client = bmkg_client
        self._running = True
        self._tasks.append(asyncio.create_task(self._poll_latest_earthquake()))
        logger.info("Scheduler started")

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        logger.info("Scheduler stopped")

    async def _poll_latest_earthquake(self) -> None:
        logger.info("Starting earthquake poller...")
        while self._running:
            try:
                payload = await self._client.get_json("/v1/earthquake/latest")
                eq = Earthquake(**payload["data"])

                # An event is identified by its origin time
                current_id = eq.occurred_at.isoformat()
                if await cache.get(_LAST_SEEN_KEY) != current_id:
                    await cache.set(_LAST_SEEN_KEY, current_id, ttl=86400)

                    if self._baseline_taken:
                        logger.info(f"New earthquake detected: {eq.region} {eq.magnitude}")
                        await notification_service.dispatch(eq)

                # Without Redis the marker is lost on restart, so the first reading
                # after startup only sets the baseline and is never announced.
                self._baseline_taken = True

            except Exception as e:
                logger.error(f"Error in earthquake poller: {e}")

            await asyncio.sleep(POLL_SECONDS)


# Global scheduler
scheduler = SchedulerService()
