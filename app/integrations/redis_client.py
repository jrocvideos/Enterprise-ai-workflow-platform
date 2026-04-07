"""Redis client with circuit breaker pattern."""
from typing import Optional

import redis.asyncio as redis
from redis.exceptions import ConnectionError, RedisError

from app.core.config import get_settings
from app.core.logging import get_logger_with_context


class RedisClient:
    """Redis client with graceful fallback."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client: Optional[redis.Redis] = None
        self.connected = False
        self.logger = get_logger_with_context()
    
    async def connect(self):
        """Initialize connection."""
        try:
            self.client = redis.from_url(
                self.settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30
            )
            await self.client.ping()
            self.connected = True
            self.logger.info("redis_connected")
        except ConnectionError as e:
            self.logger.warning("redis_connection_failed", error=str(e))
            self.connected = False
    
    async def disconnect(self):
        """Cleanup."""
        if self.client:
            await self.client.close()
            self.logger.info("redis_disconnected")
    
    async def get(self, key: str) -> Optional[str]:
        """Get with fallback."""
        if not self.connected:
            return None
        try:
            return await self.client.get(key)
        except RedisError as e:
            self.logger.error("redis_get_error", error=str(e), key=key)
            return None
    
    async def set(self, key: str, value: str, ttl: Optional[int] = None):
        """Set with fallback."""
        if not self.connected:
            return False
        try:
            ttl = ttl or self.settings.redis_ttl
            await self.client.setex(key, ttl, value)
            return True
        except RedisError as e:
            self.logger.error("redis_set_error", error=str(e), key=key)
            return False
    
    async def delete(self, key: str):
        """Delete with fallback."""
        if not self.connected:
            return False
        try:
            await self.client.delete(key)
            return True
        except RedisError as e:
            self.logger.error("redis_delete_error", error=str(e), key=key)
            return False
    
    async def health_check(self) -> bool:
        """Check connectivity."""
        if not self.client:
            return False
        try:
            await self.client.ping()
            return True
        except Exception:
            return False


# Singleton
_redis_client: Optional[RedisClient] = None

async def get_redis() -> RedisClient:
    """Get Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
        await _redis_client.connect()
    return _redis_client

async def close_redis():
    """Cleanup."""
    global _redis_client
    if _redis_client:
        await _redis_client.disconnect()
        _redis_client = None