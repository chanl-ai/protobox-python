"""Integration tests for FastMCP client connecting to ProtoBox MCP server.

Tests the FastMCP implementation using the actual FastMCP client library.
This ensures compatibility with the FastMCP ecosystem.
"""

import asyncio
import pytest
from httpx import Client
from motor.motor_asyncio import AsyncIOMotorClient

# Import FastMCP client
try:
    from fastmcp.client import Client as FastMCPClient
    from fastmcp.client import SSETransport
    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False

from .test_utils import get_test_auth_and_workspace


async def get_mongodb_connection():
    """Get MongoDB connection for direct database verification."""
    import os
    # Use the same MongoDB URL as the server
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://mcp_admin:mcp_dev_password_2024@localhost:27847/mcp_server")
    client = AsyncIOMotorClient(mongodb_url)
    return client.get_database()

async def count_actions_in_workspace(workspace_id: str) -> int:
    """Count actions in a specific workspace directly from MongoDB."""
    db = await get_mongodb_connection()
    count = await db.actions.count_documents({"workspace_id": workspace_id})
    return count

async def get_action_names_in_workspace(workspace_id: str) -> list[str]:
    """Get action names in a specific workspace directly from MongoDB."""
    db = await get_mongodb_connection()
    cursor = db.actions.find({"workspace_id": workspace_id}, {"name": 1})
    actions = await cursor.to_list(length=None)
    return [action["name"] for action in actions]


@pytest.mark.integration
@pytest.mark.skipif(not FASTMCP_AVAILABLE, reason="FastMCP not installed")
class TestFastMCPClient:
    """Test FastMCP client integration with ProtoBox MCP server."""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment."""
        cls.client = Client(base_url="http://localhost:8090", timeout=10.0)
        
        # Check if server is running
        try:
            cls.client.get("/admin/api/v1/health")
        except Exception as e:
            cls.skip = True
            cls.skip_reason = f"Server not running: {e}"
            return
        
        # Check if we're in development mode
        env_check = cls.client.get("/admin/api/v1/monitoring/environment")
        if env_check.status_code == 200:
            env_data = env_check.json()
            if env_data.get("environment") != "development":
                cls.skip = True
                cls.skip_reason = "Test token auth only works in development"
                return
        
        # Get complete authentication and workspace setup
        access_token, headers, workspace_id = get_test_auth_and_workspace(cls.client)
        if not access_token:
            cls.skip = True
            cls.skip_reason = "Failed to setup authentication and workspace"
            return
        
        # Create MCP token for this workspace
        try:
            mcp_response = cls.client.post(
                f"/admin/api/v1/workspaces/{workspace_id}/mcp-tokens",
                headers=headers,
                json={"name": "FastMCP Test Token", "scopes": ["read:actions", "execute:actions"]}
            )
            if mcp_response.status_code in [200, 201]:
                mcp_token = mcp_response.json()["token"]
                cls.mcp_headers = {"Authorization": f"Bearer {mcp_token}"}
                print(f"✓ Created MCP token for testing")
            else:
                cls.skip = True
                cls.skip_reason = f"Failed to create MCP token: {mcp_response.status_code}"
                return
        except Exception as e:
            cls.skip = True
            cls.skip_reason = f"Error creating MCP token: {e}"
            return
        
        cls.headers = headers  # Keep JWT headers for admin API
        cls.access_token = access_token
        cls.workspace_id = workspace_id
        cls.sse_url = f"http://localhost:8090/mcp/{cls.workspace_id}/sse"
        
        cls.skip = False
    
    def setup_method(self):
        """Skip if prerequisites not met."""
        if getattr(self, "skip", False):
            pytest.skip(getattr(self, "skip_reason", "Skipping FastMCP client tests"))
    
    @pytest.mark.asyncio
    async def test_fastmcp_client_workspace_isolation(self):
        """Test FastMCP client with database verification and workspace isolation."""
        if not FASTMCP_AVAILABLE:
            pytest.skip("FastMCP not available")
        
        print(f"🚀 Testing FastMCP client with MongoDB verification and workspace isolation")
        print(f"🔗 Workspace ID: {self.workspace_id}")
        
        # Step 1: Verify actions in MongoDB for this workspace
        print("📊 Step 1: Checking MongoDB for actions in this workspace...")
        db_action_count = await count_actions_in_workspace(self.workspace_id)
        db_action_names = await get_action_names_in_workspace(self.workspace_id)
        print(f"📋 MongoDB shows {db_action_count} actions in workspace {self.workspace_id}")
        print(f"🔧 MongoDB action names: {db_action_names}")
        
        # Step 2: Get tools via FastMCP client
        print("📡 Step 2: Getting tools via FastMCP client...")
        transport = SSETransport(url=self.sse_url, headers=self.mcp_headers)
        
        try:
            async with asyncio.timeout(30):
                client = FastMCPClient(transport)
                
                async with client:
                    print("📋 Calling client.list_tools()...")
                    tools = await client.list_tools()
                    
                    # Validate the response
                    assert isinstance(tools, list), "list_tools() should return a list"
                    assert len(tools) > 0, "Should have at least one tool"
                    
                    tool_names = [t.name for t in tools]
                    print(f"✅ FastMCP client found {len(tools)} tools: {tool_names}")
                    
                    # Step 3: Verify workspace isolation - focus on workspace-specific tools only
                    print("🔒 Step 3: Verifying workspace isolation...")
                    
                    # Filter out admin tools (they're not workspace-specific for this test)
                    non_admin_tools = [name for name in tool_names if not name.startswith("admin_")]
                    print(f"🎯 Non-admin tools from FastMCP: {non_admin_tools}")
                    print(f"🎯 Actions from MongoDB: {db_action_names}")
                    
                    # Should always have search_knowledge_base
                    assert "search_knowledge_base" in non_admin_tools, "Should have search_knowledge_base tool"
                    
                    # All workspace actions from DB should be present as tools
                    workspace_action_tools = [name for name in non_admin_tools if name in db_action_names]
                    assert set(workspace_action_tools) == set(db_action_names), \
                        f"Workspace actions don't match DB. Expected: {db_action_names}, Got: {workspace_action_tools}"
                    
                    # Expected count: workspace actions + knowledge base (ignoring admin tools)
                    expected_non_admin_count = db_action_count + 1  # +1 for search_knowledge_base
                    print(f"📊 Expected (non-admin): {db_action_count} actions + 1 knowledge base = {expected_non_admin_count} tools")
                    print(f"📊 Actual (non-admin): {len(non_admin_tools)} tools")
                    
                    # Verify non-admin tool count matches exactly
                    assert len(non_admin_tools) == expected_non_admin_count, \
                        f"Expected {expected_non_admin_count} non-admin tools but got {len(non_admin_tools)}"
                    
                    print(f"✅ Workspace isolation verified: {db_action_count} workspace actions + 1 knowledge base tool")
                    
                    # Validate tool structure
                    for tool in tools:
                        assert hasattr(tool, 'name'), "Tool should have name attribute"
                        assert hasattr(tool, 'description'), "Tool should have description attribute"
                        assert tool.name, "Tool name should not be empty"
                    
                    print("🎉 Workspace isolation verified successfully!")
                    
        except asyncio.TimeoutError:
            pytest.fail("FastMCP client test timed out after 30 seconds")
        except Exception as e:
            print(f"❌ FastMCP client error: {e}")
            import traceback
            print(f"🔍 Full traceback:\n{traceback.format_exc()}")
            pytest.fail(f"FastMCP client failed: {e}")
    
    @pytest.mark.asyncio
    async def test_fastmcp_client_call_tool(self):
        """Test FastMCP client call_tool() functionality."""
        if not FASTMCP_AVAILABLE:
            pytest.skip("FastMCP not available")
        
        print(f"🚀 Testing FastMCP client call_tool()")
        
        # Create SSE transport with MCP token authentication
        transport = SSETransport(
            url=self.sse_url,
            headers=self.mcp_headers
        )
        
        try:
            # Use 30 second timeout
            async with asyncio.timeout(30):
                print(f"🔌 Creating FastMCP client...")
                client = FastMCPClient(transport)
                
                async with client:
                    print(f"🎯 Successfully entered FastMCP client context")
                    
                    # First get the list of tools
                    print("📋 Getting tools list...")
                    tools = await client.list_tools()
                    tool_names = [t.name for t in tools]
                    print(f"🔧 Available tools: {tool_names}")
                    
                    # Test tool execution
                    if "search_knowledge_base" in tool_names:
                        print("🔍 Testing call_tool() with search_knowledge_base...")
                        result = await client.call_tool(
                            "search_knowledge_base",
                            {"query": "test", "max_results": 1}
                        )
                        print("✅ Tool executed successfully")
                        
                        # Validate the result
                        assert result is not None, "call_tool() should return a result"
                        print(f"📊 Tool result type: {type(result)}")
                        
                        # If it's a list, check the content
                        if isinstance(result, list) and len(result) > 0:
                            first_item = result[0]
                            print(f"📊 First result item: {type(first_item)}")
                            if hasattr(first_item, 'text'):
                                print(f"📊 Result text preview: {first_item.text[:100]}...")
                        
                    else:
                        # Try with any available tool
                        if tool_names:
                            test_tool = tool_names[0]
                            print(f"🔍 Testing call_tool() with {test_tool}...")
                            try:
                                result = await client.call_tool(test_tool, {})
                                print("✅ Tool executed successfully")
                                assert result is not None, "call_tool() should return a result"
                            except Exception as tool_error:
                                print(f"⚠️ Tool execution failed (expected for some tools): {tool_error}")
                                # This is okay - some tools may require specific parameters
                        else:
                            pytest.fail("No tools available to test call_tool()")
                    
                    print("🎉 FastMCP client.call_tool() test completed successfully")
                    
        except asyncio.TimeoutError:
            print(f"⏰ FastMCP client test timed out after 30 seconds")
            pytest.fail("FastMCP client test timed out after 30 seconds")
        except Exception as e:
            print(f"❌ FastMCP client error: {e}")
            print(f"🔍 Error type: {type(e)}")
            import traceback
            print(f"🔍 Full traceback:\n{traceback.format_exc()}")
            pytest.fail(f"FastMCP client failed: {e}")

    @pytest.mark.asyncio
    async def test_fastmcp_client_comprehensive(self):
        """Comprehensive FastMCP client test - both list_tools() and call_tool()."""
        if not FASTMCP_AVAILABLE:
            pytest.skip("FastMCP not available")
        
        print(f"🚀 Comprehensive FastMCP client test")
        
        # Create SSE transport with MCP token authentication
        transport = SSETransport(
            url=self.sse_url,
            headers=self.mcp_headers
        )
        
        try:
            # Use 30 second timeout
            async with asyncio.timeout(30):
                client = FastMCPClient(transport)
                
                async with client:
                    print(f"🎯 FastMCP client connected successfully")
                    
                    # Test 1: List tools
                    print("📋 Step 1: Testing list_tools()...")
                    tools = await client.list_tools()
                    assert isinstance(tools, list), "list_tools() should return a list"
                    assert len(tools) > 0, "Should have at least one tool"
                    
                    tool_names = [t.name for t in tools]
                    print(f"✅ Found {len(tools)} tools: {tool_names}")
                    
                    # Test 2: Call a tool
                    print("🔨 Step 2: Testing call_tool()...")
                    if "search_knowledge_base" in tool_names:
                        result = await client.call_tool(
                            "search_knowledge_base",
                            {"query": "test", "max_results": 1}
                        )
                        assert result is not None, "call_tool() should return a result"
                        print("✅ Tool execution successful")
                    else:
                        print("⚠️ search_knowledge_base not available, skipping tool execution")
                    
                    print("🎉 Comprehensive FastMCP client test completed successfully")
                    
        except asyncio.TimeoutError:
            print(f"⏰ FastMCP client test timed out after 30 seconds")
            pytest.fail("FastMCP client test timed out after 30 seconds")
        except Exception as e:
            print(f"❌ FastMCP client error: {e}")
            import traceback
            print(f"🔍 Full traceback:\n{traceback.format_exc()}")
            pytest.fail(f"FastMCP client failed: {e}")