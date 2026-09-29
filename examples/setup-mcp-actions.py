#!/usr/bin/env python3
"""
Setup MCP Server Actions

This script uses the Admin API to configure actions on a remote MCP server.
These actions will be discoverable by MCP clients (OpenAI, Claude, etc.).

Usage:
    python setup-mcp-actions.py
"""

import asyncio
import aiohttp
import json
import os
import sys

# Configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL")
MCP_API_KEY = os.getenv("MCP_API_KEY")

# Validate configuration
if not MCP_SERVER_URL:
    print("❌ Please set MCP_SERVER_URL environment variable")
    print("   Examples:")
    print("   - Local: export MCP_SERVER_URL='http://localhost:8080'")
    print("   - Staging: export MCP_SERVER_URL='https://staging.example.com'")
    print("   - Production: export MCP_SERVER_URL='https://prod.example.com'")
    sys.exit(1)

# Determine environment
if "localhost" in MCP_SERVER_URL or "127.0.0.1" in MCP_SERVER_URL:
    ENVIRONMENT = "local"
elif "staging" in MCP_SERVER_URL:
    ENVIRONMENT = "staging"
else:
    ENVIRONMENT = "production"

# API key is optional for local development
if ENVIRONMENT != "local" and not MCP_API_KEY:
    print(f"❌ Please set MCP_API_KEY for {ENVIRONMENT} environment")
    sys.exit(1)

# Sample actions to create
SAMPLE_ACTIONS = [
    {
        "name": "calculate",
        "type": "CODE_RUN",
        "description": "Perform mathematical calculations using Python",
        "enabled": True,
        "configuration": {
            "code": """
import math
import statistics

# User code execution
{code}

# Return the result
if 'result' not in locals():
    result = "No result variable defined"
"""
        }
    },
    {
        "name": "get_weather",
        "type": "REST",
        "description": "Get current weather for a city",
        "enabled": True,
        "configuration": {
            "url": "https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric",
            "method": "GET",
            "headers": {
                "User-Agent": "MCP-Server/1.0"
            }
        }
    },
    {
        "name": "search_web",
        "type": "REST",
        "description": "Search the web for information",
        "enabled": True,
        "configuration": {
            "url": "https://api.duckduckgo.com/?q={query}&format=json&no_html=1",
            "method": "GET",
            "headers": {
                "User-Agent": "MCP-Server/1.0"
            }
        }
    }
]

async def create_action(session, action):
    """Create a single action via Admin API."""
    url = f"{MCP_SERVER_URL}/admin/api/v1/actions"
    headers = {
        "Content-Type": "application/json"
    }
    
    # Add auth header if API key is provided
    if MCP_API_KEY:
        headers["Authorization"] = f"Bearer {MCP_API_KEY}"
    
    try:
        async with session.post(url, json=action, headers=headers) as resp:
            if resp.status == 201:
                data = await resp.json()
                print(f"✅ Created action: {action['name']} (ID: {data['id']})")
                return data
            elif resp.status == 409:
                print(f"⚠️  Action already exists: {action['name']}")
                return None
            else:
                error = await resp.text()
                print(f"❌ Failed to create {action['name']}: {error}")
                return None
    except Exception as e:
        print(f"❌ Error creating {action['name']}: {e}")
        return None

async def list_actions(session):
    """List all existing actions."""
    url = f"{MCP_SERVER_URL}/admin/api/v1/actions"
    headers = {}
    
    # Add auth header if API key is provided
    if MCP_API_KEY:
        headers["Authorization"] = f"Bearer {MCP_API_KEY}"
    
    try:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                actions = await resp.json()
                return actions
            else:
                print(f"❌ Failed to list actions: HTTP {resp.status}")
                return []
    except Exception as e:
        print(f"❌ Error listing actions: {e}")
        return []

async def main():
    """Main setup function."""
    print("🚀 MCP Server Action Setup")
    print(f"📡 Environment: {ENVIRONMENT.upper()}")
    print(f"🔗 Server URL: {MCP_SERVER_URL}")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # List existing actions
        print("\n📋 Existing actions:")
        existing = await list_actions(session)
        if existing:
            for action in existing:
                print(f"   • {action['name']} ({action['type']})")
        else:
            print("   No actions found")
        
        # Create sample actions
        print("\n🔧 Creating sample actions...")
        for action in SAMPLE_ACTIONS:
            await create_action(session, action)
        
        # List actions again
        print("\n📋 Updated action list:")
        updated = await list_actions(session)
        if updated:
            for action in updated:
                print(f"   • {action['name']} ({action['type']}) - {action['description']}")
        
        print("\n✅ Setup complete!")
        print("\n🎯 Next steps:")
        print("1. Use these actions with OpenAI: python openai-mcp-client.py")
        print("2. Configure Claude Desktop with: claude-desktop-config.json")
        print("3. Test the MCP protocol endpoint: curl {}/mcp/".format(MCP_SERVER_URL))

if __name__ == "__main__":
    asyncio.run(main()) 