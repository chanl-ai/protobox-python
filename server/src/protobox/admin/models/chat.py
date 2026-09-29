"""Chat models for admin API."""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any

from bson import ObjectId
from pydantic import AfterValidator, BaseModel, Field, PlainSerializer, WithJsonSchema


def validate_object_id(v: Any) -> ObjectId | str:
    """Validate and convert to ObjectId or keep as string."""
    if isinstance(v, ObjectId):
        return v
    if isinstance(v, str):
        if ObjectId.is_valid(v):
            return v  # Keep as string, let serializer handle it
        raise ValueError(f"Invalid ObjectId: {v}")
    raise ValueError("ObjectId must be ObjectId instance or string")


# Custom ObjectId type for Pydantic v2
ObjectIdType = Annotated[
    ObjectId | str,
    PlainSerializer(
        lambda x: str(x) if isinstance(x, ObjectId) else x, return_type=str, when_used="json"
    ),
    AfterValidator(validate_object_id),
    WithJsonSchema({"type": "string"}, mode="serialization"),
]


class MessageRole(str, Enum):
    """Message role enumeration."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MessageType(str, Enum):
    """Message type enumeration."""

    TEXT = "text"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    FILE_UPLOAD = "file_upload"


class ThreadStatus(str, Enum):
    """Thread status enumeration."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ToolCall(BaseModel):
    """Tool call information."""

    id: str = Field(..., description="Tool call ID")
    name: str = Field(..., description="Tool/action name")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    mcp_action_id: str | None = Field(
        None, description="MCP action ID if calling workspace action"
    )


class ToolResult(BaseModel):
    """Tool execution result."""

    tool_call_id: str = Field(..., description="Associated tool call ID")
    success: bool = Field(..., description="Whether tool execution succeeded")
    result: dict[str, Any] | None = Field(None, description="Tool execution result")
    error: str | None = Field(None, description="Error message if execution failed")
    execution_time_ms: int | None = Field(None, description="Execution time in milliseconds")


class MessageModel(BaseModel):
    """Individual message in a chat thread."""

    id: str | None = Field(None, alias="_id", description="Message ID")
    thread_id: str = Field(..., description="Thread this message belongs to")
    workspace_id: str = Field(..., description="Workspace ID for multi-tenancy")

    # Message content
    role: MessageRole = Field(..., description="Message role")
    message_type: MessageType = Field(default=MessageType.TEXT, description="Message type")
    content: str = Field(..., description="Message content")

    # Tool calling information
    tool_calls: list[ToolCall] | None = Field(None, description="Tool calls in this message")
    tool_results: list[ToolResult] | None = Field(None, description="Tool execution results")

    # File attachments
    file_attachments: list[dict[str, Any]] = Field(
        default_factory=list, description="File attachments"
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Message creation time"
    )
    user_id: str = Field(..., description="User who created this message")

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "thread_id": "thread_123",
                "workspace_id": "workspace_456",
                "role": "user",
                "message_type": "text",
                "content": "Execute the weather action for New York",
                "user_id": "user_789",
            }
        },
    }

    def model_dump_for_db(self) -> dict[str, Any]:
        """Convert model to dictionary for MongoDB storage."""
        data = self.model_dump(exclude_none=True)
        if "id" in data:
            if data["id"] is not None:
                data["_id"] = data["id"]
            del data["id"]
        return data

    @classmethod
    def from_mongo(cls, data: dict[str, Any]) -> "MessageModel":
        """Create MessageModel from MongoDB document."""
        # Create a copy to avoid modifying the original
        data_copy = data.copy()
        if "_id" in data_copy and isinstance(data_copy["_id"], ObjectId):
            data_copy["_id"] = str(data_copy["_id"])
        return cls(**data_copy)


class ThreadModel(BaseModel):
    """Chat thread model."""

    id: str | None = Field(None, alias="_id", description="Thread ID")
    workspace_id: str = Field(..., description="Workspace ID for multi-tenancy")

    # Thread metadata
    name: str = Field(..., description="Thread name/title", min_length=1, max_length=255)
    description: str | None = Field(None, description="Thread description", max_length=1000)
    status: ThreadStatus = Field(default=ThreadStatus.ACTIVE, description="Thread status")

    # Chat configuration
    system_instructions: str | None = Field(
        None, description="System instructions for the assistant"
    )
    context_data: dict[str, Any] = Field(
        default_factory=dict, description="Additional context data"
    )

    # Statistics
    message_count: int = Field(default=0, description="Number of messages in this thread")
    last_message_at: datetime | None = Field(None, description="Timestamp of last message")

    # Audit fields
    created_by: str = Field(..., description="User who created this thread")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Thread creation time"
    )
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time")

    # Sharing and permissions
    shared_with: list[str] = Field(
        default_factory=list, description="User IDs with access to this thread"
    )
    is_public: bool = Field(default=False, description="Whether thread is public within workspace")

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "workspace_id": "workspace_456",
                "name": "API Testing Session",
                "description": "Testing various API endpoints",
                "system_instructions": "You are a helpful assistant that can execute workspace actions via MCP.",
                "created_by": "user_789",
            }
        },
    }

    def model_dump_for_db(self) -> dict[str, Any]:
        """Convert model to dictionary for MongoDB storage."""
        data = self.model_dump(exclude_none=True)
        if "id" in data:
            if data["id"] is not None:
                data["_id"] = data["id"]
            del data["id"]
        return data

    @classmethod
    def from_mongo(cls, data: dict[str, Any]) -> "ThreadModel":
        """Create ThreadModel from MongoDB document."""
        # Create a copy to avoid modifying the original
        data_copy = data.copy()
        if "_id" in data_copy and isinstance(data_copy["_id"], ObjectId):
            data_copy["_id"] = str(data_copy["_id"])
        return cls(**data_copy)


class ThreadCreateRequest(BaseModel):
    """Request model for creating a new thread."""

    workspace_id: str = Field(..., description="Workspace ID")
    name: str = Field(..., description="Thread name", min_length=1, max_length=255)
    description: str | None = Field(None, description="Thread description", max_length=1000)
    system_instructions: str | None = Field(
        None, description="System instructions for assistant"
    )
    context_data: dict[str, Any] = Field(default_factory=dict, description="Additional context")
    is_public: bool = Field(default=False, description="Whether thread is public within workspace")


class ThreadUpdateRequest(BaseModel):
    """Request model for updating a thread."""

    name: str | None = Field(
        None, description="Updated thread name", min_length=1, max_length=255
    )
    description: str | None = Field(None, description="Updated description", max_length=1000)
    system_instructions: str | None = Field(None, description="Updated system instructions")
    context_data: dict[str, Any] | None = Field(None, description="Updated context data")
    status: ThreadStatus | None = Field(None, description="Updated thread status")
    is_public: bool | None = Field(None, description="Updated public status")


class MessageCreateRequest(BaseModel):
    """Request model for creating a new message."""

    thread_id: str = Field(..., description="Thread ID")
    workspace_id: str = Field(..., description="Workspace ID")
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content", min_length=1)
    message_type: MessageType = Field(default=MessageType.TEXT, description="Message type")
    tool_calls: list[ToolCall] | None = Field(None, description="Tool calls in this message")
    file_attachments: list[dict[str, Any]] = Field(
        default_factory=list, description="File attachments"
    )


class ChatSummary(BaseModel):
    """Summary statistics for chat usage."""

    total_threads: int = Field(..., description="Total number of threads")
    active_threads: int = Field(..., description="Number of active threads")
    total_messages: int = Field(..., description="Total number of messages")
    by_role: dict[str, int] = Field(..., description="Message count by role")
    tool_calls_count: int = Field(..., description="Total number of tool calls")

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_threads": 25,
                "active_threads": 18,
                "total_messages": 456,
                "by_role": {"user": 228, "assistant": 200, "tool": 28},
                "tool_calls_count": 35,
            }
        }
    }
