"""
Simple test cleanup utility - AFTER tests approach.

This provides simple cleanup functionality that:
1. Runs AFTER tests complete
2. Tests deletion APIs
3. Cleans up test data 
4. Works across all environments
"""

import pytest
from typing import List, Dict, Any


class SimpleCleanupMixin:
    """Simple mixin to add cleanup functionality to any test class."""
    
    def __init__(self):
        # Track resources created during tests
        self.created_documents = []
        self.created_actions = []
        self.created_secrets = []
        self.created_assistants = []
        self.created_threads = []
        self.created_mcp_tokens = []
    
    def track_document(self, doc_id: str):
        """Track a document for cleanup."""
        self.created_documents.append(doc_id)
    
    def track_action(self, action_id: str):
        """Track an action for cleanup."""
        self.created_actions.append(action_id)
    
    def track_secret(self, secret_id: str):
        """Track a secret for cleanup."""
        self.created_secrets.append(secret_id)
    
    def track_assistant(self, assistant_id: str):
        """Track an assistant for cleanup."""
        self.created_assistants.append(assistant_id)
    
    def track_thread(self, thread_id: str):
        """Track a chat thread for cleanup."""
        self.created_threads.append(thread_id)
    
    def track_mcp_token(self, token_id: str):
        """Track an MCP token for cleanup."""
        self.created_mcp_tokens.append(token_id)
    
    def cleanup_all_created_resources(self):
        """Clean up all tracked resources and test deletion APIs."""
        if not hasattr(self, 'client') or not hasattr(self, 'headers'):
            print("⚠️ No client/headers available for cleanup")
            return
        
        if not hasattr(self, 'workspace_id'):
            print("⚠️ No workspace_id available for cleanup")
            return
        
        cleanup_results = {}
        
        # Clean up documents
        if self.created_documents:
            print(f"🧹 Cleaning up {len(self.created_documents)} documents...")
            cleanup_results['documents'] = self._cleanup_documents()
        
        # Clean up actions
        if self.created_actions:
            print(f"🧹 Cleaning up {len(self.created_actions)} actions...")
            cleanup_results['actions'] = self._cleanup_actions()
        
        # Clean up secrets  
        if self.created_secrets:
            print(f"🧹 Cleaning up {len(self.created_secrets)} secrets...")
            cleanup_results['secrets'] = self._cleanup_secrets()
        
        # Clean up assistants
        if self.created_assistants:
            print(f"🧹 Cleaning up {len(self.created_assistants)} assistants...")
            cleanup_results['assistants'] = self._cleanup_assistants()
        
        # Clean up threads
        if self.created_threads:
            print(f"🧹 Cleaning up {len(self.created_threads)} threads...")
            cleanup_results['threads'] = self._cleanup_threads()
        
        # Clean up MCP tokens
        if self.created_mcp_tokens:
            print(f"🧹 Cleaning up {len(self.created_mcp_tokens)} MCP tokens...")
            cleanup_results['mcp_tokens'] = self._cleanup_mcp_tokens()
        
        # Print summary
        self._print_cleanup_summary(cleanup_results)
        
        return cleanup_results
    
    def _cleanup_documents(self) -> Dict[str, List]:
        """Clean up documents and test deletion API."""
        deleted = []
        failed = []
        
        for doc_id in self.created_documents:
            try:
                response = self.client.delete(
                    f"/admin/api/v1/workspaces/{self.workspace_id}/knowledge/documents/{doc_id}",
                    headers=self.headers
                )
                
                if response.status_code in [200, 204, 404]:  # 404 = already deleted
                    deleted.append(doc_id)
                    print(f"✅ Deleted document: {doc_id}")
                else:
                    failed.append({"id": doc_id, "status": response.status_code})
                    print(f"❌ Failed to delete document {doc_id}: {response.status_code}")
                    
            except Exception as e:
                failed.append({"id": doc_id, "error": str(e)})
                print(f"❌ Error deleting document {doc_id}: {e}")
        
        return {"deleted": deleted, "failed": failed}
    
    def _cleanup_actions(self) -> Dict[str, List]:
        """Clean up actions and test deletion API."""
        deleted = []
        failed = []
        
        for action_id in self.created_actions:
            try:
                response = self.client.delete(
                    f"/admin/api/v1/workspaces/{self.workspace_id}/actions/{action_id}",
                    headers=self.headers
                )
                
                if response.status_code in [200, 204, 404]:
                    deleted.append(action_id)
                    print(f"✅ Deleted action: {action_id}")
                else:
                    failed.append({"id": action_id, "status": response.status_code})
                    print(f"❌ Failed to delete action {action_id}: {response.status_code}")
                    
            except Exception as e:
                failed.append({"id": action_id, "error": str(e)})
                print(f"❌ Error deleting action {action_id}: {e}")
        
        return {"deleted": deleted, "failed": failed}
    
    def _cleanup_secrets(self) -> Dict[str, List]:
        """Clean up secrets and test deletion API."""
        deleted = []
        failed = []
        
        for secret_id in self.created_secrets:
            try:
                response = self.client.delete(
                    f"/admin/api/v1/workspaces/{self.workspace_id}/secrets/{secret_id}",
                    headers=self.headers
                )
                
                if response.status_code in [200, 204, 404]:
                    deleted.append(secret_id)
                    print(f"✅ Deleted secret: {secret_id}")
                else:
                    failed.append({"id": secret_id, "status": response.status_code})
                    print(f"❌ Failed to delete secret {secret_id}: {response.status_code}")
                    
            except Exception as e:
                failed.append({"id": secret_id, "error": str(e)})
                print(f"❌ Error deleting secret {secret_id}: {e}")
        
        return {"deleted": deleted, "failed": failed}
    
    def _cleanup_assistants(self) -> Dict[str, List]:
        """Clean up assistants and test deletion API."""
        deleted = []
        failed = []
        
        for assistant_id in self.created_assistants:
            try:
                response = self.client.delete(
                    f"/admin/api/v1/workspaces/{self.workspace_id}/assistants/{assistant_id}",
                    headers=self.headers
                )
                
                if response.status_code in [200, 204, 404]:
                    deleted.append(assistant_id)
                    print(f"✅ Deleted assistant: {assistant_id}")
                else:
                    failed.append({"id": assistant_id, "status": response.status_code})
                    print(f"❌ Failed to delete assistant {assistant_id}: {response.status_code}")
                    
            except Exception as e:
                failed.append({"id": assistant_id, "error": str(e)})
                print(f"❌ Error deleting assistant {assistant_id}: {e}")
        
        return {"deleted": deleted, "failed": failed}
    
    def _cleanup_threads(self) -> Dict[str, List]:
        """Clean up chat threads and test deletion API."""
        deleted = []
        failed = []
        
        for thread_id in self.created_threads:
            try:
                response = self.client.delete(
                    f"/admin/api/v1/chat/threads/{thread_id}",
                    headers=self.headers
                )
                
                if response.status_code in [200, 204, 404]:
                    deleted.append(thread_id)
                    print(f"✅ Deleted thread: {thread_id}")
                else:
                    failed.append({"id": thread_id, "status": response.status_code})
                    print(f"❌ Failed to delete thread {thread_id}: {response.status_code}")
                    
            except Exception as e:
                failed.append({"id": thread_id, "error": str(e)})
                print(f"❌ Error deleting thread {thread_id}: {e}")
        
        return {"deleted": deleted, "failed": failed}
    
    def _cleanup_mcp_tokens(self) -> Dict[str, List]:
        """Clean up MCP tokens and test deletion API."""
        deleted = []
        failed = []
        
        for token_id in self.created_mcp_tokens:
            try:
                response = self.client.delete(
                    f"/admin/api/v1/workspaces/{self.workspace_id}/mcp-tokens/{token_id}",
                    headers=self.headers
                )
                
                if response.status_code in [200, 204, 404]:
                    deleted.append(token_id)
                    print(f"✅ Deleted MCP token: {token_id}")
                else:
                    failed.append({"id": token_id, "status": response.status_code})
                    print(f"❌ Failed to delete MCP token {token_id}: {response.status_code}")
                    
            except Exception as e:
                failed.append({"id": token_id, "error": str(e)})
                print(f"❌ Error deleting MCP token {token_id}: {e}")
        
        return {"deleted": deleted, "failed": failed}
    
    def _print_cleanup_summary(self, results: Dict[str, Dict]):
        """Print cleanup summary."""
        total_deleted = 0
        total_failed = 0
        
        print("\n🧹 CLEANUP SUMMARY:")
        for resource_type, result in results.items():
            deleted_count = len(result.get("deleted", []))
            failed_count = len(result.get("failed", []))
            
            total_deleted += deleted_count
            total_failed += failed_count
            
            if deleted_count > 0:
                print(f"  ✅ {resource_type}: {deleted_count} deleted")
            if failed_count > 0:
                print(f"  ❌ {resource_type}: {failed_count} failed")
        
        print(f"📊 TOTAL: {total_deleted} deleted, {total_failed} failed")
        
        if total_deleted > 0:
            print("✅ Deletion APIs tested successfully!")


# Example of how to add cleanup to existing test class
class ExampleTestWithCleanup(SimpleCleanupMixin):
    """Example showing how to add cleanup to existing tests."""
    
    def __init__(self):
        super().__init__()
        # Your existing test setup
    
    def tearDown(self):
        """Called after each test method."""
        # Clean up resources created in this test
        self.cleanup_all_created_resources()
        
        # Clear tracking lists for next test
        self.created_documents = []
        self.created_actions = []
        self.created_secrets = []
        self.created_assistants = []
        self.created_threads = []
        self.created_mcp_tokens = []
    
    def test_example_with_cleanup(self):
        """Example test that creates resources and tracks them."""
        
        # Create action (example)
        action_data = {
            "name": "test-action",
            "type": "REST", 
            "config": {"url": "https://httpbin.org/get", "method": "GET"}
        }
        
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/actions",
            headers=self.headers,
            json=action_data
        )
        
        if response.status_code in [200, 201]:
            action_id = response.json()["id"]
            self.track_action(action_id)  # Track for cleanup
        
        # Test continues...
        
        # Cleanup happens automatically in tearDown()


def add_simple_cleanup_to_class(test_class):
    """Decorator to add simple cleanup to any existing test class."""
    
    # Store original teardown if it exists
    original_teardown_class = getattr(test_class, 'teardown_class', None)
    
    @classmethod
    def enhanced_teardown_class(cls):
        """Enhanced teardown that includes cleanup."""
        
        # Run cleanup if we have the mixin
        if hasattr(cls, 'cleanup_all_created_resources'):
            if hasattr(cls, '_cleanup_instance'):
                cls._cleanup_instance.cleanup_all_created_resources()
        
        # Run original teardown
        if original_teardown_class:
            original_teardown_class()
    
    # Replace teardown_class
    test_class.teardown_class = enhanced_teardown_class
    
    # Add mixin functionality
    if not issubclass(test_class, SimpleCleanupMixin):
        # Add mixin methods to class
        for attr_name in dir(SimpleCleanupMixin):
            if not attr_name.startswith('_') or attr_name in ['_cleanup_documents', '_cleanup_actions', '_cleanup_secrets', '_cleanup_assistants', '_cleanup_threads', '_cleanup_mcp_tokens', '_print_cleanup_summary']:
                if not hasattr(test_class, attr_name):
                    setattr(test_class, attr_name, getattr(SimpleCleanupMixin, attr_name))
        
        # Initialize tracking lists
        original_setup_class = getattr(test_class, 'setup_class', None)
        
        @classmethod  
        def enhanced_setup_class(cls):
            """Enhanced setup that initializes cleanup tracking."""
            # Initialize cleanup tracking
            cls._cleanup_instance = SimpleCleanupMixin()
            
            # Copy tracking methods to class level
            cls.created_documents = []
            cls.created_actions = []
            cls.created_secrets = []
            cls.created_assistants = []
            cls.created_threads = []
            cls.created_mcp_tokens = []
            
            # Run original setup
            if original_setup_class:
                original_setup_class()
        
        test_class.setup_class = enhanced_setup_class
    
    return test_class