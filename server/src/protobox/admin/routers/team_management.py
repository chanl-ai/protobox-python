"""Team management router for workspace member operations."""

from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from ..auth.dependencies import require_authentication
from ..auth.models import User
from ..database.connection import get_database_connection
from ..database.repositories.team_member_repository import TeamMemberRepository
from ..database.repositories.workspace_invitation_repository import WorkspaceInvitationRepository
from ..middleware.team_auth import (
    can_manage_member_role,
    require_invite_permission,
    require_workspace_access,
)
from ..models.team_member import (
    UpdateMemberRoleRequest,
    UpdateMemberRoleResponse,
    WorkspaceMemberListResponse,
    WorkspaceMemberResponse,
)
from ..models.workspace_invitation import (
    CreateInvitationRequest,
    InvitationListResponse,
    InvitationResponse,
)
from ..services.audit_service import AuditService
from ..services.team_service import TeamService


def get_team_service() -> TeamService:
    """Get team service instance."""
    db = get_database_connection().database
    team_member_repo = TeamMemberRepository(db)
    invitation_repo = WorkspaceInvitationRepository(db)
    audit_service = AuditService(db)
    return TeamService(team_member_repo, invitation_repo, audit_service)


router = APIRouter()


@router.get(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberListResponse,
    summary="List workspace members",
    description="Get all members of a workspace with pagination support"
)
async def list_workspace_members(
    workspace_id: str,
    skip: int = Query(0, ge=0, description="Number of members to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of members to return"),
    member: User = Depends(require_workspace_access),
    team_service: TeamService = Depends(get_team_service),
) -> WorkspaceMemberListResponse:
    """List all members of a workspace."""
    try:
        workspace_obj_id = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID format"
        )

    try:
        members, total, pending_invites = await team_service.get_workspace_members(
            workspace_obj_id, member.id, skip, limit
        )

        member_responses = [
            WorkspaceMemberResponse(
                user_id=m.user_id,
                email=m.email,
                display_name=m.display_name,
                role=m.role.value,
                joined_at=m.joined_at,
                invited_by=m.invited_by,
                last_active=m.last_active
            )
            for m in members
        ]

        return WorkspaceMemberListResponse(
            members=member_responses,
            total=total,
            pending_invites=pending_invites
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing workspace members: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workspace members"
        )


@router.post(
    "/{workspace_id}/members/invite",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite team member",
    description="Send an invitation to join the workspace with specified role"
)
async def invite_team_member(
    workspace_id: str,
    invitation_request: CreateInvitationRequest,
    member: User = Depends(require_invite_permission),
    team_service: TeamService = Depends(get_team_service),
) -> InvitationResponse:
    """Invite a new member to the workspace."""
    try:
        workspace_obj_id = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID format"
        )

    try:
        invitation = await team_service.invite_member(
            workspace_obj_id, invitation_request, member.id, member.email
        )

        from ..config import settings

        invite_link = f"{settings.frontend_url.rstrip('/')}/invite/{invitation.token}"

        return InvitationResponse(
            invitation_id=str(invitation.id),
            email=invitation.email,
            role=invitation.role.value,
            expires_at=invitation.expires_at,
            invite_link=invite_link
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inviting team member: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send invitation"
        )


@router.patch(
    "/{workspace_id}/members/{user_id}/role",
    response_model=UpdateMemberRoleResponse,
    summary="Update member role",
    description="Change a member's role in the workspace"
)
async def update_member_role(
    workspace_id: str,
    user_id: str,
    role_update: UpdateMemberRoleRequest,
    auth_result: tuple = Depends(lambda workspace_id=..., user_id=..., role=...:
                                can_manage_member_role(workspace_id, user_id, role.role)),
    current_user: User = Depends(require_authentication),
    team_service: TeamService = Depends(get_team_service),
) -> UpdateMemberRoleResponse:
    """Update a member's role."""
    try:
        workspace_obj_id = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID format"
        )

    # This is a bit hacky due to FastAPI dependency limitations
    # We'll do the authorization check inside the endpoint
    try:
        # Import the dependency function directly
        from ..middleware.team_auth import can_manage_member_role as check_role_permission

        requester_member, target_member = await check_role_permission(
            workspace_id, user_id, role_update.role, current_user
        )

        updated_member = await team_service.update_member_role(
            workspace_obj_id, user_id, role_update.role, current_user.id, current_user.email
        )

        return UpdateMemberRoleResponse(
            user_id=updated_member.user_id,
            role=updated_member.role.value,
            updated_at=updated_member.updated_at or datetime.utcnow()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating member role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update member role"
        )


@router.delete(
    "/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove team member",
    description="Remove a member from the workspace"
)
async def remove_team_member(
    workspace_id: str,
    user_id: str,
    current_user: User = Depends(require_authentication),
    team_service: TeamService = Depends(get_team_service),
):
    """Remove a member from the workspace."""
    try:
        workspace_obj_id = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID format"
        )

    try:
        # Check permissions using the middleware function directly
        from ..middleware.team_auth import can_remove_member as check_remove_permission

        requester_member, target_member = await check_remove_permission(
            workspace_id, user_id, current_user
        )

        success = await team_service.remove_member(
            workspace_obj_id, user_id, current_user.id, current_user.email
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove member"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing team member: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove team member"
        )


@router.get(
    "/{workspace_id}/invitations",
    response_model=InvitationListResponse,
    summary="Get pending invitations",
    description="List all pending invitations for the workspace"
)
async def get_pending_invitations(
    workspace_id: str,
    member: User = Depends(require_workspace_access),
    team_service: TeamService = Depends(get_team_service),
) -> InvitationListResponse:
    """Get all pending invitations for a workspace."""
    try:
        workspace_obj_id = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID format"
        )

    try:
        invitations = await team_service.get_pending_invitations(
            workspace_obj_id, member.id
        )

        invitation_responses = []
        for invitation in invitations:
            invitation_responses.append({
                "invitation_id": str(invitation.id),
                "email": invitation.email,
                "role": invitation.role.value,
                "invited_by": invitation.invited_by,
                "invited_at": invitation.invited_at,
                "expires_at": invitation.expires_at,
                "status": invitation.status.value
            })

        return InvitationListResponse(invitations=invitation_responses)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pending invitations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve invitations"
        )


@router.delete(
    "/{workspace_id}/invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel invitation",
    description="Cancel a pending invitation"
)
async def cancel_invitation(
    workspace_id: str,
    invitation_id: str,
    member: User = Depends(require_invite_permission),
    team_service: TeamService = Depends(get_team_service),
):
    """Cancel a pending invitation."""
    try:
        workspace_obj_id = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID format"
        )

    try:
        success = await team_service.cancel_invitation(
            workspace_obj_id, invitation_id, member.id, member.email
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel invitation"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling invitation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel invitation"
        )
