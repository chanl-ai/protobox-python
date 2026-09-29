"""Example service showing how to use InternalAPIClient for billing-aware operations."""

from typing import Any

from loguru import logger

from ..clients.internal_api_client import InternalAPIClient


class BillingAwareActionService:
    """Example service that checks billing limits before executing actions."""

    def __init__(self):
        """Initialize the service with internal API client."""
        self.internal_api = InternalAPIClient()

    async def create_action_with_billing_check(
        self, workspace_id: str, action_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create an action after checking billing limits.

        Args:
            workspace_id: The workspace ID
            action_data: The action data to create

        Returns:
            Created action data or error response

        Raises:
            HTTPException: If billing limits exceeded
        """
        # Check billing limits first
        billing_check = await self.internal_api.check_billing_limits(workspace_id)

        if not billing_check["can_proceed"]:
            logger.warning(
                f"Billing limit exceeded for workspace {workspace_id}: {billing_check['reason']}"
            )
            return {
                "error": "Billing limit exceeded",
                "reason": billing_check["reason"],
                "usage": billing_check.get("usage"),
                "limits": billing_check.get("limits"),
            }

        # Create the action (simplified for example)
        # In real implementation, this would use ActionService
        created_action = {
            "id": "action_123",
            "workspace_id": workspace_id,
            "name": action_data.get("name"),
            "type": action_data.get("type"),
            "status": "active",
        }

        # Update usage metrics
        await self.internal_api.update_usage(workspace_id, {"api_requests": 1})

        return {
            "action": created_action,
            "billing": {
                "plan": billing_check.get("plan", "free"),
                "usage": billing_check.get("usage"),
                "limits": billing_check.get("limits"),
            },
        }

    async def execute_action_with_billing_check(
        self, workspace_id: str, action_id: str, input_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute an action after checking billing limits.

        Args:
            workspace_id: The workspace ID
            action_id: The action ID to execute
            input_data: Input data for the action

        Returns:
            Execution result or error response
        """
        # Check billing limits
        billing_check = await self.internal_api.check_billing_limits(workspace_id)

        if not billing_check["can_proceed"]:
            return {
                "error": "Billing limit exceeded",
                "reason": billing_check["reason"],
                "usage": billing_check.get("usage"),
                "limits": billing_check.get("limits"),
            }

        # Get workspace info for context
        workspace = await self.internal_api.get_workspace(workspace_id)
        if not workspace:
            return {"error": "Workspace not found"}

        # Execute action (simplified for example)
        execution_result = {
            "id": "exec_123",
            "action_id": action_id,
            "workspace_id": workspace_id,
            "status": "completed",
            "result": {"message": "Action executed successfully"},
            "workspace_context": {
                "name": workspace.get("name"),
                "ai_model": workspace.get("settings", {}).get("aiModel", "gpt-4"),
            },
        }

        # Update usage
        await self.internal_api.update_usage(
            workspace_id, {"api_requests": 1, "chat_messages": 1 if "chat" in action_id else 0}
        )

        return execution_result

    async def get_workspace_context(self, workspace_id: str) -> dict[str, Any] | None:
        """Get workspace context including user and billing info.

        Args:
            workspace_id: The workspace ID

        Returns:
            Workspace context dictionary
        """
        # Get workspace info
        workspace = await self.internal_api.get_workspace(workspace_id)
        if not workspace:
            return None

        # Get billing info
        billing_info = await self.internal_api.get_billing_info(workspace_id)

        # Get owner info
        owner_info = None
        owner_id = workspace.get("owner_id")
        if owner_id:
            owner_info = await self.internal_api.get_user(owner_id)

        return {
            "workspace": {
                "id": workspace.get("_id"),
                "name": workspace.get("name"),
                "settings": workspace.get("settings"),
                "members": len(workspace.get("members", [])),
            },
            "owner": (
                {
                    "id": owner_info.get("_id") if owner_info else None,
                    "email": owner_info.get("email") if owner_info else None,
                    "displayName": owner_info.get("displayName") if owner_info else None,
                }
                if owner_info
                else None
            ),
            "billing": (
                {
                    "plan": (
                        billing_info.get("subscription", {}).get("plan", "free")
                        if billing_info
                        else "free"
                    ),
                    "usage": billing_info.get("usage", {}) if billing_info else {},
                    "limits": billing_info.get("limits", {}) if billing_info else {},
                }
                if billing_info
                else None
            ),
        }

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.internal_api.close()
