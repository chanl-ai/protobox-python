"""
Cache backend abstraction for ProtoBox.

Supports multiple cache backends:
- Memory (default, for development)
- Redis (for production)
"""

import asyncio
import json
import os
import time
from abc import ABC, abstractmethod
from typing import Any

from loguru import logger


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Get value from cache."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set value in cache with TTL in seconds."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete value from cache."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache entries."""
        pass


class MemoryCache(CacheBackend):
    """In-memory cache implementation."""

    def __init__(self):
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        logger.info("MemoryCache initialized")

    async def get(self, key: str) -> Any | None:
        """Get value from memory cache."""
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if entry["expires_at"] > time.time():
                    logger.debug(f"Cache hit for key: {key}")
                    return entry["value"]
                # Expired, remove it
                del self._cache[key]
                logger.debug(f"Cache expired for key: {key}")
            logger.debug(f"Cache miss for key: {key}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set value in memory cache."""
        async with self._lock:
            self._cache[key] = {"value": value, "expires_at": time.time() + ttl}
            logger.debug(f"Cache set for key: {key}, TTL: {ttl}s")

    async def delete(self, key: str) -> None:
        """Delete value from memory cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache deleted for key: {key}")

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            logger.info("Memory cache cleared")

    async def cleanup_expired(self) -> None:
        """Remove expired entries (called periodically)."""
        async with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, entry in self._cache.items() if entry["expires_at"] <= current_time
            ]
            for key in expired_keys:
                del self._cache[key]
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")


class RedisCache(CacheBackend):
    """Redis cache implementation."""

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6381")
        self._redis = None
        self._connected = False
        logger.info(f"RedisCache configured with URL: {self.redis_url}")

    async def _get_redis(self):
        """Get Redis connection, creating it if necessary."""
        if not self._connected:
            try:
                import redis.asyncio as redis

                self._redis = redis.from_url(
                    self.redis_url, encoding="utf-8", decode_responses=True
                )
                # Test connection
                await self._redis.ping()
                self._connected = True
                logger.info("Connected to Redis")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        return self._redis

    async def get(self, key: str) -> Any | None:
        """Get value from Redis."""
        try:
            redis = await self._get_redis()
            value = await redis.get(key)
            if value:
                logger.debug(f"Redis cache hit for key: {key}")
                return json.loads(value)
            logger.debug(f"Redis cache miss for key: {key}")
            return None
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set value in Redis with TTL."""
        try:
            redis = await self._get_redis()
            json_value = json.dumps(value)
            await redis.setex(key, ttl, json_value)
            logger.debug(f"Redis cache set for key: {key}, TTL: {ttl}s")
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")

    async def delete(self, key: str) -> None:
        """Delete value from Redis."""
        try:
            redis = await self._get_redis()
            await redis.delete(key)
            logger.debug(f"Redis cache deleted for key: {key}")
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {e}")

    async def clear(self) -> None:
        """Clear all cache entries (use with caution in production)."""
        try:
            redis = await self._get_redis()
            await redis.flushdb()
            logger.warning("Redis cache cleared (all keys deleted)")
        except Exception as e:
            logger.error(f"Redis clear error: {e}")


class CacheManager:
    """Cache manager that handles backend selection and key prefixing."""

    def __init__(self, backend: str = "memory", prefix: str = "protobox:"):
        self.prefix = prefix

        if backend == "redis":
            self.backend = RedisCache()
        else:
            self.backend = MemoryCache()

        logger.info(f"CacheManager initialized with {backend} backend")

    def _make_key(self, key: str) -> str:
        """Create prefixed cache key."""
        return f"{self.prefix}{key}"

    async def get_user(self, user_id: str) -> dict[str, Any] | None:
        """Get cached user data."""
        key = self._make_key(f"user:{user_id}")
        return await self.backend.get(key)

    async def set_user(self, user_id: str, user_data: dict[str, Any], ttl: int = 300) -> None:
        """Cache user data."""
        key = self._make_key(f"user:{user_id}")
        await self.backend.set(key, user_data, ttl)

    async def get_api_key_validation(self, key_id: str) -> dict[str, Any] | None:
        """Get cached API key validation result."""
        key = self._make_key(f"apikey:{key_id}")
        return await self.backend.get(key)

    async def set_api_key_validation(
        self, key_id: str, validation: dict[str, Any], ttl: int = 60
    ) -> None:
        """Cache API key validation result."""
        key = self._make_key(f"apikey:{key_id}")
        await self.backend.set(key, validation, ttl)

    async def get_workspace_subscription(self, workspace_id: str) -> dict[str, Any] | None:
        """Get cached workspace subscription data."""
        key = self._make_key(f"workspace:subscription:{workspace_id}")
        return await self.backend.get(key)

    async def set_workspace_subscription(
        self, workspace_id: str, subscription: dict[str, Any], ttl: int = 300
    ) -> None:
        """Cache workspace subscription data."""
        key = self._make_key(f"workspace:subscription:{workspace_id}")
        await self.backend.set(key, subscription, ttl)

    async def invalidate_user(self, user_id: str) -> None:
        """Invalidate user cache."""
        key = self._make_key(f"user:{user_id}")
        await self.backend.delete(key)

    async def invalidate_api_key(self, key_id: str) -> None:
        """Invalidate API key cache."""
        key = self._make_key(f"apikey:{key_id}")
        await self.backend.delete(key)

    # MCP Server caching methods
    async def get_mcp_server(self, workspace_id: str) -> dict[str, Any] | None:
        """Get cached MCP server metadata."""
        key = self._make_key(f"mcp:server:{workspace_id}")
        return await self.backend.get(key)

    async def set_mcp_server(
        self, workspace_id: str, server_data: dict[str, Any], ttl: int = 3600
    ) -> None:
        """Cache MCP server metadata (1 hour default TTL)."""
        key = self._make_key(f"mcp:server:{workspace_id}")
        await self.backend.set(key, server_data, ttl)

    async def invalidate_mcp_server(self, workspace_id: str) -> None:
        """Invalidate MCP server cache."""
        key = self._make_key(f"mcp:server:{workspace_id}")
        await self.backend.delete(key)

    # MCP Session caching methods
    async def get_mcp_session(self, session_id: str) -> dict[str, Any] | None:
        """Get cached MCP session data."""
        key = self._make_key(f"mcp:session:{session_id}")
        return await self.backend.get(key)

    async def set_mcp_session(
        self, session_id: str, session_data: dict[str, Any], ttl: int = 1800
    ) -> None:
        """Cache MCP session data (30 minutes default TTL)."""
        key = self._make_key(f"mcp:session:{session_id}")
        await self.backend.set(key, session_data, ttl)

    async def invalidate_mcp_session(self, session_id: str) -> None:
        """Invalidate MCP session cache."""
        key = self._make_key(f"mcp:session:{session_id}")
        await self.backend.delete(key)

    async def get_all_mcp_sessions(self) -> list[str]:
        """Get all active MCP session IDs (Redis only)."""
        if isinstance(self.backend, RedisCache):
            try:
                redis = await self.backend._get_redis()
                pattern = self._make_key("mcp:session:*")
                keys = await redis.keys(pattern)
                # Extract session IDs from keys
                prefix_len = len(self._make_key("mcp:session:"))
                return [key[prefix_len:] for key in keys]
            except Exception as e:
                logger.error(f"Error getting MCP sessions: {e}")
                return []
        else:
            # For memory cache, return empty list (would need to track separately)
            return []


# Singleton instance
_cache_manager: CacheManager | None = None


def get_cache_manager() -> CacheManager:
    """Get or create cache manager instance."""
    global _cache_manager

    if _cache_manager is None:
        # Get cache backend from environment
        cache_backend = os.getenv("CACHE_BACKEND", "memory").lower()
        _cache_manager = CacheManager(backend=cache_backend)

    return _cache_manager
