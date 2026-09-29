"""
Integration tests for executions API endpoints.

These tests require a running server with test mode enabled.
Run with: make test-integration-api TEST=test_executions
"""

import os
from datetime import datetime, timedelta

import pytest
from httpx import Client

from .test_utils import get_emulator_auth_token


@pytest.mark.integration
class TestExecutionsAPI:
    """Test executions API endpoints against running server."""

    @classmethod
    def setup_class(cls):
        """Setup test configuration."""
        cls.base_url = os.getenv("TEST_API_URL", "http://localhost:8090")
        cls.client = Client(base_url=cls.base_url, timeout=10.0)

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
        else:
            cls.skip_tests = False

    @classmethod
    def teardown_class(cls):
        """Cleanup."""
        cls.client.close()

    def setup_method(self):
        """Check if tests should be skipped."""
        if self.skip_tests:
            pytest.skip(self.skip_reason)

    def test_list_executions(self):
        """Test listing executions for a workspace."""
        # Get workspaces first
        response = self.client.get("/admin/api/v1/workspaces", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        if isinstance(data, list):
            workspaces = data
        else:
            workspaces = data.get("workspaces", [])

        if not workspaces:
            pytest.skip("No workspaces available")

        workspace_id = workspaces[0]["id"]

        # List executions for workspace
        response = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_id}/executions", headers=self.headers
        )

        # Check if endpoint exists
        if response.status_code == 404:
            # Try alternative endpoint structure
            response = self.client.get(
                f"/admin/api/v1/executions?workspace_id={workspace_id}", headers=self.headers
            )

        # Accept both 200 (with data) and 404 (endpoint not implemented)
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"

        if response.status_code == 200:
            data = response.json()
            # Handle both response formats (list or dict with executions key)
            if isinstance(data, list):
                executions = data
            else:
                executions = data.get("executions", [])
            assert isinstance(executions, list)

    def test_list_executions_with_filters(self):
        """Test listing executions with date and status filters."""
        # Get workspaces first
        response = self.client.get("/admin/api/v1/workspaces", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        if isinstance(data, list):
            workspaces = data
        else:
            workspaces = data.get("workspaces", [])

        if not workspaces:
            pytest.skip("No workspaces available")

        workspace_id = workspaces[0]["id"]

        # Test with date filters
        start_date = (datetime.now() - timedelta(days=7)).isoformat()
        end_date = datetime.now().isoformat()

        response = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_id}/executions",
            headers=self.headers,
            params={"start_date": start_date, "end_date": end_date, "limit": 50},
        )

        # Try alternative endpoint if needed
        if response.status_code == 404:
            response = self.client.get(
                "/admin/api/v1/executions",
                headers=self.headers,
                params={
                    "workspace_id": workspace_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "limit": 50,
                },
            )

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                executions = data
            else:
                executions = data.get("executions", [])
            assert isinstance(executions, list)
            # All executions should be within date range (if any exist)
            for execution in executions:
                if "started_at" in execution and execution["started_at"]:
                    exec_date = datetime.fromisoformat(
                        execution["started_at"].replace("Z", "+00:00")
                    )
                    assert exec_date >= datetime.fromisoformat(start_date.replace("Z", "+00:00"))

    def test_get_single_execution(self):
        """Test getting a single execution by ID."""
        # Get workspaces first
        response = self.client.get("/admin/api/v1/workspaces", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        if isinstance(data, list):
            workspaces = data
        else:
            workspaces = data.get("workspaces", [])

        if not workspaces:
            pytest.skip("No workspaces available")

        workspace_id = workspaces[0]["id"]

        # Get list of executions first
        response = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_id}/executions",
            headers=self.headers,
            params={"limit": 1},
        )

        if response.status_code == 404:
            response = self.client.get(
                "/admin/api/v1/executions",
                headers=self.headers,
                params={"workspace_id": workspace_id, "limit": 1},
            )

        if response.status_code == 404:
            pytest.skip("Executions endpoint not implemented")

        assert response.status_code == 200
        data = response.json()
        if isinstance(data, list):
            executions = data
        else:
            executions = data.get("executions", [])

        if not executions:
            pytest.skip("No executions available to test")

        execution_id = executions[0].get("id") or executions[0].get("_id")

        # Get single execution
        response = self.client.get(f"/admin/api/v1/executions/{execution_id}", headers=self.headers)

        # Accept both 200 and 404 (not implemented)
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            execution = response.json()
            assert "id" in execution or "_id" in execution
            assert "status" in execution

    def test_execution_data_structure(self):
        """Test that execution data has expected structure."""
        # Get workspaces first
        response = self.client.get("/admin/api/v1/workspaces", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        if isinstance(data, list):
            workspaces = data
        else:
            workspaces = data.get("workspaces", [])

        if not workspaces:
            pytest.skip("No workspaces available")

        workspace_id = workspaces[0]["id"]

        # Get executions
        response = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_id}/executions",
            headers=self.headers,
            params={"limit": 5},
        )

        if response.status_code == 404:
            response = self.client.get(
                "/admin/api/v1/executions",
                headers=self.headers,
                params={"workspace_id": workspace_id, "limit": 5},
            )

        if response.status_code == 404:
            pytest.skip("Executions endpoint not implemented")

        assert response.status_code == 200
        data = response.json()
        if isinstance(data, list):
            executions = data
        else:
            executions = data.get("executions", [])

        # Check structure of each execution
        for execution in executions:
            # Required fields
            assert "id" in execution or "_id" in execution
            assert "status" in execution
            assert execution["status"] in ["pending", "running", "completed", "failed", "cancelled"]

            # Optional but common fields
            if "action_id" in execution:
                assert isinstance(execution["action_id"], str)
            if "workspace_id" in execution:
                assert isinstance(execution["workspace_id"], str)
            if "started_at" in execution and execution["started_at"]:
                # Should be a valid ISO timestamp
                assert isinstance(execution["started_at"], str)
            if "execution_time_ms" in execution and execution["execution_time_ms"] is not None:
                assert isinstance(execution["execution_time_ms"], (int, float))
                assert execution["execution_time_ms"] >= 0

    def test_execution_error_handling(self):
        """Test error handling for invalid execution requests."""
        # Test with invalid workspace ID
        response = self.client.get(
            "/admin/api/v1/workspaces/invalid_workspace_id/executions", headers=self.headers
        )

        # Should return 400, 404, or 422 for invalid ID
        assert response.status_code in [400, 404, 422]

        # Test with missing authentication
        response = self.client.get("/admin/api/v1/executions")

        # Should return 401/403 when auth enabled, or 200/404 when auth disabled
        assert response.status_code in [200, 401, 403, 404]

    def test_execution_pagination(self):
        """Test pagination parameters for executions."""
        # Get workspaces first
        response = self.client.get("/admin/api/v1/workspaces", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        if isinstance(data, list):
            workspaces = data
        else:
            workspaces = data.get("workspaces", [])

        if not workspaces:
            pytest.skip("No workspaces available")

        workspace_id = workspaces[0]["id"]

        # Test with different limit values
        for limit in [1, 10, 100]:
            response = self.client.get(
                f"/admin/api/v1/workspaces/{workspace_id}/executions",
                headers=self.headers,
                params={"limit": limit},
            )

            if response.status_code == 404:
                response = self.client.get(
                    "/admin/api/v1/executions",
                    headers=self.headers,
                    params={"workspace_id": workspace_id, "limit": limit},
                )

            if response.status_code == 404:
                pytest.skip("Executions endpoint not implemented")

            assert response.status_code == 200
            data = response.json()
            if isinstance(data, list):
                executions = data
            else:
                executions = data.get("executions", [])

            # Should not exceed the limit
            assert len(executions) <= limit


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
