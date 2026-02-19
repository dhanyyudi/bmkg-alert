import asyncio
import logging
from datetime import datetime, timezone
from typing import NoReturn

from app.services.earthquake_service import earthquake_service
from app.services.notification_service import notification_service
from app.cache import cache

logger = logging.getLogger(__name__)

class SchedulerService:
    """Background scheduler for periodic tasks."""
    
    def __init__(self):
        self._tasks = []
        self._running = False
        
    @property
    def running(self):
        """Check if scheduler is running."""
        return self._running
        
    @property
    def jobs(self):
        """Get active tasks."""
        return self._tasks
        
    async def start(self):
        """Start scheduler."""
        self._running = True
        self._tasks.append(asyncio.create_task(self._poll_latest_earthquake()))
        logger.info("Scheduler started")
        
    async def stop(self):
        """Stop scheduler."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        logger.info("Scheduler stopped")
        
    async def _poll_latest_earthquake(self):
        """Poll for latest earthquake every 60 seconds."""
        logger.info("Starting earthquake poller...")
        while self._running:
            try:
                # 1. Fetch latest earthquake
                # We use internal method or just modify get_latest to not use cache validation logic here
                # But get_latest uses cache. We need to force fetch or check if changed.
                
                # Simple strategy:
                # Get latest from BMKG (this updates cache if TTL expired)
                # Compare with last processed ID
                
                eq, _, _ = await earthquake_service.get_latest()
                
                # Check if we already processed this earthquake
                last_processed_id = await cache.get("scheduler:last_processed_eq")
                
                # Identify earthquake by datetime string (as it is unique per event)
                current_id = eq.occurred_at.isoformat()
                
                if last_processed_id != current_id:
                    logger.info(f"New earthquake detected: {eq.region} {eq.magnitude}")
                    
                    # Store as processed
                    await cache.set("scheduler:last_processed_eq", current_id, ttl=86400) # 24h
                    
                    # Dispatch notification
                    await notification_service.dispatch(eq)
                
            except Exception as e:
                logger.error(f"Error in earthquake poller: {e}")
            
            # Wait 60 seconds
            await asyncio.sleep(60)

# Global scheduler
scheduler = SchedulerService()
