"""Assistant models for OpenAI integration."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AssistantStatus(str, Enum):
    """Assistant status enum."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class AssistantModel(BaseModel):
    """Model for storing assistant configuration."""

    id: str | None = Field(None, description="Database ID")
    workspace_id: str = Field(..., description="Workspace ID this assistant belongs to")
    assistant_id: str = Field(..., description="OpenAI Assistant ID")
    name: str = Field(..., description="Assistant name")
    description: str | None = Field(None, description="Assistant description")
    instructions: str = Field(..., description="Assistant instructions")
    model: str = Field("gpt-4-turbo-preview", description="OpenAI model to use")
    status: AssistantStatus = Field(AssistantStatus.ACTIVE, description="Assistant status")
    is_default: bool = Field(
        False, description="Whether this is the default assistant for the workspace"
    )
    tools: list[dict[str, Any]] = Field(default_factory=list, description="Tool configurations")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(..., description="User ID who created the assistant")

    def model_dump_for_db(self) -> dict[str, Any]:
        """Convert model to dict for database storage."""
        data = self.model_dump(exclude={"id"})
        if self.id:
            data["_id"] = self.id
        return data


class ThreadModel(BaseModel):
    """Model for conversation threads."""

    id: str | None = Field(None, description="Database ID")
    workspace_id: str = Field(..., description="Workspace ID")
    assistant_id: str = Field(..., description="Assistant ID this thread belongs to")
    thread_id: str = Field(..., description="OpenAI Thread ID")
    title: str = Field(..., description="Thread title")
    status: str = Field("active", description="Thread status")
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_message_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(..., description="User ID who created the thread")

    def model_dump_for_db(self) -> dict[str, Any]:
        """Convert model to dict for database storage."""
        data = self.model_dump(exclude={"id"})
        if self.id:
            data["_id"] = self.id
        return data


class MessageRole(str, Enum):
    """Message role enum."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ToolCall(BaseModel):
    """Model for tool calls within messages."""

    id: str = Field(..., description="Tool call ID")
    type: str = Field("function", description="Tool type")
    function: dict[str, Any] = Field(..., description="Function details")


class MessageModel(BaseModel):
    """Model for messages in a thread."""

    id: str | None = Field(None, description="Database ID")
    thread_id: str = Field(..., description="Thread ID this message belongs to")
    message_id: str | None = Field(None, description="OpenAI Message ID")
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    tool_calls: list[ToolCall] | None = Field(None, description="Tool calls in this message")
    tool_outputs: list[dict[str, Any]] | None = Field(None, description="Tool execution results")
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def model_dump_for_db(self) -> dict[str, Any]:
        """Convert model to dict for database storage."""
        data = self.model_dump(exclude={"id"})
        if self.id:
            data["_id"] = self.id
        return data


# Request/Response models for API


class AssistantCreateRequest(BaseModel):
    """Request model for creating an assistant."""

    name: str = Field(..., description="Assistant name")
    description: str | None = Field(None, description="Assistant description")
    instructions: str = Field(..., description="Assistant instructions")
    model: str = Field("gpt-4-turbo-preview", description="Model to use")
    enable_mcp_tools: bool = Field(True, description="Enable MCP tool integration")
    metadata: dict[str, Any] = Field(default_factory=dict)


class AssistantUpdateRequest(BaseModel):
    """Request model for updating an assistant."""

    name: str | None = Field(None, description="Assistant name")
    description: str | None = Field(None, description="Assistant description")
    instructions: str | None = Field(None, description="Assistant instructions")
    model: str | None = Field(None, description="Model to use")
    status: AssistantStatus | None = Field(None, description="Assistant status")
    metadata: dict[str, Any] | None = Field(None)


class ThreadCreateRequest(BaseModel):
    """Request model for creating a thread."""

    title: str = Field(..., description="Thread title")
    metadata: dict[str, Any] = Field(default_factory=dict)


class MessageCreateRequest(BaseModel):
    """Request model for sending a message."""

    content: str = Field(..., description="Message content")
    metadata: dict[str, Any] = Field(default_factory=dict)


class AssistantResponse(AssistantModel):
    """Response model for assistant data."""

    pass


class ThreadResponse(ThreadModel):
    """Response model for thread data."""

    pass


class MessageResponse(MessageModel):
    """Response model for message data."""

    pass


class RunStatus(BaseModel):
    """Model for run status updates."""

    run_id: str = Field(..., description="OpenAI Run ID")
    status: str = Field(..., description="Run status")
    required_action: dict[str, Any] | None = Field(None)
    last_error: dict[str, Any] | None = Field(None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
