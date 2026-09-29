"""Workspace service adapter - always uses direct MongoDB."""

import logging
from typing import Any

from ..models.workspace import Workspace, WorkspaceCreate, WorkspaceUpdate
from ..services.workspace_service import WorkspaceService

logger = logging.getLogger(__name__)


class WorkspaceServiceAdapter:
    """Service adapter that uses direct MongoDB for all workspace operations."""

    def __init__(self):
        # Always use direct MongoDB service
        self.workspace_service = WorkspaceService()
        logger.info("Using direct MongoDB workspace service")

    async def get_workspace(self, workspace_id: str) -> Workspace | None:
        """Get workspace information."""
        return await self.workspace_service.get_workspace(workspace_id)

    async def update_workspace(
        self, workspace_id: str, updates: WorkspaceUpdate
    ) -> Workspace | None:
        """Update workspace information."""
        return await self.workspace_service.update_workspace(workspace_id, updates)

    async def create_workspace(self, workspace_data: WorkspaceCreate) -> Workspace:
        """Create a new workspace."""
        return await self.workspace_service.create_workspace(workspace_data)

    async def list_user_workspaces(self, user_id: str) -> list[Workspace]:
        """List workspaces for a user."""
        # Use list_workspaces with owner_id filter
        return await self.workspace_service.list_workspaces(owner_id=user_id)

    async def check_user_workspace_access(self, user_id: str, workspace_id: str) -> bool:
        """Check if user has access to workspace."""
        # Check if user owns the workspace or is a member
        workspace = await self.workspace_service.get_workspace(workspace_id)
        if not workspace:
            return False

        # Check if user is owner
        if workspace.owner_id == user_id:
            return True

        # Check if user is a member
        return await self.workspace_service.is_member(workspace_id, user_id)

    async def get_billing_info(self, workspace_id: str) -> dict[str, Any] | None:
        """Get billing information for workspace."""
        # Billing is handled separately, return None for now
        logger.debug("Billing info requested - returning None")
        return None

    async def update_usage(self, workspace_id: str, usage_data: dict[str, Any]) -> bool:
        """Update usage metrics."""
        # Usage tracking is handled separately, return True for now
        logger.debug("Usage update requested - returning True")
        return True

    async def check_billing_limits(self, workspace_id: str) -> dict[str, Any]:
        """Check billing limits for workspace."""
        # No billing limits in direct MongoDB mode
        return {"can_proceed": True, "reason": "Direct MongoDB mode - no billing limits"}

    async def close(self):
        """Close any open connections."""
        # Nothing to close in direct MongoDB mode
        pass


# Global adapter instance
_workspace_adapter = None


def get_workspace_adapter() -> WorkspaceServiceAdapter:
    """Get the global workspace service adapter instance."""
    global _workspace_adapter
    if _workspace_adapter is None:
        _workspace_adapter = WorkspaceServiceAdapter()
    return _workspace_adapter
