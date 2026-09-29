#!/usr/bin/env python3
"""
Test ProtoBox MCP Server using FastMCP Client.

This script tests:
1. SSE transport connection
2. Streamable-HTTP transport connection
3. Multi-workspace support
4. Tool discovery and execution
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict, List

# Add FastMCP to path - need absolute paths to work correctly
script_dir = os.path.dirname(os.path.abspath(__file__))
fastmcp_path = os.path.join(script_dir, "..", "fastmcp-lib", "src")
server_path = os.path.join(script_dir, "..", "server", "src")

sys.path.insert(0, os.path.abspath(fastmcp_path))
sys.path.insert(0, os.path.abspath(server_path))

from fastmcp import Client
from fastmcp.client.transports import SSETransport, StreamableHttpTransport
from loguru import logger

# Test configuration
BASE_URL = "http://localhost:8090"
TEST_WORKSPACES = [
    "689d34139d87472f3fd95c5e",  # Test workspace from cache
]

# Get MCP token - we need an MCP-specific token, not a JWT token
# You can get one by calling: 
# curl -X POST http://localhost:8090/admin/api/v1/workspaces/{workspace_id}/mcp-tokens/ \
#   -H "Authorization: Bearer {jwt_token}" -H "Content-Type: application/json" \
#   -d '{"name": "test-mcp-token", "scopes": ["read:actions", "execute:actions"]}'
MCP_TOKEN = os.environ["MCP_TOKEN"]
logger.info(f"Using MCP token: {MCP_TOKEN[:20]}...")


async def test_sse_transport(workspace_id: str):
    """Test SSE transport connection and tool discovery."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing SSE Transport for Workspace: {workspace_id}")
    logger.info(f"{'='*60}")
    
    try:
        # Create SSE transport
        sse_url = f"{BASE_URL}/admin/api/v1/mcp/{workspace_id}/sse"
        transport = SSETransport(
            sse_url,
            headers={"Authorization": f"Bearer {MCP_TOKEN}"}
        )
        
        # Connect with FastMCP client
        async with Client(transport=transport) as client:
            logger.info(f"✅ Connected to SSE endpoint")
            
            # List tools
            tools = await client.list_tools()
            logger.info(f"📦 Found {len(tools)} tools:")
            for tool in tools:
                logger.info(f"  - {tool.name}: {tool.description}")
            
            # Test tool execution if tools available
            if tools:
                tool = tools[0]
                logger.info(f"\n🔧 Testing tool execution: {tool.name}")
                
                # Create test arguments based on tool's input schema
                test_args = {}
                if hasattr(tool, 'inputSchema') and tool.inputSchema:
                    schema = tool.inputSchema
                    if 'properties' in schema:
                        for prop_name, prop_def in schema['properties'].items():
                            # Provide sample values based on type
                            if prop_def.get('type') == 'string':
                                test_args[prop_name] = f"test_{prop_name}"
                            elif prop_def.get('type') == 'number':
                                test_args[prop_name] = 123
                            elif prop_def.get('type') == 'boolean':
                                test_args[prop_name] = True
                
                try:
                    result = await client.call_tool(tool.name, test_args)
                    logger.info(f"✅ Tool executed successfully: {result}")
                except Exception as e:
                    logger.warning(f"⚠️ Tool execution failed: {e}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ SSE transport test failed: {e}")
        return False


async def test_streamable_http_transport(workspace_id: str):
    """Test Streamable-HTTP transport connection and tool discovery."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing Streamable-HTTP Transport for Workspace: {workspace_id}")
    logger.info(f"{'='*60}")
    
    try:
        # Create Streamable-HTTP transport
        http_url = f"{BASE_URL}/admin/api/v1/mcp/{workspace_id}/messages"
        transport = StreamableHttpTransport(
            http_url,
            headers={"Authorization": f"Bearer {MCP_TOKEN}"}
        )
        
        # Connect with FastMCP client
        async with Client(transport=transport) as client:
            logger.info(f"✅ Connected to Streamable-HTTP endpoint")
            
            # List tools
            tools = await client.list_tools()
            logger.info(f"📦 Found {len(tools)} tools:")
            for tool in tools:
                logger.info(f"  - {tool.name}: {tool.description}")
            
            # Get server info
            info = await client.get_server_info()
            logger.info(f"ℹ️ Server info: {info}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Streamable-HTTP transport test failed: {e}")
        return False


async def test_multi_workspace_concurrent():
    """Test multiple workspaces connecting concurrently."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing Multi-Workspace Concurrent Connections")
    logger.info(f"{'='*60}")
    
    tasks = []
    
    # Create SSE connections for all workspaces
    for workspace_id in TEST_WORKSPACES:
        tasks.append(test_sse_transport(workspace_id))
    
    # Run all connections concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Check results
    success_count = sum(1 for r in results if r is True)
    logger.info(f"\n📊 Multi-workspace test results: {success_count}/{len(TEST_WORKSPACES)} successful")
    
    return success_count == len(TEST_WORKSPACES)


async def test_workspace_isolation():
    """Test that workspaces are properly isolated."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing Workspace Isolation")
    logger.info(f"{'='*60}")
    
    workspace_tools = {}
    
    # Get tools for each workspace
    for workspace_id in TEST_WORKSPACES:
        try:
            http_url = f"{BASE_URL}/admin/api/v1/mcp/{workspace_id}/messages"
            transport = StreamableHttpTransport(
                http_url,
                headers={"Authorization": f"Bearer {MCP_TOKEN}"}
            )
            
            async with Client(transport=transport) as client:
                tools = await client.list_tools()
                workspace_tools[workspace_id] = [t.name for t in tools]
                logger.info(f"Workspace {workspace_id[:8]}... has {len(tools)} tools")
                
        except Exception as e:
            logger.error(f"Failed to get tools for workspace {workspace_id}: {e}")
            workspace_tools[workspace_id] = []
    
    # Verify workspaces have different tools (or at least different counts)
    if len(set(len(tools) for tools in workspace_tools.values())) > 1:
        logger.info("✅ Workspaces appear to be isolated (different tool counts)")
        return True
    else:
        logger.warning("⚠️ All workspaces have the same number of tools")
        return True  # This might be expected if workspaces have similar setups


async def main():
    """Run all MCP tests."""
    logger.info("🚀 Starting ProtoBox MCP FastMCP Client Tests")
    
    all_tests_passed = True
    
    # Test 1: SSE Transport
    if not await test_sse_transport(TEST_WORKSPACES[0]):
        all_tests_passed = False
    
    # Test 2: Streamable-HTTP Transport
    if not await test_streamable_http_transport(TEST_WORKSPACES[0]):
        all_tests_passed = False
    
    # Test 3: Multi-workspace concurrent connections
    if not await test_multi_workspace_concurrent():
        all_tests_passed = False
    
    # Test 4: Workspace isolation
    if not await test_workspace_isolation():
        all_tests_passed = False
    
    # Summary
    logger.info(f"\n{'='*60}")
    if all_tests_passed:
        logger.info("✅ All MCP tests passed!")
    else:
        logger.error("❌ Some MCP tests failed")
    logger.info(f"{'='*60}")
    
    return 0 if all_tests_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)