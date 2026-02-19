import httpx
from app.services.notifications.base import NotificationProvider, NotificationMessage
from app.config import settings

class DiscordProvider(NotificationProvider):
    """Discord Webhook Provider."""
    
    @property
    def name(self) -> str:
        return "discord"
    
    async def send(self, message: NotificationMessage) -> bool:
        webhook_url = settings.discord_webhook_url
        if not webhook_url:
            return False
            
        color = 0x3498db  # Blue (Info)
        if message.severity == "Critical":
            color = 0xe74c3c  # Red
        elif message.severity == "High":
            color = 0xe67e22  # Orange
        elif message.severity == "Medium":
            color = 0xf1c40f  # Yellow

        payload = {
            "embeds": [{
                "title": message.title,
                "description": message.body,
                "color": color,
                "timestamp": message.timestamp.isoformat(),
                "footer": {"text": "BMKG Alert System"},
                "url": message.url or "https://bmkg.go.id"
            }]
        }
        
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(webhook_url, json=payload)
                resp.raise_for_status()
                return True
            except Exception as e:
                print(f"Failed to send Discord notification: {e}")
                return False
