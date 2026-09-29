"""
Internal API client for communicating with Next.js platform.

This client handles all platform operations (users, workspaces, billing, etc.)
that are managed by the Next.js application.
"""

import os
from typing import Any

import aiohttp
from loguru import logger

from ..cache.cache_backend import get_cache_manager


class PlatformAPIClient:
    """Client for internal communication with Next.js platform APIs."""

    def __init__(self, base_url: str = None, api_secret: str = None):
        self.base_url = base_url or os.getenv("PLATFORM_API_URL", "http://localhost:3000")
        self.api_secret = api_secret or os.getenv("INTERNAL_API_SECRET", "")
        self.cache = get_cache_manager()

        if not self.api_secret:
            logger.warning("INTERNAL_API_SECRET not set - platform API calls will fail")

        logger.info(f"PlatformAPIClient initialized with base URL: {self.base_url}")

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Make HTTP request to platform API."""
        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {self.api_secret}", "Content-Type": "application/json"}

        try:
            async with aiohttp.ClientSession() as session, session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                if response.status == 200:
                    return await response.json()
                error_text = await response.text()
                logger.error(f"Platform API error: {response.status} - {error_text}")
                return None
        except aiohttp.ClientTimeout:
            logger.error(f"Platform API timeout for {method} {endpoint}")
            return None
        except Exception as e:
            logger.error(f"Platform API request failed: {e}")
            return None

    async def validate_api_key(self, api_key: str) -> dict[str, Any] | None:
        """
        Validate API key with platform.

        Returns:
            {
                "valid": bool,
                "user_id": str,
                "workspace_id": str,
                "limits": {...}
            }
        """
        # Check cache first
        key_parts = api_key.split(":", 1)
        if len(key_parts) != 2:
            return None

        key_id = key_parts[0]
        cached = await self.cache.get_api_key_validation(key_id)
        if cached:
            logger.debug(f"API key validation cache hit for: {key_id}")
            return cached

        # Call platform API
        result = await self._make_request(
            "GET", "/api/internal/keys/validate", params={"key": api_key}
        )

        if result and result.get("valid"):
            # Cache successful validation for 60 seconds
            await self.cache.set_api_key_validation(key_id, result, ttl=60)

        return result

    async def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        """
        Get user details from platform.

        Returns user object with email, workspaces, etc.
        """
        # Check cache first
        cached = await self.cache.get_user(user_id)
        if cached:
            logger.debug(f"User cache hit for: {user_id}")
            return cached

        # Call platform API
        result = await self._make_request("GET", f"/api/internal/users/{user_id}")

        if result:
            # Cache user data for 5 minutes
            await self.cache.set_user(user_id, result, ttl=300)

        return result

    async def get_workspace_subscription(self, workspace_id: str) -> dict[str, Any] | None:
        """
        Get workspace subscription and limits.

        Returns:
            {
                "workspace_id": str,
                "plan": str,
                "status": str,
                "limits": {...},
                "usage": {...}
            }
        """
        # Check cache first
        cached = await self.cache.get_workspace_subscription(workspace_id)
        if cached:
            logger.debug(f"Workspace subscription cache hit for: {workspace_id}")
            return cached

        # Call platform API
        result = await self._make_request(
            "GET", f"/api/internal/workspaces/{workspace_id}/subscription"
        )

        if result:
            # Cache subscription data for 5 minutes
            await self.cache.set_workspace_subscription(workspace_id, result, ttl=300)

        return result

    async def track_usage(
        self,
        workspace_id: str,
        metric: str,
        count: int = 1,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Track usage for a workspace.

        Returns:
            {
                "allowed": bool,
                "remaining": int,
                "limit": int,
                "current": int
            }
        """
        # No caching for usage tracking - always hit the API
        return await self._make_request(
            "POST",
            "/api/internal/usage/track",
            data={
                "workspace_id": workspace_id,
                "metric": metric,
                "count": count,
                "metadata": metadata,
            },
        )


    async def check_usage(
        self, workspace_id: str, metric: str, count: int = 1
    ) -> dict[str, Any] | None:
        """
        Check if usage would be allowed.

        Returns:
            {
                "allowed": bool,
                "current_usage": int,
                "limit": int,
                "would_exceed": bool
            }
        """
        # Cache usage checks for 30 seconds to reduce load
        cache_key = f"usage_check:{workspace_id}:{metric}"
        cached = await self.cache.backend.get(cache_key)
        if cached:
            logger.debug(f"Usage check cache hit for: {workspace_id}/{metric}")
            return cached

        result = await self._make_request(
            "GET",
            "/api/internal/usage/check",
            params={"workspace_id": workspace_id, "metric": metric, "count": count},
        )

        if result:
            # Cache for 30 seconds
            await self.cache.backend.set(cache_key, result, ttl=30)

        return result


# Singleton instance
_platform_client: PlatformAPIClient | None = None


def get_platform_client() -> PlatformAPIClient:
    """Get or create platform API client instance."""
    global _platform_client

    if _platform_client is None:
        _platform_client = PlatformAPIClient()

    return _platform_client
