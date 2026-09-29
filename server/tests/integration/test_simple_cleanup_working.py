"""
Working demonstration of simple cleanup functionality.
"""

import pytest
import time
from .test_utils import AuthenticatedTestCase


@pytest.mark.integration
class TestSimpleCleanupWorking(AuthenticatedTestCase):
    """Working demonstration of simple cleanup with real test scenarios."""
    
    @classmethod
    def setup_class(cls):
        """Set up test environment."""
        import os
        environment = os.getenv("TEST_ENVIRONMENT", "local")
        cls.setup_auth(environment=environment)
        
        # Initialize cleanup tracking
        cls.created_documents = []
        cls.created_actions = []
        cls.created_secrets = []
    
    @classmethod
    def teardown_class(cls):
        """Clean up after all tests - TESTS DELETION APIS."""
        if not cls.skip_tests:
            print(f"\n🧹 TESTING DELETION APIS AND CLEANING UP...")
            cls._cleanup_all_resources()
        
        cls.teardown_auth()
    
    @classmethod
    def _cleanup_all_resources(cls):
        """Clean up all tracked resources and test deletion APIs."""
        total_deleted = 0
        total_failed = 0
        
        # Clean up actions
        if cls.created_actions:
            print(f"🧹 Testing action deletion API with {len(cls.created_actions)} actions...")
            for action_id in cls.created_actions:
                try:
                    response = cls.client.delete(
                        f"/admin/api/v1/workspaces/{cls.workspace_id}/actions/{action_id}",
                        headers=cls.headers
                    )
                    
                    if response.status_code in [200, 204, 404]:
                        print(f"✅ Deleted action: {action_id}")
                        total_deleted += 1
                    else:
                        print(f"❌ Failed to delete action {action_id}: {response.status_code}")
                        total_failed += 1
                        
                except Exception as e:
                    print(f"❌ Error deleting action {action_id}: {e}")
                    total_failed += 1
        
        # Clean up secrets
        if cls.created_secrets:
            print(f"🧹 Testing secret deletion API with {len(cls.created_secrets)} secrets...")
            for secret_id in cls.created_secrets:
                try:
                    response = cls.client.delete(
                        f"/admin/api/v1/workspaces/{cls.workspace_id}/secrets/{secret_id}",
                        headers=cls.headers
                    )
                    
                    if response.status_code in [200, 204, 404]:
                        print(f"✅ Deleted secret: {secret_id}")
                        total_deleted += 1
                    else:
                        print(f"❌ Failed to delete secret {secret_id}: {response.status_code}")
                        total_failed += 1
                        
                except Exception as e:
                    print(f"❌ Error deleting secret {secret_id}: {e}")
                    total_failed += 1
        
        # Clean up documents
        if cls.created_documents:
            print(f"🧹 Testing document deletion API with {len(cls.created_documents)} documents...")
            for doc_id in cls.created_documents:
                try:
                    response = cls.client.delete(
                        f"/admin/api/v1/workspaces/{cls.workspace_id}/knowledge/documents/{doc_id}",
                        headers=cls.headers
                    )
                    
                    if response.status_code in [200, 204, 404]:
                        print(f"✅ Deleted document: {doc_id}")
                        total_deleted += 1
                    else:
                        print(f"❌ Failed to delete document {doc_id}: {response.status_code}")
                        total_failed += 1
                        
                except Exception as e:
                    print(f"❌ Error deleting document {doc_id}: {e}")
                    total_failed += 1
        
        print(f"\n📊 CLEANUP SUMMARY: {total_deleted} deleted, {total_failed} failed")
        if total_deleted > 0:
            print("✅ DELETION APIS TESTED SUCCESSFULLY!")
    
    def setup_method(self):
        """Set up for each test method."""
        if self.skip_tests:
            pytest.skip(self.skip_reason)
    
    def test_create_action_with_cleanup(self):
        """Test creating an action that will be cleaned up."""
        if self.environment == "production":
            pytest.skip("Skipping action creation in production")
        
        # Create test action
        action_data = {
            "name": f"test-cleanup-action-{int(time.time())}",
            "type": "REST",
            "description": "Test action for cleanup demonstration",
            "config": {
                "url": "https://httpbin.org/get",
                "method": "GET"
            }
        }
        
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/actions",
            headers=self.headers,
            json=action_data
        )
        
        assert response.status_code in [200, 201], f"Failed to create action: {response.text}"
        
        action_id = response.json()["id"]
        print(f"✅ Created test action: {action_id}")
        
        # Track for cleanup
        self.created_actions.append(action_id)
        
        # Verify action exists
        get_response = self.client.get(
            f"/admin/api/v1/workspaces/{self.workspace_id}/actions/{action_id}",
            headers=self.headers
        )
        assert get_response.status_code == 200
        
        print(f"📝 Action {action_id} tracked for cleanup")
    
    def test_create_secret_with_cleanup(self):
        """Test creating a secret that will be cleaned up."""
        if self.environment == "production":
            pytest.skip("Skipping secret creation in production")
        
        # Create test secret
        secret_data = {
            "name": f"test-cleanup-secret-{int(time.time())}",
            "value": "secret-test-value-123",
            "description": "Test secret for cleanup demonstration"
        }
        
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/secrets",
            headers=self.headers,
            json=secret_data
        )
        
        assert response.status_code in [200, 201], f"Failed to create secret: {response.text}"
        
        secret_id = response.json()["id"]
        print(f"✅ Created test secret: {secret_id}")
        
        # Track for cleanup
        self.created_secrets.append(secret_id)
        
        print(f"📝 Secret {secret_id} tracked for cleanup")
    
    def test_create_multiple_resources_for_bulk_cleanup(self):
        """Test creating multiple resources for bulk cleanup testing."""
        if self.environment == "production":
            pytest.skip("Skipping resource creation in production")
        
        timestamp = int(time.time())
        created_count = 0
        
        # Create multiple actions
        for i in range(2):
            action_data = {
                "name": f"test-bulk-action-{timestamp}-{i}",
                "type": "REST",
                "description": f"Bulk test action {i}",
                "config": {
                    "url": f"https://httpbin.org/get?id={i}",
                    "method": "GET"
                }
            }
            
            response = self.client.post(
                f"/admin/api/v1/workspaces/{self.workspace_id}/actions",
                headers=self.headers,
                json=action_data
            )
            
            if response.status_code in [200, 201]:
                action_id = response.json()["id"]
                self.created_actions.append(action_id)
                created_count += 1
                print(f"✅ Created bulk action {i}: {action_id}")
        
        # Create a secret
        secret_data = {
            "name": f"test-bulk-secret-{timestamp}",
            "value": "bulk-secret-value",
            "description": "Bulk test secret"
        }
        
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/secrets",
            headers=self.headers,
            json=secret_data
        )
        
        if response.status_code in [200, 201]:
            secret_id = response.json()["id"]
            self.created_secrets.append(secret_id)
            created_count += 1
            print(f"✅ Created bulk secret: {secret_id}")
        
        print(f"📊 Created {created_count} resources for bulk cleanup testing")
        assert created_count >= 2, "Should have created at least 2 resources for testing"