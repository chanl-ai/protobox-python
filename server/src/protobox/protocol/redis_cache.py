"""
Redis-backed caching for workspace MCP servers.

Provides distributed caching for workspace tools and server states
to enable horizontal scaling across multiple Fly.io instances.
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional
import functools

import redis.asyncio as redis
from loguru import logger


def redis_retry(max_retries: int = 3, retry_delay: float = 0.1):
    """
    Decorator for Redis operations with retry logic and connection recovery.
    
    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    # If not connected, attempt to reconnect
                    if not self._connected:
                        await self.connect()
                    
                    # Execute the operation
                    return await func(self, *args, **kwargs)
                    
                except redis.ConnectionError as e:
                    last_exception = e
                    self._connected = False
                    logger.warning(f"Redis connection error in {func.__name__} (attempt {attempt + 1}/{max_retries + 1}): {e}")
                    
                    if attempt < max_retries:
                        await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                        continue
                    else:
                        logger.error(f"Redis operation {func.__name__} failed after {max_retries + 1} attempts")
                        
                except redis.TimeoutError as e:
                    last_exception = e
                    logger.warning(f"Redis timeout in {func.__name__} (attempt {attempt + 1}/{max_retries + 1}): {e}")
                    
                    if attempt < max_retries:
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        logger.error(f"Redis operation {func.__name__} timed out after {max_retries + 1} attempts")
                        
                except Exception as e:
                    # For other exceptions, don't retry
                    logger.error(f"Unexpected error in Redis operation {func.__name__}: {e}")
                    return None
            
            # All retries failed - return None to trigger fallback behavior
            logger.error(f"Redis operation {func.__name__} failed permanently: {last_exception}")
            return None
        
        return wrapper
    return decorator


class RedisWorkspaceCache:
    """Redis-backed cache for workspace tools and server states."""
    
    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None
        self._default_ttl = 3600  # Default 1 hour, will be overridden from settings
        self._connected = False
        self._connection_lock = asyncio.Lock()  # Prevent concurrent connection attempts
        self._last_health_check = 0
        self._health_check_interval = 30  # 30 seconds
    
    async def connect(self):
        """Connect to Redis with improved connection pooling."""
        async with self._connection_lock:
            if self._connected:
                return
            
            try:
                # Import settings inside function to avoid circular import
                from ..admin.config import settings
                
                # Update default TTL from settings
                self._default_ttl = settings.mcp_redis_ttl_seconds
                
                # Use Redis settings from configuration
                redis_url = settings.redis_url
                
                # Enhanced connection pool configuration
                self._connection_pool = redis.ConnectionPool.from_url(
                    redis_url,
                    max_connections=settings.redis_max_connections,
                    retry_on_timeout=True,
                    retry_on_error=[
                        redis.BusyLoadingError,  # Redis is loading data
                        redis.ConnectionError,   # Network issues
                        redis.TimeoutError,      # Operation timeouts
                    ],
                    socket_keepalive=settings.redis_socket_keepalive,
                    socket_keepalive_options={
                        1: 1,  # TCP_KEEPIDLE
                        2: 3,  # TCP_KEEPINTVL 
                        3: 5,  # TCP_KEEPCNT
                    },
                    socket_connect_timeout=5,  # 5 second connection timeout
                    socket_timeout=10,         # 10 second socket timeout
                    health_check_interval=self._health_check_interval,
                    password=settings.redis_password if settings.redis_password else None,
                    db=settings.redis_db
                )
                
                self._redis_client = redis.Redis(
                    connection_pool=self._connection_pool,
                    decode_responses=True,
                    retry_on_timeout=True,
                    retry_on_error=[
                        redis.BusyLoadingError,
                        redis.ConnectionError,
                    ]
                )
                
                # Test connection with timeout
                await asyncio.wait_for(self._redis_client.ping(), timeout=5.0)
                self._connected = True
                self._last_health_check = time.time()
                logger.info(f"✓ Connected to Redis at {redis_url} with enhanced pooling")
                
            except asyncio.TimeoutError:
                logger.warning("Redis connection timeout. Using in-memory fallback.")
                await self._cleanup_failed_connection()
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Using in-memory fallback.")
                await self._cleanup_failed_connection()
    
    async def _cleanup_failed_connection(self):
        """Clean up failed connection resources."""
        self._connected = False
        if self._redis_client:
            try:
                await self._redis_client.aclose()
            except:
                pass
            self._redis_client = None
        
        if self._connection_pool:
            try:
                await self._connection_pool.aclose()
            except:
                pass
            self._connection_pool = None
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self._redis_client:
            await self._redis_client.aclose()
            self._redis_client = None
        
        if self._connection_pool:
            await self._connection_pool.aclose()
            self._connection_pool = None
        
        self._connected = False
        logger.info("Disconnected from Redis")
    
    async def _ensure_healthy(self) -> bool:
        """Ensure Redis connection is healthy with periodic checks."""
        current_time = time.time()
        
        # Skip health check if recently verified
        if current_time - self._last_health_check < self._health_check_interval:
            return self._connected
        
        if not self._connected:
            return False
        
        try:
            await asyncio.wait_for(self._redis_client.ping(), timeout=2.0)
            self._last_health_check = current_time
            return True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            self._connected = False
            return False
    
    @redis_retry(max_retries=3, retry_delay=0.1)
    async def get_workspace_tools(self, workspace_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached workspace tools with retry logic."""
        if not self._redis_client or not await self._ensure_healthy():
            return None
        
        key = f"workspace:tools:{workspace_id}"
        data = await self._redis_client.get(key)
        
        if data:
            tools_data = json.loads(data)
            logger.debug(f"Cache hit for workspace {workspace_id} tools")
            return tools_data
        
        return None
    
    @redis_retry(max_retries=2, retry_delay=0.1)
    async def set_workspace_tools(
        self, 
        workspace_id: str, 
        tools: List[Dict[str, Any]], 
        ttl: Optional[int] = None
    ):
        """Cache workspace tools with retry logic."""
        if not self._redis_client or not await self._ensure_healthy():
            return
        
        key = f"workspace:tools:{workspace_id}"
        data = json.dumps(tools)
        
        await self._redis_client.setex(
            key, 
            ttl or self._default_ttl, 
            data
        )
        
        logger.debug(f"Cached {len(tools)} tools for workspace {workspace_id}")
    
    @redis_retry(max_retries=2, retry_delay=0.1)
    async def invalidate_workspace_tools(self, workspace_id: str):
        """Invalidate cached workspace tools with retry logic."""
        if not self._redis_client or not await self._ensure_healthy():
            return
        
        key = f"workspace:tools:{workspace_id}"
        await self._redis_client.delete(key)
        logger.debug(f"Invalidated tools cache for workspace {workspace_id}")
    
    async def get_workspace_server_info(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Get cached workspace server info."""
        if not self._redis_client:
            return None
        
        try:
            key = f"workspace:server:{workspace_id}"
            data = await self._redis_client.get(key)
            
            if data:
                return json.loads(data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting server info for workspace {workspace_id}: {e}")
            return None
    
    async def set_workspace_server_info(
        self, 
        workspace_id: str, 
        server_info: Dict[str, Any],
        ttl: Optional[int] = None
    ):
        """Cache workspace server info."""
        if not self._redis_client:
            return
        
        try:
            key = f"workspace:server:{workspace_id}"
            data = json.dumps(server_info)
            
            await self._redis_client.setex(
                key,
                ttl or self._default_ttl,
                data
            )
            
        except Exception as e:
            logger.error(f"Error caching server info for workspace {workspace_id}: {e}")
    
    @redis_retry(max_retries=2, retry_delay=0.05)
    async def track_workspace_activity(self, workspace_id: str):
        """Track workspace activity for cleanup scheduling with retry logic."""
        if not self._redis_client or not await self._ensure_healthy():
            return
        
        key = f"workspace:activity:{workspace_id}"
        timestamp = int(time.time())
        
        await self._redis_client.setex(key, 3600, timestamp)  # 1 hour TTL
    
    async def get_inactive_workspaces(self, inactive_threshold: int = 3600) -> List[str]:
        """Get list of inactive workspaces that can be cleaned up."""
        if not self._redis_client:
            return []
        
        try:
            pattern = "workspace:activity:*"
            keys = await self._redis_client.keys(pattern)
            
            inactive_workspaces = []
            current_time = int(time.time())
            
            for key in keys:
                timestamp = await self._redis_client.get(key)
                if timestamp and (current_time - int(timestamp)) > inactive_threshold:
                    workspace_id = key.split(":")[-1]
                    inactive_workspaces.append(workspace_id)
            
            return inactive_workspaces
            
        except Exception as e:
            logger.error(f"Error getting inactive workspaces: {e}")
            return []
    
    async def cleanup_workspace_cache(self, workspace_id: str):
        """Clean up all cached data for a workspace."""
        if not self._redis_client:
            return
        
        try:
            keys = await self._redis_client.keys(f"workspace:*:{workspace_id}")
            if keys:
                await self._redis_client.delete(*keys)
                logger.debug(f"Cleaned up cache for workspace {workspace_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up cache for workspace {workspace_id}: {e}")
    
    @redis_retry(max_retries=1, retry_delay=0.1)
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics with retry logic."""
        if not self._redis_client:
            return {"status": "disconnected", "health_check": False}
        
        # Check health before attempting operations
        is_healthy = await self._ensure_healthy()
        if not is_healthy:
            return {"status": "unhealthy", "health_check": False}
        
        info = await self._redis_client.info()
        workspace_keys = await self._redis_client.keys("workspace:*")
        
        return {
            "status": "connected",
            "health_check": True,
            "memory_used": info.get("used_memory_human", "unknown"),
            "connected_clients": info.get("connected_clients", 0),
            "total_workspace_keys": len(workspace_keys),
            "redis_version": info.get("redis_version", "unknown"),
            "pool_stats": {
                "max_connections": self._connection_pool.connection_kwargs.get("max_connections", "unknown") if self._connection_pool else "no_pool",
                "created_connections": getattr(self._connection_pool, "created_connections", 0) if self._connection_pool else 0,
                "available_connections": len(getattr(self._connection_pool, "_available_connections", [])) if self._connection_pool else 0,
            }
        }


# Global cache instance
_redis_cache: Optional[RedisWorkspaceCache] = None


async def get_redis_cache() -> RedisWorkspaceCache:
    """Get the global Redis cache instance."""
    global _redis_cache
    
    if _redis_cache is None:
        _redis_cache = RedisWorkspaceCache()
        await _redis_cache.connect()
    
    return _redis_cache


async def shutdown_redis_cache():
    """Shutdown the global Redis cache."""
    global _redis_cache
    
    if _redis_cache:
        await _redis_cache.disconnect()
        _redis_cache = None