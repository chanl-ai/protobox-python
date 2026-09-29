"""
Enhanced test base class with automatic cleanup integration.

This extends AuthenticatedTestCase to automatically manage test data cleanup
across all integration tests.
"""

import asyncio
from typing import Any, Dict, List, Optional

import pytest

from .test_data_cleanup import DataManager, ResourceCleanup
from .test_utils import AuthenticatedTestCase


class CleanupEnabledTestCase(AuthenticatedTestCase):
    """Enhanced test case with automatic test data management and cleanup."""
    
    @classmethod
    def setup_class(cls):
        """Set up test environment with cleanup management."""
        # Determine environment
        environment = cls.get_test_environment()
        cls.setup_auth(environment=environment)
        
        if not cls.skip_tests:
            # Initialize data management
            cls.data_manager = DataManager(environment)
            cls.cleanup_handler = ResourceCleanup(
                cls.client, cls.headers, cls.workspace_id, environment
            )
            
            # Run pre-test cleanup (clean slate)
            cls._run_pre_test_cleanup()
    
    @classmethod
    def teardown_class(cls):
        """Clean up after all tests with deletion API testing."""
        if hasattr(cls, 'cleanup_handler') and not cls.skip_tests:
            # Run post-test cleanup (tests deletion APIs)
            cls._run_post_test_cleanup()
        
        cls.teardown_auth()
    
    @classmethod
    def _run_pre_test_cleanup(cls):
        """Run cleanup before tests start."""
        if cls.data_manager.environment == "production":
            print("🔒 Skipping pre-test cleanup in production")
            return
        
        print(f"🧹 Running pre-test cleanup for {cls.data_manager.environment} environment...")
        
        try:
            # Clean up any existing test data
            cleanup_results = asyncio.run(
                cls.cleanup_handler.cleanup_test_data_by_prefix("test-")
            )
            
            if cleanup_results.get("cleaned_types"):
                print(f"✅ Pre-cleanup completed: {cleanup_results['cleaned_types']}")
            
            if cleanup_results.get("errors"):
                print(f"⚠️ Pre-cleanup errors: {cleanup_results['errors']}")
                
        except Exception as e:
            print(f"⚠️ Pre-test cleanup failed: {e}")
    
    @classmethod
    def _run_post_test_cleanup(cls):
        """Run cleanup after tests (tests deletion APIs)."""
        tracked_resources = cls.data_manager.get_tracked_resources()
        
        # Only run cleanup if we have tracked resources
        if not any(tracked_resources.values()):
            print("✅ No test resources to clean up")
            return
        
        print(f"🧹 Running post-test cleanup and deletion API tests...")
        
        try:
            cleanup_results = asyncio.run(
                cls.cleanup_handler.cleanup_all_tracked(tracked_resources)
            )
            
            # Validate cleanup results
            cls._validate_cleanup_results(cleanup_results)
            
        except Exception as e:
            print(f"❌ Post-test cleanup failed: {e}")
            if cls.data_manager.environment != "production":
                # Re-raise in non-production to catch cleanup issues
                raise
    
    @classmethod
    def _validate_cleanup_results(cls, cleanup_results: Dict[str, Any]):
        """Validate that cleanup worked correctly."""
        total_deleted = 0
        total_failed = 0
        
        for resource_type, results in cleanup_results.items():
            deleted_count = len(results.get("deleted", []))
            failed_count = len(results.get("failed", []))
            error_count = len(results.get("errors", []))
            
            total_deleted += deleted_count
            total_failed += failed_count + error_count
            
            if deleted_count > 0:
                print(f"✅ Deleted {deleted_count} {resource_type}")
            
            if failed_count > 0 or error_count > 0:
                print(f"⚠️ Failed to delete {failed_count + error_count} {resource_type}")
        
        print(f"🧹 Cleanup summary: {total_deleted} deleted, {total_failed} failed")
        
        # In non-production, we expect most cleanup to succeed
        if cls.data_manager.environment != "production" and total_failed > total_deleted:
            print(f"⚠️ High cleanup failure rate - deletion APIs may have issues")
    
    def track_created_resource(self, resource_type: str, resource_id: str):
        """Track a resource created during testing for automatic cleanup."""
        if hasattr(self, 'data_manager'):
            self.data_manager.track_resource(resource_type, resource_id)
            print(f"📝 Tracking {resource_type}: {resource_id}")
    
    def get_test_resource_name(self, base_name: str) -> str:
        """Get a unique test resource name."""
        if hasattr(self, 'data_manager'):
            return self.data_manager.get_test_name(base_name)
        else:
            # Fallback for production or when data manager not available
            import time
            return f"test-{base_name}-{int(time.time())}"
    
    def create_test_document(self, title: str, content: str, track: bool = True) -> Optional[str]:
        """Helper to create a test document with automatic tracking."""
        if self.environment == "production":
            pytest.skip("Skipping document creation in production")
        
        doc_data = {
            "source_type": "text",
            "title": self.get_test_resource_name(title),
            "content": content,
            "chunking_strategy": "smart"
        }
        
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/knowledge/upload",
            headers=self.headers,
            data=doc_data
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            
            # Handle async processing
            if "task_id" in result:
                # For async processing, we'd need to poll for completion
                # For now, return the task_id and handle in calling test
                task_id = result["task_id"]
                if track:
                    # We'll track the task for now, real implementation would poll for doc_id
                    self.track_created_resource("documents", task_id)
                return task_id
            else:
                document_id = result["id"]
                if track:
                    self.track_created_resource("documents", document_id)
                return document_id
        
        return None
    
    def create_test_action(self, name: str, url: str = "https://httpbin.org/get", track: bool = True) -> Optional[str]:
        """Helper to create a test action with automatic tracking."""
        if self.environment == "production":
            pytest.skip("Skipping action creation in production")
        
        action_data = {
            "name": self.get_test_resource_name(name),
            "type": "REST",
            "description": f"Test action: {name}",
            "config": {
                "url": url,
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
            if track:
                self.track_created_resource("actions", action_id)
            return action_id
        
        return None
    
    def create_test_secret(self, name: str, value: str = "test-secret-value", track: bool = True) -> Optional[str]:
        """Helper to create a test secret with automatic tracking."""
        if self.environment == "production":
            pytest.skip("Skipping secret creation in production")
        
        secret_data = {
            "name": self.get_test_resource_name(name),
            "value": value,
            "description": f"Test secret: {name}"
        }
        
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/secrets",
            headers=self.headers,
            json=secret_data
        )
        
        if response.status_code in [200, 201]:
            secret_id = response.json()["id"]
            if track:
                self.track_created_resource("secrets", secret_id)
            return secret_id
        
        return None


# Example usage test class showing the enhanced capabilities
@pytest.mark.integration
@pytest.mark.enhanced_cleanup
class TestEnhancedCleanupExample(CleanupEnabledTestCase):
    """Example test class demonstrating enhanced cleanup capabilities."""
    
    def test_document_creation_with_auto_cleanup(self):
        """Test document creation with automatic cleanup."""
        
        # Create test document - automatically tracked for cleanup
        doc_id = self.create_test_document(
            title="auto-cleanup-test",
            content="This document will be automatically cleaned up"
        )
        
        assert doc_id is not None, "Failed to create test document"
        print(f"✅ Created test document: {doc_id}")
        
        # Document will be automatically cleaned up in teardown_class
        # which also tests the deletion API
    
    def test_action_creation_with_auto_cleanup(self):
        """Test action creation with automatic cleanup."""
        
        # Create test action - automatically tracked for cleanup
        action_id = self.create_test_action(
            name="auto-cleanup-action",
            url="https://httpbin.org/uuid"
        )
        
        assert action_id is not None, "Failed to create test action"
        print(f"✅ Created test action: {action_id}")
        
        # Action will be automatically cleaned up in teardown_class
    
    def test_multiple_resources_with_auto_cleanup(self):
        """Test creating multiple resources for cleanup testing."""
        
        created_resources = []
        
        # Create multiple actions
        for i in range(3):
            action_id = self.create_test_action(f"bulk-action-{i}")
            if action_id:
                created_resources.append(f"action:{action_id}")
        
        # Create multiple documents
        for i in range(2):
            doc_id = self.create_test_document(
                f"bulk-doc-{i}",
                f"Content for bulk document {i}"
            )
            if doc_id:
                created_resources.append(f"document:{doc_id}")
        
        assert len(created_resources) >= 3, "Should have created at least 3 resources"
        print(f"✅ Created {len(created_resources)} resources for cleanup testing")
        
        # All resources will be automatically cleaned up and deletion APIs tested
    
    def test_manual_resource_tracking(self):
        """Test manual resource tracking for complex scenarios."""
        
        if self.environment == "production":
            pytest.skip("Skipping resource creation in production")
        
        # Create resource manually
        action_data = {
            "name": self.get_test_resource_name("manual-track-action"),
            "type": "REST",
            "description": "Manually tracked action",
            "config": {"url": "https://httpbin.org/get", "method": "GET"}
        }
        
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/actions",
            headers=self.headers,
            json=action_data
        )
        
        assert response.status_code in [200, 201]
        action_id = response.json()["id"]
        
        # Manually track for cleanup
        self.track_created_resource("actions", action_id)
        
        print(f"✅ Manually tracked action: {action_id}")


@pytest.mark.integration
@pytest.mark.cleanup
@pytest.mark.production
class TestProductionCleanupValidation(CleanupEnabledTestCase):
    """Production-specific cleanup validation tests."""
    
    @classmethod
    def setup_class(cls):
        """Set up for production testing."""
        cls.setup_auth(environment="production")
    
    def test_cleanup_utils_safe_in_production(self):
        """Verify cleanup utilities work safely in production."""
        
        # Should be able to initialize cleanup utilities
        assert hasattr(self, 'data_manager')
        assert hasattr(self, 'cleanup_handler')
        assert self.data_manager.environment == "production"
        
        # Should not have any tracked resources initially
        tracked = self.data_manager.get_tracked_resources()
        assert all(len(resources) == 0 for resources in tracked.values())
        
        print("✅ Cleanup utilities work safely in production")
    
    def test_production_safety_checks(self):
        """Test that production safety checks work correctly."""
        
        # Helper methods should skip creation in production
        with pytest.raises(pytest.skip.Exception):
            self.create_test_document("should-not-create", "content")
        
        with pytest.raises(pytest.skip.Exception):
            self.create_test_action("should-not-create")
        
        print("✅ Production safety checks working correctly")