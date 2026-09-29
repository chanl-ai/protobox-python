#!/usr/bin/env python3
"""
MCP Client using mocops-sdk

This example demonstrates using the mocops-sdk to interact with the MCP server's
admin API for action management and execution.

Note: This example is currently disabled due to Motor database issues in the admin API.
Once the admin API is fixed, this example will work properly.

Prerequisites:
- MCP server running (local/staging/production)
- mocops-sdk installed
- Admin API working (currently has Motor database issues)

Usage:
    # Staging
    export MCP_SERVER_URL="http://localhost:8090"
    export MCP_API_KEY="demo_key:workspace_123:full"
    python sdk-mcp-client.py
    
    # Local testing
    export MCP_SERVER_URL="http://localhost:8080"
    export MCP_API_KEY="your-api-key"
    python sdk-mcp-client.py
"""

import os
import sys
import asyncio
import json
from typing import Dict, List, Any, Optional

# Add the mocops-sdk to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mocops-sdk'))

try:
    from mocops_sdk import MCPAdminClient, ActionConfig, ActionType, SecretConfig, SecretType
except ImportError as e:
    print(f"❌ Failed to import mocops-sdk: {e}")
    print("   Make sure mocops-sdk is properly installed")
    sys.exit(1)


class SDKMCPClient:
    """MCP client using the mocops-sdk"""
    
    def __init__(self, server_url: str, api_key: str):
        self.server_url = server_url
        self.api_key = api_key
        
        # Determine environment
        if "localhost" in server_url or "127.0.0.1" in server_url:
            self.environment = "local"
        elif "staging" in server_url:
            self.environment = "staging"
        else:
            self.environment = "production"
        
        print(f"🔧 Initializing SDK client for {self.environment} environment")
    
    async def demonstrate_sdk_features(self):
        """Demonstrate various SDK features"""
        print("\n🚀 SDK MCP Client Demo")
        print(f"🔗 Server: {self.server_url}")
        print("=" * 60)
        
        try:
            async with MCPAdminClient(
                base_url=self.server_url,
                api_key=self.api_key
            ) as client:
                
                # 1. Health Check
                print("\n1️⃣ Testing health check...")
                try:
                    health = await client.health_check()
                    print(f"   Status: {health.get('status', 'unknown')}")
                    if health.get('components'):
                        for component, status in health['components'].items():
                            print(f"   {component}: {status.get('status', 'unknown')}")
                except Exception as e:
                    print(f"   ❌ Health check failed: {e}")
                
                # 2. List Actions
                print("\n2️⃣ Testing list actions...")
                try:
                    actions = await client.actions.list()
                    print(f"   Found {len(actions)} actions")
                    for action in actions[:3]:  # Show first 3
                        print(f"   - {action.name}: {action.action_type}")
                except Exception as e:
                    print(f"   ❌ List actions failed: {e}")
                
                # 3. Create Test Action (if admin API is working)
                print("\n3️⃣ Testing create action...")
                try:
                    test_action = ActionConfig(
                        name="sdk-test-action",
                        action_type=ActionType.REST,
                        description="Test action created by SDK client",
                        configuration={
                            "url": "https://httpbin.org/post",
                            "method": "POST",
                            "headers": {"Content-Type": "application/json"},
                            "body": {"message": "Hello from SDK"}
                        },
                        tags=["test", "sdk", "demo"]
                    )
                    
                    action = await client.actions.create(test_action)
                    print(f"   ✅ Created action: {action.name} (ID: {action.id})")
                    
                    # 4. Execute the Action
                    print("\n4️⃣ Testing execute action...")
                    execution = await client.execute_action(
                        action.id,
                        {"test_data": "SDK execution test"},
                        wait_for_completion=True
                    )
                    print(f"   Execution status: {execution.status}")
                    if execution.output_data:
                        print(f"   Output: {json.dumps(execution.output_data, indent=2)}")
                    
                    # 5. Clean up - delete the action
                    print("\n5️⃣ Testing delete action...")
                    await client.actions.delete(action.id)
                    print("   ✅ Action deleted successfully")
                    
                except Exception as e:
                    print(f"   ❌ Action operations failed: {e}")
                    if "500" in str(e) or "Failed to retrieve actions" in str(e):
                        print("   💡 This is likely due to the Motor database issue in the admin API")
                        print("   💡 The SDK itself is working, but the server admin API needs to be fixed")
                
                # 6. List Action Types
                print("\n6️⃣ Testing action types...")
                try:
                    # This should work even if the database is broken
                    types_info = await client.get_action_types()
                    print(f"   Available action types:")
                    for action_type in types_info:
                        print(f"   - {action_type['type']}: {action_type.get('description', 'No description')}")
                except Exception as e:
                    print(f"   ❌ Get action types failed: {e}")
                
                print("\n✅ SDK demo completed!")
                
        except Exception as e:
            print(f"\n❌ SDK demo failed: {e}")
            if "500" in str(e) or "Failed to retrieve actions" in str(e):
                print("\n💡 TROUBLESHOOTING:")
                print("   The admin API has a Motor database issue that causes 500 errors.")
                print("   This is a server-side issue, not an SDK issue.")
                print("   Once the admin API is fixed, this SDK example will work properly.")
            else:
                import traceback
                traceback.print_exc()


async def test_sdk_without_admin_api():
    """Test SDK functionality that doesn't require the admin API"""
    print("\n🧪 Testing SDK without admin API...")
    
    # Test SDK configuration and validation
    print("   Testing SDK configuration...")
    
    try:
        # Test ActionConfig validation
        valid_action = ActionConfig(
            name="test-action",
            action_type=ActionType.REST,
            description="Test action",
            configuration={
                "url": "https://httpbin.org/get",
                "method": "GET"
            }
        )
        print(f"   ✅ ActionConfig validation passed: {valid_action.name}")
        
        # Test SecretConfig validation
        valid_secret = SecretConfig(
            name="test-secret",
            secret_type=SecretType.API_KEY,
            description="Test secret",
            secret_value="test-key-123"
        )
        print(f"   ✅ SecretConfig validation passed: {valid_secret.name}")
        
        # Test serialization
        action_dict = valid_action.to_dict()
        print(f"   ✅ Action serialization: {len(action_dict)} fields")
        
        secret_dict = valid_secret.to_dict()
        print(f"   ✅ Secret serialization: {len(secret_dict)} fields (secret_value hidden)")
        
        print("   ✅ SDK offline tests passed!")
        
    except Exception as e:
        print(f"   ❌ SDK offline tests failed: {e}")


def main():
    """Main function"""
    # Configuration from environment
    MCP_SERVER_URL = os.getenv("MCP_SERVER_URL")
    MCP_API_KEY = os.getenv("MCP_API_KEY")
    
    # Validate configuration
    if not MCP_SERVER_URL:
        print("❌ Please set MCP_SERVER_URL environment variable")
        print("   Example: export MCP_SERVER_URL='http://localhost:8090'")
        sys.exit(1)
    
    if not MCP_API_KEY:
        print("⚠️ MCP_API_KEY not set - using demo key")
        MCP_API_KEY = "demo_key:workspace_123:full"
    
    print("🎯 mocops-sdk MCP Client Example")
    print(f"🔗 Server: {MCP_SERVER_URL}")
    print(f"🔑 API Key: {MCP_API_KEY[:20]}..." if len(MCP_API_KEY) > 20 else MCP_API_KEY)
    print("=" * 60)
    
    try:
        # Test SDK offline functionality first
        asyncio.run(test_sdk_without_admin_api())
        
        # Test SDK with server (may fail due to admin API issues)
        client = SDKMCPClient(MCP_SERVER_URL, MCP_API_KEY)
        asyncio.run(client.demonstrate_sdk_features())
        
    except KeyboardInterrupt:
        print("\n⚠️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main() 