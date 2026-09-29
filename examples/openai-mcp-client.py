#!/usr/bin/env python3
"""
OpenAI Native MCP Client Example

This example shows how to use OpenAI's native MCP client support to connect
to an MCP server (local, staging, or production).

Prerequisites:
- MCP server running (local/staging/production)
- OpenAI API key
- Admin API configured with actions

Usage:
    # Local testing
    export MCP_SERVER_URL="http://localhost:8080"
    export OPENAI_API_KEY="your-api-key"
    python openai-mcp-client.py
    
    # Staging
    export MCP_SERVER_URL="https://staging.your-server.com"
    export MCP_API_KEY="staging-api-key"
    python openai-mcp-client.py
    
    # Production
    export MCP_SERVER_URL="https://your-mcp-server.fly.dev"
    export MCP_API_KEY="production-api-key"
    python openai-mcp-client.py
"""

import os
import sys
from openai import OpenAI

# Configuration from environment
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL")
MCP_API_KEY = os.getenv("MCP_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Validate configuration
if not MCP_SERVER_URL:
    print("❌ Please set MCP_SERVER_URL environment variable")
    print("   Examples:")
    print("   - Local: export MCP_SERVER_URL='http://localhost:8080'")
    print("   - Staging: export MCP_SERVER_URL='https://staging.example.com'")
    print("   - Production: export MCP_SERVER_URL='https://prod.example.com'")
    sys.exit(1)

if not OPENAI_API_KEY:
    print("❌ Please set OPENAI_API_KEY environment variable")
    sys.exit(1)

# Determine environment
if "localhost" in MCP_SERVER_URL or "127.0.0.1" in MCP_SERVER_URL:
    ENVIRONMENT = "local"
elif "staging" in MCP_SERVER_URL:
    ENVIRONMENT = "staging"
else:
    ENVIRONMENT = "production"

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Configure MCP server
mcp_config = {
    "type": "mcp",
    "server_label": f"mcp-server-{ENVIRONMENT}",
    "server_url": f"{MCP_SERVER_URL}/mcp/",  # Note: Streamable HTTP endpoint
    "require_approval": "never",  # Options: "never", "always", "auto"
}

# Add authentication headers if API key is provided
if MCP_API_KEY:
    mcp_config["headers"] = {
        "Authorization": f"Bearer {MCP_API_KEY}"
    }

# Example conversation
print("🤖 OpenAI MCP Client Example")
print(f"📡 Environment: {ENVIRONMENT.upper()}")
print(f"🔗 Server URL: {MCP_SERVER_URL}")
print("=" * 50)

try:
    # Create a response using MCP tools
    print("\n🔄 Sending request to OpenAI...")
    response = client.responses.create(
        model="gpt-4o",
        tools=[mcp_config],
        input=[
            {
                "type": "message",
                "role": "user",
                "content": "What tools are available? Then calculate the fibonacci sequence up to 10."
            }
        ]
    )

    # Display the response
    print("\n📤 Response:")
    for output in response.output:
        if output.type == "message":
            print(f"\n💬 Assistant: {output.content[0].text}")
        elif output.type == "mcp_call":
            print(f"\n🔧 Tool Call: {output.name}")
            print(f"   Args: {output.arguments}")
            if output.output:
                print(f"   Result: {output.output}")
            if output.error:
                print(f"   ❌ Error: {output.error}")

    print("\n✅ Example complete!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\n💡 Troubleshooting tips:")
    if ENVIRONMENT == "local":
        print("   - Make sure the MCP server is running: make run-dev")
        print("   - Check if MongoDB is running: make db-start")
        print("   - Verify server is accessible: curl http://localhost:8080/admin/api/v1/health")
    else:
        print(f"   - Verify the server URL is correct: {MCP_SERVER_URL}")
        print(f"   - Check if API key is required for {ENVIRONMENT}")
        print("   - Test the endpoint: curl {}/admin/api/v1/health".format(MCP_SERVER_URL))
    sys.exit(1) 