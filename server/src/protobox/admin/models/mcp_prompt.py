"""MCP Prompt models for ProtoBox admin API."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .base import MongoBaseModel


class PromptMessageRole(str, Enum):
    """Message roles in prompt templates."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class PromptArgumentType(str, Enum):
    """Argument types for prompt validation."""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class PromptMessage(BaseModel):
    """Individual message in a prompt template."""
    role: PromptMessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content with optional {{variables}}")

    model_config = {
        "json_schema_extra": {
            "example": {
                "role": "system",
                "content": "You are a helpful assistant that reviews code for {{language}} projects."
            }
        }
    }


class PromptArgument(BaseModel):
    """Argument definition for prompt templates."""
    name: str = Field(..., description="Argument name", min_length=1, max_length=100)
    description: str = Field(..., description="Argument description", max_length=500)
    type: PromptArgumentType = Field(default=PromptArgumentType.STRING, description="Argument type")
    required: bool = Field(default=True, description="Whether argument is required")
    default: Any = Field(None, description="Default value if not required")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "language",
                "description": "Programming language to review",
                "type": "string",
                "required": True,
                "default": None
            }
        }
    }


class MCPPromptModel(MongoBaseModel):
    """MCP Prompt model for MongoDB storage."""

    # id, created_by, updated_by, created_at, updated_at inherited from MongoBaseModel
    workspace_id: str = Field(..., description="Workspace ID for multi-tenancy")
    name: str = Field(..., description="Prompt name (unique within workspace)", min_length=1, max_length=255)
    description: str = Field(..., description="Prompt description", max_length=1000)

    # Prompt template structure
    messages: list[PromptMessage] = Field(..., description="Prompt template messages", min_length=1)
    arguments: list[PromptArgument] = Field(default_factory=list, description="Expected arguments")

    # Template inheritance fields
    extends: str | None = Field(None, description="ID of parent template to inherit from")
    is_template: bool = Field(default=False, description="Mark prompt as reusable template")
    override_messages: list[PromptMessage] | None = Field(None, description="Messages that override parent")
    override_arguments: list[PromptArgument] | None = Field(None, description="Arguments that override parent")
    workspace_variables: dict[str, Any] | None = Field(None, description="Workspace-level variables")

    # Organization and metadata
    category: str = Field(default="general", description="Category for UI organization", max_length=100)
    tags: list[str] = Field(default_factory=list, description="Tags for categorization", max_items=20)

    # Status and permissions
    is_active: bool = Field(default=True, description="Whether prompt is active")
    is_system: bool = Field(default=False, description="System-provided vs user-created")

    # Usage tracking
    usage_count: int = Field(default=0, description="Number of times prompt was used", ge=0)
    last_used_at: datetime | None = Field(None, description="Last time prompt was used")

    # Version tracking
    version: int = Field(default=1, description="Current version number", ge=1)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "workspace_id": "6883c972274b0349b71b5ff2",
                "name": "code_review",
                "description": "Review code for quality, security, and best practices",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a senior developer reviewing {{language}} code. Focus on {{focus_areas}}."
                    },
                    {
                        "role": "user",
                        "content": "Please review this code:\n\n{{code}}"
                    }
                ],
                "arguments": [
                    {
                        "name": "language",
                        "description": "Programming language",
                        "type": "string",
                        "required": True
                    },
                    {
                        "name": "code",
                        "description": "Code to review",
                        "type": "string",
                        "required": True
                    },
                    {
                        "name": "focus_areas",
                        "description": "Areas to focus on",
                        "type": "string",
                        "required": False,
                        "default": "quality, security, performance"
                    }
                ],
                "category": "development",
                "tags": ["code", "review", "quality"],
                "is_active": True,
                "is_system": True
            }
        }
    }


class MCPPromptCreateRequest(BaseModel):
    """Request model for creating a new MCP prompt."""

    workspace_id: str | None = Field(None, description="Workspace ID (optional, can come from URL)")
    name: str = Field(..., description="Prompt name", min_length=1, max_length=255)
    description: str = Field(..., description="Prompt description", max_length=1000)
    messages: list[PromptMessage] = Field(..., description="Prompt template messages", min_length=1)
    arguments: list[PromptArgument] = Field(default_factory=list, description="Expected arguments")

    # Template inheritance fields
    extends: str | None = Field(None, description="ID of parent template to inherit from")
    is_template: bool = Field(default=False, description="Mark prompt as reusable template")
    override_messages: list[PromptMessage] | None = Field(None, description="Messages that override parent")
    override_arguments: list[PromptArgument] | None = Field(None, description="Arguments that override parent")
    workspace_variables: dict[str, Any] | None = Field(None, description="Workspace-level variables")

    category: str = Field(default="general", description="Category for organization", max_length=100)
    tags: list[str] = Field(default_factory=list, description="Tags for categorization", max_items=20)
    is_active: bool = Field(default=True, description="Whether prompt is active")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "api_documentation",
                "description": "Generate API documentation from code",
                "messages": [
                    {
                        "role": "system",
                        "content": "Generate comprehensive API documentation for the {{endpoint_type}} endpoint."
                    },
                    {
                        "role": "user",
                        "content": "{{code}}"
                    }
                ],
                "arguments": [
                    {
                        "name": "endpoint_type",
                        "description": "Type of API endpoint",
                        "type": "string",
                        "required": True
                    },
                    {
                        "name": "code",
                        "description": "API endpoint code",
                        "type": "string",
                        "required": True
                    }
                ],
                "category": "documentation",
                "tags": ["api", "documentation"],
                "is_active": True
            }
        }
    }


class MCPPromptUpdateRequest(BaseModel):
    """Request model for updating an MCP prompt."""

    name: str | None = Field(None, description="Prompt name", min_length=1, max_length=255)
    description: str | None = Field(None, description="Prompt description", max_length=1000)
    messages: list[PromptMessage] | None = Field(None, description="Prompt template messages")
    arguments: list[PromptArgument] | None = Field(None, description="Expected arguments")

    # Template inheritance fields
    extends: str | None = Field(None, description="ID of parent template to inherit from")
    is_template: bool | None = Field(None, description="Mark prompt as reusable template")
    override_messages: list[PromptMessage] | None = Field(None, description="Messages that override parent")
    override_arguments: list[PromptArgument] | None = Field(None, description="Arguments that override parent")
    workspace_variables: dict[str, Any] | None = Field(None, description="Workspace-level variables")

    category: str | None = Field(None, description="Category for organization", max_length=100)
    tags: list[str] | None = Field(None, description="Tags for categorization", max_items=20)
    is_active: bool | None = Field(None, description="Whether prompt is active")


class MCPPromptExecuteRequest(BaseModel):
    """Request model for executing/testing a prompt with arguments."""

    arguments: dict[str, Any] = Field(default_factory=dict, description="Arguments to substitute in template")

    model_config = {
        "json_schema_extra": {
            "example": {
                "arguments": {
                    "language": "Python",
                    "code": "def hello():\n    print('Hello, world!')",
                    "focus_areas": "code style, documentation"
                }
            }
        }
    }


class MCPPromptExecuteResponse(BaseModel):
    """Response model for prompt execution."""

    rendered_messages: list[dict[str, str]] = Field(..., description="Messages with variables substituted")
    argument_validation: dict[str, Any] = Field(..., description="Validation results for provided arguments")
    execution_time_ms: int = Field(..., description="Time taken to render template")

    model_config = {
        "json_schema_extra": {
            "example": {
                "rendered_messages": [
                    {
                        "role": "system",
                        "content": "You are a senior developer reviewing Python code. Focus on code style, documentation."
                    },
                    {
                        "role": "user",
                        "content": "Please review this code:\n\ndef hello():\n    print('Hello, world!')"
                    }
                ],
                "argument_validation": {
                    "valid": True,
                    "missing_required": [],
                    "invalid_types": [],
                    "warnings": []
                },
                "execution_time_ms": 15
            }
        }
    }


class MCPPromptListResponse(BaseModel):
    """Response model for listing prompts."""

    prompts: list[MCPPromptModel] = Field(..., description="List of prompts")
    total: int = Field(..., description="Total number of prompts")
    category_filter: str | None = Field(None, description="Applied category filter")
    tags_filter: list[str] | None = Field(None, description="Applied tags filter")


class MCPPromptResponse(BaseModel):
    """Response model for single prompt."""

    prompt: MCPPromptModel = Field(..., description="Prompt details")
    usage_stats: dict[str, Any] = Field(default_factory=dict, description="Usage statistics")

    model_config = {
        "json_schema_extra": {
            "example": {
                "prompt": {
                    "id": "507f1f77bcf86cd799439011",
                    "workspace_id": "6883c972274b0349b71b5ff2",
                    "name": "code_review",
                    "description": "Review code for quality and security",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a senior developer reviewing {{language}} code."
                        }
                    ],
                    "arguments": [
                        {
                            "name": "language",
                            "description": "Programming language",
                            "type": "string",
                            "required": True
                        }
                    ],
                    "category": "development",
                    "tags": ["code", "review"],
                    "is_active": True,
                    "is_system": True,
                    "usage_count": 42,
                    "created_at": "2024-01-01T00:00:00Z"
                },
                "usage_stats": {
                    "last_7_days": 12,
                    "last_30_days": 42,
                    "avg_per_day": 1.4
                }
            }
        }
    }


class MCPPromptTemplateListResponse(BaseModel):
    """Response model for listing prompt templates."""

    templates: list[MCPPromptModel] = Field(..., description="List of prompt templates")
    total: int = Field(..., description="Total number of templates")


class MCPPromptExtendRequest(BaseModel):
    """Request model for creating a prompt extending from a template."""

    name: str = Field(..., description="New prompt name", min_length=1, max_length=255)
    description: str = Field(..., description="New prompt description", max_length=1000)
    override_messages: list[PromptMessage] | None = Field(None, description="Messages that override parent")
    override_arguments: list[PromptArgument] | None = Field(None, description="Arguments that override parent")
    workspace_variables: dict[str, Any] | None = Field(None, description="Workspace-level variables")
    category: str = Field(default="general", description="Category for organization", max_length=100)
    tags: list[str] = Field(default_factory=list, description="Tags for categorization", max_items=20)
    is_active: bool = Field(default=True, description="Whether prompt is active")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "python_code_review",
                "description": "Code review specialized for Python projects",
                "override_arguments": [
                    {
                        "name": "language",
                        "description": "Programming language",
                        "type": "string",
                        "required": True,
                        "default": "Python"
                    }
                ],
                "workspace_variables": {
                    "project_type": "backend",
                    "framework": "FastAPI"
                },
                "category": "development",
                "tags": ["python", "code", "review"],
                "is_active": True
            }
        }
    }


class MCPPromptResolvedResponse(BaseModel):
    """Response model for fully resolved prompt with inheritance."""

    prompt: MCPPromptModel = Field(..., description="Original prompt")
    resolved_messages: list[PromptMessage] = Field(..., description="Messages with inheritance resolved")
    resolved_arguments: list[PromptArgument] = Field(..., description="Arguments with inheritance resolved")
    resolved_variables: dict[str, Any] = Field(default_factory=dict, description="Resolved workspace variables")
    inheritance_chain: list[str] = Field(..., description="List of template IDs in inheritance chain")
    resolution_depth: int = Field(..., description="Number of inheritance levels resolved")

    model_config = {
        "json_schema_extra": {
            "example": {
                "prompt": {
                    "id": "507f1f77bcf86cd799439011",
                    "name": "python_code_review",
                    "extends": "507f1f77bcf86cd799439010"
                },
                "resolved_messages": [
                    {
                        "role": "system",
                        "content": "You are a senior Python developer reviewing code for {{project_type}} projects."
                    }
                ],
                "resolved_arguments": [
                    {
                        "name": "code",
                        "description": "Python code to review",
                        "type": "string",
                        "required": True
                    }
                ],
                "resolved_variables": {
                    "project_type": "backend",
                    "framework": "FastAPI"
                },
                "inheritance_chain": ["507f1f77bcf86cd799439010"],
                "resolution_depth": 1
            }
        }
    }


class PromptVersionModel(MongoBaseModel):
    """Model for storing prompt version history."""

    prompt_id: str = Field(..., description="Reference to main prompt")
    version: int = Field(..., description="Version number", ge=1)

    # Snapshot of prompt data at this version
    name: str = Field(..., description="Prompt name at this version")
    description: str = Field(..., description="Prompt description at this version")
    messages: list[PromptMessage] = Field(..., description="Messages at this version")
    arguments: list[PromptArgument] = Field(default_factory=list, description="Arguments at this version")
    category: str = Field(..., description="Category at this version")
    tags: list[str] = Field(default_factory=list, description="Tags at this version")

    # Version metadata
    change_summary: str = Field(default="", description="Summary of changes in this version")

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "prompt_id": "507f1f77bcf86cd799439011",
                "version": 2,
                "name": "code_review",
                "description": "Review code for quality and security",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a senior developer reviewing code."
                    }
                ],
                "arguments": [],
                "category": "development",
                "tags": ["code", "review"],
                "change_summary": "Updated system message for clarity",
                "created_at": "2024-01-02T10:00:00Z",
                "created_by": "user_123"
            }
        }
    }


class PromptVersionListResponse(BaseModel):
    """Response model for listing prompt versions."""

    versions: list[PromptVersionModel] = Field(..., description="List of versions")
    total: int = Field(..., description="Total number of versions")
    current_version: int = Field(..., description="Current active version")
