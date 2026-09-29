#!/usr/bin/env python3
"""
Comprehensive MCP SDK Demo

This example demonstrates all the key features of the new MCP SDK v0.2.0:
- Admin API client for server management
- MCP protocol client for tool discovery and execution
- Server configuration utilities
- Real-world usage patterns

Prerequisites:
- MCP server running on localhost:8080
- Python 3.8+
- aiohttp installed
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp.sdk import AdminClient, MCPClient, ServerConfig
from mcp.sdk.types import ActionConfig, ActionType, SecretConfig, SecretType, ExecutionConfig


async def demo_admin_api():
    """Demonstrate Admin API capabilities."""
    print("🔧 Admin API Demo")
    print("=" * 50)
    
    async with AdminClient("http://localhost:8080") as admin:
        # 1. Health Check
        print("1. Health Check")
        health = await admin.health()
        print(f"   Status: {health.status}")
        print(f"   Version: {health.version}")
        print(f"   Capabilities: {list(health.capabilities.keys()) if health.capabilities else 'None'}")
        
        # 2. List existing actions
        print("\n2. List Actions")
        actions = await admin.actions.list()
        print(f"   Found {len(actions)} actions:")
        for action in actions[:3]:  # Show first 3
            print(f"   - {action.name} ({action.type}) - {action.status}")
        
        # 3. Get action types
        print("\n3. Available Action Types")
        action_types = await admin.actions.get_types()
        for action_type in action_types:
            print(f"   - {action_type['type']}: {action_type['description']}")
        
        # 4. Create a new action
        print("\n4. Create New Action")
        new_action = ActionConfig(
            name=f"sdk_demo_action_{int(datetime.now().timestamp())}",
            type=ActionType.REST,
            description="Demo action created via SDK",
            default_config={
                "url": "https://httpbin.org/json",
                "method": "GET",
                "timeout": 30
            },
            tags=["demo", "sdk", "test"]
        )
        
        created_action = await admin.actions.create(new_action)
        print(f"   Created action: {created_action.name}")
        print(f"   ID: {created_action.id}")
        
        # 5. Get the created action
        print("\n5. Get Action Details")
        retrieved_action = await admin.actions.get(created_action.id)
        print(f"   Name: {retrieved_action.name}")
        print(f"   Type: {retrieved_action.type}")
        print(f"   Status: {retrieved_action.status}")
        print(f"   Config: {json.dumps(retrieved_action.config, indent=2)}")
        
        # 6. Update the action
        print("\n6. Update Action")
        updated_config = ActionConfig(
            name=retrieved_action.name,
            type=ActionType.REST,
            description="Updated demo action via SDK",
            default_config={
                "url": "https://httpbin.org/uuid",
                "method": "GET",
                "timeout": 45
            },
            tags=["demo", "sdk", "updated"]
        )
        
        updated_action = await admin.actions.update(created_action.id, updated_config)
        print(f"   Updated action: {updated_action.name}")
        print(f"   New description: {updated_action.description}")
        
        # 7. Delete the action
        print("\n7. Delete Action")
        deleted = await admin.actions.delete(created_action.id)
        print(f"   Action deleted: {deleted}")
        
        print("\n✅ Admin API demo completed successfully!")


async def demo_mcp_protocol():
    """Demonstrate MCP Protocol capabilities."""
    print("\n🔌 MCP Protocol Demo")
    print("=" * 50)
    
    async with MCPClient("http://localhost:8080/mcp") as mcp:
        # 1. Initialize connection
        print("1. Initialize MCP Connection")
        init_result = await mcp.initialize()
        server_info = init_result.get('serverInfo', {})
        print(f"   Server: {server_info.get('name', 'Unknown')}")
        print(f"   Version: {server_info.get('version', 'Unknown')}")
        
        # 2. Get server capabilities
        print("\n2. Server Capabilities")
        capabilities = await mcp.get_capabilities()
        if capabilities:
            for cap, details in capabilities.items():
                print(f"   - {cap}: {details}")
        
        # 3. List available tools
        print("\n3. Available Tools")
        tools = await mcp.list_tools()
        print(f"   Found {len(tools)} tools:")
        for tool in tools:
            print(f"   - {tool.name}: {tool.description}")
        
        # 4. Call a simple tool
        print("\n4. Call Echo Tool")
        try:
            echo_result = await mcp.call_tool("echo", {"message": "Hello from SDK!"})
            print(f"   Result: {echo_result.content}")
            print(f"   Error: {echo_result.isError}")
        except Exception as e:
            print(f"   Error calling echo tool: {e}")
        
        # 5. Call calculator tool
        print("\n5. Call Calculator Tool")
        try:
            calc_result = await mcp.call_tool("calculator", {"expression": "2 + 3 * 4"})
            print(f"   Result: {calc_result.content}")
            print(f"   Error: {calc_result.isError}")
        except Exception as e:
            print(f"   Error calling calculator tool: {e}")
        
        # 6. Call httpbin test tool
        print("\n6. Call HTTPBin Test Tool")
        try:
            httpbin_result = await mcp.call_tool("httpbin_test", {"endpoint": "json"})
            print(f"   Result: {httpbin_result.content}")
            print(f"   Error: {httpbin_result.isError}")
        except Exception as e:
            print(f"   Error calling httpbin tool: {e}")
        
        print("\n✅ MCP Protocol demo completed successfully!")


def demo_server_config():
    """Demonstrate Server Configuration utilities."""
    print("\n⚙️  Server Configuration Demo")
    print("=" * 50)
    
    # 1. Generate OpenAI configuration
    print("1. OpenAI Configuration")
    openai_config = ServerConfig.for_openai(
        url="http://localhost:8080/mcp",
        name="my-mcp-server",
        description="Local MCP Server for Development",
        api_key="sk-demo-key"
    )
    print(f"   Config: {json.dumps(openai_config.to_dict(), indent=2)}")
    
    # 2. Generate Claude Desktop configuration
    print("\n2. Claude Desktop Configuration")
    claude_config = ServerConfig.for_claude(
        command=["python", "-m", "src.mcp.cli"],
        args=["--config", "config.yaml", "http"],
        env={"ADMIN_SECRET_KEY": "your-secret-key"}
    )
    print(f"   Config: {json.dumps(claude_config.to_dict(), indent=2)}")
    
    # 3. Generate example configurations
    print("\n3. Example Configurations")
    examples = ServerConfig.generate_example_configs(
        server_url="http://localhost:8080/mcp",
        api_key="demo-key"
    )
    
    print("   OpenAI Example:")
    print(f"   File: {examples['openai']['file_path']}")
    print(f"   Config: {json.dumps(examples['openai']['config'], indent=2)}")
    
    print("\n   Claude Example:")
    print(f"   File: {examples['claude']['file_path']}")
    print(f"   Config: {json.dumps(examples['claude']['config'], indent=2)}")
    
    # 4. Validate configurations
    print("\n4. Configuration Validation")
    openai_errors = ServerConfig.validate_config(openai_config.to_dict(), "openai")
    claude_errors = ServerConfig.validate_config(claude_config.to_dict(), "claude")
    
    print(f"   OpenAI validation errors: {openai_errors or 'None'}")
    print(f"   Claude validation errors: {claude_errors or 'None'}")
    
    print("\n✅ Server Configuration demo completed successfully!")


async def demo_real_world_workflow():
    """Demonstrate a real-world workflow combining all SDK features."""
    print("\n🚀 Real-World Workflow Demo")
    print("=" * 50)
    
    # Scenario: Set up a weather service integration
    print("Scenario: Setting up a weather service integration")
    
    async with AdminClient("http://localhost:8080") as admin:
        print("\n1. Create Weather API Secret")
        try:
            weather_secret = SecretConfig(
                name="weather_api_key",
                secret_type=SecretType.API_KEY,
                secret_value="demo-api-key-12345",
                description="OpenWeatherMap API key"
            )
            # Note: In real usage, you'd create the secret
            # secret_result = await admin.secrets.create(weather_secret)
            print("   Weather API secret configured (demo)")
        except Exception as e:
            print(f"   Note: Secret creation skipped in demo: {e}")
        
        print("\n2. Create Weather Action")
        weather_action = ActionConfig(
            name=f"weather_service_{int(datetime.now().timestamp())}",
            type=ActionType.REST,
            description="Get current weather for any city",
            default_config={
                "url": "https://api.openweathermap.org/data/2.5/weather",
                "method": "GET",
                "params": {
                    "q": "{city}",
                    "appid": "{weather_api_key}",
                    "units": "metric"
                },
                "timeout": 30,
                "headers": {
                    "User-Agent": "MCP-SDK-Demo/1.0"
                }
            },
            tags=["weather", "api", "demo"]
        )
        
        created_weather = await admin.actions.create(weather_action)
        print(f"   Created weather action: {created_weather.name}")
        
        print("\n3. Generate Client Configurations")
        # Generate configurations for different AI providers
        openai_config = ServerConfig.for_openai(
            url="http://localhost:8080/mcp",
            name="weather-mcp-server",
            description="Weather MCP Server"
        )
        
        claude_config = ServerConfig.for_claude(
            command=["python", "-m", "src.mcp.cli"],
            args=["--config", "config.yaml", "http"],
            env={"WEATHER_API_KEY": "your-actual-api-key"}
        )
        
        print("   OpenAI config generated")
        print("   Claude config generated")
        
        print("\n4. Test MCP Integration")
        async with MCPClient("http://localhost:8080/mcp") as mcp:
            tools = await mcp.list_tools()
            weather_tools = [t for t in tools if "weather" in t.name.lower()]
            print(f"   Found {len(weather_tools)} weather-related tools")
        
        print("\n5. Clean Up")
        await admin.actions.delete(created_weather.id)
        print("   Demo weather action deleted")
        
        print("\n✅ Real-world workflow demo completed successfully!")


async def main():
    """Run all demos."""
    print("🎯 MCP SDK v0.2.0 Comprehensive Demo")
    print("=" * 60)
    print("This demo showcases all the key features of the new MCP SDK:")
    print("- Admin API client for server management")
    print("- MCP protocol client for tool discovery and execution")
    print("- Server configuration utilities")
    print("- Real-world usage patterns")
    print("=" * 60)
    
    try:
        # Run all demos
        await demo_admin_api()
        await demo_mcp_protocol()
        demo_server_config()
        await demo_real_world_workflow()
        
        print("\n🎉 All demos completed successfully!")
        print("\nNext steps:")
        print("1. Check out the individual SDK components in src/mcp/sdk/")
        print("2. Read the type definitions in src/mcp/sdk/types.py")
        print("3. Use the SDK in your own projects")
        print("4. Generate configurations for your AI providers")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 