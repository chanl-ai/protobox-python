"""
Type definitions for MCP SDK - Core MCP Protocol and Admin API
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

# =============================================================================
# Core MCP Protocol Types
# =============================================================================


@dataclass
class MCPTool:
    """MCP tool definition."""

    name: str
    description: str
    inputSchema: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MCPTool":
        return cls(
            name=data["name"], description=data["description"], inputSchema=data["inputSchema"]
        )


@dataclass
class MCPToolCall:
    """MCP tool call request."""

    name: str
    arguments: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "arguments": self.arguments}


@dataclass
class MCPToolResult:
    """MCP tool call result."""

    content: list[dict[str, Any]]
    isError: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MCPToolResult":
        return cls(content=data["content"], isError=data.get("isError", False))


# =============================================================================
# Admin API Types
# =============================================================================


class ActionType(Enum):
    """Action types supported by MCP server."""

    REST = "REST"
    CODE_RUN = "CODE_RUN"
    DATABASE = "DATABASE"
    O3 = "O3"


class SecretType(Enum):
    """Secret types supported by MCP server."""

    API_KEY = "API_KEY"
    DATABASE_URL = "DATABASE_URL"
    OAUTH_TOKEN = "OAUTH_TOKEN"
    CUSTOM = "CUSTOM"


class ExecutionStatus(Enum):
    """Execution status values."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class ActionConfig:
    """Configuration for creating/updating MCP actions."""

    name: str
    type: ActionType
    description: str
    default_config: dict[str, Any] = field(default_factory=dict)
    config_schema: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    workspace_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API calls."""
        return {
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "default_config": self.default_config,
            "config_schema": self.config_schema,
            "tags": self.tags,
            "workspace_id": self.workspace_id,
        }


@dataclass
class SecretConfig:
    """Configuration for creating/updating MCP secrets."""

    name: str
    secret_type: SecretType
    secret_value: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    workspace_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API calls."""
        return {
            "name": self.name,
            "secret_type": self.secret_type.value,
            "secret_value": self.secret_value,
            "description": self.description,
            "tags": self.tags,
            "workspace_id": self.workspace_id,
        }


@dataclass
class ExecutionConfig:
    """Configuration for creating action executions."""

    action_id: str
    input_data: dict[str, Any] = field(default_factory=dict)
    config_override: dict[str, Any] | None = None
    workspace_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API calls."""
        return {
            "action_id": self.action_id,
            "input_data": self.input_data,
            "config_override": self.config_override,
            "workspace_id": self.workspace_id,
        }


# =============================================================================
# Server Configuration Types
# =============================================================================


@dataclass
class OpenAIServerConfig:
    """OpenAI MCP server configuration."""

    url: str
    name: str = "mcp-server"
    description: str = "MCP Server"
    api_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to OpenAI MCP server config format."""
        config = {
            "type": "mcp",
            "name": self.name,
            "description": self.description,
            "url": self.url,
        }
        if self.api_key:
            config["api_key"] = self.api_key
        return config


@dataclass
class ClaudeServerConfig:
    """Claude Desktop MCP server configuration."""

    command: list[str]
    args: list[str] = field(default_factory=list)
    env: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to Claude Desktop config format."""
        config = {"command": self.command, "args": self.args}
        if self.env:
            config["env"] = self.env
        return config


# =============================================================================
# Response Types
# =============================================================================


@dataclass
class ActionResponse:
    """Response from action operations."""

    id: str
    name: str
    type: str
    description: str
    config: dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
    version: str | None = None
    tags: list[str] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActionResponse":
        # Handle both config and default_config fields
        config_data = data.get("config", data.get("default_config", {}))

        return cls(
            id=data["_id"] if "_id" in data else data["id"],
            name=data["name"],
            type=data["type"],
            description=data["description"],
            config=config_data,
            status=data.get("status", "ACTIVE"),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
            version=data.get("version"),
            tags=data.get("tags", []),
        )


@dataclass
class ExecutionResponse:
    """Response from execution operations."""

    id: str
    action_id: str
    status: ExecutionStatus
    input_data: dict[str, Any]
    output_data: dict[str, Any] | None
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionResponse":
        return cls(
            id=data["_id"] if "_id" in data else data["id"],
            action_id=data["action_id"],
            status=ExecutionStatus(data["status"]),
            input_data=data["input_data"],
            output_data=data.get("output_data"),
            error_message=data.get("error_message"),
            started_at=datetime.fromisoformat(data["started_at"].replace("Z", "+00:00")),
            completed_at=(
                datetime.fromisoformat(data["completed_at"].replace("Z", "+00:00"))
                if data.get("completed_at")
                else None
            ),
        )


@dataclass
class HealthResponse:
    """Response from health check."""

    status: str
    transport: str | None = None
    version: str | None = None
    capabilities: dict[str, Any] | None = None
    timestamp: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HealthResponse":
        # Handle timestamp if present
        timestamp = None
        if "timestamp" in data:
            timestamp_str = data["timestamp"]
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except ValueError:
                timestamp = datetime.now()

        return cls(
            status=data["status"],
            transport=data.get("transport"),
            version=data.get("version"),
            capabilities=data.get("capabilities"),
            timestamp=timestamp,
        )
