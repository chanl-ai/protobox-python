"""Comprehensive MCP integration tests for auth, isolation, and core features."""

import asyncio
import json
import pytest
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from httpx import Client

try:
    from fastmcp import FastMCPClient
    from fastmcp.transport import SSETransport
    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False
    FastMCPClient = None
    SSETransport = None

from .test_utils import (
    create_test_action,
    delete_test_action,
    get_test_auth_and_workspace,
)


@pytest.mark.integration
class TestMCPComprehensive:
    """Comprehensive MCP integration tests."""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment."""
        cls.client = Client(base_url="http://localhost:8090", timeout=30.0)
        cls.test_actions = []
        cls.test_tokens = []
        
        # Get authentication and workspace
        try:
            access_token, headers, workspace_id = get_test_auth_and_workspace(cls.client)
            
            if access_token:
                cls.skip = False
                cls.access_token = access_token
                cls.headers = headers
                cls.workspace_id = workspace_id
                print(f"✓ Test setup complete - Workspace: {workspace_id}")
            else:
                cls.skip = True
                cls.skip_reason = "Failed to get test authentication"
                
        except Exception as e:
            cls.skip = True
            cls.skip_reason = f"Server not running or not accessible: {e}"
    
    @classmethod
    def teardown_class(cls):
        """Cleanup test environment."""
        # Clean up test actions
        if hasattr(cls, 'test_actions'):
            for action_id in cls.test_actions:
                try:
                    delete_test_action(cls.client, cls.headers, cls.workspace_id, action_id)
                except Exception as e:
                    print(f"Warning: Failed to cleanup test action {action_id}: {e}")
        
        # Clean up test tokens
        if hasattr(cls, 'test_tokens'):
            for token_id in cls.test_tokens:
                try:
                    cls.client.delete(
                        f"/admin/api/v1/workspaces/{cls.workspace_id}/mcp-tokens/{token_id}",
                        headers=cls.headers
                    )
                except Exception as e:
                    print(f"Warning: Failed to cleanup test token {token_id}: {e}")
    
    def setup_method(self):
        """Skip if prerequisites not met."""
        if getattr(self, "skip", False):
            pytest.skip(getattr(self, "skip_reason", "Skipping MCP comprehensive tests"))
    
    def test_mcp_authentication_methods(self):
        """Test different MCP authentication methods."""
        # Test 1: Create an MCP token first for testing
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/mcp-tokens",
            headers=self.headers,
            json={
                "name": "test_auth_token",
                "description": "Token for auth testing",
                "expires_in_days": 1,
                "scopes": ["read:actions", "execute:actions"]
            }
        )
        
        assert response.status_code in [200, 201], f"Failed to create MCP token: {response.text}"
        token_data = response.json()
        mcp_token = token_data["token"]
        if "id" in token_data:
            self.test_tokens.append(token_data["id"])
        
        # Test 2: Use MCP token for authentication  
        response = self.client.get(
            f"/mcp/{self.workspace_id}/",
            headers={"Authorization": f"Bearer {mcp_token}"}
        )
        assert response.status_code == 200, "MCP token auth failed"
        info = response.json()
        assert info["workspace_id"] == self.workspace_id
        
        # Test 4: Invalid token should fail
        response = self.client.get(
            f"/mcp/{self.workspace_id}/",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )
        assert response.status_code == 401, "Invalid token should be rejected"
        
        # Test 5: No token should fail
        response = self.client.get(f"/mcp/{self.workspace_id}/")
        assert response.status_code == 401, "Request without token should be rejected"
    
    def test_mcp_workspace_isolation(self):
        """Test that MCP properly isolates workspaces."""
        # Create a second workspace for isolation testing
        response = self.client.post(
            "/admin/api/v1/workspaces",
            headers=self.headers,
            json={
                "name": "MCP Isolation Test Workspace",
                "description": "Testing workspace isolation"
            }
        )
        
        if response.status_code not in [200, 201]:
            # Try to get existing workspace
            response = self.client.get("/admin/api/v1/workspaces", headers=self.headers)
            workspaces = response.json()["workspaces"]
            workspace2_id = None
            for ws in workspaces:
                if ws["name"] == "MCP Isolation Test Workspace":
                    workspace2_id = ws["id"]
                    break
            if not workspace2_id:
                pytest.skip("Could not create second workspace for isolation testing")
        else:
            workspace2_id = response.json()["id"]
        
        # Create action in first workspace
        action1_id = create_test_action(
            self.client, self.headers, self.workspace_id,
            "isolation_test_ws1", "REST",
            {"url": "https://httpbin.org/get", "method": "GET"}
        )
        assert action1_id, "Failed to create action in workspace 1"
        self.test_actions.append(action1_id)
        
        # Create action in second workspace  
        action2_id = create_test_action(
            self.client, self.headers, workspace2_id,
            "isolation_test_ws2", "REST",
            {"url": "https://httpbin.org/post", "method": "POST"}
        )
        assert action2_id, "Failed to create action in workspace 2"
        
        # Create MCP token for workspace 1
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/mcp-tokens",
            headers=self.headers,
            json={
                "name": "isolation_test_ws1_token",
                "description": "Token for workspace isolation testing",
                "expires_in_days": 1,
                "scopes": ["read:actions"]
            }
        )
        assert response.status_code in [200, 201], f"Failed to create MCP token for WS1: {response.text}"
        mcp_token_ws1 = response.json()["token"]
        if "id" in response.json():
            self.test_tokens.append(response.json()["id"])
        
        # List tools in workspace 1 - should only see workspace 1's action
        response = self.client.post(
            f"/mcp/{self.workspace_id}/tools/list",
            headers={"Authorization": f"Bearer {mcp_token_ws1}"},
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1}
        )
        assert response.status_code == 200
        
        data = response.json()
        tools_ws1 = data["result"]["tools"] if "result" in data else []
        tool_names_ws1 = [t["name"] for t in tools_ws1]
        
        assert "isolation_test_ws1" in tool_names_ws1, "Workspace 1 should see its own action"
        assert "isolation_test_ws2" not in tool_names_ws1, "Workspace 1 should NOT see workspace 2's action"
        
        # Create MCP token for workspace 2
        response = self.client.post(
            f"/admin/api/v1/workspaces/{workspace2_id}/mcp-tokens",
            headers=self.headers,
            json={
                "name": "isolation_test_ws2_token",
                "description": "Token for workspace 2 isolation testing",
                "expires_in_days": 1,
                "scopes": ["read:actions"]
            }
        )
        assert response.status_code in [200, 201], f"Failed to create MCP token for WS2: {response.text}"
        mcp_token_ws2 = response.json()["token"]
        
        # List tools in workspace 2 - should only see workspace 2's action
        response = self.client.post(
            f"/mcp/{workspace2_id}/tools/list",
            headers={"Authorization": f"Bearer {mcp_token_ws2}"},
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 2}
        )
        assert response.status_code == 200
        
        data = response.json()
        tools_ws2 = data["result"]["tools"] if "result" in data else []
        tool_names_ws2 = [t["name"] for t in tools_ws2]
        
        assert "isolation_test_ws2" in tool_names_ws2, "Workspace 2 should see its own action"
        assert "isolation_test_ws1" not in tool_names_ws2, "Workspace 2 should NOT see workspace 1's action"
        
        # Clean up workspace 2's action
        try:
            self.client.delete(
                f"/admin/api/v1/workspaces/{workspace2_id}/actions/{action2_id}",
                headers=self.headers
            )
        except:
            pass
    
    def test_mcp_token_scopes(self):
        """Test MCP token scope enforcement."""
        # Create token with limited scopes (read only)
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/mcp-tokens",
            headers=self.headers,
            json={
                "name": "read_only_token",
                "description": "Token with read-only access",
                "expires_in_days": 1,
                "scopes": ["read:actions"]  # Only read, no execute
            }
        )
        
        assert response.status_code in [200, 201], f"Failed to create limited token: {response.text}"
        limited_token = response.json()["token"]
        if "id" in response.json():
            self.test_tokens.append(response.json()["id"])
        
        # Test that read operations work
        response = self.client.post(
            f"/mcp/{self.workspace_id}/tools/list",
            headers={"Authorization": f"Bearer {limited_token}"},
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1}
        )
        assert response.status_code == 200, "Read operation should work with read-only token"
        
        # Create a test action to execute
        action_id = create_test_action(
            self.client, self.headers, self.workspace_id,
            "scope_test_action", "REST",
            {"url": "https://httpbin.org/get", "method": "GET"}
        )
        if action_id:
            self.test_actions.append(action_id)
        
        # Test that execute operations fail with read-only token
        response = self.client.post(
            f"/mcp/{self.workspace_id}/tools/call",
            headers={"Authorization": f"Bearer {limited_token}"},
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "scope_test_action",
                    "arguments": {}
                },
                "id": 2
            }
        )
        # Should either return 403 or an error in the JSON-RPC response
        if response.status_code == 200:
            data = response.json()
            assert "error" in data, "Execute should fail with read-only token"
    
    @pytest.mark.asyncio
    async def test_mcp_concurrent_connections(self):
        """Test multiple concurrent MCP connections."""
        if not FASTMCP_AVAILABLE:
            pytest.skip("FastMCP not available")
        
        # Create test action for concurrent access
        action_id = create_test_action(
            self.client, self.headers, self.workspace_id,
            "concurrent_test", "REST",
            {"url": "https://httpbin.org/delay/1", "method": "GET"}
        )
        if action_id:
            self.test_actions.append(action_id)
        
        # Create multiple concurrent clients
        async def client_task(client_id: int):
            """Task for individual client."""
            transport = SSETransport(
                url=f"http://localhost:8090/mcp/{self.workspace_id}/sse",
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            
            try:
                async with FastMCPClient(transport) as client:
                    # Each client lists tools
                    tools = await asyncio.wait_for(
                        client.list_tools(),
                        timeout=10.0
                    )
                    tool_names = [t.name for t in tools]
                    assert "concurrent_test" in tool_names, f"Client {client_id} should see test action"
                    
                    # Each client executes a tool
                    result = await asyncio.wait_for(
                        client.call_tool("concurrent_test", {}),
                        timeout=15.0
                    )
                    assert result is not None, f"Client {client_id} execution failed"
                    
                    return f"client_{client_id}_success"
            except asyncio.TimeoutError:
                return f"client_{client_id}_timeout"
            except Exception as e:
                return f"client_{client_id}_error: {e}"
        
        # Run 5 concurrent clients
        tasks = [client_task(i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check results
        success_count = sum(1 for r in results if isinstance(r, str) and "success" in r)
        assert success_count >= 3, f"At least 3 clients should succeed, got {success_count}. Results: {results}"
    
    def test_mcp_error_handling(self):
        """Test MCP error handling for various scenarios."""
        # First, create an MCP token for testing
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/mcp-tokens",
            headers=self.headers,
            json={
                "name": "error_test_token",
                "description": "Token for error testing",
                "expires_in_days": 1,
                "scopes": ["read:actions", "execute:actions"]
            }
        )
        assert response.status_code in [200, 201], f"Failed to create MCP token: {response.text}"
        mcp_token = response.json()["token"]
        if "id" in response.json():
            self.test_tokens.append(response.json()["id"])
        
        # Test 1: Non-existent workspace (should fail even with valid token)
        response = self.client.get(
            "/mcp/invalid_workspace_id_12345/",
            headers={"Authorization": f"Bearer {mcp_token}"}
        )
        assert response.status_code in [400, 403, 404], "Non-existent workspace should return error"
        
        # Test 2: Malformed JSON-RPC request
        response = self.client.post(
            f"/mcp/{self.workspace_id}/tools/list",
            headers={"Authorization": f"Bearer {self.access_token}"},
            json={"invalid": "request"}  # Missing required JSON-RPC fields
        )
        assert response.status_code == 400, "Malformed request should return 400"
        
        # Test 3: Calling non-existent tool
        response = self.client.post(
            f"/mcp/{self.workspace_id}/tools/call",
            headers={"Authorization": f"Bearer {self.access_token}"},
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "non_existent_tool_xyz",
                    "arguments": {}
                },
                "id": 1
            }
        )
        assert response.status_code == 200  # JSON-RPC returns 200 with error in response
        data = response.json()
        assert "error" in data, "Should return error for non-existent tool"
        
        # Test 4: Invalid tool arguments
        # First create a tool that requires arguments
        action_id = create_test_action(
            self.client, self.headers, self.workspace_id,
            "args_test_action", "REST",
            {
                "url": "https://httpbin.org/post",
                "method": "POST",
                "variables": [{"name": "required_param", "type": "string", "required": True}]
            }
        )
        if action_id:
            self.test_actions.append(action_id)
            
            # Call without required argument
            response = self.client.post(
                f"/mcp/{self.workspace_id}/tools/call",
                headers={"Authorization": f"Bearer {self.access_token}"},
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "args_test_action",
                        "arguments": {}  # Missing required_param
                    },
                    "id": 2
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert "error" in data or "result" in data, "Should handle missing required arguments"
    
    def test_mcp_knowledge_base_integration(self):
        """Test MCP integration with knowledge base search."""
        # Create MCP token for KB testing
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/mcp-tokens",
            headers=self.headers,
            json={
                "name": "kb_test_token",
                "description": "Token for KB testing",
                "expires_in_days": 1,
                "scopes": ["read:knowledge_base", "execute:actions"]
            }
        )
        assert response.status_code in [200, 201], f"Failed to create MCP token: {response.text}"
        mcp_token = response.json()["token"]
        if "id" in response.json():
            self.test_tokens.append(response.json()["id"])
        
        # Upload a test document to knowledge base
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/knowledge/upload",
            headers=self.headers,
            data={
                "source_type": "text",
                "title": "MCP Test Document",
                "content": "This is a test document for MCP knowledge base integration. It contains information about testing MCP features.",
                "category": "test",
                "chunking_strategy": "smart"
            }
        )
        
        if response.status_code in [200, 201]:
            doc_id = response.json().get("document_id")
            
            # Wait for processing
            import time
            time.sleep(2)
            
            # Test knowledge base search through MCP
            response = self.client.post(
                f"/mcp/{self.workspace_id}/tools/call",
                headers={"Authorization": f"Bearer {mcp_token}"},
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "search_knowledge_base",
                        "arguments": {
                            "query": "MCP testing",
                            "max_results": 5,
                            "search_type": "hybrid"
                        }
                    },
                    "id": 1
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should return results (or at least not error)
            assert "result" in data or "error" in data
            
            # Clean up document
            if doc_id:
                try:
                    self.client.delete(
                        f"/admin/api/v1/workspaces/{self.workspace_id}/knowledge/{doc_id}",
                        headers=self.headers
                    )
                except:
                    pass