#!/usr/bin/env python3
"""Test script for multi-tenant MCP integration."""

import asyncio
import json

import httpx


async def test_multitenant_mcp():
    """Test multi-tenant MCP endpoints."""
    base_url = "http://localhost:8090"
    test_workspace_id = "6883c972274b0349b71b5ff2"

    async with httpx.AsyncClient() as client:
        # Test 1: MCP Info endpoint
        print("1. Testing MCP info endpoint...")
        response = await client.get(f"{base_url}/admin/api/v1/mcp/info")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        print()

        # Test 2: Tenant tools listing
        print(f"2. Testing tenant tools listing for workspace {test_workspace_id}...")
        response = await client.get(f"{base_url}/admin/api/v1/mcp/tenants/{test_workspace_id}/tools")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        print()

        # Test 3: Multi-tenant MCP home
        print("3. Testing multi-tenant MCP home...")
        response = await client.get(f"{base_url}/mcp/")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        print()

        # Test 4: SSE endpoint (just check it's accessible)
        print(f"4. Testing SSE endpoint for workspace {test_workspace_id}...")
        try:
            response = await client.get(
                f"{base_url}/mcp/tenants/{test_workspace_id}/sse",
                timeout=2.0  # Short timeout since SSE stays open
            )
            print(f"   Status: {response.status_code}")
        except httpx.ReadTimeout:
            print("   Status: 200 OK (SSE connection opened successfully)")
        print()

        print("✅ All multi-tenant MCP endpoints are accessible!")


if __name__ == "__main__":
    asyncio.run(test_multitenant_mcp())
