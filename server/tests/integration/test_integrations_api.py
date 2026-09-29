"""Integration tests for integrations API endpoints."""

import pytest
from httpx import Client, ConnectError
from .test_utils import get_test_auth_and_workspace


@pytest.mark.integration
class TestIntegrationsAPI:
    """Test suite for integrations API endpoints."""

    @classmethod
    def setup_class(cls):
        """Set up test client and authentication."""
        cls.client = Client(base_url="http://localhost:8090", timeout=10.0)
        cls.headers = {}
        cls.skip_tests = False
        cls.skip_reason = ""

        # Use proper Firebase emulator authentication
        try:
            access_token, headers, workspace_id = get_test_auth_and_workspace(cls.client)
            
            if access_token:
                cls.token = access_token
                cls.headers = headers
                cls.workspace_id = workspace_id
                cls.skip_tests = False
            else:
                cls.skip_tests = True
                cls.skip_reason = "Failed to authenticate with Firebase emulator"
        except ConnectError:
            cls.skip_tests = True
            cls.skip_reason = "Server not running. Start with 'make backend'"
        except Exception as e:
            cls.skip_tests = True
            cls.skip_reason = f"Setup failed: {e}"

    @classmethod
    def teardown_class(cls):
        """Clean up after tests."""
        cls.client.close()

    def setup_method(self):
        """Skip tests if setup failed."""
        if self.skip_tests:
            pytest.skip(self.skip_reason)

    def test_get_available_integrations(self):
        """Test getting list of available integrations."""
        response = self.client.get("/admin/api/v1/integrations/available", headers=self.headers)

        assert response.status_code == 200, f"Failed to get available integrations: {response.text}"

        integrations = response.json()
        assert isinstance(integrations, list), "Response should be a list"
        assert len(integrations) > 0, "Should have at least one available integration"

        # Check structure of first integration
        first = integrations[0]
        assert "integration_type" in first
        assert "display_name" in first
        assert "description" in first
        assert "category" in first
        assert "auth_type" in first
        assert "available_actions" in first

        # Verify known integrations are present
        integration_types = [i["integration_type"] for i in integrations]
        assert "google_calendar" in integration_types, "Google Calendar should be available"
        assert "hubspot" in integration_types, "HubSpot should be available"

    def test_get_workspace_integrations(self):
        """Test getting integrations for a specific workspace."""
        response = self.client.get(
            f"/admin/api/v1/workspaces/{self.workspace_id}/integrations", headers=self.headers
        )

        assert response.status_code == 200, f"Failed to get workspace integrations: {response.text}"

        integrations = response.json()
        assert isinstance(integrations, list), "Response should be a list"
        # Workspace might not have any integrations configured yet, so empty list is OK

    def test_available_integrations_without_auth(self):
        """Test that integrations endpoint requires authentication."""
        response = self.client.get("/admin/api/v1/integrations/available")
        assert response.status_code == 401, "Should require authentication"

    def test_available_integrations_structure(self):
        """Test the structure of available integrations response."""
        response = self.client.get("/admin/api/v1/integrations/available", headers=self.headers)

        assert response.status_code == 200
        integrations = response.json()

        # Test Google Calendar integration structure
        google_cal = next(
            (i for i in integrations if i["integration_type"] == "google_calendar"), None
        )
        assert google_cal is not None, "Google Calendar integration not found"

        assert google_cal["display_name"] == "Google Calendar"
        assert google_cal["category"] == "productivity"
        assert google_cal["auth_type"] == "oauth2"

        # Check available actions
        actions = google_cal["available_actions"]
        assert len(actions) >= 2, "Google Calendar should have at least 2 actions"

        action_names = [a["action_name"] for a in actions]
        assert "schedule_appointment" in action_names
        assert "check_availability" in action_names

    def test_hubspot_integration_structure(self):
        """Test HubSpot integration structure."""
        response = self.client.get("/admin/api/v1/integrations/available", headers=self.headers)

        assert response.status_code == 200
        integrations = response.json()

        hubspot = next((i for i in integrations if i["integration_type"] == "hubspot"), None)
        assert hubspot is not None, "HubSpot integration not found"

        assert hubspot["display_name"] == "HubSpot CRM"
        assert hubspot["category"] == "crm"
        assert hubspot["auth_type"] == "api_key"

        # Check available actions
        actions = hubspot["available_actions"]
        assert len(actions) >= 2, "HubSpot should have at least 2 actions"

        action_names = [a["action_name"] for a in actions]
        assert "create_contact" in action_names
        assert "log_activity" in action_names
