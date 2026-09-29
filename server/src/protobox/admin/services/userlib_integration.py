"""
UserLib Integration Service

This service demonstrates how the Python backend can integrate with UserLib
(the user, workspace, and billing management system in Next.js) using
the InternalAPIClient pattern.
"""

import os
from typing import Any

import httpx
from loguru import logger


class InternalAPIClient:
    """Client for communicating with Next.js internal APIs"""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            headers={"Content-Type": "application/json", "x-internal-api-key": api_key},
            timeout=30.0,
        )

    async def get_user(self, user_id: str) -> dict[str, Any]:
        """Get user data from UserLib"""
        response = await self.client.get(f"{self.base_url}/api/internal/users/{user_id}")
        response.raise_for_status()
        return response.json()

    async def get_workspace(self, workspace_id: str) -> dict[str, Any]:
        """Get workspace data from UserLib"""
        response = await self.client.get(f"{self.base_url}/api/internal/workspaces/{workspace_id}")
        response.raise_for_status()
        return response.json()

    async def list_workspaces(self, user_id: str) -> list[dict[str, Any]]:
        """List all workspaces for a user"""
        response = await self.client.get(
            f"{self.base_url}/api/internal/workspaces?owner_id={user_id}"
        )
        response.raise_for_status()
        return response.json()

    async def get_billing_info(self, user_id: str) -> dict[str, Any]:
        """Get billing information for a user"""
        response = await self.client.get(f"{self.base_url}/api/internal/billing/{user_id}")
        response.raise_for_status()
        return response.json()

    async def update_usage(self, user_id: str, metric: str, quantity: int) -> dict[str, Any]:
        """Update usage metrics for billing"""
        response = await self.client.post(
            f"{self.base_url}/api/internal/billing/usage",
            json={"user_id": user_id, "metric": metric, "quantity": quantity},
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


class UserLibService:
    """Service for integrating with UserLib in Next.js"""

    def __init__(self):
        # Get configuration from environment
        self.client = InternalAPIClient(
            base_url=os.getenv("NEXTJS_URL", "http://localhost:3001"),
            api_key=os.getenv("INTERNAL_API_KEY", ""),
        )

    async def check_workspace_limits(self, workspace_id: str, metric: str) -> bool:
        """Check if workspace has capacity for more resources"""
        try:
            # Get workspace details
            workspace = await self.client.get_workspace(workspace_id)
            owner_id = workspace.get("owner_id")

            if not owner_id:
                logger.error(f"No owner_id found for workspace {workspace_id}")
                return False

            # Get billing info
            billing = await self.client.get_billing_info(owner_id)

            # Check limits
            usage = billing.get("usage", {})
            limits = billing.get("limits", {})

            current = usage.get(metric, 0)
            limit = limits.get(metric, 0)

            logger.info(f"Workspace {workspace_id} {metric}: {current}/{limit}")

            return current < limit

        except Exception as e:
            logger.error(f"Error checking workspace limits: {e}")
            return False

    async def track_api_usage(self, user_id: str, endpoint: str) -> None:
        """Track API usage for billing purposes"""
        try:
            await self.client.update_usage(user_id=user_id, metric="api_requests", quantity=1)
            logger.info(f"Tracked API usage for user {user_id} on {endpoint}")
        except Exception as e:
            logger.error(f"Error tracking API usage: {e}")

    async def get_workspace_context(self, workspace_id: str) -> dict[str, Any] | None:
        """Get full context for a workspace including user and billing info"""
        try:
            # Get workspace
            workspace = await self.client.get_workspace(workspace_id)

            # Get owner info
            owner_id = workspace.get("owner_id")
            if owner_id:
                user = await self.client.get_user(owner_id)
                billing = await self.client.get_billing_info(owner_id)

                return {"workspace": workspace, "user": user, "billing": billing}

            return {"workspace": workspace}

        except Exception as e:
            logger.error(f"Error getting workspace context: {e}")
            return None

    async def close(self):
        """Clean up resources"""
        await self.client.close()


# Example usage in FastAPI endpoints
"""
from fastapi import Depends, HTTPException
from .userlib_integration import UserLibService

async def get_userlib_service():
    service = UserLibService()
    try:
        yield service
    finally:
        await service.close()

@router.post("/actions")
async def create_action(
    workspace_id: str,
    action_data: dict,
    userlib: UserLibService = Depends(get_userlib_service)
):
    # Check if workspace has capacity for more actions
    if not await userlib.check_workspace_limits(workspace_id, "actions"):
        raise HTTPException(
            status_code=403,
            detail="Workspace has reached action limit. Please upgrade your plan."
        )

    # Create the action
    # ... your action creation logic ...

    # Track usage
    workspace_context = await userlib.get_workspace_context(workspace_id)
    if workspace_context:
        await userlib.track_api_usage(
            user_id=workspace_context["user"]["id"],
            endpoint="/actions"
        )

    return {"message": "Action created successfully"}
"""
