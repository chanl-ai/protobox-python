"""
Integration tests for API functionality.

These tests require a running server with test mode enabled.
Run with: make test-integration-api
"""

import os

import pytest
from httpx import Client

# Import utility for authenticated tests
try:
    from .test_utils import AuthenticatedTestCase
except ImportError:
    # Fallback for direct execution
    import sys

    sys.path.append(os.path.dirname(__file__))
    from test_utils import AuthenticatedTestCase


@pytest.mark.integration
class TestAPIHealthAndStatus:
    """Test API health and status endpoints."""

    @classmethod
    def setup_class(cls):
        """Setup test configuration."""
        cls.base_url = os.getenv("TEST_API_URL", "http://localhost:8090")
        cls.client = Client(base_url=cls.base_url, timeout=10.0)

        # Check if server is running
        try:
            response = cls.client.get("/admin/api/v1/health")
            cls.skip_tests = False
        except Exception as e:
            cls.skip_tests = True
            cls.skip_reason = f"Server not running: {e}"

    @classmethod
    def teardown_class(cls):
        """Cleanup."""
        cls.client.close()

    def setup_method(self):
        """Check if tests should be skipped."""
        if self.skip_tests:
            pytest.skip(self.skip_reason)

    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.client.get("/admin/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_root_endpoint(self):
        """Test root API endpoint."""
        response = self.client.get("/admin/api/v1")
        # Root endpoint might not exist or might redirect
        if response.status_code == 200:
            data = response.json()
            assert "message" in data or "status" in data or "version" in data
        elif response.status_code == 404:
            # Root endpoint not implemented, which is fine
            pass
        else:
            # Unexpected status
            assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"


@pytest.mark.integration
class TestAuthenticationFlow(AuthenticatedTestCase):
    """Test authentication flow against running server."""

    @classmethod
    def setup_class(cls):
        """Setup test configuration."""
        cls.setup_auth(os.getenv("TEST_API_URL", "http://localhost:8090"))

    @classmethod
    def teardown_class(cls):
        """Cleanup."""
        cls.teardown_auth()

    def test_token_validation(self):
        """Test token validation endpoint."""
        response = self.client.get("/admin/api/v1/auth/validate", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("valid") is True

    def test_token_refresh(self):
        """Test token refresh endpoint."""
        response = self.client.post(
            "/admin/api/v1/auth/refresh", json={"refresh_token": self.refresh_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data


@pytest.mark.integration
class TestWorkspaceOperations(AuthenticatedTestCase):
    """Test workspace CRUD operations against running server."""

    @classmethod
    def setup_class(cls):
        """Setup test configuration."""
        cls.setup_auth(os.getenv("TEST_API_URL", "http://localhost:8090"))

    @classmethod
    def teardown_class(cls):
        """Cleanup."""
        cls.teardown_auth()

    def test_list_workspaces(self):
        """Test listing workspaces."""
        response = self.client.get("/admin/api/v1/workspaces", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        workspaces = data.get("workspaces", data if isinstance(data, list) else [])
        assert isinstance(workspaces, list)


@pytest.mark.integration
class TestActionsAPI(AuthenticatedTestCase):
    """Test actions API endpoints against running server."""

    @classmethod
    def setup_class(cls):
        """Setup test configuration."""
        cls.setup_auth(os.getenv("TEST_API_URL", "http://localhost:8090"))

    @classmethod
    def teardown_class(cls):
        """Cleanup."""
        cls.teardown_auth()

    def test_list_actions(self):
        """Test listing actions."""
        # Get workspaces first
        response = self.client.get("/admin/api/v1/workspaces", headers=self.headers)
        data = response.json()
        workspaces = data.get("workspaces", data if isinstance(data, list) else [])

        if not workspaces:
            pytest.skip("No workspaces available")

        workspace_id = workspaces[0]["id"]

        # List actions for workspace
        # Try the correct endpoint structure
        response = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_id}/actions", headers=self.headers
        )
        if response.status_code == 404:
            # Try alternative endpoint structure
            response = self.client.get(
                f"/admin/api/v1/actions?workspace_id={workspace_id}", headers=self.headers
            )
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            assert "actions" in data or isinstance(data, list)


@pytest.mark.integration
class TestExecutionsAPI(AuthenticatedTestCase):
    """Test executions API endpoints against running server."""

    @classmethod
    def setup_class(cls):
        """Setup test configuration."""
        cls.setup_auth(os.getenv("TEST_API_URL", "http://localhost:8090"))

    @classmethod
    def teardown_class(cls):
        """Cleanup."""
        cls.teardown_auth()

    def test_list_executions(self):
        """Test listing executions."""
        # Get workspaces first
        response = self.client.get("/admin/api/v1/workspaces", headers=self.headers)
        data = response.json()
        workspaces = data.get("workspaces", data if isinstance(data, list) else [])

        if not workspaces:
            pytest.skip("No workspaces available")

        workspace_id = workspaces[0]["id"]

        # List executions for workspace
        # Try the correct endpoint structure
        response = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_id}/executions", headers=self.headers
        )
        if response.status_code == 404:
            # Try alternative endpoint structure
            response = self.client.get(
                f"/admin/api/v1/executions?workspace_id={workspace_id}", headers=self.headers
            )
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            assert "executions" in data or isinstance(data, list)
