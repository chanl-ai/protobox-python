"""
Example of how to use the usage tracking system in ProtoBox.

This shows how to:
1. Add usage tracking middleware to FastAPI
2. Track custom usage metrics
3. Check usage limits before operations
"""

import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from loguru import logger

from .auth.dependencies import require_authentication
from .auth.models import User
from .middleware.usage_tracking import (
    UsageTrackingMiddleware,
    check_usage_limit,
    track_custom_usage,
)


# Example: Adding middleware to FastAPI app
def setup_usage_tracking(app: FastAPI):
    """Add usage tracking middleware to the app."""
    app.add_middleware(UsageTrackingMiddleware, exclude_paths={"/health", "/docs", "/openapi.json"})


# Example: Track custom usage in an endpoint
async def upload_file_endpoint(
    file_size_mb: float, current_user: User = Depends(require_authentication)
):
    """Example endpoint that tracks storage usage."""
    workspace_id = current_user.metadata.get("workspace_id")

    if not workspace_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No workspace context")

    # Check if upload would exceed storage limit
    allowed, usage_info = await check_usage_limit(
        workspace_id=workspace_id,
        metric="storage_gb",
        requested_count=file_size_mb / 1024,  # Convert MB to GB
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Storage limit exceeded. Current: {usage_info.get('current_usage', 0)}GB, "
            f"Limit: {usage_info.get('limit', 0)}GB",
        )

    # Perform the upload operation here...

    # Track the storage usage
    success = await track_custom_usage(
        workspace_id=workspace_id,
        metric="storage_gb",
        count=file_size_mb / 1024,
        metadata={
            "operation": "file_upload",
            "file_size_mb": file_size_mb,
            "user_id": current_user.id,
        },
    )

    if not success:
        # Log warning but don't fail the operation
        logger.warning(f"Failed to track storage usage for workspace {workspace_id}")

    return {"message": "File uploaded successfully"}


# Example: Track bandwidth usage
async def download_file_endpoint(
    file_id: str, current_user: User = Depends(require_authentication)
):
    """Example endpoint that tracks bandwidth usage."""
    workspace_id = current_user.metadata.get("workspace_id")

    if not workspace_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No workspace context")

    # Get file size (mock)
    file_size_mb = 100  # In real app, get from database

    # Check bandwidth limit
    allowed, usage_info = await check_usage_limit(
        workspace_id=workspace_id, metric="bandwidth_gb", requested_count=file_size_mb / 1024
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Bandwidth limit exceeded. Current: {usage_info.get('current_usage', 0)}GB, "
            f"Limit: {usage_info.get('limit', 0)}GB",
        )

    # Stream file here...

    # Track bandwidth usage
    await track_custom_usage(
        workspace_id=workspace_id,
        metric="bandwidth_gb",
        count=file_size_mb / 1024,
        metadata={
            "operation": "file_download",
            "file_id": file_id,
            "file_size_mb": file_size_mb,
            "user_id": current_user.id,
        },
    )

    return {"message": "File download started"}


# Helper function for batch processing example
async def process_item(item: dict) -> dict:
    """Process a single item (mock implementation)."""
    # Simulate some processing
    return {"processed": True, "id": item.get("id")}


# Example: Batch operations with usage tracking
@asynccontextmanager
async def track_batch_operation(workspace_id: str, operation_name: str):
    """Context manager for tracking batch operations."""
    start_time = time.time()
    operation_count = 0

    try:
        yield operation_count
    finally:
        # Track the batch operation
        duration = time.time() - start_time
        await track_custom_usage(
            workspace_id=workspace_id,
            metric="api_calls",
            count=operation_count,
            metadata={
                "operation": operation_name,
                "duration_seconds": duration,
                "items_processed": operation_count,
            },
        )


# Usage in a batch endpoint
async def batch_process_endpoint(
    items: list[dict], current_user: User = Depends(require_authentication)
):
    """Example batch processing with usage tracking."""
    workspace_id = current_user.metadata.get("workspace_id")

    if not workspace_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No workspace context")

    # Check if batch size is within limits
    allowed, usage_info = await check_usage_limit(
        workspace_id=workspace_id, metric="api_calls", requested_count=len(items)
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"API call limit would be exceeded. Remaining: {usage_info.get('remaining', 0)}",
        )

    results = []
    async with track_batch_operation(workspace_id, "batch_process") as counter:
        for item in items:
            # Process each item
            result = await process_item(item)
            results.append(result)
            counter += 1

    return {"results": results, "processed": len(results)}


# Example: Rate limiting based on usage
from functools import wraps


def rate_limit_by_usage(metric: str, max_per_minute: int = 60):
    """Decorator to rate limit based on usage metrics."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User = None, **kwargs):
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
                )

            workspace_id = current_user.metadata.get("workspace_id")
            if not workspace_id:
                return await func(*args, current_user=current_user, **kwargs)

            # Check recent usage (you'd implement this with Redis or similar)
            # For now, just check if under limit
            allowed, usage_info = await check_usage_limit(
                workspace_id=workspace_id, metric=metric, requested_count=1
            )

            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded for {metric}",
                )

            return await func(*args, current_user=current_user, **kwargs)

        return wrapper

    return decorator


# Use the rate limiter
@rate_limit_by_usage(metric="api_calls", max_per_minute=60)
async def rate_limited_endpoint(current_user: User = Depends(require_authentication)):
    """Example endpoint with usage-based rate limiting."""
    return {"message": "Request processed"}
