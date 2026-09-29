"""Unit tests for chat models."""


import pytest
from bson import ObjectId
from pydantic import ValidationError

from protobox.admin.models.chat import (
    MessageModel,
    MessageRole,
    MessageType,
    ThreadStatus,
    ToolCall,
    ToolResult,
    validate_object_id,
)


class TestEnumerations:
    """Test chat enumerations."""

    def test_message_role_enum(self):
        """Test MessageRole enumeration."""
        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"
        assert MessageRole.SYSTEM == "system"
        assert MessageRole.TOOL == "tool"

        # Test that we can create from string
        role = MessageRole("user")
        assert role == MessageRole.USER

    def test_message_type_enum(self):
        """Test MessageType enumeration."""
        assert MessageType.TEXT == "text"
        assert MessageType.TOOL_CALL == "tool_call"
        assert MessageType.TOOL_RESULT == "tool_result"
        assert MessageType.FILE_UPLOAD == "file_upload"

    def test_thread_status_enum(self):
        """Test ThreadStatus enumeration."""
        assert ThreadStatus.ACTIVE == "active"
        assert ThreadStatus.ARCHIVED == "archived"
        assert ThreadStatus.DELETED == "deleted"


class TestToolCall:
    """Test ToolCall model."""

    def test_tool_call_minimal(self):
        """Test creating a tool call with minimal fields."""
        tool_call = ToolCall(id="call_123", name="search")
        assert tool_call.id == "call_123"
        assert tool_call.name == "search"
        assert tool_call.parameters == {}
        assert tool_call.mcp_action_id is None

    def test_tool_call_with_parameters(self):
        """Test creating a tool call with parameters."""
        tool_call = ToolCall(
            id="call_123", name="search", parameters={"query": "test", "limit": 10}
        )
        assert tool_call.parameters == {"query": "test", "limit": 10}

    def test_tool_call_with_mcp_action(self):
        """Test creating a tool call with MCP action ID."""
        tool_call = ToolCall(id="call_123", name="custom_action", mcp_action_id="action_456")
        assert tool_call.mcp_action_id == "action_456"

    def test_tool_call_validation(self):
        """Test that required fields are validated."""
        with pytest.raises(ValidationError):
            ToolCall()  # Missing required fields

        with pytest.raises(ValidationError):
            ToolCall(id="call_123")  # Missing name

        with pytest.raises(ValidationError):
            ToolCall(name="search")  # Missing id


class TestToolResult:
    """Test ToolResult model."""

    def test_tool_result_success(self):
        """Test creating a successful tool result."""
        result = ToolResult(
            tool_call_id="call_123",
            success=True,
            result={"data": "test result"},
            execution_time_ms=150,
        )
        assert result.tool_call_id == "call_123"
        assert result.success is True
        assert result.result == {"data": "test result"}
        assert result.error is None
        assert result.execution_time_ms == 150

    def test_tool_result_failure(self):
        """Test creating a failed tool result."""
        result = ToolResult(tool_call_id="call_123", success=False, error="Connection timeout")
        assert result.success is False
        assert result.error == "Connection timeout"
        assert result.result is None

    def test_tool_result_minimal(self):
        """Test creating a tool result with minimal fields."""
        result = ToolResult(tool_call_id="call_123", success=True)
        assert result.tool_call_id == "call_123"
        assert result.success is True
        assert result.result is None
        assert result.error is None
        assert result.execution_time_ms is None

    def test_tool_result_validation(self):
        """Test that required fields are validated."""
        with pytest.raises(ValidationError):
            ToolResult()  # Missing required fields

        with pytest.raises(ValidationError):
            ToolResult(tool_call_id="call_123")  # Missing success


class TestMessageModel:
    """Test MessageModel."""

    def test_message_minimal(self):
        """Test creating a message with minimal fields."""
        message = MessageModel(
            thread_id="thread_123",
            workspace_id="ws_456",
            role=MessageRole.USER,
            content="Hello, world!",
            user_id="user_789",
        )
        assert message.thread_id == "thread_123"
        assert message.workspace_id == "ws_456"
        assert message.role == MessageRole.USER
        assert message.content == "Hello, world!"
        assert message.message_type == MessageType.TEXT
        assert message.id is None

    def test_message_with_id(self):
        """Test creating a message with an ID."""
        message = MessageModel(
            _id="msg_789",
            thread_id="thread_123",
            workspace_id="ws_456",
            role=MessageRole.ASSISTANT,
            content="Hello! How can I help?",
            user_id="user_789",
        )
        assert message.id == "msg_789"

    def test_message_with_tool_call(self):
        """Test creating a tool call message."""
        message = MessageModel(
            thread_id="thread_123",
            workspace_id="ws_456",
            role=MessageRole.ASSISTANT,
            message_type=MessageType.TOOL_CALL,
            content="I'll search for that information.",
            user_id="user_789",
        )
        assert message.message_type == MessageType.TOOL_CALL

    def test_message_with_tool_result(self):
        """Test creating a tool result message."""
        message = MessageModel(
            thread_id="thread_123",
            workspace_id="ws_456",
            role=MessageRole.TOOL,
            message_type=MessageType.TOOL_RESULT,
            content='{"result": "Search completed"}',
            user_id="user_789",
        )
        assert message.role == MessageRole.TOOL
        assert message.message_type == MessageType.TOOL_RESULT

    def test_message_validation(self):
        """Test that required fields are validated."""
        with pytest.raises(ValidationError):
            MessageModel()  # Missing all required fields

        with pytest.raises(ValidationError):
            MessageModel(
                thread_id="thread_123", workspace_id="ws_456", role=MessageRole.USER
            )  # Missing content

        with pytest.raises(ValidationError):
            MessageModel(
                thread_id="thread_123", workspace_id="ws_456", content="Hello"
            )  # Missing role

    def test_message_role_validation(self):
        """Test that role must be a valid MessageRole."""
        with pytest.raises(ValidationError):
            MessageModel(
                thread_id="thread_123",
                workspace_id="ws_456",
                role="invalid_role",  # Invalid role
                content="Hello",
            )


class TestObjectIdValidation:
    """Test ObjectId validation for chat models."""

    def test_validate_object_id_with_valid_objectid(self):
        """Test validation with a valid ObjectId instance."""
        oid = ObjectId()
        result = validate_object_id(oid)
        assert result == oid

    def test_validate_object_id_with_valid_string(self):
        """Test validation with a valid ObjectId string."""
        oid_str = "507f1f77bcf86cd799439011"
        result = validate_object_id(oid_str)
        assert result == oid_str

    def test_validate_object_id_with_invalid_string(self):
        """Test validation with an invalid ObjectId string."""
        with pytest.raises(ValueError, match="Invalid ObjectId"):
            validate_object_id("invalid_id")

    def test_validate_object_id_with_invalid_type(self):
        """Test validation with an invalid type."""
        with pytest.raises(ValueError, match="ObjectId must be ObjectId instance or string"):
            validate_object_id(123)
