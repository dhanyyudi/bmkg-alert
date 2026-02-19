import httpx
from app.services.notifications.base import NotificationProvider, NotificationMessage
from app.config import settings

class SlackProvider(NotificationProvider):
    """Slack Webhook Provider."""
    
    @property
    def name(self) -> str:
        return "slack"
    
    async def send(self, message: NotificationMessage) -> bool:
        webhook_url = settings.slack_webhook_url
        if not webhook_url:
            return False
            
        # Map severity to Slack colors
        color = "#36a64f" # Green/Good
        if message.severity in ["Critical", "High"]:
             color = "#danger"
        elif message.severity == "Medium":
             color = "#warning"

        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": message.title,
                    "title_link": message.url,
                    "text": message.body,
                    "footer": "BMKG Alert System",
                    "ts": message.timestamp.timestamp()
                }
            ]
        }
        
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(webhook_url, json=payload)
                resp.raise_for_status()
                return True
            except Exception as e:
                print(f"Failed to send Slack notification: {e}")
                return False
