#!/usr/bin/env python3
"""
Automated MCP authentication testing script.
Tests MCP endpoints with real authentication without requiring manual curl permissions.
"""

import json
import sys
import requests
from pathlib import Path

def get_cached_token():
    """Get cached JWT token from .test-token file."""
    token_file = Path(".test-token")
    if token_file.exists():
        return token_file.read_text().strip()
    return None

def test_admin_auth(token):
    """Test if token works with admin API."""
    try:
        response = requests.get(
            "http://localhost:8090/admin/api/v1/auth/validate",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("valid", False), data
        return False, {"error": f"HTTP {response.status_code}"}
    except Exception as e:
        return False, {"error": str(e)}

def test_mcp_info(token, workspace_id):
    """Test MCP info endpoint."""
    try:
        response = requests.get(
            f"http://localhost:8090/mcp/{workspace_id}/",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        return response.status_code, response.json() if response.status_code == 200 else {"error": response.text}
    except Exception as e:
        return 500, {"error": str(e)}

def test_mcp_tools_list(token, workspace_id):
    """Test MCP tools list endpoint."""
    try:
        response = requests.post(
            f"http://localhost:8090/mcp/{workspace_id}/tools/list",
            headers={"Authorization": f"Bearer {token}"},
            json={"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 1},
            timeout=10
        )
        return response.status_code, response.json() if response.status_code == 200 else {"error": response.text}
    except Exception as e:
        return 500, {"error": str(e)}

def main():
    """Main test function."""
    print("🧪 MCP Authentication Test Suite")
    print("=" * 50)
    
    # Get cached token
    token = get_cached_token()
    if not token:
        print("❌ No cached token found. Run: make api-setup-token")
        sys.exit(1)
    
    print(f"🔑 Using cached token: {token[:20]}...")
    
    # Test admin auth first
    print("\n1. Testing admin API authentication...")
    is_valid, auth_data = test_admin_auth(token)
    if is_valid:
        print("✅ Admin API authentication: PASSED")
        print(f"   User: {auth_data.get('email', 'unknown')}")
        print(f"   Workspace: {auth_data.get('workspace_id', 'unknown')}")
        workspace_id = auth_data.get('workspace_id')
    else:
        print("❌ Admin API authentication: FAILED")
        print(f"   Error: {auth_data}")
        print("\n🔧 Try refreshing token: ./scripts/setup-auth-token.sh")
        sys.exit(1)
    
    if not workspace_id:
        print("❌ No workspace ID found in token")
        sys.exit(1)
    
    # Test MCP info endpoint
    print(f"\n2. Testing MCP info endpoint for workspace {workspace_id}...")
    status_code, mcp_data = test_mcp_info(token, workspace_id)
    if status_code == 200:
        print("✅ MCP info endpoint: PASSED")
        print(f"   Server: {mcp_data.get('server_name', 'unknown')}")
        print(f"   Type: {mcp_data.get('server_type', 'unknown')}")
        capabilities = mcp_data.get('capabilities', {})
        print(f"   Tools: {capabilities.get('tools', False)}")
    else:
        print("❌ MCP info endpoint: FAILED")
        print(f"   Status: {status_code}")
        print(f"   Error: {mcp_data}")
        
        # Analyze the error
        if status_code == 401:
            print("\n🔍 Analysis: JWT token is valid for admin API but rejected by MCP layer")
            print("   This indicates an issue with MCPBearerAuth.validate() method")
        return False
    
    # Test MCP tools list
    print(f"\n3. Testing MCP tools list endpoint...")
    status_code, tools_data = test_mcp_tools_list(token, workspace_id)
    if status_code == 200:
        print("✅ MCP tools list endpoint: PASSED")
        result = tools_data.get('result', {})
        tools = result.get('tools', [])
        print(f"   Found {len(tools)} tools")
        if tools:
            print(f"   Sample tools: {[t.get('name') for t in tools[:3]]}")
    else:
        print("❌ MCP tools list endpoint: FAILED")
        print(f"   Status: {status_code}")
        print(f"   Error: {tools_data}")
        return False
    
    print("\n✅ All MCP authentication tests PASSED!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)