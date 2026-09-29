"""
Test data cleanup utilities and tests for deletion APIs.

This module provides:
1. Test data lifecycle management (setup → test → cleanup)
2. Deletion API testing
3. Environment-aware cleanup strategies
4. Resource tracking and cleanup automation
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set

import pytest

from .test_utils import AuthenticatedTestCase


class DataManager:
    """Manages test data lifecycle with automatic cleanup."""
    
    def __init__(self, environment: str = "local"):
        self.environment = environment
        self.created_resources: Dict[str, List[str]] = {
            "documents": [],
            "actions": [],
            "secrets": [],
            "assistants": [],
            "threads": [],
            "mcp_tokens": [],
            "workspaces": [],
            "api_keys": []
        }
        self.test_prefix = f"test-{environment}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    def track_resource(self, resource_type: str, resource_id: str):
        """Track a created resource for cleanup."""
        if resource_type in self.created_resources:
            self.created_resources[resource_type].append(resource_id)
    
    def get_tracked_resources(self) -> Dict[str, List[str]]:
        """Get all tracked resources."""
        return self.created_resources.copy()
    
    def get_test_name(self, base_name: str) -> str:
        """Generate a unique test resource name."""
        timestamp = datetime.now().strftime('%H%M%S')
        return f"{self.test_prefix}-{base_name}-{timestamp}"


class ResourceCleanup:
    """Test resource cleanup and deletion API validation."""
    
    def __init__(self, client, headers: dict, workspace_id: str, environment: str = "local"):
        self.client = client
        self.headers = headers
        self.workspace_id = workspace_id
        self.environment = environment
        self.cleanup_results = {}
    
    async def cleanup_documents(self, document_ids: List[str]) -> Dict[str, Any]:
        """Clean up knowledge base documents and test deletion API."""
        results = {"deleted": [], "failed": [], "errors": []}
        
        for doc_id in document_ids:
            try:
                response = self.client.delete(
                    f"/admin/api/v1/workspaces/{self.workspace_id}/knowledge/documents/{doc_id}",
                    headers=self.headers
                )
                
                if response.status_code in [200, 204, 404]:  # 404 = already deleted
                    results["deleted"].append(doc_id)
                else:
                    results["failed"].append({
                        "id": doc_id,
                        "status": response.status_code,
                        "error": response.text
                    })
            except Exception as e:
                results["errors"].append({"id": doc_id, "error": str(e)})
        
        return results
    
    async def cleanup_actions(self, action_ids: List[str]) -> Dict[str, Any]:
        """Clean up actions and test deletion API."""
        results = {"deleted": [], "failed": [], "errors": []}
        
        for action_id in action_ids:
            try:
                response = self.client.delete(
                    f"/admin/api/v1/workspaces/{self.workspace_id}/actions/{action_id}",
                    headers=self.headers
                )
                
                if response.status_code in [200, 204, 404]:
                    results["deleted"].append(action_id)
                else:
                    results["failed"].append({
                        "id": action_id,
                        "status": response.status_code,
                        "error": response.text
                    })
            except Exception as e:
                results["errors"].append({"id": action_id, "error": str(e)})
        
        return results
    
    async def cleanup_secrets(self, secret_ids: List[str]) -> Dict[str, Any]:
        """Clean up secrets and test deletion API."""
        results = {"deleted": [], "failed": [], "errors": []}
        
        for secret_id in secret_ids:
            try:
                response = self.client.delete(
                    f"/admin/api/v1/workspaces/{self.workspace_id}/secrets/{secret_id}",
                    headers=self.headers
                )
                
                if response.status_code in [200, 204, 404]:
                    results["deleted"].append(secret_id)
                else:
                    results["failed"].append({
                        "id": secret_id,
                        "status": response.status_code,
                        "error": response.text
                    })
            except Exception as e:
                results["errors"].append({"id": secret_id, "error": str(e)})
        
        return results
    
    async def cleanup_assistants(self, assistant_ids: List[str]) -> Dict[str, Any]:
        """Clean up assistants and test deletion API."""
        results = {"deleted": [], "failed": [], "errors": []}
        
        for assistant_id in assistant_ids:
            try:
                response = self.client.delete(
                    f"/admin/api/v1/workspaces/{self.workspace_id}/assistants/{assistant_id}",
                    headers=self.headers
                )
                
                if response.status_code in [200, 204, 404]:
                    results["deleted"].append(assistant_id)
                else:
                    results["failed"].append({
                        "id": assistant_id,
                        "status": response.status_code,
                        "error": response.text
                    })
            except Exception as e:
                results["errors"].append({"id": assistant_id, "error": str(e)})
        
        return results
    
    async def cleanup_threads(self, thread_ids: List[str]) -> Dict[str, Any]:
        """Clean up chat threads and test deletion API."""
        results = {"deleted": [], "failed": [], "errors": []}
        
        for thread_id in thread_ids:
            try:
                response = self.client.delete(
                    f"/admin/api/v1/chat/threads/{thread_id}",
                    headers=self.headers
                )
                
                if response.status_code in [200, 204, 404]:
                    results["deleted"].append(thread_id)
                else:
                    results["failed"].append({
                        "id": thread_id,
                        "status": response.status_code,
                        "error": response.text
                    })
            except Exception as e:
                results["errors"].append({"id": thread_id, "error": str(e)})
        
        return results
    
    async def cleanup_mcp_tokens(self, token_ids: List[str]) -> Dict[str, Any]:
        """Clean up MCP tokens and test deletion API."""
        results = {"deleted": [], "failed": [], "errors": []}
        
        for token_id in token_ids:
            try:
                response = self.client.delete(
                    f"/admin/api/v1/workspaces/{self.workspace_id}/mcp-tokens/{token_id}",
                    headers=self.headers
                )
                
                if response.status_code in [200, 204, 404]:
                    results["deleted"].append(token_id)
                else:
                    results["failed"].append({
                        "id": token_id,
                        "status": response.status_code,
                        "error": response.text
                    })
            except Exception as e:
                results["errors"].append({"id": token_id, "error": str(e)})
        
        return results
    
    async def cleanup_all_tracked(self, tracked_resources: Dict[str, List[str]]) -> Dict[str, Any]:
        """Clean up all tracked resources."""
        all_results = {}
        
        # Order matters - clean up in dependency order
        cleanup_order = [
            ("documents", self.cleanup_documents),
            ("threads", self.cleanup_threads),
            ("assistants", self.cleanup_assistants),
            ("actions", self.cleanup_actions),
            ("secrets", self.cleanup_secrets),
            ("mcp_tokens", self.cleanup_mcp_tokens),
        ]
        
        for resource_type, cleanup_func in cleanup_order:
            if resource_type in tracked_resources and tracked_resources[resource_type]:
                print(f"🧹 Cleaning up {len(tracked_resources[resource_type])} {resource_type}...")
                results = await cleanup_func(tracked_resources[resource_type])
                all_results[resource_type] = results
                
                if results["deleted"]:
                    print(f"✅ Deleted {len(results['deleted'])} {resource_type}")
                if results["failed"]:
                    print(f"⚠️ Failed to delete {len(results['failed'])} {resource_type}")
                if results["errors"]:
                    print(f"❌ Errors deleting {len(results['errors'])} {resource_type}")
        
        return all_results
    
    async def cleanup_test_data_by_prefix(self, prefix: str) -> Dict[str, Any]:
        """Clean up test data by name prefix (before test run)."""
        results = {"cleaned_types": [], "errors": []}
        
        # Only run prefix cleanup for non-production environments
        if self.environment == "production":
            print("⚠️ Skipping prefix cleanup in production environment")
            return results
        
        try:
            # Find and clean documents with test prefix
            doc_response = self.client.get(
                f"/admin/api/v1/workspaces/{self.workspace_id}/knowledge/documents",
                headers=self.headers
            )
            
            if doc_response.status_code == 200:
                documents = doc_response.json()
                test_docs = [
                    doc["id"] for doc in documents 
                    if doc.get("filename", "").startswith(prefix) or 
                       doc.get("title", "").startswith(prefix)
                ]
                
                if test_docs:
                    cleanup_results = await self.cleanup_documents(test_docs)
                    results["cleaned_types"].append(f"documents: {len(cleanup_results['deleted'])}")
        
        except Exception as e:
            results["errors"].append(f"Document cleanup error: {e}")
        
        # Add similar prefix cleanup for other resource types...
        
        return results


@pytest.mark.integration
@pytest.mark.cleanup
class TestDataCleanupIntegration(AuthenticatedTestCase):
    """Integration tests for data cleanup and deletion APIs."""
    
    @classmethod
    def setup_class(cls):
        """Set up test environment."""
        # Auto-detect environment
        environment = os.getenv("TEST_ENVIRONMENT", "local")
        cls.setup_auth(environment=environment)
        cls.data_manager = DataManager(environment)
        cls.cleanup_handler = None
    
    @classmethod
    def teardown_class(cls):
        """Clean up after all tests."""
        if cls.cleanup_handler and not cls.skip_tests:
            # Run final cleanup
            tracked = cls.data_manager.get_tracked_resources()
            if any(tracked.values()):  # If there are any tracked resources
                import asyncio
                asyncio.run(cls.cleanup_handler.cleanup_all_tracked(tracked))
        
        cls.teardown_auth()
    
    def setup_method(self):
        """Set up for each test method."""
        if self.skip_tests:
            pytest.skip(self.skip_reason)
        
        # Initialize cleanup handler for this test
        self.cleanup_handler = ResourceCleanup(
            self.client, self.headers, self.workspace_id, self.environment
        )
        
        # Set class-level cleanup handler for teardown
        self.__class__.cleanup_handler = self.cleanup_handler
    
    def test_knowledge_document_deletion_api(self):
        """Test knowledge document creation and deletion API."""
        if self.environment == "production":
            pytest.skip("Skipping mutation tests in production")
        
        # Create test document
        test_content = "This is a test document for deletion API testing."
        create_response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/knowledge/upload",
            headers=self.headers,
            data={
                "source_type": "text",
                "title": self.data_manager.get_test_name("deletion-test-doc"),
                "content": test_content,
                "chunking_strategy": "smart"
            }
        )
        
        assert create_response.status_code in [200, 201], f"Failed to create document: {create_response.text}"
        
        # Extract document ID from response
        if "task_id" in create_response.json():
            # Handle async processing
            task_id = create_response.json()["task_id"]
            # Poll for completion (simplified for test)
            import time
            time.sleep(2)
            
            # Get documents to find our test document
            docs_response = self.client.get(
                f"/admin/api/v1/workspaces/{self.workspace_id}/knowledge/documents",
                headers=self.headers
            )
            assert docs_response.status_code == 200
            
            documents = docs_response.json()
            test_doc = next((doc for doc in documents if test_content in doc.get("title", "")), None)
            assert test_doc is not None, "Test document not found after creation"
            
            document_id = test_doc["id"]
        else:
            document_id = create_response.json()["id"]
        
        # Track for cleanup
        self.data_manager.track_resource("documents", document_id)
        
        # Test deletion API
        delete_response = self.client.delete(
            f"/admin/api/v1/workspaces/{self.workspace_id}/knowledge/documents/{document_id}",
            headers=self.headers
        )
        
        assert delete_response.status_code in [200, 204], f"Failed to delete document: {delete_response.text}"
        
        # Verify document is deleted
        get_response = self.client.get(
            f"/admin/api/v1/workspaces/{self.workspace_id}/knowledge/documents/{document_id}",
            headers=self.headers
        )
        
        assert get_response.status_code in [404, 410], "Document still exists after deletion"
        
        print(f"✅ Document deletion API test passed: {document_id}")
    
    def test_action_deletion_api(self):
        """Test action creation and deletion API."""
        if self.environment == "production":
            pytest.skip("Skipping mutation tests in production")
        
        # Create test action
        action_data = {
            "name": self.data_manager.get_test_name("deletion-test-action"),
            "type": "REST",
            "description": "Test action for deletion API testing",
            "config": {
                "url": "https://httpbin.org/get",
                "method": "GET"
            }
        }
        
        create_response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/actions",
            headers=self.headers,
            json=action_data
        )
        
        assert create_response.status_code in [200, 201], f"Failed to create action: {create_response.text}"
        
        action_id = create_response.json()["id"]
        self.data_manager.track_resource("actions", action_id)
        
        # Test deletion API
        delete_response = self.client.delete(
            f"/admin/api/v1/workspaces/{self.workspace_id}/actions/{action_id}",
            headers=self.headers
        )
        
        assert delete_response.status_code in [200, 204], f"Failed to delete action: {delete_response.text}"
        
        # Verify action is deleted
        get_response = self.client.get(
            f"/admin/api/v1/workspaces/{self.workspace_id}/actions/{action_id}",
            headers=self.headers
        )
        
        assert get_response.status_code in [404, 410], "Action still exists after deletion"
        
        print(f"✅ Action deletion API test passed: {action_id}")
    
    def test_bulk_cleanup_functionality(self):
        """Test bulk cleanup of multiple resources."""
        if self.environment == "production":
            pytest.skip("Skipping mutation tests in production")
        
        # Create multiple test resources
        created_docs = []
        created_actions = []
        
        # Create test documents
        for i in range(3):
            doc_data = {
                "source_type": "text",
                "title": self.data_manager.get_test_name(f"bulk-test-doc-{i}"),
                "content": f"Test document {i} for bulk cleanup testing.",
                "chunking_strategy": "smart"
            }
            
            response = self.client.post(
                f"/admin/api/v1/workspaces/{self.workspace_id}/knowledge/upload",
                headers=self.headers,
                data=doc_data
            )
            
            if response.status_code in [200, 201]:
                # Handle potential async processing
                if "task_id" in response.json():
                    import time
                    time.sleep(1)  # Brief wait for processing
                    # Would need to poll for actual document ID in real implementation
                else:
                    created_docs.append(response.json()["id"])
        
        # Create test actions
        for i in range(2):
            action_data = {
                "name": self.data_manager.get_test_name(f"bulk-test-action-{i}"),
                "type": "REST",
                "description": f"Test action {i} for bulk cleanup",
                "config": {
                    "url": f"https://httpbin.org/get?test={i}",
                    "method": "GET"
                }
            }
            
            response = self.client.post(
                f"/admin/api/v1/workspaces/{self.workspace_id}/actions",
                headers=self.headers,
                json=action_data
            )
            
            if response.status_code in [200, 201]:
                created_actions.append(response.json()["id"])
        
        # Track all created resources
        for doc_id in created_docs:
            self.data_manager.track_resource("documents", doc_id)
        for action_id in created_actions:
            self.data_manager.track_resource("actions", action_id)
        
        # Test bulk cleanup
        tracked_resources = self.data_manager.get_tracked_resources()
        cleanup_results = asyncio.run(
            self.cleanup_handler.cleanup_all_tracked(tracked_resources)
        )
        
        # Verify cleanup results
        if "documents" in cleanup_results:
            assert len(cleanup_results["documents"]["deleted"]) >= len(created_docs)
        if "actions" in cleanup_results:
            assert len(cleanup_results["actions"]["deleted"]) >= len(created_actions)
        
        print(f"✅ Bulk cleanup test passed: {cleanup_results}")
    
    def test_prefix_based_cleanup(self):
        """Test cleanup of test data by prefix."""
        if self.environment == "production":
            pytest.skip("Skipping prefix cleanup in production")
        
        # Test prefix cleanup (this would clean up any existing test data)
        cleanup_results = asyncio.run(
            self.cleanup_handler.cleanup_test_data_by_prefix("test-")
        )
        
        print(f"✅ Prefix cleanup completed: {cleanup_results}")
        
        # Verify no errors occurred
        assert len(cleanup_results.get("errors", [])) == 0, f"Cleanup errors: {cleanup_results['errors']}"


@pytest.mark.integration
@pytest.mark.cleanup
@pytest.mark.production
class TestProductionSafeCleanup(AuthenticatedTestCase):
    """Production-safe cleanup tests (read-only validation)."""
    
    @classmethod
    def setup_class(cls):
        """Set up for production cleanup testing."""
        cls.setup_auth(environment="production")
    
    @classmethod
    def teardown_class(cls):
        """Clean up after production tests."""
        cls.teardown_auth()
    
    def setup_method(self):
        """Set up for each test method."""
        if self.skip_tests:
            pytest.skip(self.skip_reason)
    
    def test_deletion_api_endpoints_exist(self):
        """Verify all deletion API endpoints exist and return appropriate responses."""
        
        # Test document deletion endpoint (should return 404 for non-existent resource)
        response = self.client.delete(
            f"/admin/api/v1/workspaces/{self.workspace_id}/knowledge/documents/non-existent-doc",
            headers=self.headers
        )
        assert response.status_code in [404, 405], f"Unexpected response for document deletion: {response.status_code}"
        
        # Test action deletion endpoint
        response = self.client.delete(
            f"/admin/api/v1/workspaces/{self.workspace_id}/actions/non-existent-action",
            headers=self.headers
        )
        assert response.status_code in [404, 405], f"Unexpected response for action deletion: {response.status_code}"
        
        # Test secret deletion endpoint
        response = self.client.delete(
            f"/admin/api/v1/workspaces/{self.workspace_id}/secrets/non-existent-secret",
            headers=self.headers
        )
        assert response.status_code in [404, 405], f"Unexpected response for secret deletion: {response.status_code}"
        
        print("✅ All deletion API endpoints are accessible")
    
    def test_cleanup_utility_initialization(self):
        """Test that cleanup utilities can be initialized safely in production."""
        
        data_manager = TestDataManager("production")
        cleanup_handler = TestResourceCleanup(
            self.client, self.headers, self.workspace_id, "production"
        )
        
        # Verify they initialize without errors
        assert data_manager.environment == "production"
        assert cleanup_handler.environment == "production"
        
        # Verify no tracked resources initially
        tracked = data_manager.get_tracked_resources()
        assert all(len(resources) == 0 for resources in tracked.values())
        
        print("✅ Cleanup utilities initialized safely in production")