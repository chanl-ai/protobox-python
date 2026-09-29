"""Unit tests for integration base classes."""

import pytest
from datetime import UTC, datetime

from protobox.admin.integrations.base_classes import (
    ActionTemplate,
    ApiKeyIntegration,
    AuthMethod,
    BaseIntegration,
    DualAuthIntegration,
    IntegrationCapability,
    IntegrationHealth,
    OAuth2Integration,
    WebhookIntegration,
)
from protobox.admin.models.integration import IntegrationType


class TestApiKeyIntegration(ApiKeyIntegration):
    """Test implementation of API key integration."""
    
    integration_type = IntegrationType.STRIPE
    display_name = "Test API Integration"
    description = "Test API key integration"
    capabilities = [IntegrationCapability.PROCESS_PAYMENT]
    api_key_header = "Authorization"
    api_key_prefix = "Bearer"
    
    def get_action_templates(self):
        return []
    
    async def validate_api_key(self, api_key: str) -> bool:
        return api_key.startswith("sk_test_")


class TestOAuth2Integration(OAuth2Integration):
    """Test implementation of OAuth2 integration."""
    
    integration_type = IntegrationType.GOOGLE_CALENDAR
    display_name = "Test OAuth2 Integration"
    description = "Test OAuth2 integration"
    capabilities = [IntegrationCapability.CREATE_EVENT]
    oauth_scopes = ["calendar.events"]
    oauth_authorize_url = "https://example.com/oauth/authorize"
    oauth_token_url = "https://example.com/oauth/token"
    
    def get_action_templates(self):
        return []


class TestWebhookIntegration(WebhookIntegration):
    """Test implementation of webhook integration."""
    
    integration_type = IntegrationType.STRIPE
    display_name = "Test Webhook Integration"
    description = "Test webhook integration"
    capabilities = [IntegrationCapability.PROCESS_PAYMENT]
    webhook_events = ["payment.succeeded", "payment.failed"]
    
    def get_action_templates(self):
        return []
    
    async def validate_webhook_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        return signature == "valid_signature"


class TestDualAuthIntegration(DualAuthIntegration):
    """Test implementation of dual auth integration."""
    
    integration_type = IntegrationType.HUBSPOT
    display_name = "Test Dual Auth Integration"
    description = "Test dual auth integration"
    capabilities = [IntegrationCapability.CREATE_LEAD]
    supported_auth_methods = [AuthMethod.OAUTH2, AuthMethod.API_KEY]
    
    def get_action_templates(self):
        return []
    
    async def test_connection(self, credentials: dict) -> IntegrationHealth:
        """Test connection based on selected auth method."""
        return IntegrationHealth(is_healthy=True)
    
    def _get_instructions_for_method(self, method: AuthMethod) -> dict:
        if method == AuthMethod.OAUTH2:
            return {"type": "oauth2", "steps": ["Authorize"]}
        else:
            return {"type": "api_key", "steps": ["Enter key"]}


class TestIntegrationBaseClasses:
    """Test suite for integration base classes."""
    
    @pytest.mark.asyncio
    async def test_api_key_integration(self):
        """Test API key integration base class."""
        integration = TestApiKeyIntegration()
        
        assert integration.auth_method == AuthMethod.API_KEY
        assert integration.api_key_header == "Authorization"
        assert integration.api_key_prefix == "Bearer"
        
        # Test valid API key
        health = await integration.test_connection({"api_key": "sk_test_123"})
        assert health.is_healthy is True
        
        # Test invalid API key
        health = await integration.test_connection({"api_key": "invalid"})
        assert health.is_healthy is False
        assert "Invalid API key format" in health.error_message
        
        # Test missing API key
        health = await integration.test_connection({})
        assert health.is_healthy is False
        assert "API key is required" in health.error_message
    
    @pytest.mark.asyncio
    async def test_oauth2_integration(self):
        """Test OAuth2 integration base class."""
        integration = TestOAuth2Integration()
        
        assert integration.auth_method == AuthMethod.OAUTH2
        assert integration.oauth_scopes == ["calendar.events"]
        
        # Test with access token
        health = await integration.test_connection({"access_token": "test_token"})
        assert health.is_healthy is True
        
        # Test without access token
        health = await integration.test_connection({})
        assert health.is_healthy is False
        assert "No access token found" in health.error_message
        
        # Test setup instructions
        instructions = integration.get_setup_instructions()
        assert instructions["type"] == "oauth2"
        assert "scopes" in instructions
    
    @pytest.mark.asyncio
    async def test_webhook_integration(self):
        """Test webhook integration base class."""
        integration = TestWebhookIntegration()
        
        assert integration.auth_method == AuthMethod.WEBHOOK
        assert integration.webhook_events == ["payment.succeeded", "payment.failed"]
        
        # Test with webhook secret
        health = await integration.test_connection({"webhook_secret": "secret123"})
        assert health.is_healthy is True
        assert health.details["events"] == ["payment.succeeded", "payment.failed"]
        
        # Test without webhook secret
        health = await integration.test_connection({})
        assert health.is_healthy is False
        assert "Webhook secret is required" in health.error_message
        
        # Test webhook URL generation
        webhook_url = integration.get_webhook_url("workspace123")
        assert "webhooks/stripe/workspace123" in webhook_url
    
    @pytest.mark.asyncio
    async def test_dual_auth_integration(self):
        """Test dual auth integration base class."""
        integration = TestDualAuthIntegration()
        
        # Default auth method should be first in list
        assert integration.auth_method == AuthMethod.OAUTH2
        
        # Test switching auth methods
        integration.select_auth_method(AuthMethod.API_KEY)
        assert integration.auth_method == AuthMethod.API_KEY
        
        # Test invalid auth method
        with pytest.raises(ValueError):
            integration.select_auth_method(AuthMethod.WEBHOOK)
        
        # Test setup instructions for different methods
        integration.select_auth_method(AuthMethod.OAUTH2)
        instructions = integration.get_setup_instructions()
        assert instructions["selected_method"] == "oauth2"
        
        integration.select_auth_method(AuthMethod.API_KEY)
        instructions = integration.get_setup_instructions()
        assert instructions["selected_method"] == "api_key"
    
    def test_action_template(self):
        """Test action template functionality."""
        template = ActionTemplate(
            id="test_template",
            name="Test Template",
            description="Test action template",
            category="test",
            capability=IntegrationCapability.CREATE_EVENT,
            required_integrations=[IntegrationType.GOOGLE_CALENDAR],
            optional_integrations=[IntegrationType.SLACK],
            config_schema={"type": "object"}
        )
        
        # Test availability check
        assert template.is_available([IntegrationType.GOOGLE_CALENDAR]) is True
        assert template.is_available([IntegrationType.SLACK]) is False
        assert template.is_available([]) is False
        
        # Test missing integrations
        missing = template.get_missing_integrations([IntegrationType.SLACK])
        assert IntegrationType.GOOGLE_CALENDAR in missing
        
        missing = template.get_missing_integrations([IntegrationType.GOOGLE_CALENDAR])
        assert len(missing) == 0
    
    def test_integration_health(self):
        """Test integration health model."""
        health = IntegrationHealth(
            is_healthy=True,
            details={"test": "data"}
        )
        
        assert health.is_healthy is True
        assert health.error_message is None
        assert health.details["test"] == "data"
        assert isinstance(health.last_check, datetime)
        
        # Test unhealthy state
        unhealthy = IntegrationHealth(
            is_healthy=False,
            error_message="Connection failed"
        )
        
        assert unhealthy.is_healthy is False
        assert unhealthy.error_message == "Connection failed"