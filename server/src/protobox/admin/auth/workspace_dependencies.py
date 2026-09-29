"""
Workspace-specific authentication dependencies.

This module provides middleware-style dependency injection for workspace-based
authorization, eliminating the need for manual workspace.members checking
in every endpoint.
"""

from dataclasses import dataclass
from typing import Optional, Set

from bson import ObjectId
from fastapi import Depends, HTTPException, Path, status
from loguru import logger

from ..models.workspace import Workspace
from ..database.repositories.team_member_repository import TeamMemberRepository
from .dependencies import require_authentication
from .models import User


@dataclass
class WorkspaceAccess:
    """
    Workspace access context containing pre-validated user permissions.

    This eliminates the need for manual workspace.members checking in endpoints.
    """
    workspace_id: str
    workspace: Workspace
    user_id: str
    user_role: str  # "owner", "admin", "member", "viewer"
    permissions: Set[str]

    @property
    def is_owner(self) -> bool:
        """Check if user is workspace owner."""
        return self.user_role == "owner"

    @property
    def is_admin_or_owner(self) -> bool:
        """Check if user has admin or owner privileges."""
        return self.user_role in ["owner", "admin"]

    @property
    def can_read(self) -> bool:
        """Check if user can read workspace resources."""
        return self.user_role in ["owner", "admin", "member", "viewer"]

    @property
    def can_write(self) -> bool:
        """Check if user can modify workspace resources."""
        return self.user_role in ["owner", "admin", "member"]

    @property
    def can_admin(self) -> bool:
        """Check if user can perform admin operations."""
        return self.user_role in ["owner", "admin"]


async def _get_workspace_access(
    workspace_id: str,
    current_user: User,
    required_role: Optional[str] = None
) -> WorkspaceAccess:
    """
    Internal function to get workspace access context.

    Args:
        workspace_id: Workspace ID from path parameter
        current_user: Authenticated user
        required_role: Minimum required role (owner, admin, member, viewer)

    Returns:
        WorkspaceAccess object with pre-validated permissions

    Raises:
        HTTPException: If workspace not found or access denied
    """
    try:
        workspace_obj_id = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID format"
        )

    # Get workspace using repository pattern (follows CLAUDE.md architecture)
    from ..services.workspace_service import WorkspaceService
    from motor.motor_asyncio import AsyncIOMotorDatabase
    from ..database.connection import get_database_connection

    db_conn = get_database_connection()
    db: AsyncIOMotorDatabase = db_conn.database
    workspace_service = WorkspaceService(db_conn)

    try:
        workspace = await workspace_service.get_workspace(workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
    except Exception as e:
        logger.error(f"Error fetching workspace {workspace_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error accessing workspace"
        )

    # Get user's role in workspace using TeamMemberRepository
    team_repo = TeamMemberRepository(db)
    logger.info(f"Looking for member with workspace_id={workspace_obj_id}, user_id={current_user.id}")
    member = await team_repo.get_member_by_workspace_and_user(workspace_obj_id, current_user.id)
    logger.info(f"Found member: {member}")

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied - not a member of this workspace"
        )

    user_role = member.role

    # Check minimum required role
    role_hierarchy = ["viewer", "member", "admin", "owner"]
    if required_role:
        if required_role not in role_hierarchy:
            raise ValueError(f"Invalid required role: {required_role}")

        required_level = role_hierarchy.index(required_role)
        user_level = role_hierarchy.index(user_role) if user_role in role_hierarchy else -1

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied - {required_role} role required"
            )

    # Compute permissions based on role
    permissions = set()
    if user_role in ["viewer", "member", "admin", "owner"]:
        permissions.add("read")
    if user_role in ["member", "admin", "owner"]:
        permissions.add("write")
    if user_role in ["admin", "owner"]:
        permissions.add("admin")
    if user_role == "owner":
        permissions.add("owner")

    return WorkspaceAccess(
        workspace_id=workspace_id,
        workspace=workspace,
        user_id=current_user.id,
        user_role=user_role,
        permissions=permissions
    )


async def require_workspace_access(
    workspace_id: str = Path(..., description="Workspace ID"),
    current_user: User = Depends(require_authentication)
) -> WorkspaceAccess:
    """
    Require any level of workspace access (viewer, member, admin, owner).

    Usage:
        async def get_workspace_info(
            workspace_access: WorkspaceAccess = Depends(require_workspace_access)
        ):
            return workspace_access.workspace
    """
    return await _get_workspace_access(workspace_id, current_user, required_role="viewer")


async def require_workspace_member(
    workspace_id: str = Path(..., description="Workspace ID"),
    current_user: User = Depends(require_authentication)
) -> WorkspaceAccess:
    """
    Require workspace member access or higher (member, admin, owner).

    Usage:
        async def create_action(
            action_data: ActionCreate,
            workspace_access: WorkspaceAccess = Depends(require_workspace_member)
        ):
            # User has member+ access to workspace_access.workspace
    """
    return await _get_workspace_access(workspace_id, current_user, required_role="member")


async def require_workspace_admin(
    workspace_id: str = Path(..., description="Workspace ID"),
    current_user: User = Depends(require_authentication)
) -> WorkspaceAccess:
    """
    Require workspace admin access or higher (admin, owner).

    Usage:
        async def update_workspace(
            update_data: WorkspaceUpdate,
            workspace_access: WorkspaceAccess = Depends(require_workspace_admin)
        ):
            # User has admin+ access to workspace_access.workspace
    """
    return await _get_workspace_access(workspace_id, current_user, required_role="admin")


async def require_workspace_owner(
    workspace_id: str = Path(..., description="Workspace ID"),
    current_user: User = Depends(require_authentication)
) -> WorkspaceAccess:
    """
    Require workspace owner access.

    Usage:
        async def delete_workspace(
            workspace_access: WorkspaceAccess = Depends(require_workspace_owner)
        ):
            # User is owner of workspace_access.workspace
    """
    return await _get_workspace_access(workspace_id, current_user, required_role="owner")


# Legacy compatibility - for endpoints that need explicit user object
async def get_workspace_and_user(
    workspace_id: str = Path(..., description="Workspace ID"),
    current_user: User = Depends(require_authentication)
) -> tuple[Workspace, User]:
    """
    Legacy compatibility function returning workspace and user separately.

    DEPRECATED: Use require_workspace_* dependencies instead.
    """
    workspace_access = await _get_workspace_access(workspace_id, current_user, required_role="viewer")
    return workspace_access.workspace, current_user