import aiosmtplib
from email.message import EmailMessage
from app.services.notifications.base import NotificationProvider, NotificationMessage
from app.config import settings

class EmailProvider(NotificationProvider):
    """Email Provider using SMTP."""
    
    @property
    def name(self) -> str:
        return "email"
    
    async def send(self, message: NotificationMessage) -> bool:
        if not settings.smtp_host or not settings.smtp_user:
            return False
            
        msg = EmailMessage()
        msg["From"] = settings.smtp_from
        msg["To"] = settings.smtp_user # Send to admin/configured user for now
        msg["Subject"] = f"[{message.severity}] {message.title}"
        msg.set_content(f"{message.body}\n\nTimestamp: {message.timestamp}\nMore info: {message.url}")
        
        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_user,
                password=settings.smtp_password,
                use_tls=True
            )
            return True
        except Exception as e:
            print(f"Failed to send Email notification: {e}")
            return False
