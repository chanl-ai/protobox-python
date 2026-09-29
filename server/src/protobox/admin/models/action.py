"""Action models for admin API."""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any

from bson import ObjectId
from pydantic import BaseModel, Field

from .base import MongoBaseModel


class ActionType(str, Enum):
    """Action types supported by the system."""

    REST = "REST"
    O3 = "O3"  # OpenAI-style actions
    DATABASE = "DATABASE"
    CODE_RUN = "CODE_RUN"
    KNOWLEDGE_BASE = "KNOWLEDGE_BASE"
    ADMIN = "ADMIN"  # Administrative tools


class ActionStatus(str, Enum):
    """Action status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"


class ActionModel(MongoBaseModel):
    """Action data model for MongoDB storage."""

    # id, created_by, updated_by, created_at, updated_at inherited from MongoBaseModel
    workspace_id: str = Field(..., description="Workspace ID for multi-tenancy")
    name: str = Field(..., description="Action name", min_length=1, max_length=255)
    type: ActionType = Field(..., description="Action type")
    description: str = Field(..., description="Action description", max_length=1000)
    version: str = Field(default="1.0.0", description="Action version")
    tags: list[str] = Field(default_factory=list, description="Action tags")

    # Configuration schema and defaults
    config_schema: dict[str, Any] = Field(
        default_factory=dict, description="JSON schema for action configuration"
    )
    default_config: dict[str, Any] = Field(
        default_factory=dict, description="Default configuration values"
    )

    # Secret references
    secret_refs: list[str] = Field(
        default_factory=list, description="References to secrets used by this action"
    )

    # Status and metadata
    status: ActionStatus = Field(default=ActionStatus.ACTIVE, description="Action status")
    is_builtin: bool = Field(default=False, description="Whether this is a built-in action")

    # Audit fields inherited from MongoBaseModel

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "name": "slack_notification",
                "type": "REST",
                "description": "Send notifications to Slack",
                "version": "1.0.0",
                "tags": ["notification", "slack"],
                "config_schema": {
                    "type": "object",
                    "properties": {
                        "webhook_url": {"type": "string"},
                        "channel": {"type": "string"},
                    },
                    "required": ["webhook_url", "channel"],
                },
                "default_config": {"channel": "#general"},
                "secret_refs": ["slack_webhook_secret"],
            }
        },
    }

    # MongoDB serialization methods inherited from MongoBaseModel


class ActionCreateRequest(BaseModel):
    """Request model for creating a new action."""

    workspace_id: str | None = Field(None, description="Workspace ID for multi-tenancy (optional, can come from URL)")
    name: str = Field(..., description="Action name", min_length=1, max_length=255)
    type: ActionType = Field(..., description="Action type")
    description: str = Field(..., description="Action description", max_length=1000)
    version: str = Field(default="1.0.0", description="Action version")
    tags: list[str] = Field(default_factory=list, description="Action tags")
    config_schema: dict[str, Any] = Field(default_factory=dict)
    default_config: dict[str, Any] = Field(default_factory=dict)
    secret_refs: list[str] = Field(default_factory=list)
    # Additional fields to support router use case
    config: dict[str, Any] | None = Field(None, description="Action configuration (alternative to default_config)")
    variables: list[dict[str, Any]] = Field(default_factory=list, description="Action variables")
    enabled: bool = Field(default=True, description="Whether action is enabled")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "slack_notification",
                "type": "REST",
                "description": "Send notifications to Slack",
                "version": "1.0.0",
                "tags": ["notification", "slack"],
                "config_schema": {
                    "type": "object",
                    "properties": {
                        "webhook_url": {"type": "string"},
                        "channel": {"type": "string"},
                    },
                    "required": ["webhook_url", "channel"],
                },
                "default_config": {"channel": "#general"},
                "secret_refs": ["slack_webhook_secret"],
            }
        }
    }


class ActionUpdateRequest(BaseModel):
    """Request model for updating an action."""

    name: str | None = Field(None, description="Action name", min_length=1, max_length=255)
    description: str | None = Field(None, description="Action description", max_length=1000)
    version: str | None = Field(None, description="Action version")
    tags: list[str] | None = Field(None, description="Action tags")
    config_schema: dict[str, Any] | None = Field(None)
    default_config: dict[str, Any] | None = Field(None)
    secret_refs: list[str] | None = Field(None)
    status: ActionStatus | None = Field(None, description="Action status")


# Code run models

class CodeRunLanguage(str, Enum):
    """Code run language."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"


class CodeRunConfig(BaseModel):
    """Configuration for CODE_RUN actions."""
    
    language: CodeRunLanguage = Field(default=CodeRunLanguage.PYTHON, description="Programming language (python, javascript)")
    
    # Cloudflare Workers for Platforms
    worker_name: str | None = Field(None, description="Cloudflare worker name for dispatch")
    dispatch_namespace: str | None = Field(None, description="Dispatch namespace name")
    entry_point: str = Field(default="main", description="Entry point file/function name")
    
    # Execution environment
    timeout: int = Field(default=30, ge=1, le=300, description="Execution timeout in seconds")
    memory_limit_mb: int = Field(default=128, ge=1, le=1024, description="Memory limit in MB")
    
    # Dependencies and imports
    dependencies: list[str] = Field(default_factory=list, description="Required packages/libraries")
    allowed_imports: list[str] = Field(default_factory=list, description="Allowed import modules")
    
    # Security settings
    allow_network: bool = Field(default=False, description="Allow network requests")
    allow_file_ops: bool = Field(default=False, description="Allow file operations")
