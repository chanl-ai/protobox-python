"""Base classes for all integration types."""

import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from ..models.integration import IntegrationType

logger = logging.getLogger(__name__)


class AuthMethod(str, Enum):
    """Authentication methods for integrations."""
    
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    WEBHOOK = "webhook"
    BASIC_AUTH = "basic_auth"
    CUSTOM = "custom"


class IntegrationCapability(str, Enum):
    """Capabilities that integrations can provide."""
    
    # Communication
    SEND_MESSAGE = "send_message"
    SEND_EMAIL = "send_email"
    SEND_SMS = "send_sms"
    MAKE_CALL = "make_call"
    
    # Calendar & Scheduling
    CREATE_EVENT = "create_event"
    CHECK_AVAILABILITY = "check_availability"
    UPDATE_EVENT = "update_event"
    DELETE_EVENT = "delete_event"
    
    # CRM & Sales
    CREATE_LEAD = "create_lead"
    CREATE_CONTACT = "create_contact"
    UPDATE_CONTACT = "update_contact"
    CREATE_DEAL = "create_deal"
    UPDATE_DEAL = "update_deal"
    CREATE_COMPANY = "create_company"
    TRACK_ACTIVITY = "track_activity"
    
    # File Management
    UPLOAD_FILE = "upload_file"
    DOWNLOAD_FILE = "download_file"
    SHARE_FILE = "share_file"
    SEARCH_FILES = "search_files"
    
    # Email Management
    READ_EMAIL = "read_email"
    SEARCH_EMAIL = "search_email"
    MANAGE_DRAFTS = "manage_drafts"
    
    # Document Management
    CREATE_DOCUMENT = "create_document"
    READ_DOCUMENT = "read_document"
    UPDATE_DOCUMENT = "update_document"
    EXPORT_DOCUMENT = "export_document"
    
    # Spreadsheet Management
    READ_DATA = "read_data"
    WRITE_DATA = "write_data"
    CREATE_SPREADSHEET = "create_spreadsheet"
    UPDATE_SPREADSHEET = "update_spreadsheet"
    
    # Project Management
    CREATE_ISSUE = "create_issue"
    UPDATE_TASK = "update_task"
    CREATE_PROJECT = "create_project"
    
    # AI & Analytics
    GENERATE_TEXT = "generate_text"
    ANALYZE_DATA = "analyze_data"
    TRACK_EVENTS = "track_events"
    VIEW_REPORTS = "view_reports"
    MANAGE_CAMPAIGNS = "manage_campaigns"
    ANALYZE_TRAFFIC = "analyze_traffic"
    
    # E-commerce & Payments
    PROCESS_PAYMENT = "process_payment"
    CREATE_INVOICE = "create_invoice"
    TRACK_ORDER = "track_order"


class ActionTemplate(BaseModel):
    """Template for creating actions from integrations."""
    
    id: str
    name: str
    description: str
    category: str
    capability: IntegrationCapability
    required_integrations: list[IntegrationType]
    optional_integrations: list[IntegrationType] = Field(default_factory=list)
    config_schema: dict[str, Any]
    default_config: dict[str, Any] = Field(default_factory=dict)
    integration_config: dict[str, dict[str, Any]] = Field(default_factory=dict)
    
    def is_available(self, connected_integrations: list[IntegrationType]) -> bool:
        """Check if this action template can be used with current integrations."""
        return all(req in connected_integrations for req in self.required_integrations)
    
    def get_missing_integrations(self, connected_integrations: list[IntegrationType]) -> list[IntegrationType]:
        """Get list of missing required integrations."""
        return [req for req in self.required_integrations if req not in connected_integrations]


class IntegrationHealth(BaseModel):
    """Health status of an integration."""
    
    is_healthy: bool
    last_check: datetime = Field(default_factory=lambda: datetime.now(UTC))
    error_message: Optional[str] = None
    details: dict[str, Any] = Field(default_factory=dict)


class BaseIntegration(ABC):
    """Base class for all integration types."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @property
    @abstractmethod
    def integration_type(self) -> IntegrationType:
        """Return the integration type."""
        pass
    
    @property
    @abstractmethod
    def auth_method(self) -> AuthMethod:
        """Return the authentication method."""
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """Return the display name for UI."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Return the description for UI."""
        pass
    
    @property
    @abstractmethod
    def capabilities(self) -> list[IntegrationCapability]:
        """Return list of capabilities this integration provides."""
        pass
    
    @abstractmethod
    async def test_connection(self, credentials: dict[str, Any]) -> IntegrationHealth:
        """Test if the integration connection is working."""
        pass
    
    @abstractmethod
    def get_setup_instructions(self) -> dict[str, Any]:
        """Get setup instructions for this integration."""
        pass
    
    def get_settings_schema(self) -> dict[str, Any]:
        """Get JSON schema for integration-specific settings."""
        return {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    def validate_settings(self, settings: dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate integration-specific settings."""
        # Default implementation - can be overridden
        return True, None
    
    def get_default_settings(self) -> dict[str, Any]:
        """Get default settings values."""
        # Extract defaults from schema if available
        schema = self.get_settings_schema()
        defaults = {}
        for key, prop in schema.get("properties", {}).items():
            if "default" in prop:
                defaults[key] = prop["default"]
        return defaults
    
    async def test_with_settings(self, settings: dict[str, Any], credentials: dict[str, Any]) -> IntegrationHealth:
        """Test integration with specific settings (before connecting)."""
        # First validate settings
        is_valid, error = self.validate_settings(settings)
        if not is_valid:
            return IntegrationHealth(
                is_healthy=False,
                error_message=f"Invalid settings: {error}"
            )
        
        # Then test connection if credentials exist
        if credentials:
            return await self.test_connection(credentials)
        
        # If no credentials, just return settings validation result
        return IntegrationHealth(
            is_healthy=True,
            details={"settings_valid": True, "credentials_required": True}
        )


class OAuth2Integration(BaseIntegration):
    """Base class for OAuth2 integrations."""
    
    auth_method = AuthMethod.OAUTH2
    
    @property
    def auth_type(self) -> str:
        """Return auth type for database compatibility."""
        from ..models.integration import AuthType
        return AuthType.OAUTH2
    
    @property
    @abstractmethod
    def oauth_scopes(self) -> list[str]:
        """Return required OAuth2 scopes."""
        pass
    
    @property
    @abstractmethod
    def oauth_authorize_url(self) -> str:
        """Return OAuth2 authorization URL."""
        pass
    
    @property
    @abstractmethod
    def oauth_token_url(self) -> str:
        """Return OAuth2 token exchange URL."""
        pass
    
    def get_setup_instructions(self) -> dict[str, Any]:
        """Get OAuth2 setup instructions."""
        return {
            "type": "oauth2",
            "steps": [
                "Click 'Connect' to authorize access",
                "Grant the requested permissions",
                "You'll be redirected back to ProtoBox"
            ],
            "scopes": self.oauth_scopes,
            "authorize_url": self.oauth_authorize_url
        }
    
    async def test_connection(self, credentials: dict[str, Any]) -> IntegrationHealth:
        """Test OAuth2 connection with access token."""
        if not credentials.get("access_token"):
            return IntegrationHealth(
                is_healthy=False,
                error_message="No access token found"
            )
        
        # Subclasses should implement specific validation
        return IntegrationHealth(
            is_healthy=True,
            details={"token_type": credentials.get("token_type", "Bearer")}
        )


class ApiKeyIntegration(BaseIntegration):
    """Base class for API key integrations."""
    
    auth_method = AuthMethod.API_KEY
    
    @property
    def auth_type(self) -> str:
        """Return auth type for database compatibility."""
        from ..models.integration import AuthType
        return AuthType.API_KEY
    
    @property
    @abstractmethod
    def api_key_header(self) -> str:
        """Return the header name for API key."""
        pass
    
    @property
    def api_key_prefix(self) -> Optional[str]:
        """Return optional prefix for API key (e.g., 'Bearer', 'Token')."""
        return None
    
    def get_setup_instructions(self) -> dict[str, Any]:
        """Get API key setup instructions."""
        return {
            "type": "api_key",
            "steps": [
                f"Get your API key from {self.display_name}",
                "Enter the API key in the field below",
                "Click 'Test Connection' to verify"
            ],
            "fields": [
                {
                    "name": "api_key",
                    "type": "password",
                    "label": "API Key",
                    "required": True,
                    "placeholder": "Enter your API key"
                }
            ]
        }
    
    async def validate_api_key(self, api_key: str) -> bool:
        """Validate if the API key is in correct format."""
        # Basic validation - subclasses should override
        return bool(api_key and len(api_key) > 10)
    
    async def test_connection(self, credentials: dict[str, Any]) -> IntegrationHealth:
        """Test API key connection."""
        api_key = credentials.get("api_key")
        if not api_key:
            return IntegrationHealth(
                is_healthy=False,
                error_message="API key is required"
            )
        
        is_valid = await self.validate_api_key(api_key)
        if not is_valid:
            return IntegrationHealth(
                is_healthy=False,
                error_message="Invalid API key format"
            )
        
        return IntegrationHealth(
            is_healthy=True,
            details={"key_length": len(api_key)}
        )


class WebhookIntegration(BaseIntegration):
    """Base class for webhook integrations."""
    
    auth_method = AuthMethod.WEBHOOK
    
    @property
    @abstractmethod
    def webhook_events(self) -> list[str]:
        """Return list of webhook events this integration handles."""
        pass
    
    @abstractmethod
    async def validate_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        secret: str
    ) -> bool:
        """Validate webhook signature."""
        pass
    
    def get_webhook_url(self, workspace_id: str) -> str:
        """Get the webhook URL for this integration."""
        from ..config import settings
        base_url = settings.mcp_server_url or "http://localhost:8090"
        return f"{base_url}/admin/api/v1/webhooks/{self.integration_type.value}/{workspace_id}"
    
    def get_setup_instructions(self) -> dict[str, Any]:
        """Get webhook setup instructions."""
        return {
            "type": "webhook",
            "steps": [
                f"Go to {self.display_name} webhook settings",
                "Add the webhook URL provided below",
                "Copy the webhook secret",
                "Enter the secret in the field below",
                "Configure the events you want to receive"
            ],
            "fields": [
                {
                    "name": "webhook_secret",
                    "type": "password",
                    "label": "Webhook Secret",
                    "required": True,
                    "placeholder": "Enter webhook secret"
                }
            ],
            "events": self.webhook_events
        }
    
    async def test_connection(self, credentials: dict[str, Any]) -> IntegrationHealth:
        """Test webhook configuration."""
        webhook_secret = credentials.get("webhook_secret")
        if not webhook_secret:
            return IntegrationHealth(
                is_healthy=False,
                error_message="Webhook secret is required"
            )
        
        return IntegrationHealth(
            is_healthy=True,
            details={
                "events": self.webhook_events,
                "secret_configured": True
            }
        )


class DualAuthIntegration(BaseIntegration):
    """Base class for integrations supporting multiple auth methods."""
    
    @property
    @abstractmethod
    def supported_auth_methods(self) -> list[AuthMethod]:
        """Return list of supported authentication methods."""
        pass
    
    @property
    def auth_method(self) -> AuthMethod:
        """Return the currently selected auth method."""
        return self._selected_auth_method or self.supported_auth_methods[0]
    
    def __init__(self):
        super().__init__()
        self._selected_auth_method: Optional[AuthMethod] = None
    
    def select_auth_method(self, method: AuthMethod):
        """Select which authentication method to use."""
        if method not in self.supported_auth_methods:
            raise ValueError(f"Auth method {method} not supported by {self.display_name}")
        self._selected_auth_method = method
    
    def get_setup_instructions(self) -> dict[str, Any]:
        """Get setup instructions based on selected auth method."""
        return {
            "type": "dual_auth",
            "supported_methods": [m.value for m in self.supported_auth_methods],
            "selected_method": self.auth_method.value,
            "instructions": self._get_instructions_for_method(self.auth_method)
        }
    
    @abstractmethod
    def _get_instructions_for_method(self, method: AuthMethod) -> dict[str, Any]:
        """Get instructions for specific auth method."""
        pass