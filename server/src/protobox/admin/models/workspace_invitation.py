"""Workspace invitation models for team member invitations."""

import secrets
from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from .base import MongoBaseModel, PyObjectId
from .team_member import MemberRole


class InvitationStatus(str, Enum):
    """Invitation status definitions."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class WorkspaceInvitation(MongoBaseModel):
    """Workspace invitation model."""

    workspace_id: PyObjectId = Field(..., description="Workspace ObjectId")
    email: str = Field(..., description="Invited user email address")
    role: MemberRole = Field(..., description="Invited member role")
    token: str = Field(..., description="Secure invitation token")
    invited_by: str = Field(..., description="User ID who sent the invitation")
    invited_at: datetime = Field(default_factory=datetime.utcnow, description="Invitation timestamp")
    expires_at: datetime = Field(..., description="Invitation expiry timestamp")
    status: InvitationStatus = Field(default=InvitationStatus.PENDING, description="Invitation status")
    accepted_at: datetime | None = Field(None, description="When invitation was accepted")

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        """Validate role is a valid MemberRole and not OWNER."""
        if isinstance(v, str):
            try:
                role = MemberRole(v)
            except ValueError:
                raise ValueError(f"Invalid role: {v}. Must be one of: {list(MemberRole)}")
        else:
            role = v

        if role == MemberRole.OWNER:
            raise ValueError("Cannot invite users as owners")

        return role

    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v):
        """Basic email validation."""
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email format")
        return v.lower()

    @classmethod
    def create_invitation(
        cls,
        workspace_id: PyObjectId,
        email: str,
        role: MemberRole,
        invited_by: str,
        expires_in_days: int = 7
    ) -> "WorkspaceInvitation":
        """Create a new invitation with secure token and expiry."""
        # Generate secure token
        token = secrets.token_urlsafe(32)

        # Set expiry date
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        return cls(
            workspace_id=workspace_id,
            email=email.lower(),
            role=role,
            token=token,
            invited_by=invited_by,
            expires_at=expires_at
        )

    def is_expired(self) -> bool:
        """Check if invitation is expired."""
        return datetime.utcnow() > self.expires_at

    def can_be_accepted(self) -> bool:
        """Check if invitation can be accepted."""
        return (
            self.status == InvitationStatus.PENDING and
            not self.is_expired()
        )

    def mark_as_expired(self) -> None:
        """Mark invitation as expired."""
        if self.is_expired() and self.status == InvitationStatus.PENDING:
            self.status = InvitationStatus.EXPIRED

    def accept(self) -> None:
        """Mark invitation as accepted."""
        if not self.can_be_accepted():
            raise ValueError("Invitation cannot be accepted")

        self.status = InvitationStatus.ACCEPTED
        self.accepted_at = datetime.utcnow()

    def cancel(self) -> None:
        """Cancel invitation."""
        if self.status == InvitationStatus.PENDING:
            self.status = InvitationStatus.CANCELLED


class CreateInvitationRequest(BaseModel):
    """Request model for creating invitation."""
    email: str = Field(..., description="Email address to invite")
    role: MemberRole = Field(..., description="Role to assign to invited member")
    send_email: bool = Field(default=True, description="Whether to send email notification")

    @field_validator('role')
    @classmethod
    def validate_role_not_owner(cls, v):
        """Validate that role is not owner."""
        if v == MemberRole.OWNER:
            raise ValueError("Cannot invite users as owners")
        return v

    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v):
        """Basic email validation."""
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email format")
        return v.lower()


class InvitationResponse(BaseModel):
    """Response model for invitation."""
    invitation_id: str
    email: str
    role: str
    expires_at: datetime
    invite_link: str


class InvitationListItem(BaseModel):
    """Response model for invitation list item."""
    invitation_id: str
    email: str
    role: str
    invited_by: str
    invited_at: datetime
    expires_at: datetime
    status: str


class InvitationListResponse(BaseModel):
    """Response model for invitation list."""
    invitations: list[InvitationListItem]
