"""Unit tests for assistant models - simplified version."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from protobox.admin.models.assistant import (
    AssistantCreateRequest,
    AssistantModel,
    AssistantStatus,
    AssistantUpdateRequest,
    MessageRole,
    ThreadModel,
)


class TestAssistantStatus:
    """Test AssistantStatus enumeration."""

    def test_assistant_status_values(self):
        """Test assistant status values."""
        assert AssistantStatus.ACTIVE == "active"
        assert AssistantStatus.INACTIVE == "inactive"
        assert AssistantStatus.ERROR == "error"


class TestAssistantModel:
    """Test AssistantModel."""

    def test_assistant_creation(self):
        """Test creating an assistant."""
        assistant = AssistantModel(
            workspace_id="ws_123",
            assistant_id="asst_abc123",
            name="Test Assistant",
            instructions="Be helpful",
            created_by="user_456",
        )

        assert assistant.workspace_id == "ws_123"
        assert assistant.assistant_id == "asst_abc123"
        assert assistant.name == "Test Assistant"
        assert assistant.instructions == "Be helpful"
        assert assistant.model == "gpt-4-turbo-preview"  # Default
        assert assistant.status == AssistantStatus.ACTIVE  # Default
        assert assistant.is_default is False  # Default
        assert assistant.tools == []
        assert assistant.metadata == {}
        assert isinstance(assistant.created_at, datetime)
        assert assistant.created_by == "user_456"

    def test_assistant_with_all_fields(self):
        """Test creating an assistant with all fields."""
        assistant = AssistantModel(
            id="assistant_789",
            workspace_id="ws_123",
            assistant_id="asst_abc123",
            name="Advanced Assistant",
            description="An advanced AI assistant",
            instructions="Be helpful and concise",
            model="gpt-4",
            status=AssistantStatus.ERROR,
            is_default=True,
            tools=[{"type": "code_interpreter"}],
            metadata={"version": "1.0"},
            created_by="user_456",
        )

        assert assistant.id == "assistant_789"
        assert assistant.description == "An advanced AI assistant"
        assert assistant.model == "gpt-4"
        assert assistant.status == AssistantStatus.ERROR
        assert assistant.is_default is True
        assert len(assistant.tools) == 1
        assert assistant.metadata["version"] == "1.0"

    def test_assistant_model_dump_for_db(self):
        """Test converting assistant to database format."""
        assistant = AssistantModel(
            id="assistant_123",
            workspace_id="ws_123",
            assistant_id="asst_abc123",
            name="Test Assistant",
            instructions="Be helpful",
            created_by="user_456",
        )

        db_data = assistant.model_dump_for_db()
        assert "_id" in db_data
        assert db_data["_id"] == "assistant_123"
        assert "id" not in db_data
        assert db_data["workspace_id"] == "ws_123"

    def test_assistant_validation(self):
        """Test assistant validation."""
        # Missing required fields
        with pytest.raises(ValidationError):
            AssistantModel()

        with pytest.raises(ValidationError):
            AssistantModel(
                workspace_id="ws_123",
                assistant_id="asst_123",
                # Missing name, instructions, created_by
            )


class TestThreadModel:
    """Test ThreadModel."""

    def test_thread_creation(self):
        """Test creating a thread."""
        thread = ThreadModel(
            workspace_id="ws_123",
            assistant_id="asst_abc123",
            thread_id="thread_def456",
            title="Test Conversation",
            created_by="user_456",
        )

        assert thread.workspace_id == "ws_123"
        assert thread.assistant_id == "asst_abc123"
        assert thread.thread_id == "thread_def456"
        assert thread.title == "Test Conversation"
        assert thread.status == "active"  # Default
        assert thread.metadata == {}
        assert isinstance(thread.created_at, datetime)
        assert isinstance(thread.last_message_at, datetime)
        assert thread.created_by == "user_456"

    def test_thread_model_dump_for_db(self):
        """Test converting thread to database format."""
        thread = ThreadModel(
            id="thread_123",
            workspace_id="ws_123",
            assistant_id="asst_abc123",
            thread_id="thread_def456",
            title="Test Conversation",
            created_by="user_456",
        )

        db_data = thread.model_dump_for_db()
        assert "_id" in db_data
        assert db_data["_id"] == "thread_123"
        assert "id" not in db_data


class TestMessageRole:
    """Test MessageRole enumeration."""

    def test_message_roles(self):
        """Test message role values."""
        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"
        assert MessageRole.SYSTEM == "system"


class TestAssistantRequests:
    """Test assistant request models."""

    def test_create_request(self):
        """Test AssistantCreateRequest."""
        request = AssistantCreateRequest(
            name="New Assistant", instructions="Be helpful", model="gpt-4"
        )

        assert request.name == "New Assistant"
        assert request.instructions == "Be helpful"
        assert request.model == "gpt-4"

    def test_update_request(self):
        """Test AssistantUpdateRequest."""
        request = AssistantUpdateRequest(name="Updated Name", status=AssistantStatus.INACTIVE)

        assert request.name == "Updated Name"
        assert request.status == AssistantStatus.INACTIVE
