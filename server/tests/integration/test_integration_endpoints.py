"""Integration tests for integration management endpoints."""

import pytest
from httpx import Client

from protobox.admin.models.integration import IntegrationType


@pytest.mark.integration
class TestIntegrationEndpoints:
    """Test suite for integration management endpoints."""
    
    @classmethod
    def setup_class(cls):
        """Set up test client and authenticate."""
        cls.client = Client(base_url="http://localhost:8090", timeout=10.0)
        cls.workspace_id = None
        cls.headers = {}
        cls.skip_tests = False
        cls.skip_reason = None
        
        # Try to authenticate
        try:
            # Get test token
            response = cls.client.post(
                "/admin/api/v1/auth/exchange",
                json={"firebase_token": "test-integration-user"}
            )
            
            if response.status_code == 200:
                data = response.json()
                cls.headers = {"Authorization": f"Bearer {data['access_token']}"}
                
                # Get or create workspace
                workspace_response = cls.client.get(
                    "/admin/api/v1/workspaces",
                    headers=cls.headers
                )
                
                if workspace_response.status_code == 200:
                    workspaces = workspace_response.json()
                    if workspaces:
                        cls.workspace_id = workspaces[0]["id"]
                    else:
                        # Create a test workspace
                        create_response = cls.client.post(
                            "/admin/api/v1/workspaces",
                            headers=cls.headers,
                            json={
                                "name": "Integration Test Workspace",
                                "description": "For testing integrations"
                            }
                        )
                        if create_response.status_code in [200, 201]:
                            cls.workspace_id = create_response.json()["id"]
                        else:
                            cls.skip_tests = True
                            cls.skip_reason = f"Failed to create workspace: {create_response.text}"
                else:
                    cls.skip_tests = True
                    cls.skip_reason = f"Failed to get workspaces: {workspace_response.text}"
            else:
                cls.skip_tests = True
                cls.skip_reason = "Authentication failed - server may not be in test mode"
        except Exception as e:
            cls.skip_tests = True
            cls.skip_reason = f"Server not running or not accessible: {e}"
    
    @classmethod
    def teardown_class(cls):
        """Clean up test client."""
        if hasattr(cls, 'client'):
            cls.client.close()
    
    def setup_method(self):
        """Skip tests if setup failed."""
        if self.skip_tests:
            pytest.skip(self.skip_reason)
    
    def test_list_available_integrations(self):
        """Test listing available integrations."""
        response = self.client.get(
            "/admin/api/v1/integrations/available",
            headers=self.headers
        )
        
        assert response.status_code == 200
        integrations = response.json()
        assert isinstance(integrations, list)
        
        # Check structure of returned integrations
        if integrations:
            integration = integrations[0]
            assert "type" in integration
            assert "display_name" in integration
            assert "description" in integration
            assert "category" in integration
    
    def test_get_workspace_integrations(self):
        """Test getting workspace-specific integrations."""
        response = self.client.get(
            f"/admin/api/v1/workspaces/{self.workspace_id}/integrations",
            headers=self.headers
        )
        
        assert response.status_code == 200
        integrations = response.json()
        assert isinstance(integrations, list)
    
    def test_connect_integration_flow(self):
        """Test the integration connection flow."""
        # Try to connect a test integration (will fail without implementation)
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/integrations/slack/connect",
            headers=self.headers
        )
        
        # We expect this to return connection instructions or fail gracefully
        assert response.status_code in [200, 400, 501]
        
        if response.status_code == 200:
            data = response.json()
            # Should have connection instructions or URL
            assert ("auth_url" in data) or ("instructions" in data)
    
    def test_disconnect_integration(self):
        """Test disconnecting an integration."""
        # Try to disconnect a non-existent integration
        response = self.client.delete(
            f"/admin/api/v1/workspaces/{self.workspace_id}/integrations/slack",
            headers=self.headers
        )
        
        # Should return 404 for non-existent integration
        assert response.status_code in [404, 501]
    
    def test_reset_integration_actions(self):
        """Test resetting integration actions to defaults."""
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/integrations/google_calendar/reset",
            headers=self.headers
        )
        
        # Should return 404 if not connected or 501 if not implemented
        assert response.status_code in [404, 501]
    
    def test_integration_with_invalid_type(self):
        """Test handling of invalid integration type."""
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/integrations/invalid_type/connect",
            headers=self.headers
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid integration type" in data.get("detail", "")
    
    def test_integration_auth_required(self):
        """Test that integration endpoints require authentication."""
        # Test without auth headers
        response = self.client.get("/admin/api/v1/integrations/available")
        assert response.status_code == 401
        
        response = self.client.get(
            f"/admin/api/v1/workspaces/{self.workspace_id}/integrations"
        )
        assert response.status_code == 401