import logging
import httpx
from typing import Any

from app.config import settings
from app.services.notifications.base import NotificationProvider, NotificationMessage

logger = logging.getLogger(__name__)

class TelegramProvider(NotificationProvider):
    """Telegram Bot notification provider."""
    
    @property
    def name(self) -> str:
        return "Telegram"
        
    def __init__(self):
        self.bot_token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id
        self.enabled = bool(self.bot_token and self.chat_id)
        
        if self.enabled:
            logger.info("Telegram provider enabled")
        else:
            logger.info("Telegram provider disabled (missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID)")
            
    async def send(self, message: NotificationMessage) -> bool:
        """Send notification via Telegram Bot API."""
        if not self.enabled:
            return False
            
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            # Format message with HTML
            text = (
                f"<b>{message.title}</b>\n\n"
                f"{message.body}\n\n"
                f"Severity: {message.severity}\n"
                f"Time: {message.timestamp}"
            )
            
            if message.url:
                text += f"\n<a href='{message.url}'>View Details</a>"
            
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)
                response.raise_for_status()
                
            logger.info(f"Telegram notification sent: {message.title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False
