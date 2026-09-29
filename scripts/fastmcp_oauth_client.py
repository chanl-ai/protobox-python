#!/usr/bin/env python3
"""
Standalone FastMCP client with OAuth authentication for ProtoBox MCP server.

This demonstrates how to use FastMCP's OAuth flow with ProtoBox.
"""

import asyncio
from pathlib import Path

# FastMCP imports
from fastmcp import Client
from fastmcp.client.auth import OAuth


async def main():
    """Main function demonstrating FastMCP OAuth client."""
    
    # ProtoBox MCP server URL
    # In production, this would be your actual server URL
    MCP_SERVER_URL = "http://localhost:8090/mcp"
    
    print("🚀 FastMCP OAuth Client for ProtoBox")
    print("="*50)
    
    # Create OAuth instance for ProtoBox MCP server
    # FastMCP will handle:
    # 1. Dynamic client registration (if supported)
    # 2. Opening browser for authorization
    # 3. Handling redirect and code exchange
    # 4. Storing and refreshing tokens
    oauth = OAuth(
        mcp_url=MCP_SERVER_URL,
        scopes=["mcp:read", "mcp:execute", "mcp:write"],
        client_name="FastMCP Desktop Client",
        token_storage_cache_dir=Path.home() / ".protobox" / "oauth-tokens"
    )
    
    print(f"📍 Connecting to MCP server: {MCP_SERVER_URL}")
    print(f"🔐 Using OAuth authentication")
    print(f"📂 Token cache: {oauth.token_storage_cache_dir}")
    print()
    
    try:
        # Create FastMCP client with OAuth authentication
        async with Client(MCP_SERVER_URL, auth=oauth) as client:
            print("✅ Successfully connected with OAuth!")
            print()
            
            # Test 1: Ping the server
            print("📡 Testing connection...")
            try:
                await client.ping()
                print("✅ Server is responsive")
            except Exception as e:
                print(f"⚠️  Ping failed: {e}")
            
            # Test 2: List available tools
            print("\n📋 Listing available tools...")
            try:
                tools = await client.list_tools()
                print(f"✅ Found {len(tools)} tools:")
                
                for tool in tools[:5]:  # Show first 5 tools
                    tool_name = getattr(tool, 'name', str(tool))
                    tool_desc = getattr(tool, 'description', '')[:50] if hasattr(tool, 'description') else ''
                    print(f"   • {tool_name}: {tool_desc}")
                
                if len(tools) > 5:
                    print(f"   ... and {len(tools) - 5} more tools")
                    
            except Exception as e:
                print(f"❌ Failed to list tools: {e}")
            
            # Test 3: List resources (if available)
            print("\n📚 Listing available resources...")
            try:
                resources = await client.list_resources()
                if resources:
                    print(f"✅ Found {len(resources)} resources")
                    for resource in resources[:3]:
                        print(f"   • {resource}")
                else:
                    print("   No resources available")
            except Exception as e:
                print(f"⚠️  Resources not available: {e}")
            
            # Test 4: Execute a simple tool (if available)
            print("\n⚡ Testing tool execution...")
            if tools:
                # Try to find a safe read-only tool to test
                safe_tools = [
                    "admin_get_workspace_info",
                    "admin_list_actions", 
                    "get_workspace_settings",
                    "list_knowledge_base"
                ]
                
                test_tool = None
                for safe_tool in safe_tools:
                    if any(getattr(t, 'name', '') == safe_tool for t in tools):
                        test_tool = safe_tool
                        break
                
                if test_tool:
                    try:
                        print(f"   Executing '{test_tool}'...")
                        result = await client.call_tool(test_tool, {})
                        print(f"✅ Tool executed successfully")
                        if result:
                            print(f"   Result preview: {str(result)[:100]}...")
                    except Exception as e:
                        print(f"⚠️  Tool execution failed: {e}")
                else:
                    print("   No safe test tools available")
            
            print("\n" + "="*50)
            print("🎉 FastMCP OAuth client test complete!")
            print("="*50)
            
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print("\n💡 Troubleshooting tips:")
        print("   1. Make sure the ProtoBox server is running")
        print("   2. Check that OAuth is properly configured")
        print("   3. Try clearing token cache if authentication fails")
        print(f"   4. Token cache location: {oauth.token_storage_cache_dir}")


async def test_manual_oauth_flow():
    """
    Alternative: Manual OAuth flow for testing without browser.
    This shows how to use FastMCP with a pre-obtained OAuth token.
    """
    
    from fastmcp.client import SSETransport
    
    print("\n🔧 Manual OAuth Token Test")
    print("="*50)
    
    # If you already have an OAuth token (from our test scripts)
    OAUTH_TOKEN = input("Enter your OAuth token (or press Enter to skip): ").strip()
    
    if not OAUTH_TOKEN:
        print("Skipping manual token test")
        return
    
    WORKSPACE_ID = input("Enter your workspace ID: ").strip()
    
    # Create SSE transport with OAuth bearer token
    transport = SSETransport(
        url=f"http://localhost:8090/mcp/{WORKSPACE_ID}/sse",
        headers={"Authorization": f"Bearer {OAUTH_TOKEN}"}
    )
    
    try:
        async with Client(transport) as client:
            print("✅ Connected with manual OAuth token!")
            
            # List tools
            tools = await client.list_tools()
            print(f"✅ Found {len(tools)} tools")
            
            # Show tool names
            for tool in tools[:3]:
                print(f"   • {getattr(tool, 'name', str(tool))}")
                
    except Exception as e:
        print(f"❌ Failed with manual token: {e}")


if __name__ == "__main__":
    import sys
    
    print("FastMCP OAuth Client Demo")
    print("Choose mode:")
    print("  1. Automatic OAuth flow (opens browser)")
    print("  2. Manual token (for testing)")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "2":
        asyncio.run(test_manual_oauth_flow())
    else:
        asyncio.run(main())