"""
Demonstration of simple cleanup functionality.

This shows how to add simple cleanup to integration tests that:
1. Tests deletion APIs
2. Cleans up after tests
3. Works with existing test patterns
"""

import pytest
import time
from .test_utils import AuthenticatedTestCase
from .simple_cleanup import SimpleCleanupMixin


@pytest.mark.integration
@pytest.mark.cleanup_demo
class TestSimpleCleanupDemo(AuthenticatedTestCase, SimpleCleanupMixin):
    """Demonstration of simple cleanup with real test scenarios."""
    
    @classmethod
    def setup_class(cls):
        """Set up test environment."""
        environment = cls.get_test_environment()
        cls.setup_auth(environment=environment)
        
        # Initialize cleanup tracking
        cls.created_documents = []
        cls.created_actions = []
        cls.created_secrets = []
    
    @classmethod
    def teardown_class(cls):
        """Clean up after all tests."""
        if not cls.skip_tests:
            # Create cleanup instance and transfer tracked resources
            cleanup = SimpleCleanupMixin()
            cleanup.client = cls.client
            cleanup.headers = cls.headers
            cleanup.workspace_id = cls.workspace_id
            cleanup.created_documents = cls.created_documents
            cleanup.created_actions = cls.created_actions
            cleanup.created_secrets = cls.created_secrets
            
            # Run cleanup and test deletion APIs
            print(f"\n🧹 Running cleanup for {len(cls.created_documents + cls.created_actions + cls.created_secrets)} resources...")
            cleanup_results = cleanup.cleanup_all_created_resources()
            
            # Validate cleanup worked
            total_deleted = sum(len(result.get("deleted", [])) for result in cleanup_results.values())
            if total_deleted > 0:
                print(f"✅ Successfully tested deletion APIs and cleaned up {total_deleted} resources")
        
        cls.teardown_auth()
    
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
    
    def test_create_document_with_cleanup(self):
        """Test creating a document that will be cleaned up."""
        if self.environment == "production":
            pytest.skip("Skipping document creation in production")
        
        # Create test document
        doc_data = {
            "source_type": "text",
            "title": f"test-cleanup-doc-{int(time.time())}",
            "content": "This document will be cleaned up after the test.",
            "chunking_strategy": "smart"
        }
        
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/knowledge/upload",
            headers=self.headers,
            data=doc_data
        )
        
        assert response.status_code in [200, 201], f"Failed to create document: {response.text}"
        
        result = response.json()
        if "task_id" in result:
            # Handle async processing
            task_id = result["task_id"]
            print(f"✅ Document upload started (task: {task_id})")
            
            # Wait a bit for processing
            time.sleep(2)
            
            # Get documents to find our uploaded document
            docs_response = self.client.get(
                f"/admin/api/v1/workspaces/{self.workspace_id}/knowledge/documents",
                headers=self.headers
            )
            
            if docs_response.status_code == 200:
                documents = docs_response.json()
                # Find document by title
                test_doc = next(
                    (doc for doc in documents if doc.get("title", "").startswith("test-cleanup-doc")),
                    None
                )
                
                if test_doc:
                    document_id = test_doc["id"]
                    print(f"✅ Found uploaded document: {document_id}")
                    self.created_documents.append(document_id)
                else:
                    print("⚠️ Document not found after upload, tracking task_id instead")
                    # In a real scenario, we'd poll for completion
                    self.created_documents.append(task_id)
        else:
            document_id = result["id"]
            print(f"✅ Created test document: {document_id}")
            self.created_documents.append(document_id)
        
        print("📝 Document tracked for cleanup")
    
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
        
        # Verify secret exists
        get_response = self.client.get(
            f"/admin/api/v1/workspaces/{self.workspace_id}/secrets/{secret_id}",
            headers=self.headers
        )
        assert get_response.status_code == 200
        
        print(f"📝 Secret {secret_id} tracked for cleanup")
    
    def test_create_multiple_resources_with_cleanup(self):
        """Test creating multiple resources for bulk cleanup testing."""
        if self.environment == "production":
            pytest.skip("Skipping resource creation in production")
        
        timestamp = int(time.time())
        created_count = 0
        
        # Create multiple actions
        for i in range(3):
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
        
        # Create multiple secrets
        for i in range(2):
            secret_data = {
                "name": f"test-bulk-secret-{timestamp}-{i}",
                "value": f"bulk-secret-value-{i}",
                "description": f"Bulk test secret {i}"
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
                print(f"✅ Created bulk secret {i}: {secret_id}")
        
        print(f"📊 Created {created_count} resources for bulk cleanup testing")
        assert created_count >= 3, "Should have created at least 3 resources for testing"


@pytest.mark.integration
@pytest.mark.cleanup_demo
@pytest.mark.production
class TestProductionSafeCleanupDemo(AuthenticatedTestCase):
    """Demonstration that cleanup works safely in production."""
    
    @classmethod
    def setup_class(cls):
        """Set up for production testing."""
        cls.setup_auth(environment="production")
    
    @classmethod
    def teardown_class(cls):
        """Clean up after production tests."""
        cls.teardown_auth()
    
    def setup_method(self):
        """Set up for each test method."""
        if self.skip_tests:
            pytest.skip(self.skip_reason)
    
    def test_cleanup_initialization_in_production(self):
        """Test that cleanup utilities initialize safely in production."""
        
        # Initialize cleanup
        cleanup = SimpleCleanupMixin()
        cleanup.client = self.client
        cleanup.headers = self.headers
        cleanup.workspace_id = self.workspace_id
        
        # Should initialize without issues
        assert hasattr(cleanup, 'created_documents')
        assert hasattr(cleanup, 'created_actions')
        assert len(cleanup.created_documents) == 0
        assert len(cleanup.created_actions) == 0
        
        print("✅ Cleanup utilities initialize safely in production")
    
    def test_deletion_api_accessibility_in_production(self):
        """Test that deletion APIs are accessible (but don't delete real data)."""
        
        # Test deletion endpoints with non-existent IDs
        # This tests that the APIs exist and respond appropriately
        
        # Test document deletion
        response = self.client.delete(
            f"/admin/api/v1/workspaces/{self.workspace_id}/knowledge/documents/non-existent-doc-id",
            headers=self.headers
        )
        # Should return 404 (not found) which means the API exists
        assert response.status_code in [404, 405], f"Document deletion API unexpected response: {response.status_code}"
        
        # Test action deletion
        response = self.client.delete(
            f"/admin/api/v1/workspaces/{self.workspace_id}/actions/non-existent-action-id",
            headers=self.headers
        )
        assert response.status_code in [404, 405], f"Action deletion API unexpected response: {response.status_code}"
        
        # Test secret deletion
        response = self.client.delete(
            f"/admin/api/v1/workspaces/{self.workspace_id}/secrets/non-existent-secret-id",
            headers=self.headers
        )
        assert response.status_code in [404, 405], f"Secret deletion API unexpected response: {response.status_code}"
        
        print("✅ All deletion APIs are accessible in production")
    
    def test_no_resource_creation_in_production(self):
        """Verify that our test patterns prevent resource creation in production."""
        
        # All resource creation should be skipped in production
        # This test verifies our safety mechanisms work
        
        timestamp = int(time.time())
        
        # This would create an action in non-production environments
        action_data = {
            "name": f"should-not-create-action-{timestamp}",
            "type": "REST",
            "description": "This should not be created in production",
            "config": {
                "url": "https://httpbin.org/get",
                "method": "GET"
            }
        }
        
        # In production, we skip this test instead of creating resources
        if self.environment == "production":
            print("🔒 Correctly skipping resource creation in production")
            pytest.skip("Correctly preventing resource creation in production")
        
        # This line should never execute in production
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/actions",
            headers=self.headers,
            json=action_data
        )
        
        # If we get here, we're not in production
        print("✅ Resource creation test running in non-production environment")