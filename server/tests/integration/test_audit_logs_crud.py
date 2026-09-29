"""
Integration tests for audit logs on CRUD operations.

Tests that CREATE, UPDATE, and DELETE operations properly create audit logs.
"""

import json
import logging
from datetime import datetime
from unittest.mock import patch

import pytest
from httpx import Client

logger = logging.getLogger(__name__)


@pytest.mark.integration
class TestAuditLogsCRUD:
    """Test audit logs for CRUD operations on actions."""

    @classmethod
    def setup_class(cls):
        """Setup test client and authenticate."""
        cls.client = Client(base_url="http://localhost:8090", timeout=10.0)
        cls.skip_tests = False
        cls.skip_reason = ""
        
        # Try to get test token
        try:
            response = cls.client.post(
                "/admin/api/v1/auth/exchange",
                json={"firebase_token": "test-user123"}
            )
            if response.status_code == 200:
                cls.token = response.json()["access_token"]
                cls.headers = {"Authorization": f"Bearer {cls.token}"}
                
                # Get or create test workspace
                workspaces_response = cls.client.get(
                    "/admin/api/v1/workspaces",
                    headers=cls.headers
                )
                if workspaces_response.status_code == 200:
                    workspaces = workspaces_response.json()
                    if workspaces:
                        cls.workspace_id = workspaces[0]["id"]
                    else:
                        # Create a test workspace
                        create_response = cls.client.post(
                            "/admin/api/v1/workspaces",
                            json={"name": "Test Workspace for Audit Logs"},
                            headers=cls.headers
                        )
                        if create_response.status_code in [200, 201]:
                            cls.workspace_id = create_response.json()["id"]
                        else:
                            cls.skip_tests = True
                            cls.skip_reason = "Failed to create test workspace"
                else:
                    cls.skip_tests = True
                    cls.skip_reason = "Failed to get workspaces"
            else:
                cls.skip_tests = True
                cls.skip_reason = "Test mode not enabled or server not running"
        except Exception as e:
            cls.skip_tests = True
            cls.skip_reason = f"Server not running or connection failed: {e}"
    
    @classmethod
    def teardown_class(cls):
        """Cleanup test client."""
        if hasattr(cls, 'client'):
            cls.client.close()
    
    def setup_method(self):
        """Check if tests should be skipped."""
        if self.skip_tests:
            pytest.skip(self.skip_reason)
    
    def test_audit_log_on_action_create(self):
        """Test that CREATE operation creates an audit log."""
        # Create an action
        action_data = {
            "name": f"test-action-{datetime.utcnow().timestamp()}",
            "type": "REST",
            "description": "Test action for audit logs",
            "config": {
                "url": "https://api.example.com/test",
                "method": "GET"
            }
        }
        
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/actions",
            json=action_data,
            headers=self.headers
        )
        
        assert response.status_code in [200, 201], f"Failed to create action: {response.text}"
        action = response.json()
        action_id = action["id"]
        
        # Check audit logs for CREATE operation
        audit_response = self.client.get(
            f"/admin/api/v1/workspaces/{self.workspace_id}/audit-logs",
            params={"resource_type": "action", "limit": 10},
            headers=self.headers
        )
        
        assert audit_response.status_code == 200, f"Failed to get audit logs: {audit_response.text}"
        audit_data = audit_response.json()
        logs = audit_data.get("logs", [])
        
        # Find the CREATE log for our action
        create_log = None
        for log in logs:
            if (log.get("resource_id") == action_id and 
                log.get("action") == "CREATE"):
                create_log = log
                break
        
        assert create_log is not None, f"No CREATE audit log found for action {action_id}"
        assert create_log["resource_type"] == "action"
        assert create_log["workspace_id"] == self.workspace_id
        
        # Clean up - delete the action
        self.client.delete(
            f"/admin/api/v1/workspaces/{self.workspace_id}/actions/{action_id}",
            headers=self.headers
        )
    
    def test_audit_log_on_action_update(self):
        """Test that UPDATE operation creates an audit log."""
        # First create an action
        action_data = {
            "name": f"test-action-update-{datetime.utcnow().timestamp()}",
            "type": "REST",
            "description": "Original description",
            "config": {
                "url": "https://api.example.com/test",
                "method": "GET"
            }
        }
        
        create_response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/actions",
            json=action_data,
            headers=self.headers
        )
        
        assert create_response.status_code in [200, 201], f"Failed to create action: {create_response.text}"
        action = create_response.json()
        action_id = action["id"]
        
        # Update the action
        update_data = {
            "description": "Updated description for audit test",
            "tags": ["audit", "test", "updated"]
        }
        
        update_response = self.client.put(
            f"/admin/api/v1/workspaces/{self.workspace_id}/actions/{action_id}",
            json=update_data,
            headers=self.headers
        )
        
        assert update_response.status_code == 200, f"Failed to update action: {update_response.text}"
        
        # Check audit logs for UPDATE operation
        audit_response = self.client.get(
            f"/admin/api/v1/workspaces/{self.workspace_id}/audit-logs",
            params={"resource_type": "action", "limit": 20},
            headers=self.headers
        )
        
        assert audit_response.status_code == 200, f"Failed to get audit logs: {audit_response.text}"
        audit_data = audit_response.json()
        logs = audit_data.get("logs", [])
        
        # Find the UPDATE log for our action
        update_log = None
        for log in logs:
            if (log.get("resource_id") == action_id and 
                log.get("action") == "UPDATE"):
                update_log = log
                break
        
        assert update_log is not None, f"No UPDATE audit log found for action {action_id}. Found logs: {json.dumps(logs, indent=2)}"
        assert update_log["resource_type"] == "action"
        assert update_log["workspace_id"] == self.workspace_id
        
        # Check that changes are recorded
        changes = update_log.get("changes", {})
        assert "description" in changes, "UPDATE log missing description change"
        assert "tags" in changes, "UPDATE log missing tags change"
        
        # Clean up - delete the action
        self.client.delete(
            f"/admin/api/v1/workspaces/{self.workspace_id}/actions/{action_id}",
            headers=self.headers
        )
    
    def test_audit_log_on_action_delete(self):
        """Test that DELETE operation creates an audit log."""
        # First create an action
        action_data = {
            "name": f"test-action-delete-{datetime.utcnow().timestamp()}",
            "type": "REST",
            "description": "Test action to be deleted",
            "config": {
                "url": "https://api.example.com/test",
                "method": "GET"
            }
        }
        
        create_response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/actions",
            json=action_data,
            headers=self.headers
        )
        
        assert create_response.status_code in [200, 201], f"Failed to create action: {create_response.text}"
        action = create_response.json()
        action_id = action["id"]
        action_name = action["name"]
        
        # Delete the action
        delete_response = self.client.delete(
            f"/admin/api/v1/workspaces/{self.workspace_id}/actions/{action_id}",
            headers=self.headers
        )
        
        assert delete_response.status_code == 204, f"Failed to delete action: {delete_response.text if delete_response.status_code != 204 else 'No content'}"
        
        # Check audit logs for DELETE operation
        audit_response = self.client.get(
            f"/admin/api/v1/workspaces/{self.workspace_id}/audit-logs",
            params={"resource_type": "action", "limit": 20},
            headers=self.headers
        )
        
        assert audit_response.status_code == 200, f"Failed to get audit logs: {audit_response.text}"
        audit_data = audit_response.json()
        logs = audit_data.get("logs", [])
        
        # Find the DELETE log for our action
        delete_log = None
        for log in logs:
            if (log.get("resource_id") == action_id and 
                log.get("action") == "DELETE"):
                delete_log = log
                break
        
        assert delete_log is not None, f"No DELETE audit log found for action {action_id}. Found logs: {json.dumps(logs, indent=2)}"
        assert delete_log["resource_type"] == "action"
        assert delete_log["workspace_id"] == self.workspace_id
        
        # Check metadata
        metadata = delete_log.get("metadata", {})
        assert metadata.get("action_name") == action_name or metadata.get("action_action_name") == action_name, f"DELETE log missing action_name in metadata: {metadata}"
    
    def test_all_crud_operations_logged(self):
        """Test that all CRUD operations (CREATE, UPDATE, DELETE) are logged."""
        # Create an action
        action_data = {
            "name": f"test-action-all-{datetime.utcnow().timestamp()}",
            "type": "REST",
            "description": "Test all CRUD operations",
            "config": {
                "url": "https://api.example.com/test",
                "method": "GET"
            }
        }
        
        create_response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/actions",
            json=action_data,
            headers=self.headers
        )
        
        assert create_response.status_code in [200, 201]
        action = create_response.json()
        action_id = action["id"]
        
        # Update the action
        update_data = {
            "description": "Updated for full CRUD test",
            "tags": ["crud", "test"]
        }
        
        update_response = self.client.put(
            f"/admin/api/v1/workspaces/{self.workspace_id}/actions/{action_id}",
            json=update_data,
            headers=self.headers
        )
        
        assert update_response.status_code == 200
        
        # Delete the action
        delete_response = self.client.delete(
            f"/admin/api/v1/workspaces/{self.workspace_id}/actions/{action_id}",
            headers=self.headers
        )
        
        assert delete_response.status_code == 204
        
        # Check audit logs for all operations
        audit_response = self.client.get(
            f"/admin/api/v1/workspaces/{self.workspace_id}/audit-logs",
            params={"resource_type": "action", "limit": 50},
            headers=self.headers
        )
        
        assert audit_response.status_code == 200
        audit_data = audit_response.json()
        logs = audit_data.get("logs", [])
        
        # Check for each operation
        operations_found = {"CREATE": False, "UPDATE": False, "DELETE": False}
        
        for log in logs:
            if log.get("resource_id") == action_id:
                action = log.get("action")
                if action in operations_found:
                    operations_found[action] = True
        
        # Verify all operations were logged
        for operation, found in operations_found.items():
            assert found, f"{operation} operation was not logged for action {action_id}"
        
        logger.info("✅ All CRUD operations were properly audited")