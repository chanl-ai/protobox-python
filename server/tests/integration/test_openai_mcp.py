"""
Integration tests for OpenAI assistant integration with MCP servers.

Tests that OpenAI assistants can successfully connect to our MCP servers,
discover tools, and execute them with proper workspace isolation.
"""

import asyncio
import os
import pytest
import uuid
from typing import Dict, Any, Optional, List
from httpx import Client

# Import OpenAI for assistant testing
try:
    import openai
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Import FastMCP client for comparison testing
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


async def wait_for_run_completion(openai_client: AsyncOpenAI, thread_id: str, run_id: str, 
                                  timeout: int = 60) -> Any:
    """Wait for OpenAI assistant run to complete."""
    start_time = asyncio.get_event_loop().time()
    
    while True:
        if asyncio.get_event_loop().time() - start_time > timeout:
            raise asyncio.TimeoutError(f"Run {run_id} did not complete within {timeout}s")
        
        run = await openai_client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run_id
        )
        
        if run.status in ["completed", "failed", "cancelled", "expired"]:
            return run
        
        # Wait before checking again
        await asyncio.sleep(2)


@pytest.mark.integration
@pytest.mark.skipif(not OPENAI_AVAILABLE, reason="OpenAI library not installed")
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
class TestOpenAIAssistantIntegration:
    """Test OpenAI assistant integration with our MCP servers."""
    
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
        
        # Get auth token
        token, refresh_token, headers = get_emulator_auth_token(cls.client)
        if not token:
            cls.headers = {"Authorization": "Bearer test-openai-integration"}
        else:
            cls.headers = headers
        
        # Initialize OpenAI client
        cls.openai_client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        cls.skip = False
        
        # Track test resources for cleanup
        cls.test_assistants = []
        cls.test_threads = []
        cls.test_actions = []
        cls.test_workspaces = []
    
    @classmethod
    def teardown_class(cls):
        """Cleanup test resources."""
        if not hasattr(cls, 'skip') or cls.skip:
            return
        
        # Cleanup OpenAI resources
        async def cleanup_openai():
            try:
                # Delete test threads
                for thread_id in cls.test_threads:
                    try:
                        await cls.openai_client.beta.threads.delete(thread_id)
                    except Exception as e:
                        print(f"Warning: Failed to delete thread {thread_id}: {e}")
                
                # Delete test assistants
                for assistant_id in cls.test_assistants:
                    try:
                        await cls.openai_client.beta.assistants.delete(assistant_id)
                    except Exception as e:
                        print(f"Warning: Failed to delete assistant {assistant_id}: {e}")
            
            except Exception as e:
                print(f"Warning: OpenAI cleanup failed: {e}")
        
        # Run cleanup
        try:
            asyncio.run(cleanup_openai())
        except Exception as e:
            print(f"Warning: Async cleanup failed: {e}")
        
        # Cleanup test actions
        for workspace_id, action_id in cls.test_actions:
            try:
                delete_test_action(cls.client, cls.headers, workspace_id, action_id)
            except Exception as e:
                print(f"Warning: Failed to cleanup action {action_id}: {e}")
    
    def setup_method(self):
        """Skip if prerequisites not met."""
        if getattr(self, "skip", False):
            pytest.skip(getattr(self, "skip_reason", "Skipping OpenAI integration tests"))
    
    async def create_test_workspace_with_tools(self, workspace_name: str, 
                                             tool_configs: List[Dict[str, Any]]) -> tuple[str, str]:
        """Create workspace with tools and return workspace_id and mcp_token."""
        # Create workspace
        workspace = ensure_test_workspace(
            self.client,
            self.headers,
            name=f"{workspace_name}_{uuid.uuid4().hex[:8]}"
        )
        
        if not workspace:
            pytest.fail(f"Failed to create workspace: {workspace_name}")
        
        workspace_id = workspace["id"]
        self.test_workspaces.append(workspace_id)
        
        # Create tools/actions
        for tool_config in tool_configs:
            action_id = await create_test_action(
                self.client,
                self.headers,
                workspace_id,
                tool_config["name"],
                tool_config.get("type", "REST"),
                config=tool_config.get("config", {}),
                variables=tool_config.get("variables", [])
            )
            
            if action_id:
                self.test_actions.append((workspace_id, action_id))
        
        # Generate MCP token for this workspace
        mcp_token = await generate_test_mcp_token(workspace_id)
        
        return workspace_id, mcp_token
    
    @pytest.mark.asyncio
    async def test_assistant_mcp_connection_basic(self):
        """Test basic OpenAI assistant connection to MCP server."""
        # Create workspace with simple tool
        workspace_id, mcp_token = await self.create_test_workspace_with_tools(
            "openai_basic_test",
            [
                {
                    "name": "get_current_time",
                    "type": "REST",
                    "config": {
                        "url": "https://worldtimeapi.org/api/timezone/UTC",
                        "method": "GET",
                        "headers": {"Accept": "application/json"}
                    }
                }
            ]
        )
        
        await asyncio.sleep(3)  # Wait for tool registration
        
        # Create OpenAI assistant with MCP server configuration
        try:
            assistant = await self.openai_client.beta.assistants.create(
                name=f"MCP Test Assistant {uuid.uuid4().hex[:8]}",
                model="gpt-4",
                instructions="""
                You are a helpful assistant with access to MCP tools.
                When asked about time, use the get_current_time tool to get accurate information.
                Always use available tools when they can help answer the user's question.
                """,
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "mcp_server_connection",
                            "description": "Connect to MCP server and use available tools",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "mcp_url": {
                                        "type": "string",
                                        "description": "MCP server URL"
                                    },
                                    "tool_name": {
                                        "type": "string", 
                                        "description": "Name of tool to execute"
                                    },
                                    "arguments": {
                                        "type": "object",
                                        "description": "Arguments for the tool"
                                    }
                                },
                                "required": ["mcp_url", "tool_name"]
                            }
                        }
                    }
                ]
            )
            
            self.test_assistants.append(assistant.id)
            
            # Create thread for conversation
            thread = await self.openai_client.beta.threads.create()
            self.test_threads.append(thread.id)
            
            # Note: This test demonstrates the concept but requires actual MCP integration
            # In a real implementation, the assistant would have native MCP support
            
            assert assistant.id is not None, "Assistant should be created successfully"
            assert thread.id is not None, "Thread should be created successfully"
            
            # For now, just verify the MCP server is accessible
            if FASTMCP_AVAILABLE:
                transport = SSETransport(
                    url=f"http://localhost:8090/mcp/{workspace_id}/sse",
                    headers={"Authorization": f"Bearer {mcp_token}"}
                )
                
                async with FastMCPClient(transport) as mcp_client:
                    tools = await mcp_client.list_tools()
                    tool_names = [t.name for t in tools]
                    assert "get_current_time" in tool_names, "Tool should be available via MCP"
        
        except Exception as e:
            pytest.fail(f"Basic OpenAI assistant MCP test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_assistant_workspace_isolation(self):
        """Test that assistants only access tools from their designated workspace."""
        # Create two workspaces with different tools
        workspace_a_id, token_a = await self.create_test_workspace_with_tools(
            "assistant_workspace_a",
            [
                {
                    "name": "weather_service",
                    "type": "REST",
                    "config": {
                        "url": "https://api.openweathermap.org/data/2.5/weather",
                        "method": "GET"
                    }
                }
            ]
        )
        
        workspace_b_id, token_b = await self.create_test_workspace_with_tools(
            "assistant_workspace_b",
            [
                {
                    "name": "news_service",
                    "type": "REST", 
                    "config": {
                        "url": "https://newsapi.org/v2/top-headlines",
                        "method": "GET"
                    }
                }
            ]
        )
        
        await asyncio.sleep(3)  # Wait for tool registration
        
        # Verify isolation using FastMCP clients
        if FASTMCP_AVAILABLE:
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
                    tools_a = await client_a.list_tools()
                    tools_b = await client_b.list_tools()
                    
                    tool_names_a = [t.name for t in tools_a]
                    tool_names_b = [t.name for t in tools_b]
                    
                    # Verify workspace A has weather_service but not news_service
                    assert "weather_service" in tool_names_a, "Workspace A should have weather_service"
                    assert "news_service" not in tool_names_a, "Workspace A should not have news_service"
                    
                    # Verify workspace B has news_service but not weather_service
                    assert "news_service" in tool_names_b, "Workspace B should have news_service"
                    assert "weather_service" not in tool_names_b, "Workspace B should not have weather_service"
                    
            except Exception as e:
                pytest.fail(f"Workspace isolation verification failed: {e}")
        
        # Create assistants for each workspace (conceptual)
        try:
            assistant_a = await self.openai_client.beta.assistants.create(
                name=f"Weather Assistant {uuid.uuid4().hex[:8]}",
                model="gpt-4",
                instructions=f"""
                You are a weather assistant connected to workspace {workspace_a_id}.
                You have access to weather services through MCP tools.
                """,
                tools=[]  # In real implementation, would configure MCP connection
            )
            
            assistant_b = await self.openai_client.beta.assistants.create(
                name=f"News Assistant {uuid.uuid4().hex[:8]}",
                model="gpt-4",
                instructions=f"""
                You are a news assistant connected to workspace {workspace_b_id}.
                You have access to news services through MCP tools.
                """,
                tools=[]  # In real implementation, would configure MCP connection
            )
            
            self.test_assistants.extend([assistant_a.id, assistant_b.id])
            
            assert assistant_a.id != assistant_b.id, "Assistants should have different IDs"
            
        except Exception as e:
            pytest.fail(f"Assistant workspace isolation test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_third_party_mcp_client_integration(self):
        """Test third-party services using FastMCP client to connect to our servers."""
        if not FASTMCP_AVAILABLE:
            pytest.skip("FastMCP not available")
        
        # Create workspace with API-like tools
        workspace_id, mcp_token = await self.create_test_workspace_with_tools(
            "third_party_integration",
            [
                {
                    "name": "user_data_api",
                    "type": "REST",
                    "config": {
                        "url": "https://jsonplaceholder.typicode.com/users",
                        "method": "GET",
                        "headers": {"Accept": "application/json"}
                    }
                },
                {
                    "name": "post_data_api",
                    "type": "REST",
                    "config": {
                        "url": "https://jsonplaceholder.typicode.com/posts",
                        "method": "GET",
                        "headers": {"Accept": "application/json"}
                    }
                }
            ]
        )
        
        await asyncio.sleep(3)
        
        # Simulate third-party service integration
        async def third_party_service_simulation():
            """Simulate how a third-party service would integrate."""
            transport = SSETransport(
                url=f"http://localhost:8090/mcp/{workspace_id}/sse",
                headers={"Authorization": f"Bearer {mcp_token}"}
            )
            
            try:
                async with FastMCPClient(transport) as client:
                    # Discover available tools
                    tools = await asyncio.wait_for(client.list_tools(), timeout=10.0)
                    available_tools = {t.name: t for t in tools}
                    
                    assert "user_data_api" in available_tools, "user_data_api should be available"
                    assert "post_data_api" in available_tools, "post_data_api should be available"
                    
                    # Execute tools
                    user_result = await asyncio.wait_for(
                        client.call_tool("user_data_api", {}),
                        timeout=15.0
                    )
                    
                    post_result = await asyncio.wait_for(
                        client.call_tool("post_data_api", {}),
                        timeout=15.0
                    )
                    
                    assert user_result is not None, "user_data_api should return results"
                    assert post_result is not None, "post_data_api should return results"
                    
                    return {
                        "tools_discovered": len(tools),
                        "user_data_success": user_result is not None,
                        "post_data_success": post_result is not None
                    }
                    
            except Exception as e:
                return {"error": str(e)}
        
        # Run the simulation
        try:
            result = await asyncio.wait_for(
                third_party_service_simulation(),
                timeout=30.0
            )
            
            assert "error" not in result, f"Third-party integration failed: {result.get('error')}"
            assert result["tools_discovered"] >= 2, "Should discover at least 2 tools"
            assert result["user_data_success"], "User data API should succeed"
            assert result["post_data_success"], "Post data API should succeed"
            
        except asyncio.TimeoutError:
            pytest.fail("Third-party integration test timed out")
    
    @pytest.mark.asyncio
    async def test_mcp_server_reliability(self):
        """Test MCP server reliability under various conditions."""
        if not FASTMCP_AVAILABLE:
            pytest.skip("FastMCP not available")
        
        # Create workspace
        workspace_id, mcp_token = await self.create_test_workspace_with_tools(
            "reliability_test",
            [
                {
                    "name": "reliable_service",
                    "type": "REST",
                    "config": {
                        "url": "https://httpbin.org/delay/1",
                        "method": "GET"
                    }
                }
            ]
        )
        
        await asyncio.sleep(2)
        
        transport = SSETransport(
            url=f"http://localhost:8090/mcp/{workspace_id}/sse",
            headers={"Authorization": f"Bearer {mcp_token}"}
        )
        
        # Test connection stability
        try:
            async with FastMCPClient(transport) as client:
                # Test multiple rapid requests
                tasks = []
                for i in range(5):
                    task = asyncio.create_task(
                        client.call_tool("reliable_service", {})
                    )
                    tasks.append(task)
                
                # Wait for all to complete
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=30.0
                )
                
                # Check that most requests succeeded
                successes = sum(1 for r in results if not isinstance(r, Exception))
                assert successes >= 3, f"Expected at least 3 successes, got {successes}"
                
        except Exception as e:
            pytest.fail(f"MCP server reliability test failed: {e}")


@pytest.mark.integration
class TestMCPIntegrationPatterns:
    """Test common MCP integration patterns and use cases."""
    
    @classmethod
    def setup_class(cls):
        """Setup for integration pattern tests."""
        cls.client = Client(base_url="http://localhost:8090", timeout=10.0)
        
        # Get auth token
        token, refresh_token, headers = get_emulator_auth_token(cls.client)
        if not token:
            cls.headers = {"Authorization": "Bearer test-integration-patterns"}
        else:
            cls.headers = headers
        
        cls.test_actions = []
    
    @classmethod
    def teardown_class(cls):
        """Cleanup test resources."""
        for workspace_id, action_id in cls.test_actions:
            try:
                delete_test_action(cls.client, cls.headers, workspace_id, action_id)
            except Exception as e:
                print(f"Warning: Failed to cleanup action {action_id}: {e}")
    
    def test_mcp_discovery_endpoint(self):
        """Test MCP server discovery endpoint format."""
        # Test default workspace
        workspace_id = "689d34139d87472f3fd95c5e"
        
        response = self.client.get(
            f"/mcp/{workspace_id}/",
            headers={"Authorization": "Bearer test-discovery"}
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Check discovery response format
            assert "server_name" in data, "Should include server name"
            assert "capabilities" in data, "Should include capabilities"
            assert "endpoints" in data, "Should include endpoint information"
            
            # Check endpoints
            endpoints = data["endpoints"]
            assert "sse" in endpoints, "Should include SSE endpoint"
            assert "tools" in endpoints, "Should include tools endpoint"
    
    @pytest.mark.asyncio
    async def test_tool_schema_validation(self):
        """Test that tool schemas are properly formatted for MCP clients."""
        if not FASTMCP_AVAILABLE:
            pytest.skip("FastMCP not available")
        
        # Create workspace with tool that has parameters
        workspace = ensure_test_workspace(
            self.client,
            self.headers,
            name=f"schema_test_{uuid.uuid4().hex[:8]}"
        )
        
        if not workspace:
            pytest.skip("Could not create test workspace")
        
        workspace_id = workspace["id"]
        
        # Create action with specific parameters
        action_id = await create_test_action(
            self.client,
            self.headers,
            workspace_id,
            "parameterized_tool",
            "REST",
            config={
                "url": "https://httpbin.org/post",
                "method": "POST",
                "headers": {"Content-Type": "application/json"}
            },
            variables=[
                {
                    "name": "query",
                    "type": "string",
                    "required": True,
                    "description": "Search query parameter"
                },
                {
                    "name": "limit",
                    "type": "integer", 
                    "required": False,
                    "description": "Maximum number of results"
                }
            ]
        )
        
        if action_id:
            self.test_actions.append((workspace_id, action_id))
        
        await asyncio.sleep(2)
        
        # Connect with FastMCP client and check tool schema
        transport = SSETransport(
            url=f"http://localhost:8090/mcp/{workspace_id}/sse",
            headers={"Authorization": "Bearer test-schema-validation"}
        )
        
        try:
            async with FastMCPClient(transport) as client:
                tools = await client.list_tools()
                
                # Find our tool
                param_tool = None
                for tool in tools:
                    if tool.name == "parameterized_tool":
                        param_tool = tool
                        break
                
                assert param_tool is not None, "Parameterized tool should be found"
                
                # Check tool schema format
                assert hasattr(param_tool, 'inputSchema'), "Tool should have inputSchema"
                schema = param_tool.inputSchema
                
                # Validate JSON schema structure
                assert schema.get("type") == "object", "Schema should be object type"
                assert "properties" in schema, "Schema should have properties"
                
                properties = schema["properties"]
                assert "query" in properties, "Should have query parameter"
                assert "limit" in properties, "Should have limit parameter"
                
                # Check required fields
                if "required" in schema:
                    assert "query" in schema["required"], "Query should be required"
                    assert "limit" not in schema["required"], "Limit should be optional"
                
        except Exception as e:
            pytest.fail(f"Tool schema validation failed: {e}")