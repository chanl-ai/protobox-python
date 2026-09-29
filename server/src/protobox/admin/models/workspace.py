"""Workspace model for ProtoBox."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .base import MongoBaseModel


class WorkspaceMember(BaseModel):
    """Member of a workspace."""

    user_id: str
    role: str = "member"  # owner, admin, member
    added_at: datetime = Field(default_factory=datetime.utcnow)


class WorkspaceBase(BaseModel):
    """Base workspace model."""

    name: str
    description: str | None = None
    slug: str | None = None
    owner_id: str
    settings: dict[str, Any] | None = Field(default_factory=dict)
    members: list[WorkspaceMember] | None = Field(default_factory=list)
    is_active: bool = True


class WorkspaceCreate(WorkspaceBase):
    """Model for creating a workspace."""

    pass


class WorkspaceUpdate(BaseModel):
    """Model for updating a workspace."""

    name: str | None = None
    description: str | None = None
    slug: str | None = None
    settings: dict[str, Any] | None = None
    is_active: bool | None = None


class Workspace(WorkspaceBase, MongoBaseModel):
    """Workspace model with database fields."""

    # MongoBaseModel already provides id, created_at, updated_at

    model_config = {
        **MongoBaseModel.model_config,
        "json_schema_extra": {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "name": "My Workspace",
                "description": "A workspace for my projects",
                "owner_id": "user_123",
                "settings": {"theme": "dark"},
                "members": [
                    {"user_id": "user_456", "role": "member", "added_at": "2024-01-01T00:00:00Z"}
                ],
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        },
    }
