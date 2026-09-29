"""
Integration tests for MCP protocol compatibility.

Tests our native protocol implementation against FastMCP clients to ensure
complete compatibility before migration from FastMCP library.
"""

import asyncio
import json
import pytest
from typing import Dict, Any, Optional
from httpx import Client

# Import enhanced test utilities
from .enhanced_test_utils import create_test_action_with_retries, ResourceManager

# Import FastMCP client for compatibility testing
try:
    from fastmcp.client import Client as FastMCPClient
    from fastmcp.client import SSETransport
    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False

from .test_utils import (
    ensure_test_workspace, 
    get_emulator_auth_token,
    create_test_action,
    delete_test_action,
    generate_test_mcp_token
)


@pytest.mark.integration
@pytest.mark.skipif(not FASTMCP_AVAILABLE, reason="FastMCP not installed")
class TestProtocolCompatibility:
    """Test MCP protocol compatibility with FastMCP clients."""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment."""
        cls.client = Client(base_url="http://localhost:8090", timeout=30.0)
        
        # Check if server is running
        try:
            health_response = cls.client.get("/admin/api/v1/health")
            if health_response.status_code != 200:
                cls.skip = True
                cls.skip_reason = f"Server health check failed: {health_response.status_code}"
                return
        except Exception as e:
            cls.skip = True
            cls.skip_reason = f"Server not running: {e}"
            return
        
        # Get auth token and workspace
        token, refresh_token, headers = get_emulator_auth_token(cls.client)
        if not token:
            # In development, we can use test tokens
            cls.headers = {"Authorization": "Bearer test-protocol-compatibility"}
        else:
            cls.headers = headers
        
        # Ensure workspace exists
        ws = ensure_test_workspace(cls.client, cls.headers)
        if not ws:
            cls.skip = True
            cls.skip_reason = "Could not create or access test workspace"
            return
            
        cls.workspace_id = ws["id"]
        cls.skip = False
        
        # Store test actions for cleanup
        cls.test_actions = []
    
    @classmethod
    def teardown_class(cls):
        """Cleanup test environment."""
        if hasattr(cls, 'test_actions'):
            for action_id in cls.test_actions:
                try:
                    delete_test_action(cls.client, cls.headers, cls.workspace_id, action_id)
                except Exception as e:
                    print(f"Warning: Failed to cleanup test action {action_id}: {e}")
    
    def setup_method(self):
        """Skip if prerequisites not met."""
        if getattr(self, "skip", False):
            pytest.skip(getattr(self, "skip_reason", "Skipping protocol compatibility tests"))
    
    async def create_test_action_helper(self, name: str, action_type: str = "REST", 
                                      config: Optional[Dict[str, Any]] = None) -> str:
        """Helper to create a test action and track for cleanup."""
        action_config = config or {
            "url": "https://httpbin.org/get",
            "method": "GET",
            "headers": {"Content-Type": "application/json"}
        }
        
        # First try to delete any existing action with the same name
        try:
            # Get list of existing actions
            response = self.client.get(
                f"/admin/api/v1/workspaces/{self.workspace_id}/actions",
                headers=self.headers
            )
            if response.status_code == 200:
                existing_actions = response.json()
                for action in existing_actions:
                    if action.get("name") == name:
                        # Delete the existing action
                        delete_response = self.client.delete(
                            f"/admin/api/v1/workspaces/{self.workspace_id}/actions/{action['id']}",
                            headers=self.headers
                        )
                        if delete_response.status_code in [200, 204]:
                            print(f"✓ Deleted existing action: {name}")
                        break
        except Exception as e:
            print(f"Warning: Could not check/delete existing action: {e}")
        
        # Now create the action using enhanced method with retries
        action_id = create_test_action_with_retries(
            self.client, 
            self.headers, 
            self.workspace_id, 
            name, 
            action_type, 
            config=action_config,
            max_retries=3
        )
        
        if action_id:
            self.test_actions.append(action_id)
        
        return action_id
    
    def test_mcp_endpoints_exist(self):
        """Test that MCP endpoints are available and respond correctly."""
        # Test MCP info endpoint
        response = self.client.get(
            f"/mcp/{self.workspace_id}/",
            headers={"Authorization": "Bearer test-protocol-compatibility"}
        )
        
        assert response.status_code == 200, f"MCP info endpoint failed: {response.text}"
        
        info = response.json()
        assert "server_name" in info
        assert "capabilities" in info
        assert info["capabilities"]["tools"] is True
    
    def test_jsonrpc_tools_list(self):
        """Test JSON-RPC tools/list endpoint."""
        response = self.client.post(
            f"/mcp/{self.workspace_id}/tools/list",
            headers={"Authorization": "Bearer test-protocol-compatibility"},
            json={
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": 1
            }
        )
        
        assert response.status_code == 200, f"Tools list failed: {response.text}"
        
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "result" in data
        assert "tools" in data["result"]
        assert isinstance(data["result"]["tools"], list)
    
    @pytest.mark.asyncio
    async def test_dynamic_tool_registration(self):
        """Test that dynamically created actions appear as tools."""
        # Create a test action
        action_id = await self.create_test_action_helper(
            "test_dynamic_tool",
            "REST",
            {
                "url": "https://httpbin.org/json",
                "method": "GET",
                "headers": {"Accept": "application/json"}
            }
        )
        
        assert action_id, "Failed to create test action"
        
        # Wait a moment for tool registration
        await asyncio.sleep(1)
        
        # Check that the tool appears in the list
        response = self.client.post(
            f"/mcp/{self.workspace_id}/tools/list",
            headers={"Authorization": "Bearer test-protocol-compatibility"},
            json={
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": 2
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        tool_names = [tool["name"] for tool in data["result"]["tools"]]
        assert "test_dynamic_tool" in tool_names, f"Dynamic tool not found in: {tool_names}"
    
    @pytest.mark.asyncio
    async def test_tool_execution(self):
        """Test tool execution through JSON-RPC."""
        # Create a test action that returns predictable data
        action_id = await self.create_test_action_helper(
            "test_execution_tool",
            "REST",
            {
                "url": "https://httpbin.org/json",
                "method": "GET",
                "headers": {"Accept": "application/json"}
            }
        )
        
        assert action_id, "Failed to create test action"
        await asyncio.sleep(1)  # Wait for registration
        
        # Execute the tool
        response = self.client.post(
            f"/mcp/{self.workspace_id}/tools/call",
            headers={"Authorization": "Bearer test-protocol-compatibility"},
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "test_execution_tool",
                    "arguments": {}
                },
                "id": 3
            }
        )
        
        assert response.status_code == 200, f"Tool execution failed: {response.text}"
        
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "result" in data
        assert "content" in data["result"]
        assert len(data["result"]["content"]) > 0
    
    @pytest.mark.asyncio
    async def test_fastmcp_client_connection(self):
        """Test FastMCP client connection and basic operations."""
        if not FASTMCP_AVAILABLE:
            pytest.skip("FastMCP not available")
        
        # Create test actions for the client to discover
        action1_id = await self.create_test_action_helper(
            "fastmcp_test_action_1",
            "REST",
            {
                "url": "https://httpbin.org/get",
                "method": "GET"
            }
        )
        
        action2_id = await self.create_test_action_helper(
            "fastmcp_test_action_2", 
            "REST",
            {
                "url": "https://httpbin.org/post",
                "method": "POST",
                "headers": {"Content-Type": "application/json"}
            }
        )
        
        assert action1_id and action2_id, "Failed to create test actions"
        await asyncio.sleep(2)  # Wait for registration
        
        # Create FastMCP client
        transport = SSETransport(
            url=f"http://localhost:8090/mcp/{self.workspace_id}/sse",
            headers={"Authorization": "Bearer test-protocol-compatibility"}
        )
        
        try:
            async with FastMCPClient(transport) as client:
                # Test connection and initialization
                await asyncio.wait_for(client.ping(), timeout=10.0)
                
                # Test tool discovery
                tools = await asyncio.wait_for(client.list_tools(), timeout=10.0)
                tool_names = [t.name for t in tools]
                
                assert "fastmcp_test_action_1" in tool_names, f"Action 1 not found in tools: {tool_names}"
                assert "fastmcp_test_action_2" in tool_names, f"Action 2 not found in tools: {tool_names}"
                
                # Test tool execution
                result = await asyncio.wait_for(
                    client.call_tool("fastmcp_test_action_1", {}),
                    timeout=15.0
                )
                
                assert result is not None, "Tool execution should return a result"
                
        except asyncio.TimeoutError:
            pytest.fail("FastMCP client operations timed out")
        except Exception as e:
            pytest.fail(f"FastMCP client failed: {e}")
    
    @pytest.mark.asyncio
    async def test_concurrent_fastmcp_clients(self):
        """Test multiple FastMCP clients connecting simultaneously."""
        if not FASTMCP_AVAILABLE:
            pytest.skip("FastMCP not available")
        
        # Create test action
        action_id = await self.create_test_action_helper(
            "concurrent_test_action",
            "REST",
            {"url": "https://httpbin.org/get", "method": "GET"}
        )
        
        assert action_id, "Failed to create test action"
        await asyncio.sleep(1)
        
        # Create multiple clients
        async def client_task(client_id: int):
            transport = SSETransport(
                url=f"http://localhost:8090/mcp/{self.workspace_id}/sse",
                headers={"Authorization": f"Bearer test-protocol-compatibility-{client_id}"}
            )
            
            async with FastMCPClient(transport) as client:
                # Each client should be able to discover tools
                tools = await client.list_tools()
                tool_names = [t.name for t in tools]
                assert "concurrent_test_action" in tool_names
                
                # Each client should be able to execute tools
                result = await client.call_tool("concurrent_test_action", {})
                assert result is not None
                
                return f"client_{client_id}_success"
        
        # Run multiple clients concurrently
        tasks = [client_task(i) for i in range(3)]
        
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks),
                timeout=30.0
            )
            
            assert len(results) == 3
            assert all("success" in result for result in results)
            
        except asyncio.TimeoutError:
            pytest.fail("Concurrent client test timed out")
    
    def test_error_handling(self):
        """Test error handling in JSON-RPC responses."""
        # Test calling non-existent tool
        response = self.client.post(
            f"/mcp/{self.workspace_id}/tools/call",
            headers={"Authorization": "Bearer test-protocol-compatibility"},
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "non_existent_tool_xyz",
                    "arguments": {}
                },
                "id": 4
            }
        )
        
        assert response.status_code == 200  # JSON-RPC errors return 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "result" in data  # Our implementation returns result with error content
        
        # Should contain error information in the content
        content = data["result"]["content"][0]["text"]
        assert "not found" in content.lower() or "error" in content.lower()
    
    def test_authentication_validation(self):
        """Test that authentication is properly validated."""
        # Test with invalid token
        response = self.client.get(
            f"/mcp/{self.workspace_id}/",
            headers={"Authorization": "Bearer invalid-token-xyz"}
        )
        
        # Should reject invalid tokens
        assert response.status_code == 401, f"Should reject invalid token, got: {response.status_code}"
    
    @pytest.mark.asyncio
    async def test_sse_connection_stability(self):
        """Test SSE connection stability over time."""
        if not FASTMCP_AVAILABLE:
            pytest.skip("FastMCP not available")
        
        # Create test action
        action_id = await self.create_test_action_helper(
            "stability_test_action",
            "REST",
            {"url": "https://httpbin.org/get", "method": "GET"}
        )
        
        assert action_id, "Failed to create test action"
        await asyncio.sleep(1)
        
        transport = SSETransport(
            url=f"http://localhost:8090/mcp/{self.workspace_id}/sse",
            headers={"Authorization": "Bearer test-protocol-compatibility"}
        )
        
        try:
            async with FastMCPClient(transport) as client:
                # Perform multiple operations over time
                for i in range(5):
                    await asyncio.sleep(1)  # Wait between operations
                    
                    tools = await client.list_tools()
                    assert len(tools) > 0, f"Tools disappeared on iteration {i}"
                    
                    result = await client.call_tool("stability_test_action", {})
                    assert result is not None, f"Tool execution failed on iteration {i}"
                    
        except Exception as e:
            pytest.fail(f"SSE connection stability test failed: {e}")


@pytest.mark.integration
class TestMCPProtocolCompliance:
    """Test MCP protocol compliance without FastMCP dependency."""
    
    @classmethod
    def setup_class(cls):
        """Setup for protocol compliance tests."""
        cls.client = Client(base_url="http://localhost:8090", timeout=10.0)
        
        # Simple test setup - use default workspace
        cls.workspace_id = "689d34139d87472f3fd95c5e"  # Default test workspace
        cls.test_token = "test-protocol-compliance"
    
    def test_mcp_server_info(self):
        """Test MCP server information endpoint."""
        response = self.client.get(
            f"/mcp/{self.workspace_id}/",
            headers={"Authorization": f"Bearer {self.test_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required MCP server info fields
        assert "server_name" in data
        assert "server_type" in data
        assert "capabilities" in data
        assert "tools" in data["capabilities"]
    
    def test_jsonrpc_format_compliance(self):
        """Test JSON-RPC 2.0 format compliance."""
        # Test tools/list
        response = self.client.post(
            f"/mcp/{self.workspace_id}/tools/list",
            headers={"Authorization": f"Bearer {self.test_token}"},
            json={
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": "test-id-123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check JSON-RPC 2.0 compliance
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "test-id-123"
        assert "result" in data or "error" in data
        
        if "result" in data:
            assert "tools" in data["result"]
    
    def test_tools_list_format(self):
        """Test tools/list response format compliance."""
        response = self.client.post(
            f"/mcp/{self.workspace_id}/tools/list",
            headers={"Authorization": f"Bearer {self.test_token}"},
            json={
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        tools = data["result"]["tools"]
        
        for tool in tools:
            # Each tool should have required fields
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            
            # inputSchema should be valid JSON schema
            schema = tool["inputSchema"]
            assert "type" in schema
            assert schema["type"] == "object"
    
    def test_tools_call_format(self):
        """Test tools/call response format compliance."""
        # First get available tools
        tools_response = self.client.post(
            f"/mcp/{self.workspace_id}/tools/list",
            headers={"Authorization": f"Bearer {self.test_token}"},
            json={
                "jsonrpc": "2.0",
                "method": "tools/list", 
                "params": {},
                "id": 1
            }
        )
        
        assert tools_response.status_code == 200
        tools_data = tools_response.json()
        tools = tools_data["result"]["tools"]
        
        if not tools:
            pytest.skip("No tools available for testing")
        
        # Test calling the first available tool
        tool_name = tools[0]["name"]
        
        response = self.client.post(
            f"/mcp/{self.workspace_id}/tools/call",
            headers={"Authorization": f"Bearer {self.test_token}"},
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": {}
                },
                "id": 2
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check JSON-RPC 2.0 compliance
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 2
        assert "result" in data or "error" in data
        
        if "result" in data:
            result = data["result"]
            assert "content" in result
            assert isinstance(result["content"], list)
            
            # Each content item should have type and text
            for content_item in result["content"]:
                assert "type" in content_item
                assert "text" in content_item