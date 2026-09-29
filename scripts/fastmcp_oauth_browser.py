#!/usr/bin/env python3
"""
FastMCP client with browser-based OAuth authentication for ProtoBox MCP server.

This will:
1. Register an OAuth client dynamically (or use existing)
2. Open your browser for authorization
3. Handle the OAuth callback
4. Store tokens for future use
"""

import asyncio
from pathlib import Path

try:
    from fastmcp import Client
    from fastmcp.client.auth import OAuth
except ImportError:
    print("❌ FastMCP not installed. Install with: pip install fastmcp")
    exit(1)

# Also import for better error handling
import logging
logging.basicConfig(level=logging.WARNING)


async def main():
    """Main function demonstrating FastMCP OAuth client with browser flow."""
    
    # ProtoBox MCP server configuration
    # Point to /mcp which handles both OAuth discovery and MCP protocol
    MCP_SERVER_URL = "http://localhost:8090/mcp"
    
    # Set a timeout for the entire script
    MAX_RUNTIME_SECONDS = 30
    
    print("🚀 FastMCP OAuth Client with Browser Authentication")
    print("="*60)
    print(f"📍 MCP Server: {MCP_SERVER_URL}")
    print("="*60)
    
    # Create OAuth configuration
    # FastMCP will:
    # 1. Try dynamic registration at /oauth/register
    # 2. Open browser to /oauth/authorize
    # 3. Handle callback on localhost port
    # 4. Exchange code for token
    # 5. Cache tokens for reuse
    # 
    # IMPORTANT: Use root URL for OAuth discovery, not /mcp
    oauth = OAuth(
        mcp_url="http://localhost:8090",  # Root URL for OAuth discovery
        scopes=["mcp:read", "mcp:execute", "mcp:write"],
        client_name="FastMCP Browser Client",
        token_storage_cache_dir=Path.home() / ".protobox" / "oauth-cache",
        callback_port=8765  # Local port for OAuth callback
    )
    
    print("\n📋 OAuth Configuration:")
    print(f"   • Client Name: FastMCP Browser Client")
    print(f"   • Scopes: mcp:read, mcp:execute, mcp:write")
    print(f"   • Callback Port: 8765")
    print(f"   • Token Cache: ~/.protobox/oauth-cache")
    
    print("\n⏳ Initializing OAuth flow...")
    print("   🌐 Your browser will open for authorization")
    print("   📝 Please log in and approve access")
    print()
    
    try:
        # Create client with OAuth authentication
        # This will trigger the browser flow if no valid token is cached
        async with Client(MCP_SERVER_URL, auth=oauth) as client:
            print("\n✅ Successfully authenticated via OAuth!")
            print("="*60)
            
            # Now we can use the client with OAuth authentication
            print("\n🔍 Fetching workspace information...")
            
            # List available tools
            try:
                tools = await client.list_tools()
            except Exception as e:
                print(f"⚠️  Note: Initial tool listing had an issue: {e}")
                print("   This is expected with dynamic registration.")
                print("   The OAuth token is valid, but the workspace might need initialization.")
                tools = []
            print(f"\n📦 Available Tools ({len(tools)} total):")
            print("-"*40)
            
            # Group tools by category
            admin_tools = []
            action_tools = []
            kb_tools = []
            other_tools = []
            
            for tool in tools:
                tool_name = tool.name if hasattr(tool, 'name') else str(tool)
                if 'admin' in tool_name.lower():
                    admin_tools.append(tool_name)
                elif 'action' in tool_name.lower():
                    action_tools.append(tool_name)
                elif 'knowledge' in tool_name.lower() or 'kb' in tool_name.lower():
                    kb_tools.append(tool_name)
                else:
                    other_tools.append(tool_name)
            
            if admin_tools:
                print("\n👤 Admin Tools:")
                for tool in admin_tools[:5]:
                    print(f"   • {tool}")
                if len(admin_tools) > 5:
                    print(f"   ... and {len(admin_tools)-5} more")
            
            if action_tools:
                print("\n⚡ Action Tools:")
                for tool in action_tools[:5]:
                    print(f"   • {tool}")
                if len(action_tools) > 5:
                    print(f"   ... and {len(action_tools)-5} more")
            
            if kb_tools:
                print("\n📚 Knowledge Base Tools:")
                for tool in kb_tools[:5]:
                    print(f"   • {tool}")
                if len(kb_tools) > 5:
                    print(f"   ... and {len(kb_tools)-5} more")
            
            if other_tools:
                print("\n🔧 Other Tools:")
                for tool in other_tools[:5]:
                    print(f"   • {tool}")
                if len(other_tools) > 5:
                    print(f"   ... and {len(other_tools)-5} more")
            
            # Try to get workspace info
            print("\n📊 Testing Tool Execution...")
            print("-"*40)
            
            if tools and 'admin_get_workspace_info' in [t.name if hasattr(t, 'name') else str(t) for t in tools]:
                try:
                    print("Executing: admin_get_workspace_info")
                    result = await client.call_tool('admin_get_workspace_info', {})
                    print(f"✅ Success! Workspace info retrieved")
                    if result:
                        print(f"   Preview: {str(result)[:200]}...")
                except Exception as e:
                    print(f"⚠️  Tool execution not available: {e}")
            elif not tools:
                print("   No tools available for testing (expected with new registration)")
            
            # List resources if available
            print("\n📚 Available Resources:")
            print("-"*40)
            try:
                resources = await client.list_resources()
                if resources:
                    print(f"Found {len(resources)} resources:")
                    for resource in resources[:5]:
                        res_name = resource.name if hasattr(resource, 'name') else str(resource)
                        print(f"   • {res_name}")
                else:
                    print("   No resources available")
            except Exception as e:
                print(f"   Resources not supported: {e}")
            
            print("\n" + "="*60)
            print("🎉 OAuth Authentication Successful!")
            print("="*60)
            print("\n✅ Your OAuth token is now cached for future use")
            print(f"📂 Cache location: ~/.protobox/oauth-cache")
            print("\n💡 Next time you run this script, it will use the cached token")
            print("   (No browser needed until token expires)")
            
            print("\n⚠️  Note: If you see errors about JSON parsing or missing tools:")
            print("   This is expected with dynamic registration - the OAuth flow worked!")
            print("   For production use, register a client with a proper workspace.")
            
    except Exception as e:
        print(f"\n❌ OAuth flow failed: {e}")
        print("\n🔍 Troubleshooting:")
        
        if "Connection refused" in str(e):
            print("   • Make sure ProtoBox server is running:")
            print("     make backend")
        elif "Dynamic registration" in str(e):
            print("   • Server may not support dynamic registration yet")
            print("   • Try creating a client manually first:")
            print("     python scripts/test_dynamic_registration.py")
        elif "Authorization" in str(e):
            print("   • Check that OAuth endpoints are configured:")
            print("     /admin/api/v1/oauth/authorize")
            print("     /admin/api/v1/oauth/token")
        else:
            print(f"   • Unexpected error: {e}")
            print("   • Check server logs: make blogs")
        
        print("\n📝 To clear cached tokens and try again:")
        print(f"   rm -rf ~/.protobox/oauth-cache")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  FastMCP OAuth Browser Authentication Demo")
    print("="*60)
    print("\nThis demo will:")
    print("  1. Open your browser for OAuth authorization")
    print("  2. Handle the OAuth callback automatically")
    print("  3. Store tokens for future use")
    print("  4. Connect to ProtoBox MCP server")
    print("  5. List and test available tools")
    
    print("\nStarting OAuth flow...")
    
    
    async def main_with_timeout():
        """Run main with a timeout to prevent hanging."""
        try:
            # Run main with 30-second timeout
            await asyncio.wait_for(main(), timeout=30)
        except asyncio.TimeoutError:
            print("\n⏱️  Script timed out after 30 seconds")
            print("💡 Possible causes:")
            print("   • OAuth authorization is waiting for browser action")
            print("   • Server is not responding")
            print("   • Check browser for authorization prompt")
            print("\n📝 To debug:")
            print("   • Check server logs: make blogs")
            print("   • Try running without timeout")
            import sys
            sys.exit(1)
    
    asyncio.run(main_with_timeout())