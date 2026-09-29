"""MCP Resource models for ProtoBox admin API."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .base import MongoBaseModel


class ResourceType(str, Enum):
    """Resource types for MCP resources."""
    KNOWLEDGE_BASE = "knowledge_base"
    FILE = "file"
    API = "api"
    DATABASE = "database"
    ACTION = "action"
    WORKSPACE_CONFIG = "workspace_config"


class ResourceSourceType(str, Enum):
    """Source types for resource content."""
    KNOWLEDGE_BASE = "knowledge_base"
    UPLOADED_FILE = "uploaded_file"
    EXTERNAL_URL = "external_url"
    API_SCHEMA = "api_schema"
    DATABASE_SCHEMA = "database_schema"
    WORKSPACE_SETTING = "workspace_setting"
    ACTION_DEFINITION = "action_definition"
    EXECUTION_LOG = "execution_log"


class ResourceSource(BaseModel):
    """Source information for a resource."""
    type: ResourceSourceType = Field(..., description="Type of resource source")
    id: str = Field(..., description="Reference ID to source document/file")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional source metadata")

    model_config = {
        "json_schema_extra": {
            "example": {
                "type": "knowledge_base",
                "id": "507f1f77bcf86cd799439011",
                "metadata": {
                    "document_title": "API Guidelines",
                    "page_count": 15,
                    "file_format": "pdf"
                }
            }
        }
    }


class ResourceAccessControl(BaseModel):
    """Access control settings for resources."""
    public: bool = Field(default=False, description="Whether resource is publicly accessible")
    allowed_clients: list[str] = Field(default_factory=list, description="List of allowed client IDs")
    require_authentication: bool = Field(default=True, description="Whether authentication is required")

    model_config = {
        "json_schema_extra": {
            "example": {
                "public": False,
                "allowed_clients": ["fastmcp", "openai-mcp"],
                "require_authentication": True
            }
        }
    }


class MCPResourceModel(MongoBaseModel):
    """MCP Resource model for MongoDB storage."""

    # id, created_by, updated_by, created_at, updated_at inherited from MongoBaseModel
    workspace_id: str = Field(..., description="Workspace ID for multi-tenancy")
    uri: str = Field(..., description="Unique resource identifier (RFC 3986 compliant)", min_length=1, max_length=500)
    name: str = Field(..., description="Human-readable resource name", min_length=1, max_length=255)
    description: str = Field(..., description="Resource description", max_length=1000)

    # Content metadata
    mime_type: str = Field(default="text/plain", description="MIME type of resource content", max_length=100)
    resource_type: ResourceType = Field(..., description="Type of resource")
    source: ResourceSource = Field(..., description="Source information")

    # Content preview and size
    content_preview: str = Field(default="", description="First 500 chars for UI preview", max_length=500)
    size: int = Field(default=0, description="Size in bytes", ge=0)

    # URI template support (RFC 6570)
    is_template: bool = Field(default=False, description="Whether URI supports template variables")
    uri_template: str | None = Field(None, description="RFC 6570 URI template", max_length=500)

    # Status and permissions
    is_active: bool = Field(default=True, description="Whether resource is active")
    access_control: ResourceAccessControl = Field(default_factory=ResourceAccessControl, description="Access control settings")

    # Usage tracking
    access_count: int = Field(default=0, description="Number of times resource was accessed", ge=0)
    last_accessed_at: datetime | None = Field(None, description="Last time resource was accessed")

    @field_validator('uri')
    @classmethod
    def validate_uri(cls, v: str) -> str:
        """Validate URI format."""
        if not v or len(v) < 1:
            raise ValueError("URI cannot be empty")
        # Basic URI validation - should start with scheme or be path-only
        if not (v.startswith(('http://', 'https://', 'file://', '/')) or '/' in v):
            raise ValueError("URI must be a valid path or include scheme")
        return v

    @field_validator('uri_template')
    @classmethod
    def validate_uri_template(cls, v: str | None) -> str | None:
        """Validate URI template format."""
        if v is None:
            return v
        # Basic validation for RFC 6570 URI template syntax
        if '{' in v and '}' in v:
            return v
        raise ValueError("URI template must contain variable placeholders {var}")

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "workspace_id": "6883c972274b0349b71b5ff2",
                "uri": "kb://api-guidelines",
                "name": "API Development Guidelines",
                "description": "Comprehensive guidelines for API development and best practices",
                "mime_type": "text/markdown",
                "resource_type": "knowledge_base",
                "source": {
                    "type": "knowledge_base",
                    "id": "507f1f77bcf86cd799439011",
                    "metadata": {
                        "document_title": "API Guidelines v2.1",
                        "category": "documentation"
                    }
                },
                "content_preview": "# API Development Guidelines\n\nThis document outlines the standards and best practices...",
                "size": 15420,
                "is_template": False,
                "uri_template": None,
                "is_active": True,
                "access_control": {
                    "public": False,
                    "allowed_clients": ["fastmcp"],
                    "require_authentication": True
                },
                "access_count": 25
            }
        }
    }


class MCPResourceCreateRequest(BaseModel):
    """Request model for creating a new MCP resource."""

    workspace_id: str | None = Field(None, description="Workspace ID (optional, can come from URL)")
    uri: str = Field(..., description="Unique resource identifier", min_length=1, max_length=500)
    name: str = Field(..., description="Human-readable resource name", min_length=1, max_length=255)
    description: str = Field(..., description="Resource description", max_length=1000)
    mime_type: str = Field(default="text/plain", description="MIME type", max_length=100)
    resource_type: ResourceType = Field(..., description="Type of resource")
    source: ResourceSource = Field(..., description="Source information")
    is_template: bool = Field(default=False, description="Whether URI supports templates")
    uri_template: str | None = Field(None, description="RFC 6570 URI template", max_length=500)
    is_active: bool = Field(default=True, description="Whether resource is active")
    access_control: ResourceAccessControl = Field(default_factory=ResourceAccessControl, description="Access control")

    model_config = {
        "json_schema_extra": {
            "example": {
                "uri": "kb://user-manual",
                "name": "User Manual",
                "description": "Complete user manual for the application",
                "mime_type": "text/markdown",
                "resource_type": "knowledge_base",
                "source": {
                    "type": "knowledge_base",
                    "id": "507f1f77bcf86cd799439012",
                    "metadata": {"category": "documentation"}
                },
                "is_template": False,
                "is_active": True,
                "access_control": {
                    "public": True,
                    "require_authentication": False
                }
            }
        }
    }


class MCPResourceUpdateRequest(BaseModel):
    """Request model for updating an MCP resource."""

    name: str | None = Field(None, description="Resource name", min_length=1, max_length=255)
    description: str | None = Field(None, description="Resource description", max_length=1000)
    mime_type: str | None = Field(None, description="MIME type", max_length=100)
    is_template: bool | None = Field(None, description="Whether URI supports templates")
    uri_template: str | None = Field(None, description="RFC 6570 URI template", max_length=500)
    is_active: bool | None = Field(None, description="Whether resource is active")
    access_control: ResourceAccessControl | None = Field(None, description="Access control settings")


class MCPResourceContentResponse(BaseModel):
    """Response model for resource content."""

    content: str = Field(..., description="Resource content")
    mime_type: str = Field(..., description="Content MIME type")
    size: int = Field(..., description="Content size in bytes")
    last_modified: datetime | None = Field(None, description="Last modification time")
    etag: str | None = Field(None, description="ETag for caching")

    model_config = {
        "json_schema_extra": {
            "example": {
                "content": "# API Guidelines\n\nThis document provides comprehensive guidelines...",
                "mime_type": "text/markdown",
                "size": 15420,
                "last_modified": "2024-01-15T10:30:00Z",
                "etag": "\"33a64df551425fcc55e4d42a148795d9f25f89d4\""
            }
        }
    }


class MCPResourceListResponse(BaseModel):
    """Response model for listing resources."""

    resources: list[MCPResourceModel] = Field(..., description="List of resources")
    total: int = Field(..., description="Total number of resources")
    resource_type_filter: ResourceType | None = Field(None, description="Applied resource type filter")
    uri_pattern: str | None = Field(None, description="Applied URI pattern filter")


class MCPResourceSyncResponse(BaseModel):
    """Response model for knowledge base sync operation."""

    synced_count: int = Field(..., description="Number of resources synced")
    created_count: int = Field(..., description="Number of new resources created")
    updated_count: int = Field(..., description="Number of resources updated")
    deleted_count: int = Field(..., description="Number of resources deleted")
    errors: list[str] = Field(default_factory=list, description="Any errors encountered during sync")
    duration_ms: int = Field(..., description="Time taken for sync operation")

    model_config = {
        "json_schema_extra": {
            "example": {
                "synced_count": 15,
                "created_count": 3,
                "updated_count": 2,
                "deleted_count": 1,
                "errors": [],
                "duration_ms": 1250
            }
        }
    }


class MCPResourceStatsResponse(BaseModel):
    """Response model for resource usage statistics."""

    total_resources: int = Field(..., description="Total number of resources")
    active_resources: int = Field(..., description="Number of active resources")
    by_type: dict[str, int] = Field(default_factory=dict, description="Count by resource type")
    by_mime_type: dict[str, int] = Field(default_factory=dict, description="Count by MIME type")
    total_size: int = Field(..., description="Total size of all resources in bytes")
    total_accesses: int = Field(..., description="Total number of resource accesses")
    most_accessed: list[dict[str, Any]] = Field(default_factory=list, description="Most frequently accessed resources")

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_resources": 25,
                "active_resources": 23,
                "by_type": {
                    "knowledge_base": 15,
                    "action": 8,
                    "file": 2
                },
                "by_mime_type": {
                    "text/markdown": 12,
                    "application/json": 8,
                    "text/plain": 5
                },
                "total_size": 1048576,
                "total_accesses": 342,
                "most_accessed": [
                    {
                        "uri": "kb://api-guidelines",
                        "name": "API Guidelines",
                        "access_count": 45
                    }
                ]
            }
        }
    }
