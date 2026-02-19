import httpx
from app.services.notifications.base import NotificationProvider, NotificationMessage
from app.config import settings

class WebhookProvider(NotificationProvider):
    """Generic Webhook Provider."""
    
    @property
    def name(self) -> str:
        return "webhook"
    
    async def send(self, message: NotificationMessage) -> bool:
        webhook_url = settings.generic_webhook_url
        if not webhook_url:
            return False
            
        payload = message.model_dump(mode='json')
        
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(webhook_url, json=payload)
                resp.raise_for_status()
                return True
            except Exception as e:
                print(f"Failed to send Webhook notification: {e}")
                return False
