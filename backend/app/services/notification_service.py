from typing import Union
import logging
from app.services.notifications.base import NotificationProvider, NotificationMessage
from app.services.notifications.discord import DiscordProvider
from app.services.notifications.slack import SlackProvider
from app.services.notifications.webhook import WebhookProvider
from app.services.notifications.webhook import WebhookProvider
from app.services.notifications.email import EmailProvider
from app.services.notifications.telegram import TelegramProvider
from app.models.nowcast import Warning
from app.models.earthquake import Earthquake
import asyncio

logger = logging.getLogger(__name__)

class NotificationService:
    """Service to deliver notifications across multiple channels."""
    
    def __init__(self):
        self.providers: list[NotificationProvider] = [
            DiscordProvider(),
            SlackProvider(),
            WebhookProvider(),
            WebhookProvider(),
            EmailProvider(),
            TelegramProvider(),
        ]
    
    async def dispatch(self, alert: Union[Warning, Earthquake]):
        """Dispatch an alert to all configured providers."""
        if isinstance(alert, Warning):
            message = self._create_message_from_warning(alert)
        elif isinstance(alert, Earthquake):
            message = self._create_message_from_earthquake(alert)
        else:
            logger.warning(f"Unknown alert type: {type(alert)}")
            return

        logger.info(f"Dispatching alert: {message.title}")
        
        # Send to all providers in parallel
        tasks = [provider.send(message) for provider in self.providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        logger.info(f"Notification Results: {results}")
        
    def _create_message_from_warning(self, warning: Warning) -> NotificationMessage:
        """Convert Warning model to NotificationMessage."""
        severity = warning.severity.value if hasattr(warning.severity, 'value') else str(warning.severity)
        
        return NotificationMessage(
            title=f"{warning.event} - {warning.headline}",
            body=warning.description,
            severity=severity,
            timestamp=warning.effective or warning.created_at,
            url="https://bmkg-alert.com", # TODO: Link to actual alert detail
            original_data=warning.model_dump(mode='json')
        )

    def _create_message_from_earthquake(self, eq: Earthquake) -> NotificationMessage:
        """Convert Earthquake model to NotificationMessage."""
        # Determine severity based on magnitude
        severity = "Info"
        if eq.magnitude >= 6.0:
            severity = "Critical"
        elif eq.magnitude >= 5.0:
            severity = "High"
        elif eq.magnitude >= 4.0:
            severity = "Medium"
            
        title = f"Gempa Mag: {eq.magnitude} - {eq.region}"
        body = (
            f"Waktu: {eq.occurred_at}\n"
            f"Lokasi: {eq.lat_text}, {eq.lon_text}\n"
            f"Kedalaman: {eq.depth_km} km\n"
            f"Potensi: {eq.tsunami_potential or '-'}\n"
            f"Dirasakan: {eq.felt_report or '-'}"
        )
        
        return NotificationMessage(
            title=title,
            body=body,
            severity=severity,
            timestamp=eq.occurred_at,
            url=eq.shakemap_url or "https://bmkg-alert.com",
            original_data=eq.model_dump(mode='json')
        )

# Global notification service
notification_service = NotificationService()
