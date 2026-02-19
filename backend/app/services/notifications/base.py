from abc import ABC, abstractmethod
from typing import Any, Optional
from pydantic import BaseModel
from datetime import datetime

class NotificationMessage(BaseModel):
    """Unified notification message model."""
    title: str
    body: str
    severity: str  # Critical, High, Medium, Low
    timestamp: datetime
    url: Optional[str] = None
    original_data: Optional[dict[str, Any]] = None  # Original alert data

class NotificationProvider(ABC):
    """Abstract base class for notification providers."""
    
    @abstractmethod
    async def send(self, message: NotificationMessage) -> bool:
        """Send a notification. Returns True if successful."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g. 'discord', 'email')."""
        pass
