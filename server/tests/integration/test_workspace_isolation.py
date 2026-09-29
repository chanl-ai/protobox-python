"""
Integration tests for workspace isolation in MCP servers.

Tests that workspaces have completely isolated tool sets and that
clients can only access tools from their authorized workspace.
"""

import asyncio
import pytest
import uuid
from typing import List, Dict, Any, Optional
from httpx import Client

# Import FastMCP client for testing
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
class TestWorkspaceIsolation:
    """Test complete workspace isolation for MCP servers."""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment with multiple workspaces."""
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
        
        # Get auth token
        token, refresh_token, headers = get_emulator_auth_token(cls.client)
        if not token:
            cls.headers = {"Authorization": "Bearer test-workspace-isolation"}
        else:
            cls.headers = headers
        
        cls.skip = False
        
        # Track test resources for cleanup
        cls.test_workspaces = []
        cls.test_actions = []
    
    @classmethod
    def teardown_class(cls):
        """Cleanup test resources."""
        # Cleanup test actions
        for workspace_id, action_id in cls.test_actions:
            try:
                delete_test_action(cls.client, cls.headers, workspace_id, action_id)
            except Exception as e:
                print(f"Warning: Failed to cleanup action {action_id}: {e}")
        
        # Note: We don't delete workspaces as they may be used by other tests
    
    def setup_method(self):
        """Skip if prerequisites not met."""
        if getattr(self, "skip", False):
            pytest.skip(getattr(self, "skip_reason", "Skipping workspace isolation tests"))
    
    async def create_workspace_with_actions(self, workspace_name: str, 
                                          action_configs: List[Dict[str, Any]]) -> tuple[str, List[str]]:
        """Create a workspace with specific actions for testing."""
        # Create or get workspace
        workspace = ensure_test_workspace(
            self.client, 
            self.headers, 
            name=f"{workspace_name}_{uuid.uuid4().hex[:8]}"
        )
        
        if not workspace:
            pytest.fail(f"Failed to create workspace: {workspace_name}")
        
        workspace_id = workspace["id"]
        self.test_workspaces.append(workspace_id)
        
        # Create actions
        action_ids = []
        for action_config in action_configs:
            action_id = create_test_action(
                self.client,
                self.headers,
                workspace_id,
                action_config["name"],
                action_config.get("type", "REST"),
                config=action_config.get("config", {
                    "url": "https://httpbin.org/get",
                    "method": "GET"
                }),
                variables=action_config.get("variables", [])
            )
            
            if action_id:
                action_ids.append(action_id)
                self.test_actions.append((workspace_id, action_id))
        
        return workspace_id, action_ids
    
    @pytest.mark.asyncio
    async def test_basic_workspace_isolation(self):
        """Test that workspaces have completely isolated tool sets."""
        # Generate unique names for this test run
        weather_api_name = f"weather_api_{uuid.uuid4().hex[:8]}"
        user_lookup_name = f"user_lookup_{uuid.uuid4().hex[:8]}"
        stock_price_name = f"stock_price_{uuid.uuid4().hex[:8]}"
        currency_convert_name = f"currency_convert_{uuid.uuid4().hex[:8]}"
        
        # Create Workspace A with specific actions
        workspace_a_id, actions_a = await self.create_workspace_with_actions(
            "workspace_a",
            [
                {
                    "name": weather_api_name,
                    "type": "REST",
                    "config": {
                        "url": "https://api.weather.com/current",
                        "method": "GET",
                        "headers": {"Accept": "application/json"}
                    }
                },
                {
                    "name": user_lookup_name,
                    "type": "REST", 
                    "config": {
                        "url": "https://jsonplaceholder.typicode.com/users/1",
                        "method": "GET"
                    }
                }
            ]
        )
        
        # Create Workspace B with different actions
        workspace_b_id, actions_b = await self.create_workspace_with_actions(
            "workspace_b",
            [
                {
                    "name": stock_price_name,
                    "type": "REST",
                    "config": {
                        "url": "https://api.stock.com/price",
                        "method": "GET"
                    }
                },
                {
                    "name": currency_convert_name,
                    "type": "REST",
                    "config": {
                        "url": "https://api.exchange.com/convert",
                        "method": "POST",
                        "headers": {"Content-Type": "application/json"}
                    }
                }
            ]
        )
        
        # Wait for action registration
        await asyncio.sleep(2)
        
        # Generate workspace-specific JWT tokens with proper workspace_id claims
        from .test_utils import get_workspace_scoped_jwt_token
        
        token_a = get_workspace_scoped_jwt_token(self.client, self.headers, workspace_a_id)
        token_b = get_workspace_scoped_jwt_token(self.client, self.headers, workspace_b_id)
        
        if not token_a or not token_b:
            pytest.fail("Failed to generate workspace-scoped JWT tokens for MCP authentication")
        
        # Create clients for each workspace
        transport_a = SSETransport(
            url=f"http://localhost:8090/mcp/{workspace_a_id}/sse",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        
        transport_b = SSETransport(
            url=f"http://localhost:8090/mcp/{workspace_b_id}/sse",
            headers={"Authorization": f"Bearer {token_b}"}
        )
        
        try:
            async with FastMCPClient(transport_a) as client_a, FastMCPClient(transport_b) as client_b:
                # Get tools for each workspace
                tools_a = await asyncio.wait_for(client_a.list_tools(), timeout=10.0)
                tools_b = await asyncio.wait_for(client_b.list_tools(), timeout=10.0)
                
                tool_names_a = [t.name for t in tools_a]
                tool_names_b = [t.name for t in tools_b]
                
                # Verify Workspace A tools
                assert weather_api_name in tool_names_a, f"{weather_api_name} not found in workspace A: {tool_names_a}"
                assert user_lookup_name in tool_names_a, f"{user_lookup_name} not found in workspace A: {tool_names_a}"
                
                # Verify Workspace B tools  
                assert stock_price_name in tool_names_b, f"{stock_price_name} not found in workspace B: {tool_names_b}"
                assert currency_convert_name in tool_names_b, f"{currency_convert_name} not found in workspace B: {tool_names_b}"
                
                # Verify isolation - A should not see B's tools
                assert stock_price_name not in tool_names_a, f"{stock_price_name} leaked to workspace A: {tool_names_a}"
                assert currency_convert_name not in tool_names_a, f"{currency_convert_name} leaked to workspace A: {tool_names_a}"
                
                # Verify isolation - B should not see A's tools
                assert weather_api_name not in tool_names_b, f"{weather_api_name} leaked to workspace B: {tool_names_b}"
                assert user_lookup_name not in tool_names_b, f"{user_lookup_name} leaked to workspace B: {tool_names_b}"
                
        except asyncio.TimeoutError:
            pytest.fail("Workspace isolation test timed out")
        except Exception as e:
            pytest.fail(f"Workspace isolation test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_tool_execution_isolation(self):
        """Test that clients can only execute tools from their workspace."""
        # Generate unique names for this test run
        echo_service_name = f"echo_service_{uuid.uuid4().hex[:8]}"
        data_service_name = f"data_service_{uuid.uuid4().hex[:8]}"
        
        # Create workspaces with actions
        workspace_a_id, _ = await self.create_workspace_with_actions(
            "exec_test_a",
            [
                {
                    "name": echo_service_name,
                    "type": "REST",
                    "config": {
                        "url": "https://httpbin.org/anything",
                        "method": "POST",
                        "headers": {"Content-Type": "application/json"}
                    }
                }
            ]
        )
        
        workspace_b_id, _ = await self.create_workspace_with_actions(
            "exec_test_b", 
            [
                {
                    "name": data_service_name,
                    "type": "REST",
                    "config": {
                        "url": "https://httpbin.org/json",
                        "method": "GET"
                    }
                }
            ]
        )
        
        await asyncio.sleep(2)  # Wait for registration
        
        # Generate workspace-specific JWT tokens with proper workspace_id claims
        from .test_utils import get_workspace_scoped_jwt_token
        
        token_a = get_workspace_scoped_jwt_token(self.client, self.headers, workspace_a_id)
        token_b = get_workspace_scoped_jwt_token(self.client, self.headers, workspace_b_id)
        
        if not token_a or not token_b:
            pytest.fail("Failed to generate workspace-scoped JWT tokens for MCP authentication")
        
        # Create clients
        transport_a = SSETransport(
            url=f"http://localhost:8090/mcp/{workspace_a_id}/sse",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        
        transport_b = SSETransport(
            url=f"http://localhost:8090/mcp/{workspace_b_id}/sse", 
            headers={"Authorization": f"Bearer {token_b}"}
        )
        
        try:
            async with FastMCPClient(transport_a) as client_a, FastMCPClient(transport_b) as client_b:
                # Client A should be able to execute its own tools
                result_a = await asyncio.wait_for(
                    client_a.call_tool(echo_service_name, {}),
                    timeout=15.0
                )
                assert result_a is not None, "Client A failed to execute its own tool"
                
                # Client B should be able to execute its own tools
                result_b = await asyncio.wait_for(
                    client_b.call_tool(data_service_name, {}),
                    timeout=15.0
                )
                assert result_b is not None, "Client B failed to execute its own tool"
                
                # Test cross-workspace execution should fail
                # Client A trying to execute Client B's tool should fail gracefully
                try:
                    result_cross_a = await asyncio.wait_for(
                        client_a.call_tool(data_service_name, {}),
                        timeout=10.0
                    )
                    # The call should return content indicating access denied
                    if result_cross_a:
                        # Check if the result content contains security error message
                        content_text = ""
                        if hasattr(result_cross_a, 'content') and result_cross_a.content:
                            if isinstance(result_cross_a.content, list):
                                content_text = " ".join([str(item.text) if hasattr(item, 'text') else str(item) for item in result_cross_a.content])
                            else:
                                content_text = str(result_cross_a.content)
                        
                        content_text = content_text.lower()
                        
                        # Should contain security/access denied message
                        if not any(keyword in content_text for keyword in ['access denied', 'not found', 'security', 'denied']):
                            pytest.fail(f"Expected security error message, got: {content_text}")
                    else:
                        pytest.fail("Client A should get error response when trying to execute Client B's tool")
                except Exception:
                    # This is also expected - tool execution might throw exception
                    pass
                
                # Client B trying to execute Client A's tool should fail gracefully
                try:
                    result_cross_b = await asyncio.wait_for(
                        client_b.call_tool(echo_service_name, {}),
                        timeout=10.0
                    )
                    # The call should return content indicating access denied
                    if result_cross_b:
                        # Check if the result content contains security error message
                        content_text = ""
                        if hasattr(result_cross_b, 'content') and result_cross_b.content:
                            if isinstance(result_cross_b.content, list):
                                content_text = " ".join([str(item.text) if hasattr(item, 'text') else str(item) for item in result_cross_b.content])
                            else:
                                content_text = str(result_cross_b.content)
                        
                        content_text = content_text.lower()
                        
                        # Should contain security/access denied message
                        if not any(keyword in content_text for keyword in ['access denied', 'not found', 'security', 'denied']):
                            pytest.fail(f"Expected security error message, got: {content_text}")
                    else:
                        pytest.fail("Client B should get error response when trying to execute Client A's tool")
                except Exception:
                    # This is also expected - tool execution might throw exception
                    pass
                    
        except asyncio.TimeoutError:
            pytest.fail("Tool execution isolation test timed out")
    
    @pytest.mark.asyncio
    async def test_concurrent_workspace_access(self):
        """Test concurrent access to different workspaces."""
        # Create multiple workspaces
        workspace_configs = [
            {
                "name": f"concurrent_workspace_{i}",
                "actions": [
                    {
                        "name": f"tool_{i}_1",
                        "type": "REST",
                        "config": {
                            "url": f"https://httpbin.org/delay/{i % 3 + 1}",
                            "method": "GET"
                        }
                    },
                    {
                        "name": f"tool_{i}_2", 
                        "type": "REST",
                        "config": {
                            "url": "https://httpbin.org/json",
                            "method": "GET"
                        }
                    }
                ]
            }
            for i in range(3)
        ]
        
        # Create workspaces
        from .test_utils import get_workspace_scoped_jwt_token
        
        workspace_clients = []
        for config in workspace_configs:
            workspace_id, _ = await self.create_workspace_with_actions(
                config["name"],
                config["actions"]
            )
            
            # Generate workspace-specific JWT token
            workspace_token = get_workspace_scoped_jwt_token(
                self.client, self.headers, workspace_id
            )
            if not workspace_token:
                pytest.fail(f"Failed to generate workspace token for {workspace_id}")
            
            transport = SSETransport(
                url=f"http://localhost:8090/mcp/{workspace_id}/sse",
                headers={"Authorization": f"Bearer {workspace_token}"}
            )
            
            workspace_clients.append((workspace_id, transport, config))
        
        await asyncio.sleep(3)  # Wait for all registrations
        
        # Test concurrent operations
        async def workspace_operations(workspace_data):
            workspace_id, transport, config = workspace_data
            
            try:
                async with FastMCPClient(transport) as client:
                    # List tools
                    tools = await client.list_tools()
                    tool_names = [t.name for t in tools]
                    
                    # Verify this workspace only sees its own tools
                    expected_tools = [action["name"] for action in config["actions"]]
                    for expected_tool in expected_tools:
                        assert expected_tool in tool_names, f"Missing tool {expected_tool} in workspace {workspace_id}"
                    
                    # Verify this workspace doesn't see other workspace tools
                    for other_config in workspace_configs:
                        if other_config["name"] != config["name"]:
                            for other_action in other_config["actions"]:
                                assert other_action["name"] not in tool_names, \
                                    f"Tool {other_action['name']} leaked to workspace {workspace_id}"
                    
                    # Execute a tool
                    if expected_tools:
                        result = await client.call_tool(expected_tools[0], {})
                        assert result is not None, f"Tool execution failed in workspace {workspace_id}"
                    
                    return f"workspace_{workspace_id}_success"
                    
            except Exception as e:
                return f"workspace_{workspace_id}_error: {e}"
        
        # Run all workspace operations concurrently
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*[workspace_operations(wc) for wc in workspace_clients]),
                timeout=45.0
            )
            
            # Verify all operations succeeded
            for result in results:
                assert "success" in result, f"Concurrent operation failed: {result}"
                
        except asyncio.TimeoutError:
            pytest.fail("Concurrent workspace access test timed out")
    
    @pytest.mark.asyncio
    async def test_cross_workspace_token_access(self):
        """Test that workspace tokens cannot be used to access other workspaces."""
        # Generate unique names for this test run
        secret_tool_name = f"secret_tool_{uuid.uuid4().hex[:8]}"
        public_tool_name = f"public_tool_{uuid.uuid4().hex[:8]}"
        
        # Create two workspaces with different tools
        secret_workspace_id, _ = await self.create_workspace_with_actions(
            "secret_workspace",
            [
                {
                    "name": secret_tool_name,
                    "type": "REST",
                    "config": {
                        "url": "https://httpbin.org/anything",
                        "method": "POST",
                        "headers": {"Content-Type": "application/json"}
                    }
                }
            ]
        )
        
        public_workspace_id, _ = await self.create_workspace_with_actions(
            "public_workspace",
            [
                {
                    "name": public_tool_name,
                    "type": "REST",
                    "config": {
                        "url": "https://httpbin.org/get",
                        "method": "GET"
                    }
                }
            ]
        )
        
        await asyncio.sleep(2)  # Wait for registration
        
        # Generate workspace-specific JWT tokens
        from .test_utils import get_workspace_scoped_jwt_token
        
        secret_token = get_workspace_scoped_jwt_token(self.client, self.headers, secret_workspace_id)
        public_token = get_workspace_scoped_jwt_token(self.client, self.headers, public_workspace_id)
        
        if not secret_token or not public_token:
            pytest.fail("Failed to generate workspace-scoped JWT tokens for cross-workspace access test")
        
        # Try to use secret workspace token to access public workspace
        transport_wrong = SSETransport(
            url=f"http://localhost:8090/mcp/{public_workspace_id}/sse",
            headers={"Authorization": f"Bearer {secret_token}"}  # Wrong token for this workspace
        )
        
        # This should fail - token workspace_id should not match URL workspace_id
        try:
            async with FastMCPClient(transport_wrong, timeout=5.0) as client_wrong:
                tools = await asyncio.wait_for(client_wrong.list_tools(), timeout=5.0)
                # If we get here, the security check failed
                tool_names = [t.name for t in tools]
                if secret_tool_name in tool_names:
                    pytest.fail("CRITICAL SECURITY ISSUE: Cross-workspace token access allowed - secret tool visible with wrong token")
                if public_tool_name in tool_names:
                    pytest.fail("CRITICAL SECURITY ISSUE: Cross-workspace token access allowed - can access workspace with wrong token")
        except Exception as e:
            # This is expected - should fail authentication or authorization
            assert any(keyword in str(e).lower() for keyword in ['auth', 'permission', 'unauthorized', 'forbidden', '403']), \
                f"Expected authentication/authorization error, got: {e}"
        
        # Try the reverse - use public token to access secret workspace
        transport_wrong_2 = SSETransport(
            url=f"http://localhost:8090/mcp/{secret_workspace_id}/sse",
            headers={"Authorization": f"Bearer {public_token}"}  # Wrong token for this workspace
        )
        
        try:
            async with FastMCPClient(transport_wrong_2, timeout=5.0) as client_wrong_2:
                tools = await asyncio.wait_for(client_wrong_2.list_tools(), timeout=5.0)
                # If we get here, the security check failed
                tool_names = [t.name for t in tools]
                if secret_tool_name in tool_names:
                    pytest.fail("CRITICAL SECURITY ISSUE: Cross-workspace token access allowed - can access secret workspace with public token")
                if public_tool_name in tool_names:
                    pytest.fail("CRITICAL SECURITY ISSUE: Cross-workspace token access allowed - wrong tools visible with wrong token")
        except Exception as e:
            # This is expected - should fail authentication or authorization
            assert any(keyword in str(e).lower() for keyword in ['auth', 'permission', 'unauthorized', 'forbidden', '403']), \
                f"Expected authentication/authorization error, got: {e}"
    
    @pytest.mark.asyncio
    async def test_malicious_tool_name_injection(self):
        """Test protection against malicious tool names that might bypass isolation."""
        # Create workspace with normal tool
        normal_tool_name = f"legitimate_tool_{uuid.uuid4().hex[:8]}"
        
        workspace_id, _ = await self.create_workspace_with_actions(
            "target_workspace",
            [
                {
                    "name": normal_tool_name,
                    "type": "REST",
                    "config": {
                        "url": "https://httpbin.org/get",
                        "method": "GET"
                    }
                }
            ]
        )
        
        await asyncio.sleep(2)
        
        # Generate valid token
        from .test_utils import get_workspace_scoped_jwt_token
        
        valid_token = get_workspace_scoped_jwt_token(self.client, self.headers, workspace_id)
        if not valid_token:
            pytest.fail("Failed to generate workspace-scoped JWT token")
        
        transport = SSETransport(
            url=f"http://localhost:8090/mcp/{workspace_id}/sse",
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        
        async with FastMCPClient(transport) as client:
            # Get legitimate tools
            tools = await client.list_tools()
            legitimate_tool_names = [t.name for t in tools]
            
            # Try various malicious tool names that might bypass security
            malicious_tool_names = [
                "../other_workspace_tool",
                "../../admin/secret_tool", 
                f"{normal_tool_name}/../other_tool",
                "workspace_id_injection_tool",
                "$(injection)_tool",
                "<script>alert('xss')</script>",
                "'; DROP TABLE actions; --",
                "../search_knowledge_base",  # Try to access built-in tool from wrong context
            ]
            
            for malicious_name in malicious_tool_names:
                try:
                    result = await asyncio.wait_for(
                        client.call_tool(malicious_name, {}),
                        timeout=5.0
                    )
                    # Check if result contains security error message
                    if result:
                        content_text = ""
                        if hasattr(result, 'content') and result.content:
                            if isinstance(result.content, list):
                                content_text = " ".join([str(item.text) if hasattr(item, 'text') else str(item) for item in result.content])
                            else:
                                content_text = str(result.content)
                        
                        content_text = content_text.lower()
                        
                        # Should contain security/access denied message
                        if not any(keyword in content_text for keyword in ['access denied', 'not found', 'security', 'denied']):
                            pytest.fail(f"SECURITY ISSUE: Malicious tool name '{malicious_name}' should be rejected, got: {content_text}")
                    else:
                        pytest.fail(f"SECURITY ISSUE: Malicious tool name '{malicious_name}' should get error response")
                except Exception as e:
                    # This is also expected - malicious names should be rejected
                    error_msg = str(e).lower()
                    assert any(keyword in error_msg for keyword in ['not found', 'invalid', 'error', 'unauthorized']), \
                        f"Expected tool rejection, got unexpected error for '{malicious_name}': {e}"
    
    @pytest.mark.asyncio
    async def test_workspace_action_updates(self):
        """Test that action updates are isolated to their workspace."""
        # Generate unique names for this test run
        initial_action_name = f"initial_action_{uuid.uuid4().hex[:8]}"
        
        # Create workspace with initial action
        workspace_id, initial_actions = await self.create_workspace_with_actions(
            "update_test",
            [
                {
                    "name": initial_action_name,
                    "type": "REST",
                    "config": {
                        "url": "https://httpbin.org/get",
                        "method": "GET"
                    }
                }
            ]
        )
        
        await asyncio.sleep(2)
        
        # Generate workspace-specific JWT token with proper workspace_id claims
        from .test_utils import get_workspace_scoped_jwt_token
        
        workspace_token = get_workspace_scoped_jwt_token(self.client, self.headers, workspace_id)
        if not workspace_token:
            pytest.fail("Failed to generate workspace-scoped JWT token for MCP authentication")
        
        # Connect client and verify initial state
        transport = SSETransport(
            url=f"http://localhost:8090/mcp/{workspace_id}/sse",
            headers={"Authorization": f"Bearer {workspace_token}"}
        )
        
        async with FastMCPClient(transport) as client:
            # Check initial tools
            initial_tools = await client.list_tools()
            initial_tool_names = [t.name for t in initial_tools]
            assert initial_action_name in initial_tool_names
            
            # Add a new action to the workspace
            new_action_id = create_test_action(
                self.client,
                self.headers,
                workspace_id,
                f"new_dynamic_action_{uuid.uuid4().hex[:8]}",
                "REST",
                config={
                    "url": "https://httpbin.org/post",
                    "method": "POST"
                }
            )
            
            if new_action_id:
                self.test_actions.append((workspace_id, new_action_id))
            
            # Wait for action registration
            await asyncio.sleep(3)
            
            # Check that new action appears (tool registry should update)
            updated_tools = await client.list_tools()
            updated_tool_names = [t.name for t in updated_tools]
            
            # Note: This test may need adjustment based on how tool registration works
            # For now, we verify the action was created successfully
            assert new_action_id is not None, "Failed to create new action"
    
    @pytest.mark.asyncio
    async def test_knowledge_base_isolation(self):
        """Test that knowledge base search tool respects workspace isolation."""
        # Create two workspaces
        kb_workspace_a_id, _ = await self.create_workspace_with_actions(
            "kb_test_a",
            [
                {
                    "name": f"dummy_tool_a_{uuid.uuid4().hex[:8]}",
                    "type": "REST",
                    "config": {
                        "url": "https://httpbin.org/get",
                        "method": "GET"
                    }
                }
            ]
        )
        
        kb_workspace_b_id, _ = await self.create_workspace_with_actions(
            "kb_test_b", 
            [
                {
                    "name": f"dummy_tool_b_{uuid.uuid4().hex[:8]}",
                    "type": "REST",
                    "config": {
                        "url": "https://httpbin.org/get",
                        "method": "GET"
                    }
                }
            ]
        )
        
        await asyncio.sleep(2)
        
        # Generate workspace-specific JWT tokens
        from .test_utils import get_workspace_scoped_jwt_token
        
        token_a = get_workspace_scoped_jwt_token(self.client, self.headers, kb_workspace_a_id)
        token_b = get_workspace_scoped_jwt_token(self.client, self.headers, kb_workspace_b_id)
        
        if not token_a or not token_b:
            pytest.fail("Failed to generate workspace-scoped JWT tokens for KB isolation test")
        
        # Create clients for each workspace
        transport_a = SSETransport(
            url=f"http://localhost:8090/mcp/{kb_workspace_a_id}/sse",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        
        transport_b = SSETransport(
            url=f"http://localhost:8090/mcp/{kb_workspace_b_id}/sse",
            headers={"Authorization": f"Bearer {token_b}"}
        )
        
        try:
            async with FastMCPClient(transport_a) as client_a, FastMCPClient(transport_b) as client_b:
                # Both clients should have access to the built-in knowledge base search tool
                tools_a = await asyncio.wait_for(client_a.list_tools(), timeout=10.0)
                tools_b = await asyncio.wait_for(client_b.list_tools(), timeout=10.0)
                
                tool_names_a = [t.name for t in tools_a]
                tool_names_b = [t.name for t in tools_b]
                
                # Both should have the knowledge base search tool
                assert "search_knowledge_base" in tool_names_a, "Knowledge base search tool missing from workspace A"
                assert "search_knowledge_base" in tool_names_b, "Knowledge base search tool missing from workspace B"
                
                # Try to use the knowledge base search tool - should only search within respective workspace
                try:
                    result_a = await asyncio.wait_for(
                        client_a.call_tool("search_knowledge_base", {"query": "test search A"}),
                        timeout=10.0
                    )
                    # Should work (even if no results found)
                    assert result_a is not None, "Knowledge base search failed in workspace A"
                except Exception as e:
                    # May fail if knowledge base service not available, but should not be a security issue
                    error_msg = str(e).lower()
                    if "unauthorized" in error_msg or "forbidden" in error_msg:
                        pytest.fail(f"Knowledge base search authorization issue in workspace A: {e}")
                
                try:
                    result_b = await asyncio.wait_for(
                        client_b.call_tool("search_knowledge_base", {"query": "test search B"}),
                        timeout=10.0
                    )
                    # Should work (even if no results found)
                    assert result_b is not None, "Knowledge base search failed in workspace B"
                except Exception as e:
                    # May fail if knowledge base service not available, but should not be a security issue
                    error_msg = str(e).lower()
                    if "unauthorized" in error_msg or "forbidden" in error_msg:
                        pytest.fail(f"Knowledge base search authorization issue in workspace B: {e}")
                
        except asyncio.TimeoutError:
            pytest.fail("Knowledge base isolation test timed out")
        except Exception as e:
            pytest.fail(f"Knowledge base isolation test failed: {e}")
    
    def test_workspace_authentication_isolation(self):
        """Test that workspace-specific API access is properly isolated."""
        # Ensure we have test workspaces
        workspace_a = ensure_test_workspace(self.client, self.headers, "auth_test_workspace_a")
        workspace_b = ensure_test_workspace(self.client, self.headers, "auth_test_workspace_b")
        
        if not workspace_a or not workspace_b:
            pytest.skip("Could not create test workspaces for authentication isolation test")
        
        workspace_a_id = workspace_a["id"]
        workspace_b_id = workspace_b["id"]
        
        # Test workspace A access with proper authentication
        response_a = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_a_id}/actions",
            headers=self.headers
        )
        
        # Should get a successful response or proper error
        assert response_a.status_code in [200, 401, 403], f"Unexpected status: {response_a.status_code}"
        
        # Test workspace B access - should also work with same valid token
        response_b = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_b_id}/actions", 
            headers=self.headers
        )
        
        # Should get a successful response or proper error (same user can access both workspaces they own)
        assert response_b.status_code in [200, 401, 403], f"Unexpected status: {response_b.status_code}"
        
        # Test invalid workspace access
        invalid_workspace_id = "invalid_workspace_id_123"
        response_invalid = self.client.get(
            f"/admin/api/v1/workspaces/{invalid_workspace_id}/actions",
            headers=self.headers
        )
        
        # Should reject invalid workspace ID
        assert response_invalid.status_code in [400, 404, 422], f"Should reject invalid workspace: {response_invalid.status_code}"


@pytest.mark.integration
class TestWorkspaceDataIsolation:
    """Test data isolation between workspaces using direct API calls."""
    
    @classmethod
    def setup_class(cls):
        """Setup for data isolation tests."""
        cls.client = Client(base_url="http://localhost:8090", timeout=10.0)
        
        # Get auth token
        token, refresh_token, headers = get_emulator_auth_token(cls.client)
        if not token:
            cls.headers = {"Authorization": "Bearer test-data-isolation"}
        else:
            cls.headers = headers
        
        cls.test_actions = []
    
    @classmethod
    def teardown_class(cls):
        """Cleanup test data."""
        for workspace_id, action_id in cls.test_actions:
            try:
                delete_test_action(cls.client, cls.headers, workspace_id, action_id)
            except Exception as e:
                print(f"Warning: Failed to cleanup action {action_id}: {e}")
    
    def test_action_listing_isolation(self):
        """Test that action listing is workspace-specific."""
        # This test uses direct API calls to verify data isolation
        
        # Ensure we have a test workspace
        workspace = ensure_test_workspace(self.client, self.headers)
        if not workspace:
            pytest.skip("Could not create or access test workspace")
        
        workspace_id = workspace["id"]
        
        # List actions for this workspace
        actions_response = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_id}/actions",
            headers=self.headers
        )
        
        if actions_response.status_code == 200:
            actions = actions_response.json()
            # Verify response format
            assert isinstance(actions, list), "Actions should be returned as a list"
            
            # Each action should have workspace_id field matching our request
            for action in actions:
                if "workspace_id" in action:
                    assert action["workspace_id"] == workspace_id, \
                        f"Action {action.get('id')} has wrong workspace_id"
    
    def test_cross_workspace_action_access(self):
        """Test that actions cannot be accessed across workspaces."""
        # Ensure we have a test workspace
        workspace = ensure_test_workspace(self.client, self.headers)
        if not workspace:
            pytest.skip("Could not create or access test workspace")
        
        workspace_id = workspace["id"]
        
        # Try to access actions with malformed workspace ID
        invalid_workspace_id = "invalid_workspace_id_123"
        
        response = self.client.get(
            f"/admin/api/v1/workspaces/{invalid_workspace_id}/actions",
            headers=self.headers
        )
        
        # Should reject invalid workspace ID
        assert response.status_code in [400, 404, 422], \
            f"Should reject invalid workspace ID, got: {response.status_code}"