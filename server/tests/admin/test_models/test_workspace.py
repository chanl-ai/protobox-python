"""Unit tests for workspace models."""

from datetime import datetime

import pytest
from bson import ObjectId
from pydantic import ValidationError

from protobox.admin.models.workspace import (
    Workspace,
    WorkspaceBase,
    WorkspaceCreate,
    WorkspaceMember,
    WorkspaceUpdate,
)


class TestWorkspaceMember:
    """Test WorkspaceMember model."""

    def test_member_creation_with_defaults(self):
        """Test creating a member with default values."""
        member = WorkspaceMember(user_id="user_123")
        assert member.user_id == "user_123"
        assert member.role == "member"
        assert isinstance(member.added_at, datetime)

    def test_member_creation_with_custom_role(self):
        """Test creating a member with a custom role."""
        member = WorkspaceMember(user_id="user_123", role="admin")
        assert member.role == "admin"

    def test_member_creation_with_all_fields(self):
        """Test creating a member with all fields specified."""
        added_time = datetime.utcnow()
        member = WorkspaceMember(user_id="user_123", role="owner", added_at=added_time)
        assert member.user_id == "user_123"
        assert member.role == "owner"
        assert member.added_at == added_time


class TestWorkspaceBase:
    """Test WorkspaceBase model."""

    def test_workspace_base_minimal(self):
        """Test creating a workspace with minimal required fields."""
        workspace = WorkspaceBase(name="Test Workspace", owner_id="user_123")
        assert workspace.name == "Test Workspace"
        assert workspace.owner_id == "user_123"
        assert workspace.description is None
        assert workspace.slug is None
        assert workspace.settings == {}
        assert workspace.members == []
        assert workspace.is_active is True

    def test_workspace_base_with_all_fields(self):
        """Test creating a workspace with all fields."""
        member = WorkspaceMember(user_id="user_456")
        workspace = WorkspaceBase(
            name="Test Workspace",
            description="A test workspace",
            slug="test-workspace",
            owner_id="user_123",
            settings={"theme": "dark", "language": "en"},
            members=[member],
            is_active=False,
        )
        assert workspace.name == "Test Workspace"
        assert workspace.description == "A test workspace"
        assert workspace.slug == "test-workspace"
        assert workspace.owner_id == "user_123"
        assert workspace.settings == {"theme": "dark", "language": "en"}
        assert len(workspace.members) == 1
        assert workspace.members[0].user_id == "user_456"
        assert workspace.is_active is False

    def test_workspace_base_validation(self):
        """Test that required fields are validated."""
        with pytest.raises(ValidationError):
            WorkspaceBase()  # Missing required fields

        with pytest.raises(ValidationError):
            WorkspaceBase(name="Test")  # Missing owner_id

        with pytest.raises(ValidationError):
            WorkspaceBase(owner_id="user_123")  # Missing name


class TestWorkspaceCreate:
    """Test WorkspaceCreate model."""

    def test_workspace_create_inherits_from_base(self):
        """Test that WorkspaceCreate inherits from WorkspaceBase."""
        workspace = WorkspaceCreate(name="New Workspace", owner_id="user_123")
        assert workspace.name == "New Workspace"
        assert workspace.owner_id == "user_123"
        assert workspace.is_active is True


class TestWorkspaceUpdate:
    """Test WorkspaceUpdate model."""

    def test_workspace_update_all_optional(self):
        """Test that all fields in WorkspaceUpdate are optional."""
        update = WorkspaceUpdate()
        assert update.name is None
        assert update.description is None
        assert update.slug is None
        assert update.settings is None
        assert update.is_active is None

    def test_workspace_update_partial(self):
        """Test updating only some fields."""
        update = WorkspaceUpdate(name="Updated Name", is_active=False)
        assert update.name == "Updated Name"
        assert update.description is None
        assert update.is_active is False

    def test_workspace_update_all_fields(self):
        """Test updating all fields."""
        update = WorkspaceUpdate(
            name="Updated Name",
            description="Updated description",
            slug="updated-slug",
            settings={"new": "settings"},
            is_active=False,
        )
        assert update.name == "Updated Name"
        assert update.description == "Updated description"
        assert update.slug == "updated-slug"
        assert update.settings == {"new": "settings"}
        assert update.is_active is False


class TestWorkspace:
    """Test Workspace model (full database model)."""

    def test_workspace_creation_minimal(self):
        """Test creating a workspace with minimal fields."""
        workspace = Workspace(name="Test Workspace", owner_id="user_123")
        assert workspace.name == "Test Workspace"
        assert workspace.owner_id == "user_123"
        assert workspace.id is None  # Not set until saved to DB
        assert isinstance(workspace.created_at, datetime)
        assert isinstance(workspace.updated_at, datetime)

    def test_workspace_creation_with_id(self):
        """Test creating a workspace with an ID."""
        oid = ObjectId()
        workspace = Workspace(_id=oid, name="Test Workspace", owner_id="user_123")
        assert workspace.id == oid
        assert workspace.name == "Test Workspace"

    def test_workspace_creation_with_members(self):
        """Test creating a workspace with members."""
        members = [
            WorkspaceMember(user_id="user_456", role="admin"),
            WorkspaceMember(user_id="user_789", role="member"),
        ]
        workspace = Workspace(name="Team Workspace", owner_id="user_123", members=members)
        assert len(workspace.members) == 2
        assert workspace.members[0].user_id == "user_456"
        assert workspace.members[0].role == "admin"
        assert workspace.members[1].user_id == "user_789"
        assert workspace.members[1].role == "member"

    def test_workspace_model_dump(self):
        """Test dumping workspace to dictionary."""
        oid = ObjectId()
        workspace = Workspace(
            _id=oid,
            name="Test Workspace",
            owner_id="user_123",
            description="Test description",
            slug="test-workspace",
        )

        data = workspace.model_dump(mode="json")
        assert data["_id"] == str(oid)
        assert data["id"] == str(oid)
        assert data["name"] == "Test Workspace"
        assert data["owner_id"] == "user_123"
        assert data["description"] == "Test description"
        assert data["slug"] == "test-workspace"
        assert isinstance(data["created_at"], str)
        assert isinstance(data["updated_at"], str)

    def test_workspace_json_serialization(self):
        """Test that workspace can be serialized to JSON."""
        import json

        workspace = Workspace(
            name="Test Workspace", owner_id="user_123", settings={"theme": "dark"}
        )

        # This should not raise an error
        json_str = json.dumps(workspace.model_dump(mode="json"))
        assert "Test Workspace" in json_str
        assert "user_123" in json_str
        assert "theme" in json_str

    def test_workspace_slug_validation(self):
        """Test workspace slug field."""
        workspace = Workspace(name="Test Workspace", owner_id="user_123", slug="test-workspace-123")
        assert workspace.slug == "test-workspace-123"

        # Slug can be None
        workspace2 = Workspace(name="Test Workspace", owner_id="user_123", slug=None)
        assert workspace2.slug is None
