import logging

import aiosmtplib
from email.message import EmailMessage
from app.services.notifications.base import NotificationProvider, NotificationMessage
from app.config import settings

logger = logging.getLogger(__name__)

class EmailProvider(NotificationProvider):
    """Email Provider using SMTP."""
    
    @property
    def name(self) -> str:
        return "email"
    
    async def send(self, message: NotificationMessage) -> bool:
        if not settings.smtp_host or not settings.smtp_user:
            return False
            
        msg = EmailMessage()
        msg["From"] = settings.smtp_from or settings.smtp_user
        msg["To"] = settings.smtp_user # Send to admin/configured user for now
        msg["Subject"] = f"[{message.severity}] {message.title}"
        content = message.body
        if message.url:
            content += f"\n\nPeta guncangan: {message.url}"
        msg.set_content(content)
        
        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_user,
                password=settings.smtp_password,
                use_tls=settings.smtp_port == 465,
                start_tls=settings.smtp_port == 587,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send Email notification: {e}")
            return False
