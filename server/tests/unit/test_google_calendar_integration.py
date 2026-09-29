"""Unit tests for Google Calendar integration."""

import pytest

from protobox.admin.integrations.google_calendar import GoogleCalendarIntegration
from protobox.admin.integrations.base_classes import AuthMethod, IntegrationCapability, IntegrationHealth
from protobox.admin.models.integration import IntegrationType


class TestGoogleCalendarIntegration:
    """Test suite for Google Calendar integration."""
    
    def setup_method(self):
        """Set up test instance."""
        self.integration = GoogleCalendarIntegration()
    
    def test_integration_properties(self):
        """Test basic integration properties."""
        assert self.integration.integration_type == IntegrationType.GOOGLE_CALENDAR
        assert self.integration.display_name == "Google Calendar"
        assert self.integration.auth_method == AuthMethod.OAUTH2
        assert IntegrationCapability.CREATE_EVENT in self.integration.capabilities
        assert IntegrationCapability.CHECK_AVAILABILITY in self.integration.capabilities
    
    def test_oauth_configuration(self):
        """Test OAuth2 configuration."""
        assert "https://www.googleapis.com/auth/calendar.events" in self.integration.oauth_scopes
        assert "https://www.googleapis.com/auth/calendar.readonly" in self.integration.oauth_scopes
        assert self.integration.oauth_authorize_url == "https://accounts.google.com/o/oauth2/v2/auth"
        assert self.integration.oauth_token_url == "https://oauth2.googleapis.com/token"
    
    @pytest.mark.asyncio
    async def test_connection_without_token(self):
        """Test connection test without access token."""
        health = await self.integration.test_connection({})
        assert health.is_healthy is False
        assert "No access token found" in health.error_message
    
    @pytest.mark.asyncio
    async def test_connection_with_token(self):
        """Test connection test with access token."""
        health = await self.integration.test_connection({
            "access_token": "test_token_123",
            "token_type": "Bearer",
            "scope": "https://www.googleapis.com/auth/calendar.events"
        })
        
        # Should pass basic validation (actual API call would fail in test)
        assert health.is_healthy is True
        assert health.details["token_type"] == "Bearer"
        assert "https://www.googleapis.com/auth/calendar.events" in health.details["scopes"]
    
    def test_setup_instructions(self):
        """Test setup instructions generation."""
        instructions = self.integration.get_setup_instructions()
        assert instructions["type"] == "oauth2"
        assert "scopes" in instructions
        assert "authorize_url" in instructions
        assert len(instructions["scopes"]) == 2