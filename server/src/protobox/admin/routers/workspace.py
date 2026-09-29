"""Workspace router that enforces workspace-scoped routes and access control."""

import logging

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer

from ..auth.dependencies import require_authentication
from ..auth.models import User

logger = logging.getLogger(__name__)

# Create workspace router with workspace_id in path
workspace_router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["workspace"])

# Security scheme
security = HTTPBearer(auto_error=False)


async def verify_workspace_access(
    request: Request, workspace_id: str, current_user: User = Depends(require_authentication)
) -> tuple[str, str]:
    """
    Verify user has access to the workspace and return (user_id, workspace_id).
    This replaces get_current_user and get_current_workspace_id dependencies.
    """
    # Validate workspace_id is a valid ObjectId
    try:
        ObjectId(workspace_id)
    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid workspace ID format"
        )

    # SECURITY: Verify user has access to the workspace
    from ..database.connection import get_database_connection

    # Check if workspace exists and user has access
    db = get_database_connection()
    workspace = await db.database["workspaces"].find_one({
        "_id": ObjectId(workspace_id),
        "$or": [
            {"owner_id": current_user.id},
            {"members.user_id": current_user.id}
        ]
    })
    
    if not workspace:
        logger.warning(f"User {current_user.id} denied access to workspace {workspace_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Access denied: You don't have permission to access this workspace"
        )
    
    logger.debug(f"User {current_user.id} granted access to workspace {workspace_id}")
    return current_user.id, workspace_id


# Simplified dependencies that extract from the verified tuple
async def get_current_user(
    user_and_workspace: tuple[str, str] = Depends(verify_workspace_access),
) -> str:
    """Get current user ID from verified access."""
    return user_and_workspace[0]


async def get_workspace_id(
    user_and_workspace: tuple[str, str] = Depends(verify_workspace_access),
) -> str:
    """Get workspace ID from verified access."""
    return user_and_workspace[1]


# Import the adapter for feature flag support
from ..models.workspace import Workspace
from ..services.workspace_service_adapter import get_workspace_adapter


@workspace_router.get("/info", response_model=Workspace, summary="Get workspace information")
async def get_workspace_info(
    workspace_id: str = Depends(get_workspace_id), user_id: str = Depends(get_current_user)
):
    """
    Get workspace information using the feature-flagged service adapter.

    This endpoint demonstrates the Client-Side Isolation Architecture feature flag:
    - When use_client_side_isolation=true: Uses Next.js internal APIs
    - When use_client_side_isolation=false: Uses direct MongoDB access
    """
    try:
        # Use the service adapter which respects the feature flag
        adapter = get_workspace_adapter()
        workspace = await adapter.get_workspace(workspace_id)

        if not workspace:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

        # Verify user has access (additional security check)
        has_access = await adapter.check_user_workspace_access(user_id, workspace_id)
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this workspace"
            )

        return workspace

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workspace info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workspace information",
        )


# Re-export for convenience
__all__ = ["workspace_router", "verify_workspace_access", "get_current_user", "get_workspace_id"]
