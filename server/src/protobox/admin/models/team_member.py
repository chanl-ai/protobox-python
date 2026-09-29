"""Team member models for workspace member management."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from .base import MongoBaseModel, PyObjectId


class MemberRole(str, Enum):
    """Member role definitions with hierarchy."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class MemberPermissions(BaseModel):
    """Member permissions based on role."""
    can_invite: bool = False
    can_remove: bool = False
    can_manage_roles: bool = False
    can_manage_workspace: bool = False


class WorkspaceMember(MongoBaseModel):
    """Workspace member model."""

    workspace_id: PyObjectId = Field(..., description="Workspace ObjectId")
    user_id: str = Field(..., description="User ID from Firebase")
    email: str = Field(..., description="User email address")
    display_name: str = Field(..., description="User display name")
    role: MemberRole = Field(..., description="Member role")
    joined_at: datetime = Field(default_factory=datetime.utcnow, description="When member joined workspace")
    invited_by: str | None = Field(None, description="User ID who invited this member")
    last_active: datetime | None = Field(None, description="Last activity timestamp")
    permissions: MemberPermissions = Field(default_factory=MemberPermissions, description="Role-based permissions")

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        """Validate role is a valid MemberRole."""
        if isinstance(v, str):
            try:
                return MemberRole(v)
            except ValueError:
                raise ValueError(f"Invalid role: {v}. Must be one of: {list(MemberRole)}")
        return v

    def model_post_init(self, __context) -> None:
        """Set permissions based on role after initialization."""
        self.permissions = self._get_permissions_for_role(self.role)

    @staticmethod
    def _get_permissions_for_role(role: MemberRole) -> MemberPermissions:
        """Get permissions based on role."""
        if role == MemberRole.OWNER:
            return MemberPermissions(
                can_invite=True,
                can_remove=True,
                can_manage_roles=True,
                can_manage_workspace=True
            )
        if role == MemberRole.ADMIN:
            return MemberPermissions(
                can_invite=True,
                can_remove=True,
                can_manage_roles=True,  # Can manage member roles, but not other admins
                can_manage_workspace=False
            )
        # MEMBER
        return MemberPermissions(
            can_invite=False,
            can_remove=False,
            can_manage_roles=False,
            can_manage_workspace=False
        )

    @classmethod
    def get_role_hierarchy(cls) -> dict[MemberRole, int]:
        """Get role hierarchy for permission checking."""
        return {
            MemberRole.OWNER: 3,
            MemberRole.ADMIN: 2,
            MemberRole.MEMBER: 1
        }

    def can_manage_role(self, target_role: MemberRole) -> bool:
        """Check if this member can manage another member's role."""
        hierarchy = self.get_role_hierarchy()
        return hierarchy[self.role] > hierarchy[target_role]

    def can_remove_member(self, target_role: MemberRole) -> bool:
        """Check if this member can remove another member."""
        if not self.permissions.can_remove:
            return False

        # Owners can remove anyone except other owners
        if self.role == MemberRole.OWNER:
            return target_role != MemberRole.OWNER

        # Admins can remove members only
        if self.role == MemberRole.ADMIN:
            return target_role == MemberRole.MEMBER

        return False


class WorkspaceMemberResponse(BaseModel):
    """Response model for workspace member."""
    user_id: str
    email: str
    display_name: str
    role: str
    joined_at: datetime
    invited_by: str | None = None
    last_active: datetime | None = None


class WorkspaceMemberListResponse(BaseModel):
    """Response model for workspace member list."""
    members: list[WorkspaceMemberResponse]
    total: int
    pending_invites: int


class UpdateMemberRoleRequest(BaseModel):
    """Request model for updating member role."""
    role: MemberRole = Field(..., description="New role for the member")

    @field_validator('role')
    @classmethod
    def validate_role_not_owner(cls, v):
        """Validate that role is not owner (owners cannot be assigned via API)."""
        if v == MemberRole.OWNER:
            raise ValueError("Owner role cannot be assigned via API")
        return v


class UpdateMemberRoleResponse(BaseModel):
    """Response model for updating member role."""
    user_id: str
    role: str
    updated_at: datetime
