"""
Workspace and authentication settings for MCP server.

This module provides centralized configuration for workspace isolation,
authentication, and multi-tenancy support.
"""

import os
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

# Removed deprecated AuthMode - now always uses Firebase authentication


class WorkspaceIsolationMode(str, Enum):
    """Workspace isolation enforcement mode."""

    STRICT = "strict"  # All operations require workspace context
    RELAXED = "relaxed"  # Some operations allowed without workspace
    DISABLED = "disabled"  # No workspace isolation (development only)


class DatabaseSettings(BaseModel):
    """Database configuration settings."""

    url: str = Field(
        default="mongodb://localhost:27017/mcp_server", description="MongoDB connection URL"
    )
    database_name: str | None = Field(
        default=None, description="Override database name (extracted from URL if not provided)"
    )
    auth_source: str = Field(default="admin", description="Authentication database")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure MongoDB URL is properly formatted."""
        if not v.startswith(("mongodb://", "mongodb+srv://")):
            raise ValueError("MongoDB URL must start with mongodb:// or mongodb+srv://")
        return v


class WorkspaceSettings(BaseModel):
    """Workspace and multi-tenancy settings."""

    isolation_mode: WorkspaceIsolationMode = Field(
        default=WorkspaceIsolationMode.STRICT, description="Workspace isolation enforcement mode"
    )
    default_workspace: str | None = Field(
        default=None, description="Default workspace for development (only used in RELAXED mode)"
    )
    workspace_header: str = Field(
        default="X-Workspace-ID", description="HTTP header for workspace identification"
    )
    allow_cross_workspace_admin: bool = Field(
        default=False, description="Allow admin users to access all workspaces"
    )


class AuthenticationSettings(BaseModel):
    """Authentication configuration - now always uses Firebase authentication."""
    api_key_header: str = Field(default="Authorization", description="HTTP header for API key")
    api_key_prefix: str = Field(default="Bearer", description="Prefix for API key in header")
    require_workspace_in_token: bool = Field(
        default=True, description="Require workspace ID to be embedded in auth token"
    )

    # Supabase-specific settings
    supabase_url: str | None = Field(default=None, description="Supabase project URL")
    supabase_anon_key: str | None = Field(default=None, description="Supabase anonymous key")
    supabase_jwt_secret: str | None = Field(
        default=None, description="Supabase JWT secret for token validation"
    )


class SecuritySettings(BaseModel):
    """Security configuration."""

    enable_rate_limiting: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(
        default=100, description="Maximum requests per minute per workspace"
    )
    enable_audit_logging: bool = Field(
        default=True, description="Enable audit logging for all operations"
    )
    encrypt_sensitive_data: bool = Field(
        default=True, description="Encrypt sensitive data in database"
    )
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["*"], description="CORS allowed origins"
    )


class MCPWorkspaceConfig(BaseModel):
    """Complete workspace configuration for MCP server."""

    database: DatabaseSettings = Field(
        default_factory=DatabaseSettings, description="Database configuration"
    )
    workspace: WorkspaceSettings = Field(
        default_factory=WorkspaceSettings, description="Workspace settings"
    )
    authentication: AuthenticationSettings = Field(
        default_factory=AuthenticationSettings, description="Authentication settings"
    )
    security: SecuritySettings = Field(
        default_factory=SecuritySettings, description="Security settings"
    )

    @classmethod
    def from_env(cls) -> "MCPWorkspaceConfig":
        """Create configuration from environment variables."""
        # Database settings
        # Support multiple env var names for MongoDB URL (prefer MCP_MONGODB_URL for clarity)
        mongodb_url = (
            os.getenv("MCP_MONGODB_URL")
            or os.getenv("MONGODB_URI")
            or os.getenv("MONGODB_URL")
            or "mongodb://localhost:27017/mcp_server"
        )

        database = DatabaseSettings(
            url=mongodb_url,
            database_name=os.getenv("MONGODB_DATABASE"),
            auth_source=os.getenv("MONGODB_AUTH_SOURCE", "admin"),
        )

        # Workspace settings
        workspace = WorkspaceSettings(
            isolation_mode=WorkspaceIsolationMode(
                os.getenv("WORKSPACE_ISOLATION_MODE", "strict").lower()
            ),
            default_workspace=os.getenv("DEFAULT_WORKSPACE"),
            workspace_header=os.getenv("WORKSPACE_HEADER", "X-Workspace-ID"),
            allow_cross_workspace_admin=os.getenv("ALLOW_CROSS_WORKSPACE_ADMIN", "false").lower()
            == "true",
        )

        # Authentication settings - now always Firebase
        authentication = AuthenticationSettings(
            api_key_header=os.getenv("API_KEY_HEADER", "Authorization"),
            api_key_prefix=os.getenv("API_KEY_PREFIX", "Bearer"),
            require_workspace_in_token=os.getenv("REQUIRE_WORKSPACE_IN_TOKEN", "true").lower()
            == "true",
            supabase_url=os.getenv("SUPABASE_URL"),
            supabase_anon_key=os.getenv("SUPABASE_ANON_KEY"),
            supabase_jwt_secret=os.getenv("SUPABASE_JWT_SECRET"),
        )

        # Security settings
        security = SecuritySettings(
            enable_rate_limiting=os.getenv("ENABLE_RATE_LIMITING", "true").lower() == "true",
            rate_limit_requests=int(os.getenv("RATE_LIMIT_REQUESTS", "100")),
            enable_audit_logging=os.getenv("ENABLE_AUDIT_LOGGING", "true").lower() == "true",
            encrypt_sensitive_data=os.getenv("ENCRYPT_SENSITIVE_DATA", "true").lower() == "true",
            allowed_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
        )

        return cls(
            database=database, workspace=workspace, authentication=authentication, security=security
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump()


# Global configuration instance
_config: MCPWorkspaceConfig | None = None


def get_workspace_config() -> MCPWorkspaceConfig:
    """Get the workspace configuration singleton."""
    global _config
    if _config is None:
        _config = MCPWorkspaceConfig.from_env()
    return _config


def set_workspace_config(config: MCPWorkspaceConfig) -> None:
    """Set the workspace configuration (for testing)."""
    global _config
    _config = config
