"""Team-based authorization middleware for workspace operations."""


from bson import ObjectId
from fastapi import Depends, HTTPException, status

from ..auth.dependencies import get_current_user, get_service_context, require_authentication
from ..auth.models import ServiceContext, User
from ..database.connection import get_database_connection
from ..database.repositories.team_member_repository import TeamMemberRepository
from ..models.team_member import MemberRole, WorkspaceMember


class TeamAuthService:
    """Service for team-based authorization checks."""

    def __init__(self, team_member_repo: TeamMemberRepository):
        self.team_member_repo = team_member_repo

    async def get_workspace_member(
        self, workspace_id: ObjectId, user_id: str
    ) -> WorkspaceMember | None:
        """Get workspace member for user."""
        return await self.team_member_repo.get_member_by_workspace_and_user(workspace_id, user_id)

    async def verify_workspace_access(
        self, workspace_id: ObjectId, user_id: str, min_role: MemberRole | None = None
    ) -> WorkspaceMember:
        """
        Verify user has access to workspace with optional minimum role requirement.
        
        Args:
            workspace_id: Workspace to check access for
            user_id: User to verify
            min_role: Minimum role required (optional)
            
        Returns:
            WorkspaceMember object if authorized
            
        Raises:
            HTTPException: If access denied
        """
        member = await self.get_workspace_member(workspace_id, user_id)

        # Fallback: Check legacy workspace structure if team member not found
        if not member:
            from datetime import datetime
            import logging
            
            logger = logging.getLogger(__name__)
            db = get_database_connection().database
            
            # Check legacy workspace structure
            workspace = await db.workspaces.find_one({"_id": workspace_id})
            
            if workspace:
                # Get user details once
                user_doc = await db.users.find_one({"firebase_uid": user_id})
                user_email = user_doc.get("email") if user_doc else None
                display_name = user_doc.get("displayName") if user_doc else (user_email.split("@")[0] if user_email else f"user-{user_id}")
                
                # Check if user is owner
                if workspace.get("owner_id") == user_id:
                    # Auto-create team member for legacy workspace owner
                    logger.info(f"Auto-creating team member for legacy workspace owner: {user_id}")
                    
                    # Create team member record
                    workspace_member = WorkspaceMember(
                        workspace_id=workspace_id,
                        user_id=user_id,
                        email=user_email or "",
                        display_name=display_name,
                        role=MemberRole.OWNER,
                        invited_by=None,
                        joined_at=datetime.utcnow(),
                    )
                    
                    member = await self.team_member_repo.create_member(workspace_member)
                else:
                    # Check if user is in members array
                    members = workspace.get("members", [])
                    for m in members:
                        if m.get("user_id") == user_id:
                            # Auto-create team member for legacy workspace member
                            logger.info(f"Auto-creating team member for legacy workspace member: {user_id}")
                            
                            # Map legacy role to MemberRole
                            legacy_role = m.get("role", "member").lower()
                            if legacy_role == "owner":
                                member_role = MemberRole.OWNER
                            elif legacy_role == "admin":
                                member_role = MemberRole.ADMIN
                            else:
                                member_role = MemberRole.MEMBER
                            
                            # Create team member record
                            workspace_member = WorkspaceMember(
                                workspace_id=workspace_id,
                                user_id=user_id,
                                email=user_email or "",
                                display_name=display_name,
                                role=member_role,
                                invited_by=m.get("invited_by"),
                                joined_at=m.get("joined_at", datetime.utcnow()),
                            )
                            
                            member = await self.team_member_repo.create_member(workspace_member)
                            break

        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this workspace"
            )

        if min_role:
            role_hierarchy = WorkspaceMember.get_role_hierarchy()
            if role_hierarchy[member.role] < role_hierarchy[min_role]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Minimum role required: {min_role.value}"
                )

        return member

    async def verify_permission(
        self, workspace_id: ObjectId, user_id: str, permission: str
    ) -> WorkspaceMember:
        """
        Verify user has specific permission in workspace.
        
        Args:
            workspace_id: Workspace to check permission for
            user_id: User to verify
            permission: Permission to check (e.g., 'can_invite', 'can_remove')
            
        Returns:
            WorkspaceMember object if authorized
            
        Raises:
            HTTPException: If permission denied
        """
        member = await self.get_workspace_member(workspace_id, user_id)

        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this workspace"
            )

        # Check if member has the required permission
        if not getattr(member.permissions, permission, False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have permission: {permission}"
            )

        return member

    async def get_user_workspaces(self, user_id: str) -> list[WorkspaceMember]:
        """
        Get all workspaces where user is a member.

        Args:
            user_id: User to get workspaces for

        Returns:
            List of WorkspaceMember objects for all user's workspaces
        """
        return await self.team_member_repo.get_workspaces_by_user(user_id)


async def get_team_auth_service() -> TeamAuthService:
    """Dependency to get TeamAuthService instance."""
    db = get_database_connection().database
    team_member_repo = TeamMemberRepository(db)
    return TeamAuthService(team_member_repo)


class WorkspaceRole:
    """Dependency class for role-based authorization."""

    def __init__(self, min_role: MemberRole):
        self.min_role = min_role

    async def __call__(
        self,
        workspace_id: str,
        current_user: User = Depends(require_authentication),
        team_auth: TeamAuthService = Depends(get_team_auth_service)
    ) -> WorkspaceMember:
        """Verify user has minimum role in workspace."""
        try:
            workspace_obj_id = ObjectId(workspace_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid workspace ID format"
            )

        return await team_auth.verify_workspace_access(
            workspace_obj_id, current_user.id, self.min_role
        )


class WorkspacePermission:
    """Dependency class for permission-based authorization."""

    def __init__(self, permission: str):
        self.permission = permission

    async def __call__(
        self,
        workspace_id: str,
        current_user: User = Depends(require_authentication),
        team_auth: TeamAuthService = Depends(get_team_auth_service)
    ) -> WorkspaceMember:
        """Verify user has specific permission in workspace."""
        try:
            workspace_obj_id = ObjectId(workspace_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid workspace ID format"
            )

        return await team_auth.verify_permission(
            workspace_obj_id, current_user.id, self.permission
        )


# Common role dependencies
require_workspace_member = WorkspaceRole(MemberRole.MEMBER)
require_workspace_admin = WorkspaceRole(MemberRole.ADMIN)
require_workspace_owner = WorkspaceRole(MemberRole.OWNER)

# Common permission dependencies
require_invite_permission = WorkspacePermission("can_invite")
require_remove_permission = WorkspacePermission("can_remove")
require_role_management_permission = WorkspacePermission("can_manage_roles")
require_workspace_management_permission = WorkspacePermission("can_manage_workspace")


async def require_workspace_access(
    workspace_id: str,
    current_user: User | None = Depends(get_current_user),
    service_context: ServiceContext | None = Depends(get_service_context),
    team_auth: TeamAuthService = Depends(get_team_auth_service)
) -> WorkspaceMember | ServiceContext:
    """
    Workspace access requirement - accepts EITHER user auth OR service auth.

    Returns WorkspaceMember for user auth, ServiceContext for service auth.
    """
    try:
        workspace_obj_id = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID format"
        )

    # Service auth - skip workspace membership check
    if service_context:
        has_workspace_scope = any(
            scope.startswith("workspace:") or scope == "*"
            for scope in service_context.scopes
        )
        if not has_workspace_scope:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Service does not have workspace access permissions"
            )
        return service_context

    # User auth - validate workspace membership
    if current_user:
        return await team_auth.verify_workspace_access(workspace_obj_id, current_user.id)

    # Neither auth provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide either JWT token or service API key.",
        headers={"WWW-Authenticate": "Bearer"}
    )


async def require_workspace_access_flexible(
    workspace_id: str,
    current_user: User | None = Depends(get_current_user),
    service_context: ServiceContext | None = Depends(get_service_context),
    team_auth: TeamAuthService = Depends(get_team_auth_service)
) -> WorkspaceMember | ServiceContext:
    """
    Flexible workspace access that accepts EITHER user auth OR service auth.

    For user authentication:
    - Validates workspace membership
    - Returns WorkspaceMember object

    For service authentication:
    - Skips workspace membership check
    - Validates service scopes include workspace:* permissions
    - Returns ServiceContext object

    Args:
        workspace_id: Workspace to access
        current_user: Optional user from JWT/API key
        service_context: Optional service from service API key
        team_auth: Team authorization service

    Returns:
        WorkspaceMember if user auth, ServiceContext if service auth

    Raises:
        HTTPException: If neither auth provided or invalid
    """
    try:
        workspace_obj_id = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID format"
        )

    # If service key provided, validate and return service context
    if service_context:
        # Check if service has workspace access scopes
        has_workspace_scope = any(
            scope.startswith("workspace:") or scope == "*"
            for scope in service_context.scopes
        )

        if not has_workspace_scope:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Service does not have workspace access permissions"
            )

        return service_context

    # If user provided, validate workspace membership
    if current_user:
        return await team_auth.verify_workspace_access(workspace_obj_id, current_user.id)

    # Neither user nor service auth provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide either JWT token or service API key.",
        headers={"WWW-Authenticate": "Bearer"}
    )


async def can_manage_member_role(
    workspace_id: str,
    target_user_id: str,
    new_role: MemberRole,
    current_user: User = Depends(require_authentication),
    team_auth: TeamAuthService = Depends(get_team_auth_service)
) -> tuple[WorkspaceMember, WorkspaceMember]:
    """
    Check if current user can manage target member's role.
    
    Returns:
        Tuple of (requester_member, target_member)
    """
    try:
        workspace_obj_id = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID format"
        )

    # Get requester member
    requester_member = await team_auth.verify_workspace_access(workspace_obj_id, current_user.id)

    # Get target member
    target_member = await team_auth.get_workspace_member(workspace_obj_id, target_user_id)
    if not target_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target member not found in workspace"
        )

    # Check if requester can manage roles
    if not requester_member.permissions.can_manage_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage roles"
        )

    # Check specific role management rules
    role_hierarchy = WorkspaceMember.get_role_hierarchy()

    # Cannot change own role
    if requester_member.user_id == target_member.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change your own role"
        )

    # Cannot change owner role
    if target_member.role == MemberRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change owner role"
        )

    # Owners can change anyone's role (except other owners)
    if requester_member.role == MemberRole.OWNER:
        if target_member.role == MemberRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot change another owner's role"
            )
        return requester_member, target_member

    # Admins can only change members' roles
    if requester_member.role == MemberRole.ADMIN:
        if target_member.role != MemberRole.MEMBER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admins can only change member roles"
            )

        # Admins cannot promote to owner
        if new_role == MemberRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot promote to owner role"
            )

        return requester_member, target_member

    # Members cannot change roles
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions to manage roles"
    )


async def can_remove_member(
    workspace_id: str,
    target_user_id: str,
    current_user: User = Depends(require_authentication),
    team_auth: TeamAuthService = Depends(get_team_auth_service)
) -> tuple[WorkspaceMember, WorkspaceMember]:
    """
    Check if current user can remove target member.
    
    Returns:
        Tuple of (requester_member, target_member)
    """
    try:
        workspace_obj_id = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID format"
        )

    # Get requester member
    requester_member = await team_auth.verify_workspace_access(workspace_obj_id, current_user.id)

    # Get target member
    target_member = await team_auth.get_workspace_member(workspace_obj_id, target_user_id)
    if not target_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target member not found in workspace"
        )

    # Check if requester can remove members
    if not requester_member.can_remove_member(target_member.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to remove this member"
        )

    # Cannot remove self (members should leave, not be removed)
    if requester_member.user_id == target_member.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot remove yourself from workspace"
        )

    return requester_member, target_member
