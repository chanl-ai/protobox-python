"""MCP OAuth models for OAuth 2.1 authorization server."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MCPOAuthClient(BaseModel):
    """OAuth client registration for MCP access.
    
    Each client is owned by a specific user within a workspace.
    This ensures clear accountability and granular access control.
    """
    
    id: str | None = Field(None, alias="_id")
    client_id: str  # Generated UUID with mcp_ prefix
    client_secret_hash: str  # Bcrypt hashed secret
    client_name: str
    client_type: Literal["confidential", "public"]
    
    # Ownership - Each client belongs to ONE user in ONE workspace
    user_id: str  # The user who owns this client (REQUIRED)
    workspace_id: str  # The workspace context
    
    # OAuth configuration
    redirect_uris: list[str]
    allowed_scopes: list[str] = Field(
        default_factory=lambda: ["mcp:read", "mcp:execute"]
    )
    allowed_grant_types: list[str] = Field(
        default_factory=lambda: ["authorization_code", "refresh_token"]
    )
    
    # Metadata
    description: str | None = None
    logo_uri: str | None = None
    client_uri: str | None = None
    policy_uri: str | None = None
    tos_uri: str | None = None
    
    # Security settings
    require_pkce: bool = True  # Always require PKCE for security
    token_endpoint_auth_method: Literal["client_secret_post", "client_secret_basic"] = "client_secret_post"
    
    # Status and tracking
    status: Literal["active", "revoked"] = "active"
    created_by: str  # Same as user_id, kept for consistency
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_used_at: datetime | None = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={datetime: lambda v: v.isoformat() if v else None}
    )
    
    def model_dump_for_db(self) -> dict:
        """Convert model to dict for database storage."""
        data = self.model_dump(exclude={"id"}, by_alias=True)
        return data
    
    @field_validator("updated_at", mode="before")
    @classmethod
    def set_updated_at(cls, _):
        return datetime.now(UTC)


class MCPAuthorizationCode(BaseModel):
    """Temporary authorization codes for OAuth flow."""
    
    id: str | None = Field(None, alias="_id")
    code: str  # Random secure token
    client_id: str
    user_id: str
    workspace_id: str
    
    # OAuth parameters
    redirect_uri: str
    scope: str
    state: str | None = None
    
    # PKCE parameters (required)
    code_challenge: str
    code_challenge_method: Literal["S256"] = "S256"
    
    # Security
    expires_at: datetime  # 10 minutes from creation
    used: bool = False
    used_at: datetime | None = None
    
    # IP tracking for security
    created_from_ip: str | None = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={datetime: lambda v: v.isoformat() if v else None}
    )
    
    def model_dump_for_db(self) -> dict:
        """Convert model to dict for database storage."""
        data = self.model_dump(exclude={"id"}, by_alias=True)
        return data
    
    @property
    def is_expired(self) -> bool:
        """Check if authorization code is expired."""
        # Make expires_at timezone-aware if it isn't already
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return datetime.now(UTC) >= expires
    
    @property
    def is_valid(self) -> bool:
        """Check if authorization code is still valid."""
        return not self.used and not self.is_expired


class MCPOAuthToken(BaseModel):
    """OAuth access and refresh tokens."""
    
    id: str | None = Field(None, alias="_id")
    token_hash: str  # SHA256 hash of the actual token
    token_type: Literal["access", "refresh"] = "access"
    
    # Association
    client_id: str
    user_id: str
    workspace_id: str
    
    # OAuth parameters
    scope: str
    expires_at: datetime | None  # None for refresh tokens that don't expire
    
    # Refresh token association
    refresh_token_hash: str | None = None  # For access tokens, hash of associated refresh token
    parent_token_hash: str | None = None  # For refresh tokens, previous refresh token (rotation)
    
    # Security tracking
    created_from_ip: str | None = None
    last_used_at: datetime | None = None
    last_used_from_ip: str | None = None
    use_count: int = 0
    
    # Status
    revoked: bool = False
    revoked_at: datetime | None = None
    revoked_reason: str | None = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={datetime: lambda v: v.isoformat() if v else None}
    )
    
    def model_dump_for_db(self) -> dict:
        """Convert model to dict for database storage."""
        data = self.model_dump(exclude={"id"}, by_alias=True)
        return data
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        if self.expires_at is None:
            return False  # No expiry (refresh tokens)
        # Make expires_at timezone-aware if it isn't already
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return datetime.now(UTC) >= expires
    
    @property
    def is_valid(self) -> bool:
        """Check if token is still valid."""
        return not self.revoked and not self.is_expired


class OAuthTokenRequest(BaseModel):
    """Token endpoint request per OAuth 2.1 spec."""
    
    grant_type: Literal["authorization_code", "refresh_token"]
    
    # For authorization_code grant
    code: str | None = None
    redirect_uri: str | None = None
    code_verifier: str | None = None  # PKCE
    
    # For refresh_token grant
    refresh_token: str | None = None
    scope: str | None = None  # Optional scope reduction
    
    # Client authentication
    client_id: str
    client_secret: str | None = None  # Required for confidential clients


class OAuthTokenResponse(BaseModel):
    """Token endpoint response per OAuth 2.1 spec."""
    
    access_token: str
    token_type: Literal["Bearer"] = "Bearer"
    expires_in: int  # Seconds until expiration
    refresh_token: str | None = None
    scope: str


class OAuthErrorResponse(BaseModel):
    """OAuth error response per RFC 6749."""
    
    error: Literal[
        "invalid_request",
        "invalid_client",
        "invalid_grant",
        "unauthorized_client",
        "unsupported_grant_type",
        "invalid_scope",
        "server_error",
        "temporarily_unavailable"
    ]
    error_description: str | None = None
    error_uri: str | None = None


class MCPOAuthClientCreate(BaseModel):
    """Request to create a new OAuth client."""
    
    client_name: str
    redirect_uris: list[str]
    client_type: Literal["confidential", "public"] = "confidential"
    description: str | None = None
    logo_uri: str | None = None
    client_uri: str | None = None
    scopes: list[str] = Field(
        default_factory=lambda: ["mcp:read", "mcp:execute"]
    )


class MCPOAuthClientResponse(BaseModel):
    """Response when creating a new OAuth client."""
    
    client_id: str
    client_secret: str  # Only returned once at creation!
    client_name: str
    redirect_uris: list[str]
    allowed_scopes: list[str]
    created_at: datetime
    
    # Important security notice
    message: str = "Store the client_secret securely. It will not be shown again."