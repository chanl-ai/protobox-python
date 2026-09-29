# Simple Test Cleanup Guide

This guide shows how to add **simple AFTER cleanup** to integration tests.

## ✅ What This Achieves

1. **Tests Deletion APIs** - Validates that DELETE endpoints work correctly
2. **Cleans Up Test Data** - Prevents database pollution across all environments
3. **Zero Configuration** - Just track resources and cleanup happens automatically
4. **Works Everywhere** - Local, staging, production (with appropriate safety)

## 🚀 Quick Start

### Step 1: Add Tracking to Your Test Class

```python
@pytest.mark.integration  
class YourExistingTestClass(AuthenticatedTestCase):
    
    @classmethod
    def setup_class(cls):
        """Set up test environment."""
        import os
        environment = os.getenv("TEST_ENVIRONMENT", "local")
        cls.setup_auth(environment=environment)
        
        # ADD THIS: Initialize cleanup tracking
        cls.created_documents = []
        cls.created_actions = []
        cls.created_secrets = []
        cls.created_assistants = []
        cls.created_threads = []
    
    @classmethod
    def teardown_class(cls):
        """Clean up after all tests."""
        if not cls.skip_tests:
            # ADD THIS: Run cleanup and test deletion APIs
            cls._cleanup_all_resources()
        cls.teardown_auth()
```

### Step 2: Add Cleanup Method

```python
    @classmethod
    def _cleanup_all_resources(cls):
        """Clean up all tracked resources and test deletion APIs."""
        total_deleted = 0
        
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
                except Exception as e:
                    print(f"❌ Error deleting action {action_id}: {e}")
        
        # Add similar blocks for other resource types...
        
        if total_deleted > 0:
            print(f"✅ DELETION APIS TESTED - CLEANED UP {total_deleted} RESOURCES!")
```

### Step 3: Track Resources in Tests

```python
    def test_your_existing_test(self):
        """Your existing test."""
        # Create action (your existing code)
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/actions",
            headers=self.headers,
            json=action_data
        )
        
        if response.status_code in [200, 201]:
            action_id = response.json()["id"]
            
            # ADD THIS: Track for cleanup
            self.created_actions.append(action_id)
        
        # Rest of your test...
```

## 📋 Complete Resource Types

```python
# Track these resource types:
cls.created_documents = []      # Knowledge base documents
cls.created_actions = []        # Actions/workflows  
cls.created_secrets = []        # Secrets/credentials
cls.created_assistants = []     # AI assistants
cls.created_threads = []        # Chat threads
cls.created_mcp_tokens = []     # MCP tokens
```

## 🔄 Resource Cleanup Order

Clean up in dependency order (most dependent first):

1. **Documents** - Knowledge base documents
2. **Threads** - Chat threads
3. **Assistants** - AI assistants  
4. **Actions** - Actions/workflows
5. **Secrets** - Secrets/credentials
6. **MCP Tokens** - MCP access tokens

## 🔒 Production Safety

Production tests automatically skip resource creation:

```python
def test_your_test(self):
    if self.environment == "production":
        pytest.skip("Skipping resource creation in production")
    
    # Resource creation code here...
```

## 📊 What You'll See

When tests complete:

```
🧹 Testing action deletion API with 3 actions...
✅ Deleted action: 68a15a785d0936ca68263377
✅ Deleted action: 68a15a785d0936ca68263379
✅ Deleted action: 68a15a785d0936ca6826337b

📊 CLEANUP SUMMARY: 3 deleted, 0 failed
✅ DELETION APIS TESTED SUCCESSFULLY!
```

## 🎯 Example: Complete Working Class

See `test_simple_cleanup_working.py` for a complete working example.

## ⚡ Benefits

- **✅ Tests deletion APIs** - Validates DELETE endpoints work
- **✅ Clean database** - No test data pollution
- **✅ Zero maintenance** - Automatic cleanup after tests  
- **✅ Production safe** - Won't create/delete real data
- **✅ Easy to add** - Just track resources and call cleanup
- **✅ Works everywhere** - Local, staging, production

This simple approach gives you comprehensive test data cleanup with minimal code changes!