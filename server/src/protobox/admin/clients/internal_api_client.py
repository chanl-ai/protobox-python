"""Internal API client for accessing Next.js internal APIs."""

import os
from typing import Any

import httpx
from loguru import logger


class InternalAPIClient:
    """Client for accessing Next.js internal APIs for user/workspace/billing data."""

    def __init__(self, base_url: str = None, api_key: str = None):
        """Initialize the internal API client.

        Args:
            base_url: Base URL for the Next.js server (defaults to env var or localhost)
            api_key: Internal API key for authentication (defaults to env var)
        """
        self.base_url = base_url or os.getenv("NEXTJS_INTERNAL_API_URL", "http://localhost:3001")
        self.api_key = api_key or os.getenv(
            "INTERNAL_API_KEY", ""
        )
        self.client = httpx.AsyncClient(
            headers={"x-internal-api-key": self.api_key, "Content-Type": "application/json"},
            timeout=30.0,
        )

    async def get_user(self, user_id: str) -> dict[str, Any] | None:
        """Get user information from Next.js internal API.

        Args:
            user_id: MongoDB ObjectId of the user

        Returns:
            User data dictionary or None if not found
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/internal/users/{user_id}")
            if response.status_code == 200:
                return response.json()
            if response.status_code == 404:
                logger.warning(f"User {user_id} not found")
                return None
            logger.error(
                f"Failed to get user {user_id}: {response.status_code} - {response.text}"
            )
            return None
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None

    async def update_user(self, user_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Update user information via Next.js internal API.

        Args:
            user_id: MongoDB ObjectId of the user
            updates: Dictionary of fields to update

        Returns:
            Updated user data or None if failed
        """
        try:
            response = await self.client.patch(
                f"{self.base_url}/api/internal/users/{user_id}", json=updates
            )
            if response.status_code == 200:
                return response.json()
            logger.error(
                f"Failed to update user {user_id}: {response.status_code} - {response.text}"
            )
            return None
        except Exception as e:
            logger.error(f"Failed to update user {user_id}: {e}")
            return None

    async def get_workspace(self, workspace_id: str) -> dict[str, Any] | None:
        """Get workspace information from Next.js internal API.

        Args:
            workspace_id: MongoDB ObjectId of the workspace

        Returns:
            Workspace data dictionary or None if not found
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/internal/workspaces/{workspace_id}"
            )
            if response.status_code == 200:
                return response.json()
            if response.status_code == 404:
                logger.warning(f"Workspace {workspace_id} not found")
                return None
            logger.error(
                f"Failed to get workspace {workspace_id}: {response.status_code} - {response.text}"
            )
            return None
        except Exception as e:
            logger.error(f"Failed to get workspace {workspace_id}: {e}")
            return None

    async def update_workspace(
        self, workspace_id: str, updates: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Update workspace information via Next.js internal API.

        Args:
            workspace_id: MongoDB ObjectId of the workspace
            updates: Dictionary of fields to update

        Returns:
            Updated workspace data or None if failed
        """
        try:
            response = await self.client.patch(
                f"{self.base_url}/api/internal/workspaces/{workspace_id}", json=updates
            )
            if response.status_code == 200:
                return response.json()
            logger.error(
                f"Failed to update workspace {workspace_id}: {response.status_code} - {response.text}"
            )
            return None
        except Exception as e:
            logger.error(f"Failed to update workspace {workspace_id}: {e}")
            return None

    async def create_workspace(self, workspace_data: dict[str, Any]) -> dict[str, Any] | None:
        """Create a new workspace via Next.js internal API.

        Args:
            workspace_data: Dictionary with workspace creation data

        Returns:
            Created workspace data or None if failed
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/internal/workspaces", json=workspace_data
            )
            if response.status_code == 201:
                return response.json()
            logger.error(
                f"Failed to create workspace: {response.status_code} - {response.text}"
            )
            return None
        except Exception as e:
            logger.error(f"Failed to create workspace: {e}")
            return None

    async def get_billing_info(self, workspace_id: str) -> dict[str, Any] | None:
        """Get billing information from Next.js internal API.

        Args:
            workspace_id: MongoDB ObjectId of the workspace

        Returns:
            Billing info dictionary or None if not found
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/internal/billing/{workspace_id}")
            if response.status_code == 200:
                return response.json()
            logger.error(
                f"Failed to get billing info for workspace {workspace_id}: {response.status_code} - {response.text}"
            )
            return None
        except Exception as e:
            logger.error(f"Failed to get billing info for workspace {workspace_id}: {e}")
            return None

    async def update_usage(self, workspace_id: str, usage_data: dict[str, Any]) -> bool:
        """Update usage metrics via Next.js internal API.

        Args:
            workspace_id: MongoDB ObjectId of the workspace
            usage_data: Dictionary with usage metrics (api_requests, storage_mb, chat_messages)

        Returns:
            True if successful, False otherwise
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/internal/usage/{workspace_id}", json=usage_data
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to update usage for workspace {workspace_id}: {e}")
            return False

    async def check_billing_limits(self, workspace_id: str) -> dict[str, Any]:
        """Check if workspace can proceed based on billing limits.

        Args:
            workspace_id: MongoDB ObjectId of the workspace

        Returns:
            Dictionary with billing check results
        """
        billing_info = await self.get_billing_info(workspace_id)
        if not billing_info:
            return {"can_proceed": False, "reason": "Failed to fetch billing information"}

        usage = billing_info.get("usage", {})
        limits = billing_info.get("limits", {})

        # Check API request limits
        api_requests = usage.get("api_requests", 0)
        api_limit = limits.get("api_requests", -1)

        if api_limit != -1 and api_requests >= api_limit:
            return {
                "can_proceed": False,
                "reason": "API request limit exceeded",
                "usage": usage,
                "limits": limits,
            }

        # Check storage limits
        storage_mb = usage.get("storage_mb", 0)
        storage_limit = limits.get("storage_mb", -1)

        if storage_limit != -1 and storage_mb >= storage_limit:
            return {
                "can_proceed": False,
                "reason": "Storage limit exceeded",
                "usage": usage,
                "limits": limits,
            }

        # Check chat message limits
        chat_messages = usage.get("chat_messages", 0)
        chat_limit = limits.get("chat_messages", -1)

        if chat_limit != -1 and chat_messages >= chat_limit:
            return {
                "can_proceed": False,
                "reason": "Chat message limit exceeded",
                "usage": usage,
                "limits": limits,
            }

        return {
            "can_proceed": True,
            "usage": usage,
            "limits": limits,
            "plan": billing_info.get("subscription", {}).get("plan", "free"),
        }

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
