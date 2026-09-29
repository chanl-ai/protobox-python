"""
Usage tracking middleware for ProtoBox.

Tracks API calls and other usage metrics by calling the Next.js platform.
"""

from typing import Any

from fastapi import Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from ..clients.platform_api_client import get_platform_client


class UsageTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware to track API usage."""

    def __init__(self, app, exclude_paths: set | None = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or {
            "/health",
            "/admin/api/v1/health",
            "/docs",
            "/openapi.json",
            "/favicon.ico",
        }
        self.platform_client = get_platform_client()

    async def dispatch(self, request: Request, call_next):
        # Skip tracking for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Skip if no user context (unauthenticated requests)
        if not hasattr(request.state, "user") or not request.state.user:
            return await call_next(request)

        user = request.state.user
        workspace_id = user.metadata.get("workspace_id") if user.metadata else None

        if not workspace_id:
            # No workspace context, skip tracking
            return await call_next(request)

        # Process the request
        response = await call_next(request)

        # Track usage only for successful requests
        if 200 <= response.status_code < 400:
            try:
                # Track API call
                await self.platform_client.track_usage(
                    workspace_id=workspace_id,
                    metric="api_calls",
                    count=1,
                    metadata={
                        "endpoint": request.url.path,
                        "method": request.method,
                        "user_id": user.id,
                        "status_code": response.status_code,
                    },
                )
                logger.debug(f"Tracked API usage for workspace {workspace_id}")
            except Exception as e:
                # Don't fail the request if usage tracking fails
                logger.error(f"Failed to track usage: {e}")

        return response


async def track_custom_usage(
    workspace_id: str, metric: str, count: int = 1, metadata: dict[str, Any] | None = None
) -> bool:
    """
    Track custom usage metrics.

    Args:
        workspace_id: Workspace ID
        metric: Metric name (e.g., 'storage_gb', 'bandwidth_gb')
        count: Usage count
        metadata: Additional metadata

    Returns:
        True if tracking was successful
    """
    try:
        platform_client = get_platform_client()
        result = await platform_client.track_usage(
            workspace_id=workspace_id, metric=metric, count=count, metadata=metadata
        )
        return result is not None and result.get("allowed", False)
    except Exception as e:
        logger.error(f"Failed to track custom usage: {e}")
        return False


async def check_usage_limit(
    workspace_id: str, metric: str, requested_count: int = 1
) -> tuple[bool, dict[str, Any] | None]:
    """
    Check if usage would exceed limits.

    Args:
        workspace_id: Workspace ID
        metric: Metric name
        requested_count: Amount to check

    Returns:
        Tuple of (allowed, usage_info)
    """
    try:
        platform_client = get_platform_client()
        result = await platform_client.check_usage(
            workspace_id=workspace_id, metric=metric, count=requested_count
        )

        if result:
            allowed = result.get("allowed", False)
            return allowed, result

        # If check fails, assume allowed to not block operations
        return True, None
    except Exception as e:
        logger.error(f"Failed to check usage limit: {e}")
        # On error, allow the operation
        return True, None
