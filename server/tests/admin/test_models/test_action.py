"""Tests for action models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from protobox.admin.models.action import (
    ActionCreateRequest,
    ActionModel,
    ActionStatus,
    ActionType,
    ActionUpdateRequest,
)


class TestActionModel:
    """Test cases for ActionModel."""

    def test_action_model_creation(self):
        """Test action model creation with valid data."""
        action_data = {
            "workspace_id": "507f1f77bcf86cd799439011",
            "name": "test_action",
            "type": ActionType.REST,
            "description": "Test action description",
            "created_by": "user123",
        }

        action = ActionModel(**action_data)

        assert action.name == "test_action"
        assert action.type == ActionType.REST
        assert action.description == "Test action description"
        assert action.created_by == "user123"
        assert action.version == "1.0.0"  # default value
        assert action.status == ActionStatus.ACTIVE  # default value
        assert action.tags == []  # default empty list
        assert action.secret_refs == []  # default empty list
        assert isinstance(action.created_at, datetime)
        assert isinstance(action.updated_at, datetime)

    def test_action_model_validation_required_fields(self):
        """Test action model validation for required fields."""
        # Missing required 'name' field
        with pytest.raises(ValidationError) as exc_info:
            ActionModel(
                workspace_id="507f1f77bcf86cd799439011",
                type=ActionType.REST,
                description="Test description",
                created_by="user123",
            )

        assert "name" in str(exc_info.value)

        # Missing required 'created_by' field
        with pytest.raises(ValidationError) as exc_info:
            ActionModel(
                workspace_id="507f1f77bcf86cd799439011",
                name="test_action",
                type=ActionType.REST,
                description="Test description",
            )

        assert "created_by" in str(exc_info.value)

    def test_action_model_validation_field_lengths(self):
        """Test action model field length validation."""
        # Name too long
        with pytest.raises(ValidationError):
            ActionModel(
                workspace_id="507f1f77bcf86cd799439011",
                name="a" * 256,  # exceeds max_length=255
                type=ActionType.REST,
                description="Test description",
                created_by="user123",
            )

        # Description too long
        with pytest.raises(ValidationError):
            ActionModel(
                workspace_id="507f1f77bcf86cd799439011",
                name="test_action",
                type=ActionType.REST,
                description="a" * 1001,  # exceeds max_length=1000
                created_by="user123",
            )

    def test_action_model_dump_for_db(self):
        """Test action model database serialization."""
        action = ActionModel(
            workspace_id="507f1f77bcf86cd799439011",
            name="test_action",
            type=ActionType.REST,
            description="Test description",
            created_by="user123",
        )

        db_data = action.model_dump_for_db()

        # Should not include _id if it was None
        assert "_id" not in db_data
        assert db_data["name"] == "test_action"
        assert db_data["type"] == "REST"
        assert db_data["created_by"] == "user123"

        # Test with explicit ID
        action.id = "some_id"
        db_data = action.model_dump_for_db()
        assert db_data["_id"] == "some_id"


class TestActionTypes:
    """Test cases for action type definitions."""

    def test_action_types_enum(self):
        """Test action types enumeration values."""
        assert ActionType.REST == "REST"
        assert ActionType.O3 == "O3"
        assert ActionType.DATABASE == "DATABASE"
        assert ActionType.CODE_RUN == "CODE_RUN"

        # Test all enum values are present
        expected_types = {"REST", "O3", "DATABASE", "CODE_RUN"}
        actual_types = {action_type.value for action_type in ActionType}
        assert actual_types == expected_types

    def test_action_status_enum(self):
        """Test action status enumeration values."""
        assert ActionStatus.ACTIVE == "active"
        assert ActionStatus.INACTIVE == "inactive"
        assert ActionStatus.DEPRECATED == "deprecated"


class TestActionRequests:
    """Test cases for action request models."""

    def test_action_create_request(self):
        """Test action create request model."""
        request_data = {
            "workspace_id": "507f1f77bcf86cd799439011",
            "name": "new_action",
            "type": ActionType.REST,
            "description": "New action description",
        }

        request = ActionCreateRequest(**request_data)

        assert request.name == "new_action"
        assert request.type == ActionType.REST
        assert request.description == "New action description"
        assert request.version == "1.0.0"  # default
        assert request.tags == []  # default

    def test_action_update_request(self):
        """Test action update request model."""
        request_data = {"name": "updated_action", "status": ActionStatus.INACTIVE}

        request = ActionUpdateRequest(**request_data)

        assert request.name == "updated_action"
        assert request.status == ActionStatus.INACTIVE
        assert request.description is None  # optional field
        assert request.version is None  # optional field
