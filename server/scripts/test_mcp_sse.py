#!/usr/bin/env python3
"""Test ProtoBox multi-tenant MCP SSE connection using OpenAI Agent SDK."""

import asyncio
import os
import sys

# Check for required packages
try:
    from agents import Agent, Runner
    from agents.mcp import MCPServerSse
except ImportError:
    print("Error: OpenAI Agent SDK not installed.")
    print("Please install it with: pip install openai-agents-sdk")
    sys.exit(1)


async def test_mcp_sse_connection(
    sse_url: str,
    tenant_name: str = "Test Tenant",
    openai_api_key: str | None = None
):
    """Test MCP SSE connection with OpenAI Agent SDK.
    
    Args:
        sse_url: The SSE endpoint URL (e.g., http://localhost:8090/mcp/WORKSPACE_ID/sse)
        tenant_name: Display name for the tenant
        openai_api_key: OpenAI API key (uses env var if not provided)
    """
    # Set API key if provided
    if openai_api_key:
        os.environ["OPENAI_API_KEY"] = openai_api_key

    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Set it with: export OPENAI_API_KEY='your-api-key'")
        return

    print(f"🔌 Connecting to MCP SSE endpoint: {sse_url}")
    print(f"🏢 Tenant: {tenant_name}")
    print()

    try:
        # Create MCP SSE connection
        async with MCPServerSse(
            name=f"{tenant_name} MCP",
            params={"url": sse_url}
        ) as mcp_server:
            print("✅ Connected to MCP server!")

            # Create an agent with the MCP server
            agent = Agent(
                name=f"{tenant_name} Assistant",
                instructions=f"""You are an assistant for {tenant_name}.
                First, list all available tools you have access to.
                Then, if you have any tools available, demonstrate using one of them.
                If no tools are available, explain that no actions have been configured yet.""",
                model="gpt-4o",
                mcp_servers=[mcp_server]
            )

            # Run the agent
            print("🤖 Running agent to discover and test tools...")
            print()

            result = await Runner.run(
                starting_agent=agent,
                input="What tools do you have available, and can you demonstrate one?"
            )

            print("📋 Agent Response:")
            print("-" * 50)
            print(result.final_output)
            print("-" * 50)

    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        print("Common issues:")
        print("1. Make sure the server is running: make restart")
        print("2. Verify the workspace ID exists in the database")
        print("3. Check that OPENAI_API_KEY is set correctly")
        print("4. Ensure the SSE URL is correct")


async def main():
    """Main function to run the test."""
    # Default values
    default_base_url = "http://localhost:8090"
    default_workspace_id = "6883c972274b0349b71b5ff2"  # Test workspace from CLAUDE.md

    # Parse command line arguments
    if len(sys.argv) > 1:
        # Full SSE URL provided
        sse_url = sys.argv[1]
    else:
        # Use defaults
        sse_url = f"{default_base_url}/mcp/{default_workspace_id}/sse"

    print("🚀 ProtoBox Multi-tenant MCP SSE Test")
    print("=" * 60)
    print()

    # Extract workspace ID from URL for display
    if "/mcp/" in sse_url:
        workspace_id = sse_url.split("/mcp/")[1].split("/")[0]
        tenant_name = f"Workspace {workspace_id}"
    else:
        tenant_name = "ProtoBox Workspace"

    await test_mcp_sse_connection(sse_url, tenant_name)

    print()
    print("💡 Usage examples:")
    print(f"  python {sys.argv[0]}")
    print(f"  python {sys.argv[0]} {default_base_url}/mcp/YOUR_WORKSPACE_ID/sse")
    print("  make test-mcp-sse")
    print(f"  make test-mcp-sse URL={default_base_url}/mcp/YOUR_WORKSPACE_ID/sse")


if __name__ == "__main__":
    asyncio.run(main())
