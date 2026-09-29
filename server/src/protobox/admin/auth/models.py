"""
Authentication models for JWT and API key management.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from bson import ObjectId
from pydantic import BaseModel, Field


class AuthProvider(str, Enum):
    """Authentication provider types."""

    FIREBASE = "firebase"
    JWT = "jwt"
    API_KEY = "api_key"
    SUPABASE = "supabase"
    CUSTOM = "custom"


class TokenType(str, Enum):
    """JWT token types."""

    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"


class JWTClaims(BaseModel):
    """JWT token claims."""

    sub: str | None = Field(None, description="Subject (user ID)")
    uid: str | None = Field(None, description="User ID (alternative to sub)")
    email: str | None = Field(None, description="User email")
    workspace_id: str | None = Field(None, description="Workspace ID")
    provider: AuthProvider | None = Field(AuthProvider.JWT, description="Auth provider")
    token_type: TokenType | None = Field(TokenType.ACCESS, description="Token type")
    exp: int | None = Field(None, description="Expiration timestamp")
    iat: int | None = Field(None, description="Issued at timestamp")
    nbf: int | None = Field(None, description="Not before timestamp")
    jti: str | None = Field(None, description="JWT ID")

    # Additional fields from our JWT implementation
    role: str | None = Field(None, description="User role")
    permissions: list[str] | None = Field(default_factory=list, description="User permissions")
    metadata: dict[str, Any] | None = Field(
        default_factory=dict, description="Additional metadata"
    )

    @property
    def user_id(self) -> str:
        """Get user ID from either sub or uid field."""
        return self.sub or self.uid or ""


class User(BaseModel):
    """User model that works with both Firebase/JWT and Supabase auth."""

    # Core fields (works with both auth systems)
    id: str = Field(..., description="User ID (Firebase UID or Supabase UUID)")
    email: str = Field(..., description="User email address")
    email_verified: bool = Field(default=False, description="Email verification status")

    # Optional Supabase-specific field
    supabase_id: str | None = Field(
        default=None, description="Supabase user UUID if using Supabase"
    )

    # Auth provider info
    provider: AuthProvider | None = Field(default=AuthProvider.JWT, description="Auth provider")

    # Workspace info
    workspace_id: str | None = Field(default=None, description="Current workspace ID")

    # Permissions
    permissions: list[str] = Field(default_factory=list, description="User permissions")

    # MongoDB extensions
    api_keys: list[str] = Field(default_factory=list, description="List of API key IDs")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional user metadata")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        # Allow ObjectId conversion
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}

    @classmethod
    def from_mongo(cls, data: dict[str, Any]) -> "User":
        """Create User from MongoDB document."""
        if "_id" in data:
            data["id"] = str(data["_id"])
            del data["_id"]
        return cls(**data)

    @classmethod
    def from_jwt_claims(cls, claims: JWTClaims) -> "User":
        """Create User from JWT claims."""
        return cls(
            id=claims.user_id,  # Use Firebase UID for workspace membership lookups
            email=claims.email or "",
            email_verified=True,  # Assume verified if they have a JWT
            provider=claims.provider or AuthProvider.JWT,
            workspace_id=claims.workspace_id,
            permissions=claims.permissions or ["*"],  # Use claims permissions if available
            metadata={
                "from_jwt": True,
                "db_id": (claims.metadata or {}).get("db_id"),  # Store database ID for reference
                **(claims.metadata or {}),  # Include any metadata from claims
            },
        )


class AuthContext(BaseModel):
    """Authentication context for requests."""

    user: User | None = Field(None, description="Authenticated user")
    token_type: TokenType | None = Field(None, description="Token type used")
    provider: AuthProvider | None = Field(None, description="Auth provider used")
    workspace_id: str | None = Field(None, description="Current workspace ID")
    permissions: list[str] = Field(default_factory=list, description="User permissions")


class APIKey(BaseModel):
    """API key model for MongoDB storage."""

    id: str | None = Field(default=None, description="MongoDB ObjectId as string")
    key_id: str = Field(..., description="Public key identifier (ak_...)")
    key_hash: str = Field(..., description="Hashed secret key")
    user_id: str = Field(..., description="MongoDB User ID")
    supabase_user_id: str = Field(..., description="Supabase user UUID")

    name: str = Field(..., description="Human-readable key name")
    permissions: list[str] = Field(default_factory=list, description="API permissions")

    # Metadata
    last_used: datetime | None = Field(default=None, description="Last usage timestamp")
    usage_count: int = Field(default=0, description="Total usage count")

    # Lifecycle
    is_active: bool = Field(default=True, description="Whether key is active")
    expires_at: datetime | None = Field(default=None, description="Expiration timestamp")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}

    @classmethod
    def from_mongo(cls, data: dict[str, Any]) -> "APIKey":
        """Create APIKey from MongoDB document."""
        if "_id" in data:
            data["id"] = str(data["_id"])
            del data["_id"]
        return cls(**data)


# Request/Response models
class CreateAPIKeyRequest(BaseModel):
    """Request to create a new API key."""

    name: str = Field(..., description="Human-readable name for the API key")
    permissions: list[str] = Field(default_factory=list, description="List of permissions")
    expires_days: int | None = Field(default=None, description="Days until expiration")


class CreateAPIKeyResponse(BaseModel):
    """Response with new API key details."""

    key_id: str = Field(..., description="Public key identifier")
    secret_key: str = Field(..., description="Secret key (only shown once)")
    name: str = Field(..., description="Key name")
    permissions: list[str] = Field(..., description="Key permissions")
    expires_at: datetime | None = Field(default=None, description="Expiration date")
    created_at: datetime = Field(..., description="Creation timestamp")


class APIKeyInfo(BaseModel):
    """Public API key information (without secret)."""

    key_id: str = Field(..., description="Public key identifier")
    name: str = Field(..., description="Key name")
    permissions: list[str] = Field(..., description="Key permissions")
    is_active: bool = Field(..., description="Whether key is active")
    last_used: datetime | None = Field(default=None, description="Last usage")
    usage_count: int = Field(..., description="Usage count")
    expires_at: datetime | None = Field(default=None, description="Expiration date")
    created_at: datetime = Field(..., description="Creation timestamp")


class SupabaseUserInfo(BaseModel):
    """Supabase user information from JWT token."""

    sub: str = Field(..., description="Supabase user UUID")
    email: str = Field(..., description="User email")
    email_verified: bool = Field(default=False, description="Email verification status")
    aud: str = Field(..., description="Audience")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    iss: str = Field(..., description="Issuer")


class ServiceAPIKey(BaseModel):
    """Service API key model for service-to-service authentication."""

    id: str | None = Field(default=None, description="MongoDB ObjectId as string")
    service_name: str = Field(..., description="Name of the service (e.g., 'mcp-server')")
    key_hash: str = Field(..., description="Hashed secret key (bcrypt)")
    scopes: list[str] = Field(
        default_factory=list, description="Permissions scopes (e.g., 'workspace:actions:read')"
    )
    description: str | None = Field(default=None, description="Optional description")

    # Metadata
    created_by: str | None = Field(default=None, description="User ID who created this key")
    last_used_at: datetime | None = Field(default=None, description="Last usage timestamp")
    revoked_at: datetime | None = Field(default=None, description="Revocation timestamp")

    # Lifecycle
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}

    @classmethod
    def from_mongo(cls, data: dict[str, Any]) -> "ServiceAPIKey":
        """Create ServiceAPIKey from MongoDB document."""
        if "_id" in data:
            data["id"] = str(data["_id"])
            del data["_id"]
        return cls(**data)

    @property
    def is_active(self) -> bool:
        """Check if service key is active (not revoked)."""
        return self.revoked_at is None


class ServiceContext(BaseModel):
    """Service authentication context for requests."""

    service_name: str = Field(..., description="Name of the authenticated service")
    scopes: list[str] = Field(default_factory=list, description="Service permissions")
    key_id: str | None = Field(default=None, description="Service key ID for audit logging")
    user_id: str | None = Field(default=None, description="End-user ID (from X-User-ID header)")
