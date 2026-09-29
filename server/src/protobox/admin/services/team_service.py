"""Team management service for workspace member operations."""

from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException, status
from loguru import logger

from ..database.repositories.team_member_repository import TeamMemberRepository
from ..database.repositories.workspace_invitation_repository import WorkspaceInvitationRepository
from ..models.audit_log import AuditAction
from ..models.team_member import MemberRole, WorkspaceMember
from ..models.workspace_invitation import (
    CreateInvitationRequest,
    InvitationStatus,
    WorkspaceInvitation,
)
from .audit_service import AuditService
from .base_service import BaseService


class TeamService(BaseService):
    """Service for managing workspace teams and invitations."""

    def __init__(self, team_member_repo: TeamMemberRepository, invitation_repo: WorkspaceInvitationRepository, audit_service: AuditService):
        self.team_member_repo = team_member_repo
        self.invitation_repo = invitation_repo
        self.audit_service = audit_service

    async def get_workspace_members(
        self, workspace_id: ObjectId, requester_user_id: str, skip: int = 0, limit: int = 100
    ) -> tuple[list[WorkspaceMember], int, int]:
        """
        Get all members of a workspace with pagination.
        
        Returns:
            Tuple of (members, total_members, pending_invitations)
        """
        # Verify requester has access to workspace
        await self._verify_workspace_member(workspace_id, requester_user_id)

        # Get members with pagination
        members = await self.team_member_repo.get_members_by_workspace(workspace_id, skip, limit)
        total_members = await self.team_member_repo.count_members_by_workspace(workspace_id)
        pending_invitations = await self.invitation_repo.count_pending_invitations(workspace_id)

        return members, total_members, pending_invitations

    async def invite_member(
        self, workspace_id: ObjectId, invitation_request: CreateInvitationRequest, inviter_user_id: str, inviter_email: str
    ) -> WorkspaceInvitation:
        """Invite a new member to the workspace."""
        # Verify inviter has permission to invite
        inviter_member = await self._verify_workspace_member(workspace_id, inviter_user_id)
        if not inviter_member.permissions.can_invite:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to invite members"
            )

        # Check if user is already a member
        existing_member = await self.team_member_repo.get_member_by_email(workspace_id, invitation_request.email)
        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of this workspace"
            )

        # Check for existing pending invitation
        if await self.invitation_repo.has_pending_invitation(workspace_id, invitation_request.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="There is already a pending invitation for this email"
            )

        # Create invitation
        invitation = WorkspaceInvitation.create_invitation(
            workspace_id=workspace_id,
            email=invitation_request.email,
            role=invitation_request.role,
            invited_by=inviter_user_id
        )

        # Save invitation
        created_invitation = await self.invitation_repo.create_invitation(invitation)

        # Log audit event
        await self.audit_service.log_action(
            user_id=inviter_user_id,
            workspace_id=str(workspace_id),
            action=AuditAction.CREATE,
            resource_type="workspace_invitation",
            resource_id=str(created_invitation.id),
            user_email=inviter_email,
            metadata={
                "invited_email": invitation_request.email,
                "invited_role": invitation_request.role.value,
                "send_email": invitation_request.send_email
            }
        )

        logger.info(f"Member invited: {invitation_request.email} to workspace {workspace_id} by {inviter_user_id}")

        return created_invitation

    async def update_member_role(
        self, workspace_id: ObjectId, target_user_id: str, new_role: MemberRole,
        requester_user_id: str, requester_email: str
    ) -> WorkspaceMember:
        """Update a member's role."""
        # Verify requester has permission
        requester_member = await self._verify_workspace_member(workspace_id, requester_user_id)

        # Get target member
        target_member = await self.team_member_repo.get_member_by_workspace_and_user(workspace_id, target_user_id)
        if not target_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in workspace"
            )

        # Check permissions
        if not self._can_update_role(requester_member, target_member, new_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to change this member's role"
            )

        # Prevent changing owner role
        if target_member.role == MemberRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot change owner role"
            )

        # Update role
        old_role = target_member.role
        updated_member = await self.team_member_repo.update_member_role(
            workspace_id, target_user_id, new_role, requester_user_id
        )

        if not updated_member:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update member role"
            )

        # Log audit event
        await self.audit_service.log_action(
            user_id=requester_user_id,
            workspace_id=str(workspace_id),
            action=AuditAction.UPDATE,
            resource_type="workspace_member",
            resource_id=target_user_id,
            user_email=requester_email,
            changes={
                "role": {"old": old_role.value, "new": new_role.value}
            },
            metadata={
                "target_user_id": target_user_id,
                "target_email": target_member.email
            }
        )

        logger.info(f"Member role updated: {target_user_id} from {old_role.value} to {new_role.value} by {requester_user_id}")

        return updated_member

    async def remove_member(
        self, workspace_id: ObjectId, target_user_id: str, requester_user_id: str, requester_email: str
    ) -> bool:
        """Remove a member from the workspace."""
        # Verify requester has permission
        requester_member = await self._verify_workspace_member(workspace_id, requester_user_id)

        # Get target member
        target_member = await self.team_member_repo.get_member_by_workspace_and_user(workspace_id, target_user_id)
        if not target_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in workspace"
            )

        # Check permissions
        if not requester_member.can_remove_member(target_member.role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to remove this member"
            )

        # Prevent removing owners
        if target_member.role == MemberRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot remove owner from workspace"
            )

        # Check if removing last owner (shouldn't happen due to above check, but safety)
        if target_member.role == MemberRole.OWNER:
            owner_count = await self.team_member_repo.count_members_by_role(workspace_id, MemberRole.OWNER)
            if owner_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot remove the last owner of the workspace"
                )

        # Remove member
        success = await self.team_member_repo.remove_member(workspace_id, target_user_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove member"
            )

        # Log audit event
        await self.audit_service.log_action(
            user_id=requester_user_id,
            workspace_id=str(workspace_id),
            action=AuditAction.DELETE,
            resource_type="workspace_member",
            resource_id=target_user_id,
            user_email=requester_email,
            metadata={
                "removed_user_id": target_user_id,
                "removed_email": target_member.email,
                "removed_role": target_member.role.value
            }
        )

        logger.info(f"Member removed: {target_user_id} from workspace {workspace_id} by {requester_user_id}")

        return success

    async def get_pending_invitations(
        self, workspace_id: ObjectId, requester_user_id: str
    ) -> list[WorkspaceInvitation]:
        """Get all pending invitations for a workspace."""
        # Verify requester has access to workspace
        await self._verify_workspace_member(workspace_id, requester_user_id)

        # Mark expired invitations before returning
        await self.invitation_repo.mark_expired_invitations()

        return await self.invitation_repo.get_invitations_by_workspace(workspace_id)

    async def cancel_invitation(
        self, workspace_id: ObjectId, invitation_id: str, requester_user_id: str, requester_email: str
    ) -> bool:
        """Cancel a pending invitation."""
        # Verify requester has permission
        requester_member = await self._verify_workspace_member(workspace_id, requester_user_id)
        if not requester_member.permissions.can_invite:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to manage invitations"
            )

        # Get invitation
        invitation = await self.invitation_repo.get_invitation_by_id(invitation_id)
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found"
            )

        # Verify invitation belongs to this workspace
        if invitation.workspace_id != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invitation does not belong to this workspace"
            )

        # Cancel invitation
        success = await self.invitation_repo.delete_invitation(invitation_id)

        if success:
            # Log audit event
            await self.audit_service.log_action(
                user_id=requester_user_id,
                workspace_id=str(workspace_id),
                action=AuditAction.DELETE,
                resource_type="workspace_invitation",
                resource_id=invitation_id,
                user_email=requester_email,
                metadata={
                    "cancelled_email": invitation.email,
                    "cancelled_role": invitation.role.value
                }
            )

            logger.info(f"Invitation cancelled: {invitation_id} by {requester_user_id}")

        return success

    async def accept_invitation_by_token(
        self, token: str, accepting_user_id: str, accepting_user_email: str, display_name: str
    ) -> WorkspaceMember:
        """Accept an invitation using its token."""
        # Get invitation by token
        invitation = await self.invitation_repo.get_invitation_by_token(token)
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found"
            )

        # Check if invitation can be accepted
        if not invitation.can_be_accepted():
            status_detail = "expired" if invitation.is_expired() else invitation.status.value
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invitation cannot be accepted - status: {status_detail}"
            )

        # Check if user is already a member
        existing_member = await self.team_member_repo.get_member_by_workspace_and_user(
            invitation.workspace_id, accepting_user_id
        )
        if existing_member:
            # Mark invitation as accepted but don't create duplicate member
            await self.invitation_repo.update_invitation_status(
                str(invitation.id), InvitationStatus.ACCEPTED, datetime.utcnow()
            )
            return existing_member

        # Create new member
        new_member = WorkspaceMember(
            workspace_id=invitation.workspace_id,
            user_id=accepting_user_id,
            email=accepting_user_email,
            display_name=display_name,
            role=invitation.role,
            invited_by=invitation.invited_by,
            joined_at=datetime.utcnow()
        )

        created_member = await self.team_member_repo.create_member(new_member)

        # Mark invitation as accepted
        await self.invitation_repo.update_invitation_status(
            str(invitation.id), InvitationStatus.ACCEPTED, datetime.utcnow()
        )

        # Log audit event
        await self.audit_service.log_action(
            user_id=accepting_user_id,
            workspace_id=str(invitation.workspace_id),
            action=AuditAction.CREATE,
            resource_type="workspace_member",
            resource_id=accepting_user_id,
            user_email=accepting_user_email,
            metadata={
                "joined_via_invitation": str(invitation.id),
                "role": invitation.role.value,
                "invited_by": invitation.invited_by
            }
        )

        logger.info(f"Invitation accepted: {accepting_user_id} joined workspace {invitation.workspace_id}")

        return created_member

    async def _verify_workspace_member(self, workspace_id: ObjectId, user_id: str) -> WorkspaceMember:
        """Verify user is a member of the workspace."""
        member = await self.team_member_repo.get_member_by_workspace_and_user(workspace_id, user_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this workspace"
            )
        return member

    def _can_update_role(
        self, requester: WorkspaceMember, target: WorkspaceMember, new_role: MemberRole
    ) -> bool:
        """Check if requester can update target's role to new_role."""
        # Must have role management permission
        if not requester.permissions.can_manage_roles:
            return False

        # Cannot change own role
        if requester.user_id == target.user_id:
            return False

        # Owners can change anyone's role (except other owners)
        if requester.role == MemberRole.OWNER:
            return target.role != MemberRole.OWNER

        # Admins can only change members' roles, not other admins or owners
        if requester.role == MemberRole.ADMIN:
            return target.role == MemberRole.MEMBER and new_role in [MemberRole.MEMBER, MemberRole.ADMIN]

        return False

    async def cleanup_expired_invitations(self) -> int:
        """Clean up expired invitations (background task)."""
        marked_expired = await self.invitation_repo.mark_expired_invitations()
        cleaned_up = await self.invitation_repo.cleanup_old_invitations(days_old=30)

        if marked_expired > 0 or cleaned_up > 0:
            logger.info(f"Cleaned up {marked_expired} expired invitations and {cleaned_up} old invitations")

        return marked_expired + cleaned_up
