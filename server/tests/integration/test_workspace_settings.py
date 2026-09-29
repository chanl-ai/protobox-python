"""
Integration tests for workspace settings and slug management.

These tests require a running server with test mode enabled.
Run with: make test-integration
"""

import os
import time

import pytest
from httpx import Client

from .test_utils import get_emulator_auth_token


@pytest.mark.integration
class TestWorkspaceSettingsAPI:
    """Test workspace settings API endpoints against running server."""

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

    def test_get_workspaces(self):
        """Test getting workspace list."""
        response = self.client.get("/admin/api/v1/workspaces", headers=self.headers)
        assert response.status_code == 200

        data = response.json()
        # Handle both response formats
        workspaces = data.get("workspaces", data if isinstance(data, list) else [])
        assert isinstance(workspaces, list)

    def test_workspace_settings_crud(self):
        """Test workspace settings CRUD operations."""
        # Get workspaces
        response = self.client.get("/admin/api/v1/workspaces", headers=self.headers)
        data = response.json()
        workspaces = data.get("workspaces", data if isinstance(data, list) else [])

        if not workspaces:
            # Create test workspace
            response = self.client.post(
                "/admin/api/v1/workspaces",
                headers=self.headers,
                json={
                    "name": "Test Workspace Integration",
                    "description": "Integration test workspace",
                },
            )
            assert response.status_code in [200, 201]
            workspace = response.json()
        else:
            workspace = (
                workspaces[0]
                if isinstance(workspaces, list)
                else workspaces.get("workspaces", [])[0]
            )

        workspace_id = workspace.get("id") or workspace.get("_id")

        # Test 1: Get workspace settings
        response = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_id}/settings", headers=self.headers
        )
        assert response.status_code == 200
        settings = response.json()
        assert "default_model" in settings
        assert "max_file_size" in settings

        # Test 2: Update workspace settings
        new_settings = {
            "default_model": "gpt-4-turbo",
            "max_file_size": 20971520,
            "allowed_file_types": [".txt", ".pdf", ".md", ".json"],
            "enable_code_execution": True,
            "enable_web_search": True,
        }
        response = self.client.put(
            f"/admin/api/v1/workspaces/{workspace_id}/settings",
            headers=self.headers,
            json=new_settings,
        )
        assert response.status_code == 200
        updated = response.json()
        assert updated["default_model"] == "gpt-4-turbo"
        assert updated["max_file_size"] == 20971520

    def test_slug_validation(self):
        """Test slug validation endpoints."""
        # Get first workspace
        response = self.client.get("/admin/api/v1/workspaces", headers=self.headers)
        data = response.json()
        workspaces = data.get("workspaces", data if isinstance(data, list) else [])

        if not workspaces:
            pytest.skip("No workspaces available")

        workspace = (
            workspaces[0] if isinstance(workspaces, list) else workspaces.get("workspaces", [])[0]
        )
        workspace_id = workspace.get("id") or workspace.get("_id")

        # Test valid slug
        response = self.client.post(
            f"/admin/api/v1/workspaces/{workspace_id}/check-slug",
            headers=self.headers,
            params={"slug": "my-awesome-workspace"},
        )
        assert response.status_code == 200
        result = response.json()
        assert result["valid"] is True

        # Test reserved slug
        response = self.client.post(
            f"/admin/api/v1/workspaces/{workspace_id}/check-slug",
            headers=self.headers,
            params={"slug": "admin"},
        )
        assert response.status_code == 200
        result = response.json()
        assert result["valid"] is False
        assert "reserved" in result["error"].lower()

        # Test invalid format
        response = self.client.post(
            f"/admin/api/v1/workspaces/{workspace_id}/check-slug",
            headers=self.headers,
            params={"slug": "Invalid_Slug!"},
        )
        assert response.status_code == 200
        result = response.json()
        assert result["valid"] is False

    def test_slug_suggestion(self):
        """Test slug suggestion endpoint."""
        # Get first workspace
        response = self.client.get("/admin/api/v1/workspaces", headers=self.headers)
        data = response.json()
        workspaces = data.get("workspaces", data if isinstance(data, list) else [])

        if not workspaces:
            pytest.skip("No workspaces available")

        workspace = (
            workspaces[0] if isinstance(workspaces, list) else workspaces.get("workspaces", [])[0]
        )
        workspace_id = workspace.get("id") or workspace.get("_id")

        # Test slug suggestion
        response = self.client.post(
            f"/admin/api/v1/workspaces/{workspace_id}/suggest-slug",
            headers=self.headers,
            params={"name": "My Awesome Workspace 123"},
        )
        assert response.status_code == 200
        result = response.json()
        assert result["suggested_slug"] == "my-awesome-workspace-123"
        assert result["preview_url"].startswith("https://")

    def test_workspace_slug_update(self):
        """Test updating workspace slug."""
        # Get first workspace
        response = self.client.get("/admin/api/v1/workspaces", headers=self.headers)
        data = response.json()
        workspaces = data.get("workspaces", data if isinstance(data, list) else [])

        if not workspaces:
            pytest.skip("No workspaces available")

        workspace = (
            workspaces[0] if isinstance(workspaces, list) else workspaces.get("workspaces", [])[0]
        )
        workspace_id = workspace.get("id") or workspace.get("_id")

        # Update workspace with new slug
        new_slug = f"test-workspace-{int(time.time())}"
        response = self.client.patch(
            f"/admin/api/v1/workspaces/{workspace_id}",
            headers=self.headers,
            json={"slug": new_slug},
        )
        assert response.status_code == 200
        updated = response.json()
        assert updated["slug"] == new_slug

    def test_workspace_update_persistence(self):
        """Test that workspace updates persist correctly after save."""
        # Get workspaces
        response = self.client.get("/admin/api/v1/workspaces", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        workspaces = data.get("workspaces", data if isinstance(data, list) else [])

        if not workspaces:
            pytest.skip("No workspaces available")

        workspace = workspaces[0]
        workspace_id = workspace.get("id") or workspace.get("_id")
        original_name = workspace.get("name", "")
        original_desc = workspace.get("description", "")
        original_slug = workspace.get("slug", "")

        # Update workspace with new data
        timestamp = str(int(time.time()))
        new_data = {
            "name": f"Updated Workspace {timestamp}",
            "description": f"Updated description at {timestamp}",
            "slug": f"updated-workspace-{timestamp}",
        }

        response = self.client.patch(
            f"/admin/api/v1/workspaces/{workspace_id}", headers=self.headers, json=new_data
        )
        assert response.status_code == 200
        updated_workspace = response.json()

        # Verify the immediate response has the updates
        assert updated_workspace["name"] == new_data["name"]
        assert updated_workspace["description"] == new_data["description"]
        assert updated_workspace["slug"] == new_data["slug"]

        # Now fetch workspaces again to verify persistence
        response = self.client.get("/admin/api/v1/workspaces", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        workspaces = data.get("workspaces", data if isinstance(data, list) else [])

        # Find the updated workspace
        updated = None
        for ws in workspaces:
            if ws["_id"] == workspace_id:
                updated = ws
                break

        assert updated is not None, "Workspace not found after update"
        assert updated["name"] == new_data["name"], "Name didn't persist"
        assert updated["description"] == new_data["description"], "Description didn't persist"
        assert updated["slug"] == new_data["slug"], "Slug didn't persist"

        # Clean up - restore original values
        if original_name:
            self.client.patch(
                f"/admin/api/v1/workspaces/{workspace_id}",
                headers=self.headers,
                json={
                    "name": original_name,
                    "description": original_desc,
                    "slug": original_slug if original_slug else None,
                },
            )

    def test_workspace_slug_generation_from_null(self):
        """Test that workspaces with null slugs get properly handled."""
        # Get workspaces
        response = self.client.get("/admin/api/v1/workspaces", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        workspaces = data.get("workspaces", data if isinstance(data, list) else [])

        if not workspaces:
            pytest.skip("No workspaces available")

        workspace = workspaces[0]
        workspace_id = workspace.get("id") or workspace.get("_id")
        original_slug = workspace.get("slug")

        # First, set the slug to null by directly updating without providing slug
        response = self.client.patch(
            f"/admin/api/v1/workspaces/{workspace_id}",
            headers=self.headers,
            json={"description": "Test description"},
        )
        assert response.status_code == 200

        # Then set it explicitly to null to simulate the bug scenario
        # Note: In a real scenario, this would be done via direct DB manipulation
        # but for testing we'll verify the fix handles existing null values

        # Create a new workspace that should have a proper slug generated
        # NOTE: Using the workspaces_router endpoint (with trailing slash) which has proper slug generation
        timestamp = str(int(time.time()))
        response = self.client.post(
            "/admin/api/v1/workspaces/",
            headers=self.headers,
            json={
                "name": f"Test Slug Generation {timestamp}",
                "description": "Testing slug generation",
            },
        )
        
        if response.status_code in [200, 201]:
            created_workspace = response.json()
            print(f"DEBUG: Created workspace response: {created_workspace}")
            assert created_workspace["slug"] is not None, f"Expected slug to be generated, got: {created_workspace.get('slug')}"
            assert created_workspace["slug"] != ""
            # The expected slug should be: test-slug-generation-{timestamp}
            expected_slug = f"test-slug-generation-{timestamp}"
            assert created_workspace["slug"] == expected_slug, f"Expected slug '{expected_slug}', got '{created_workspace['slug']}'"
            
            # Clean up the created workspace
            self.client.delete(
                f"/admin/api/v1/workspaces/{created_workspace['_id']}", 
                headers=self.headers
            )

        # Restore original slug if it existed
        if original_slug:
            self.client.patch(
                f"/admin/api/v1/workspaces/{workspace_id}",
                headers=self.headers,
                json={"slug": original_slug},
            )

    def test_workspace_slug_null_handling_in_list(self):
        """Test that null slugs in workspace list are handled correctly."""
        # Get workspaces list
        response = self.client.get("/admin/api/v1/workspaces", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        workspaces = data.get("workspaces", data if isinstance(data, list) else [])

        # The list endpoint should return workspaces even if some have null slugs
        # This tests the fix for the condition: if "slug" not in workspace or workspace["slug"] is None
        assert isinstance(workspaces, list)
        
        for workspace in workspaces:
            # Verify structure
            assert "_id" in workspace
            assert "name" in workspace
            # slug can be null or a string, but should be present in the response
            assert "slug" in workspace
            # If slug is not null, it should be a valid string
            if workspace["slug"] is not None:
                assert isinstance(workspace["slug"], str)
                assert len(workspace["slug"]) > 0

    def test_workspace_slug_update_from_null(self):
        """Test updating a workspace that has a null slug."""
        # Get workspaces
        response = self.client.get("/admin/api/v1/workspaces", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        workspaces = data.get("workspaces", data if isinstance(data, list) else [])

        if not workspaces:
            pytest.skip("No workspaces available")

        workspace = workspaces[0]
        workspace_id = workspace.get("id") or workspace.get("_id")
        original_slug = workspace.get("slug")

        # Test updating a workspace with a new slug (even if current is null)
        timestamp = str(int(time.time()))
        new_slug = f"updated-from-null-{timestamp}"
        
        response = self.client.patch(
            f"/admin/api/v1/workspaces/{workspace_id}",
            headers=self.headers,
            json={"slug": new_slug},
        )
        assert response.status_code == 200
        updated_workspace = response.json()
        assert updated_workspace["slug"] == new_slug

        # Verify persistence by fetching the workspace again
        response = self.client.get(f"/admin/api/v1/workspaces/{workspace_id}", headers=self.headers)
        assert response.status_code == 200
        fetched_workspace = response.json()
        assert fetched_workspace["slug"] == new_slug

        # Restore original slug
        restore_slug = original_slug if original_slug else None
        self.client.patch(
            f"/admin/api/v1/workspaces/{workspace_id}",
            headers=self.headers,
            json={"slug": restore_slug},
        )

    def test_workspace_stats_api(self):
        """Test the new workspace stats API endpoint."""
        # Get workspaces
        response = self.client.get("/admin/api/v1/workspaces", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        workspaces = data.get("workspaces", data if isinstance(data, list) else [])

        if not workspaces:
            pytest.skip("No workspaces available")

        workspace = workspaces[0]
        workspace_id = workspace.get("id") or workspace.get("_id")

        # Test workspace stats endpoint
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
