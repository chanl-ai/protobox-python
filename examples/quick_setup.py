#!/usr/bin/env python3
"""
Quick Setup Script for MCP Server

This script helps new users quickly set up their MCP server with
example actions and get started in minutes.
"""

import asyncio
import os
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.mcp.admin_cli import MCPAdminClient, Config, generate_api_key
from action_templates import ALL_TEMPLATES


async def quick_setup():
    """Quick setup wizard for new users"""
    print("🚀 MCP Server Quick Setup")
    print("=" * 50)
    
    # Check if already configured
    config = Config()
    if config.api_key and not os.getenv("FORCE_SETUP"):
        print(f"✅ Already configured for workspace: {config.workspace}")
        print(f"   Server: {config.server_url}")
        print(f"   API Key: {config.api_key}")
        print("\nRun with FORCE_SETUP=1 to reconfigure")
        return
    
    # Get username
    username = input("Enter your username: ").strip()
    if not username:
        print("❌ Username is required")
        return
    
    # Generate configuration
    api_key = generate_api_key()
    server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8090")
    
    # Save configuration
    config.workspace = username
    config.api_key = api_key
    config.server_url = server_url
    
    print(f"\n✅ Configuration saved!")
    print(f"   Workspace: {username}")
    print(f"   API Key: {api_key}")
    print(f"   Server: {server_url}")
    
    # Ask about example actions
    print("\n📦 Would you like to install example actions?")
    print("   1. Weather lookup")
    print("   2. Calculator")
    print("   3. Web search")
    print("   4. Text analysis")
    print("   5. JSON formatter")
    print("   6. URL shortener")
    print("   7. GitHub search")
    
    install_examples = input("\nInstall examples? [Y/n] ").strip().lower()
    if install_examples != 'n':
        await install_example_actions(config)
    
    # Show next steps
    print("\n🎉 Setup complete! Here's how to use your MCP server:")
    print("\n1. List your actions:")
    print("   mcp-admin action list")
    
    print("\n2. Create a new action:")
    print("   mcp-admin action create --name my_action --type REST --url https://api.example.com")
    
    print("\n3. Use with ChatGPT:")
    print(f"   Add this to your Custom GPT configuration:")
    chatgpt_config = {
        "type": "mcp",
        "server_url": f"{server_url}/mcp",
        "api_key": api_key
    }
    print(f"   {json.dumps(chatgpt_config, indent=2)}")
    
    print("\n4. Get more info:")
    print("   mcp-admin info")


async def install_example_actions(config: Config):
    """Install example actions"""
    client = MCPAdminClient(config.server_url, config.api_key)
    
    print("\n📥 Installing example actions...")
    
    # Filter out actions that need API keys
    templates_to_install = [
        t for t in ALL_TEMPLATES 
        if "{{" not in t.get("configuration", {}).get("url", "") 
        or t["name"] in ["calculate", "analyze_text", "format_json"]
    ]
    
    for template in templates_to_install:
        try:
            result = await client.create_action(template)
            print(f"   ✅ {template['name']}: {template['description']}")
        except Exception as e:
            if "already exists" in str(e):
                print(f"   ⏭️  {template['name']}: Already exists")
            else:
                print(f"   ❌ {template['name']}: {e}")
    
    print("\n💡 Note: Some actions (weather, GitHub) require API keys.")
    print("   Create secrets with: mcp-admin secret create <name> <value>")


async def main():
    """Main entry point"""
    try:
        await quick_setup()
    except KeyboardInterrupt:
        print("\n\n👋 Setup cancelled")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())