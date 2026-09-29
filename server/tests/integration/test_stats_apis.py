"""
Integration tests for stats API endpoints.

These tests require a running server with test mode enabled.
Run with: make test-integration
"""

import os

import pytest
from httpx import Client

from .test_utils import get_emulator_auth_token


@pytest.mark.integration
class TestStatsAPIs:
    """Test stats API endpoints against running server."""

    @classmethod
    def setup_class(cls):
        """Setup test configuration."""
        cls.base_url = os.getenv("TEST_API_URL", "http://localhost:8090")
        cls.client = Client(base_url=cls.base_url, timeout=10.0)
        cls.skip_tests = False
        cls.skip_reason = None

        # Check if server is running
        try:
            cls.client.get("/admin/api/v1/health")
        except Exception as e:
            cls.skip_tests = True
            cls.skip_reason = f"Server not running: {e}"
            return

        # Get Firebase emulator token
        cls.token, cls.refresh_token, cls.headers = get_emulator_auth_token(cls.client)

        if not cls.token:
            cls.skip_tests = True
            cls.skip_reason = "Authentication not enabled or Firebase emulator not running"
            return

    @classmethod
    def teardown_class(cls):
        """Cleanup."""
        cls.client.close()

    def setup_method(self):
        """Check if tests should be skipped."""
        if self.skip_tests:
            pytest.skip(self.skip_reason)

    def _get_test_workspace_id(self):
        """Helper to get a test workspace ID."""
        response = self.client.get("/admin/api/v1/workspaces", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        workspaces = data.get("workspaces", data if isinstance(data, list) else [])
        
        if not workspaces:
            pytest.skip("No workspaces available")
            
        return workspaces[0]["id"]

    def test_actions_stats_api(self):
        """Test the actions stats API endpoint."""
        workspace_id = self._get_test_workspace_id()
        
        response = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_id}/actions/stats", 
            headers=self.headers
        )
        assert response.status_code == 200
        stats = response.json()
        
        # Verify stats structure
        assert "total_actions" in stats
        assert "active_actions" in stats
        assert "inactive_actions" in stats
        assert "actions_by_type" in stats
        assert "recent_executions" in stats
        
        # Verify stats are integers
        assert isinstance(stats["total_actions"], int)
        assert isinstance(stats["active_actions"], int)
        assert isinstance(stats["inactive_actions"], int)
        assert isinstance(stats["recent_executions"], int)
        
        # Verify actions_by_type is a dict
        assert isinstance(stats["actions_by_type"], dict)
        
        # Verify totals add up correctly
        assert stats["total_actions"] == stats["active_actions"] + stats["inactive_actions"]

    def test_mcp_tokens_stats_api(self):
        """Test the MCP tokens stats API endpoint."""
        workspace_id = self._get_test_workspace_id()
        
        response = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_id}/mcp-tokens/stats", 
            headers=self.headers
        )
        assert response.status_code == 200
        stats = response.json()
        
        # Verify stats structure
        assert "total_tokens" in stats
        assert "active_tokens" in stats
        assert "expired_tokens" in stats
        assert "tokens_by_status" in stats
        assert "recent_usage" in stats
        
        # Verify stats are integers
        assert isinstance(stats["total_tokens"], int)
        assert isinstance(stats["active_tokens"], int)
        assert isinstance(stats["expired_tokens"], int)
        assert isinstance(stats["recent_usage"], int)
        
        # Verify tokens_by_status is a dict
        assert isinstance(stats["tokens_by_status"], dict)
        
        # Verify totals add up correctly
        assert stats["total_tokens"] == stats["active_tokens"] + stats["expired_tokens"]

    def test_oauth_clients_stats_api(self):
        """Test the OAuth clients stats API endpoint."""
        workspace_id = self._get_test_workspace_id()
        
        response = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_id}/oauth-clients/stats", 
            headers=self.headers
        )
        assert response.status_code == 200
        stats = response.json()
        
        # Verify stats structure
        assert "total_clients" in stats
        assert "active_clients" in stats
        assert "inactive_clients" in stats
        assert "clients_by_type" in stats
        assert "recent_authorizations" in stats
        
        # Verify stats are integers
        assert isinstance(stats["total_clients"], int)
        assert isinstance(stats["active_clients"], int)
        assert isinstance(stats["inactive_clients"], int)
        assert isinstance(stats["recent_authorizations"], int)
        
        # Verify clients_by_type is a dict
        assert isinstance(stats["clients_by_type"], dict)

    def test_workspace_stats_api(self):
        """Test the workspace stats API endpoint."""
        workspace_id = self._get_test_workspace_id()
        
        response = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_id}/stats", 
            headers=self.headers
        )
        assert response.status_code == 200
        stats = response.json()
        
        # Verify stats structure
        assert "actions_count" in stats
        assert "mcp_tokens_count" in stats
        assert "oauth_clients_count" in stats
        assert "integrations_count" in stats
        assert "knowledge_docs_count" in stats
        
        # Verify stats are integers
        assert isinstance(stats["actions_count"], int)
        assert isinstance(stats["mcp_tokens_count"], int)
        assert isinstance(stats["oauth_clients_count"], int)
        assert isinstance(stats["integrations_count"], int)
        assert isinstance(stats["knowledge_docs_count"], int)
        
        # All counts should be non-negative
        assert stats["actions_count"] >= 0
        assert stats["mcp_tokens_count"] >= 0
        assert stats["oauth_clients_count"] >= 0
        assert stats["integrations_count"] >= 0
        assert stats["knowledge_docs_count"] >= 0

    def test_stats_apis_unauthorized(self):
        """Test that stats APIs require authentication."""
        workspace_id = self._get_test_workspace_id()
        
        # Test without authentication headers
        endpoints = [
            f"/admin/api/v1/workspaces/{workspace_id}/actions/stats",
            f"/admin/api/v1/workspaces/{workspace_id}/mcp-tokens/stats", 
            f"/admin/api/v1/workspaces/{workspace_id}/oauth-clients/stats",
            f"/admin/api/v1/workspaces/{workspace_id}/stats",
        ]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            assert response.status_code == 401, f"Endpoint {endpoint} should require authentication"

    def test_stats_apis_invalid_workspace(self):
        """Test stats APIs with invalid workspace ID."""
        invalid_workspace_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format but non-existent
        
        endpoints = [
            f"/admin/api/v1/workspaces/{invalid_workspace_id}/actions/stats",
            f"/admin/api/v1/workspaces/{invalid_workspace_id}/mcp-tokens/stats",
            f"/admin/api/v1/workspaces/{invalid_workspace_id}/oauth-clients/stats", 
            f"/admin/api/v1/workspaces/{invalid_workspace_id}/stats",
        ]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint, headers=self.headers)
            # Should return 400 (invalid format), 403 (access denied), or 404 (not found)
            assert response.status_code in [400, 403, 404], f"Endpoint {endpoint} should deny access to invalid workspace"

    def test_stats_apis_performance(self):
        """Test that stats APIs respond quickly."""
        workspace_id = self._get_test_workspace_id()
        
        import time
        
        endpoints = [
            f"/admin/api/v1/workspaces/{workspace_id}/actions/stats",
            f"/admin/api/v1/workspaces/{workspace_id}/mcp-tokens/stats",
            f"/admin/api/v1/workspaces/{workspace_id}/oauth-clients/stats",
            f"/admin/api/v1/workspaces/{workspace_id}/stats",
        ]
        
        for endpoint in endpoints:
            start_time = time.time()
            response = self.client.get(endpoint, headers=self.headers)
            end_time = time.time()
            
            assert response.status_code == 200, f"Endpoint {endpoint} should return 200"
            
            # Stats APIs should respond quickly (under 2 seconds)
            response_time = end_time - start_time
            assert response_time < 2.0, f"Endpoint {endpoint} took {response_time:.2f}s (should be < 2.0s)"