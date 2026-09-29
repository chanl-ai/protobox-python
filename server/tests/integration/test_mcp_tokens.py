"""Integration tests for MCP tokens API."""

import os

import pytest
from httpx import Client

from .test_utils import get_emulator_auth_token


@pytest.mark.integration
class TestMCPTokensAPI:
    """Test MCP tokens endpoints."""

    @classmethod
    def setup_class(cls):
        """Set up test client and authentication."""
        cls.base_url = os.getenv("TEST_API_URL", "http://localhost:8090")
        cls.client = Client(base_url=cls.base_url, timeout=10.0)
        cls.workspace_id = "689ce93ac66218cb8cff5637"  # Test workspace
        cls.created_tokens = []  # Track tokens for cleanup
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
        """Clean up created tokens."""
        if not cls.skip_tests and cls.created_tokens:
            for token_id in cls.created_tokens:
                try:
                    cls.client.delete(
                        f"/admin/api/v1/workspaces/{cls.workspace_id}/mcp-tokens/{token_id}",
                        headers=cls.headers,
                    )
                except Exception:
                    pass  # Ignore cleanup errors
        cls.client.close()

    def setup_method(self):
        """Check if tests should be skipped."""
        if self.skip_tests:
            pytest.skip(self.skip_reason)

    def test_list_mcp_tokens(self):
        """Test listing MCP tokens."""
        response = self.client.get(
            f"/admin/api/v1/workspaces/{self.workspace_id}/mcp-tokens/", headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Check token structure if any exist
        if data:
            token = data[0]
            assert "token_id" in token
            assert "name" in token
            assert "workspace_id" in token
            assert "status" in token
            assert "created_at" in token

    def test_create_mcp_token(self):
        """Test creating an MCP token."""
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/mcp-tokens/",
            headers=self.headers,
            json={
                "name": "test-integration-token",
                "description": "Integration test token",
                "expires_in_days": 7,
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "token" in data
        assert "token_id" in data
        assert "name" in data
        assert "workspace_id" in data
        assert "mcp_url" in data
        assert data["name"] == "test-integration-token"
        assert data["workspace_id"] == self.workspace_id

        # Verify MCP URL format (enhanced security - token NOT in URL)
        mcp_url = data["mcp_url"]
        assert f"/mcp/{self.workspace_id}/sse" in mcp_url
        assert self.workspace_id in mcp_url
        
        # Verify token is NOT in URL (security best practice)
        assert "token=" not in mcp_url
        assert data["token"] not in mcp_url

        # Check URL uses correct base URL
        if "localhost" in mcp_url:
            assert mcp_url.startswith("http://localhost:8090")
        else:
            assert mcp_url.startswith("https://")

        # Verify correct path format (new native MCP endpoint)
        assert f"/mcp/{self.workspace_id}/sse" in mcp_url

        # Track for cleanup
        self.created_tokens.append(data["token_id"])

    def test_create_token_without_expiry(self):
        """Test creating a token that never expires."""
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/mcp-tokens/",
            headers=self.headers,
            json={
                "name": "test-permanent-token",
                "description": "Token without expiry",
                # No expires_in_days means it never expires
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert "token" in data
        assert "expires_at" in data
        assert data["expires_at"] is None  # Should be None for permanent tokens

        # Track for cleanup
        self.created_tokens.append(data["token_id"])

    def test_create_token_with_scopes(self):
        """Test creating a token with specific scopes."""
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/mcp-tokens/",
            headers=self.headers,
            json={
                "name": "test-scoped-token",
                "description": "Token with limited scopes",
                "scopes": ["read:actions", "execute:actions"],
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert "token" in data
        assert "token_id" in data

        # Track for cleanup
        self.created_tokens.append(data["token_id"])

    def test_revoke_mcp_token(self):
        """Test revoking an MCP token."""
        # First create a token
        create_response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/mcp-tokens/",
            headers=self.headers,
            json={"name": "test-token-to-revoke", "description": "Will be revoked"},
        )
        assert create_response.status_code == 200
        token_data = create_response.json()
        token_id = token_data["token_id"]

        # Now revoke it
        revoke_response = self.client.delete(
            f"/admin/api/v1/workspaces/{self.workspace_id}/mcp-tokens/{token_id}",
            headers=self.headers,
        )
        assert revoke_response.status_code == 200
        revoke_data = revoke_response.json()
        assert "message" in revoke_data
        assert token_id in revoke_data["message"]

        # Verify token is revoked by listing with include_revoked
        list_response = self.client.get(
            f"/admin/api/v1/workspaces/{self.workspace_id}/mcp-tokens/?include_revoked=true",
            headers=self.headers,
        )
        assert list_response.status_code == 200
        tokens = list_response.json()

        # Find the revoked token
        revoked_token = next((t for t in tokens if t["token_id"] == token_id), None)
        if revoked_token:
            assert revoked_token["status"] == "revoked"

    def test_invalid_workspace_id(self):
        """Test with invalid workspace ID format."""
        response = self.client.get(
            "/admin/api/v1/workspaces/invalid-id/mcp-tokens/", headers=self.headers
        )
        assert response.status_code == 400
        data = response.json()
        assert "Invalid workspace ID format" in str(data)

    def test_missing_auth_header(self):
        """Test accessing MCP tokens without authentication."""
        response = self.client.get(f"/admin/api/v1/workspaces/{self.workspace_id}/mcp-tokens/")
        assert response.status_code in [401, 403]
        data = response.json()
        assert "Authentication required" in str(data) or "Not authenticated" in str(data)

    def test_create_token_missing_name(self):
        """Test creating a token without required name field."""
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/mcp-tokens/",
            headers=self.headers,
            json={"description": "Missing name field"},
        )
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data

    def test_revoke_nonexistent_token(self):
        """Test revoking a token that doesn't exist."""
        response = self.client.delete(
            f"/admin/api/v1/workspaces/{self.workspace_id}/mcp-tokens/nonexistent-token-id",
            headers=self.headers,
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in str(data).lower()

    def test_list_tokens_with_filter(self):
        """Test listing tokens with include_revoked filter."""
        # List without revoked (default)
        response1 = self.client.get(
            f"/admin/api/v1/workspaces/{self.workspace_id}/mcp-tokens/", headers=self.headers
        )
        assert response1.status_code == 200
        active_tokens = response1.json()

        # List with revoked
        response2 = self.client.get(
            f"/admin/api/v1/workspaces/{self.workspace_id}/mcp-tokens/?include_revoked=true",
            headers=self.headers,
        )
        assert response2.status_code == 200
        all_tokens = response2.json()

        # All tokens list should be >= active tokens list
        assert len(all_tokens) >= len(active_tokens)

        # Check that active list doesn't have revoked tokens
        for token in active_tokens:
            assert token["status"] != "revoked"
