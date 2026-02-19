"""Cache wrapper with Redis and in-memory fallback."""

import json
import time
from typing import Any
from app.config import settings

# Try to import Redis, but don't fail if not available
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class DateTimeEncoder(json.JSONEncoder):
    """JSON Encoder that handles datetime objects."""
    def default(self, obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return super().default(obj)


class InMemoryCache:
    """Simple in-memory cache with TTL for development."""
    
    def __init__(self):
        self._data: dict[str, tuple[Any, float]] = {}
    
    def _is_expired(self, expires_at: float) -> bool:
        return time.time() > expires_at
    
    async def get(self, key: str) -> Any | None:
        if key not in self._data:
            return None
        value, expires_at = self._data[key]
        if self._is_expired(expires_at):
            del self._data[key]
            return None
        return value
    
    async def set(self, key: str, value: Any, ttl: int) -> None:
        expires_at = time.time() + ttl
        self._data[key] = (value, expires_at)
    
    async def delete(self, key: str) -> None:
        self._data.pop(key, None)
    
    async def ttl(self, key: str) -> int:
        if key not in self._data:
            return -2
        _, expires_at = self._data[key]
        remaining = int(expires_at - time.time())
        return max(0, remaining)
    
    async def ping(self) -> bool:
        return True


class Cache:
    """Cache wrapper with Redis primary and in-memory fallback."""
    
    def __init__(self, redis_url: str | None = None):
        """Initialize cache.
        
        Args:
            redis_url: Redis connection URL (defaults to settings)
        """
        self.redis_url = redis_url or settings.redis_url
        self._redis: Any | None = None
        self._fallback: InMemoryCache | None = None
        self._use_fallback = False
    
    async def connect(self) -> None:
        """Establish Redis connection or fallback to in-memory."""
        if not REDIS_AVAILABLE:
            self._use_fallback = True
            self._fallback = InMemoryCache()
            return
        
        try:
            self._redis = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
            )
            await self._redis.ping()
            self._use_fallback = False
        except Exception:
            # Fall back to in-memory cache
            self._use_fallback = True
            self._fallback = InMemoryCache()
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._redis is not None:
            await self._redis.close()
            self._redis = None
    
    def _make_key(self, key: str) -> str:
        """Prefix key with namespace."""
        return f"bmkg:{key}"
    
    async def get(self, key: str) -> Any | None:
        """Get value from cache."""
        if self._fallback is None and self._redis is None:
            await self.connect()
        
        if self._use_fallback:
            return await self._fallback.get(self._make_key(key))
        
        value = await self._redis.get(self._make_key(key))
        if value is None:
            return None
        return json.loads(value)
    
    async def set(self, key: str, value: Any, ttl: int) -> None:
        """Set value in cache with TTL."""
        if self._fallback is None and self._redis is None:
            await self.connect()
        
        if self._use_fallback:
            await self._fallback.set(self._make_key(key), value, ttl)
            return
        
        serialized = json.dumps(value, cls=DateTimeEncoder)
        await self._redis.setex(self._make_key(key), ttl, serialized)
    
    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        if self._fallback is None and self._redis is None:
            await self.connect()
        
        if self._use_fallback:
            await self._fallback.delete(self._make_key(key))
            return
        
        await self._redis.delete(self._make_key(key))
    
    async def ttl(self, key: str) -> int:
        """Get remaining TTL for a key."""
        if self._fallback is None and self._redis is None:
            await self.connect()
        
        if self._use_fallback:
            return await self._fallback.ttl(self._make_key(key))
        
        return await self._redis.ttl(self._make_key(key))
    
    async def health_check(self) -> bool:
        """Check if cache is available.
        
        Returns:
            True if healthy (Redis or fallback)
        """
        try:
            if self._fallback is None and self._redis is None:
                await self.connect()
            
            if self._use_fallback:
                return await self._fallback.ping()
            
            await self._redis.ping()
            return True
        except Exception:
            return False
    
    def is_using_fallback(self) -> bool:
        """Check if using in-memory fallback.
        
        Returns:
            True if using in-memory cache
        """
        return self._use_fallback


# Global cache instance
cache = Cache()
