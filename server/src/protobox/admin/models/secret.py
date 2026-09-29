"""Secret models for admin API."""

from datetime import datetime
from typing import Any

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, validator

from ..secrets.types import SecretType


class SecretModel(BaseModel):
    """Secret data model for MongoDB storage."""

    id: str | None = Field(None, alias="_id", description="Secret ID")
    workspace_id: str = Field(..., description="Workspace ID for multi-tenancy")
    user_id: str = Field(..., description="User who created the secret")

    # Secret identification
    name: str = Field(..., min_length=1, max_length=100, description="Human-readable secret name")
    description: str | None = Field(None, max_length=500, description="Secret description")
    secret_type: SecretType = Field(..., description="Type of secret")

    # Encrypted data
    encrypted_value: str = Field(..., description="AES-256 encrypted secret value")
    salt: str = Field(..., description="Salt used for encryption")
    iv: str = Field(..., description="Initialization vector for AES-GCM")
    tag: str = Field(..., description="Authentication tag for AES-GCM")

    # Metadata
    tags: list[str] = Field(default_factory=list, description="Tags for organization")
    is_active: bool = Field(default=True, description="Whether the secret is active")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )
    expires_at: datetime | None = Field(None, description="Expiration timestamp")
    last_used_at: datetime | None = Field(None, description="Last usage timestamp")

    # Usage tracking
    usage_count: int = Field(default=0, description="Number of times secret has been used")
    max_usage_count: int | None = Field(None, description="Maximum allowed usage count")

    # Validation
    @validator("name")
    def validate_name(cls, v):
        """Validate secret name contains only allowed characters."""
        if not v.replace("_", "").replace("-", "").replace(" ", "").isalnum():
            raise ValueError(
                "Name must contain only alphanumeric characters, spaces, hyphens, and underscores"
            )
        return v

    @validator("tags")
    def validate_tags(cls, v):
        """Validate tags format."""
        if len(v) > 10:
            raise ValueError("Maximum 10 tags allowed")
        for tag in v:
            if not isinstance(tag, str) or len(tag) > 50:
                raise ValueError("Each tag must be a string with maximum 50 characters")
        return v

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "workspace_id": "workspace_123",
                "user_id": "user_456",
                "name": "api_key_production",
                "description": "Production API key for external service",
                "secret_type": "API_KEY",
                "tags": ["production", "api", "external"],
                "is_active": True,
            }
        },
    )

    def model_dump_for_db(self) -> dict[str, Any]:
        """Convert model to dictionary for MongoDB storage."""
        data = self.model_dump(by_alias=True, exclude_none=True)
        # Remove _id if it's None to let MongoDB generate it
        if data.get("_id") is None:
            data.pop("_id", None)
        return data

    def is_expired(self) -> bool:
        """Check if secret is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def is_usage_exceeded(self) -> bool:
        """Check if secret usage count has been exceeded."""
        if self.max_usage_count is None:
            return False
        return self.usage_count >= self.max_usage_count

    def can_be_used(self) -> bool:
        """Check if secret can be used (active, not expired, not usage exceeded)."""
        return self.is_active and not self.is_expired() and not self.is_usage_exceeded()

    def increment_usage(self) -> None:
        """Increment usage count and update last used timestamp."""
        self.usage_count += 1
        self.last_used_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class SecretCreateRequest(BaseModel):
    """Request model for creating a secret."""

    workspace_id: str = Field(..., description="Workspace ID")
    name: str = Field(..., min_length=1, max_length=100, description="Secret name")
    description: str | None = Field(None, max_length=500, description="Secret description")
    secret_type: SecretType = Field(..., description="Type of secret")
    secret_value: str = Field(..., min_length=1, description="Plaintext secret value to encrypt")

    # Optional fields
    tags: list[str] = Field(default_factory=list, description="Tags for organization")
    expires_at: datetime | None = Field(None, description="Expiration timestamp")
    max_usage_count: int | None = Field(None, ge=1, description="Maximum usage count")

    # Validation
    @validator("name")
    def validate_name(cls, v):
        """Validate secret name."""
        if not v.replace("_", "").replace("-", "").replace(" ", "").isalnum():
            raise ValueError(
                "Name must contain only alphanumeric characters, spaces, hyphens, and underscores"
            )
        return v

    @validator("secret_value")
    def validate_secret_value(cls, v):
        """Validate secret value is not empty."""
        if not v.strip():
            raise ValueError("Secret value cannot be empty")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workspace_id": "workspace_123",
                "name": "api_key_production",
                "description": "Production API key for external service",
                "secret_type": "API_KEY",
                "secret_value": "<your-api-key>",
                "tags": ["production", "api"],
            }
        }
    )


class SecretUpdateRequest(BaseModel):
    """Request model for updating a secret."""

    name: str | None = Field(
        None, min_length=1, max_length=100, description="Updated secret name"
    )
    description: str | None = Field(None, max_length=500, description="Updated description")
    secret_value: str | None = Field(None, min_length=1, description="Updated secret value")

    # Optional fields
    tags: list[str] | None = Field(None, description="Updated tags")
    is_active: bool | None = Field(None, description="Updated active status")
    expires_at: datetime | None = Field(None, description="Updated expiration")
    max_usage_count: int | None = Field(None, ge=1, description="Updated max usage count")

    # Validation
    @validator("name")
    def validate_name(cls, v):
        """Validate secret name if provided."""
        if v is not None and not v.replace("_", "").replace("-", "").replace(" ", "").isalnum():
            raise ValueError(
                "Name must contain only alphanumeric characters, spaces, hyphens, and underscores"
            )
        return v

    @validator("secret_value")
    def validate_secret_value(cls, v):
        """Validate secret value if provided."""
        if v is not None and not v.strip():
            raise ValueError("Secret value cannot be empty")
        return v


class SecretListResponse(BaseModel):
    """Response model for listing secrets (without sensitive data)."""

    id: str = Field(..., description="Secret ID")
    workspace_id: str = Field(..., description="Workspace ID")
    user_id: str = Field(..., description="User ID who created the secret")

    name: str = Field(..., description="Secret name")
    description: str | None = Field(None, description="Secret description")
    secret_type: SecretType = Field(..., description="Type of secret")

    tags: list[str] = Field(..., description="Secret tags")
    is_active: bool = Field(..., description="Whether secret is active")

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    expires_at: datetime | None = Field(None, description="Expiration timestamp")
    last_used_at: datetime | None = Field(None, description="Last usage timestamp")

    # Usage tracking
    usage_count: int = Field(..., description="Usage count")
    max_usage_count: int | None = Field(None, description="Maximum usage count")

    # Status indicators
    is_expired: bool = Field(..., description="Whether secret is expired")
    is_usage_exceeded: bool = Field(..., description="Whether usage count exceeded")
    can_be_used: bool = Field(..., description="Whether secret can be used")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "workspace_id": "workspace_123",
                "user_id": "user_456",
                "name": "api_key_production",
                "description": "Production API key",
                "secret_type": "API_KEY",
                "tags": ["production", "api"],
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "usage_count": 15,
                "is_expired": False,
                "is_usage_exceeded": False,
                "can_be_used": True,
            }
        }
    )


class SecretUsageLog(BaseModel):
    """Model for secret usage logging."""

    id: str | None = Field(None, alias="_id", description="Log entry ID")
    secret_id: str = Field(..., description="ID of the secret that was used")
    workspace_id: str = Field(..., description="Workspace ID")
    user_id: str = Field(..., description="User who accessed the secret")

    # Usage details
    action_id: str | None = Field(None, description="ID of action that used the secret")
    access_method: str = Field(..., description="How the secret was accessed")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When secret was accessed"
    )

    # Context
    ip_address: str | None = Field(None, description="IP address of the request")
    user_agent: str | None = Field(None, description="User agent string")
    additional_context: dict[str, Any] = Field(
        default_factory=dict, description="Additional context"
    )

    model_config = ConfigDict(populate_by_name=True, json_encoders={ObjectId: str})

    def model_dump_for_db(self) -> dict[str, Any]:
        """Convert model to dictionary for MongoDB storage."""
        data = self.model_dump(by_alias=True, exclude_none=True)
        if data.get("_id") is None:
            data.pop("_id", None)
        return data
