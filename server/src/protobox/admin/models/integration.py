"""Integration models for managing third-party integrations."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, validator


class IntegrationType(str, Enum):
    """Supported integration types."""

    # Google Services
    GOOGLE_CALENDAR = "google_calendar"
    GMAIL = "gmail"
    GOOGLE_DRIVE = "google_drive"
    GOOGLE_SHEETS = "google_sheets"
    GOOGLE_DOCS = "google_docs"
    GOOGLE_ANALYTICS = "google_analytics"
    GOOGLE_ADS = "google_ads"
    
    # Other Services
    HUBSPOT = "hubspot"
    SLACK = "slack"
    SHOPIFY = "shopify"
    STRIPE = "stripe"
    MICROSOFT_365 = "microsoft_365"
    SALESFORCE = "salesforce"
    GITHUB = "github"
    LINKEDIN = "linkedin"
    OPENAI = "openai"
    TWILIO = "twilio"
    SENDGRID = "sendgrid"
    NOTION = "notion"
    RESEND = "resend"
    ANTHROPIC = "anthropic"
    AIRTABLE = "airtable"


class IntegrationStatus(str, Enum):
    """Integration connection status."""

    NOT_CONNECTED = "not_connected"
    CONNECTED = "connected"
    ERROR = "error"
    SETUP = "setup"


class AuthType(str, Enum):
    """Authentication types for integrations."""

    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    WEBHOOK = "webhook"
    NONE = "none"


class OAuth2TokenData(BaseModel):
    """OAuth2 token data."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"
    expires_in: int | None = None
    expires_at: datetime | None = None
    scope: str | None = None


class IntegrationAction(BaseModel):
    """Available action for an integration."""

    action_name: str
    display_name: str
    description: str
    required_scopes: list[str] = Field(default_factory=list)


class IntegrationUIConfig(BaseModel):
    """UI configuration for displaying integration."""

    integration_type: IntegrationType
    display_name: str
    description: str
    icon_url: str | None = None
    category: str
    auth_type: AuthType
    oauth_config: dict[str, Any] | None = None
    available_actions: list[IntegrationAction] = Field(default_factory=list)
    required_scopes: list[str] = Field(default_factory=list)
    setup_instructions: str | None = None


class IntegrationModel(BaseModel):
    """Integration model for database storage."""

    id: str | None = Field(None, alias="_id")
    workspace_id: str
    integration_type: IntegrationType
    status: IntegrationStatus = IntegrationStatus.NOT_CONNECTED
    auth_type: AuthType

    # Connection metadata
    connected_at: datetime | None = None
    connected_by: str | None = None
    last_sync_at: datetime | None = None

    # Configuration
    config: dict[str, Any] = Field(default_factory=dict)

    # OAuth specific
    oauth_data: OAuth2TokenData | None = None
    oauth_secret_id: str | None = None  # Reference to encrypted OAuth secret

    # API Key specific
    api_key_secret_id: str | None = None

    # Error information
    error_message: str | None = None
    error_at: datetime | None = None

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(
        populate_by_name=True, json_encoders={datetime: lambda v: v.isoformat() if v else None}
    )

    def model_dump_for_db(self) -> dict:
        """Convert model to dict for database storage."""
        data = self.model_dump(exclude={"id"}, by_alias=True)
        # Convert enums to strings
        data["integration_type"] = self.integration_type.value
        data["status"] = self.status.value
        data["auth_type"] = self.auth_type.value
        return data

    @validator("updated_at", pre=True, always=True)
    def set_updated_at(cls, v):
        return datetime.now(UTC)


class IntegrationCreateRequest(BaseModel):
    """Request to create a new integration."""

    workspace_id: str
    integration_type: IntegrationType
    auth_type: AuthType
    config: dict[str, Any] = Field(default_factory=dict)


class IntegrationUpdateRequest(BaseModel):
    """Request to update an integration."""

    status: IntegrationStatus | None = None
    config: dict[str, Any] | None = None
    oauth_data: OAuth2TokenData | None = None
    api_key_secret_id: str | None = None
    error_message: str | None = None
