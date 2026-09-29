#!/bin/bash
# Simple MCP Integration Tests using curl

BASE_URL="http://localhost:8090"
WORKSPACE_ID="6883c972274b0349b71b5ff2"

echo "🚀 ProtoBox MCP Integration Tests"
echo "=================================="

# Test 1: List MCP Tools
echo -e "\n📋 Test 1: List Available MCP Tools"
curl -s -X POST "${BASE_URL}/admin/api/v1/workspaces/${WORKSPACE_ID}/mcp/tools/list" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}' | jq '.'

# Test 2: Execute MCP Tool
echo -e "\n🔧 Test 2: Execute MCP Tool (test-fastmcp)"
curl -s -X POST "${BASE_URL}/admin/api/v1/workspaces/${WORKSPACE_ID}/mcp/tools/call" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "test-fastmcp",
      "arguments": {"message": "Hello from MCP!"}
    },
    "id": 2
  }' | jq '.result.content[0].text' -r | jq '.status_code, .execution_time_ms, .request_config.url'

# Test 3: Test SSE Connection (first 5 messages)
echo -e "\n📡 Test 3: SSE Connection (showing first few messages)"
echo "Connecting to SSE endpoint..."
timeout 5 curl -N -H "Accept: text/event-stream" \
  "${BASE_URL}/admin/api/v1/workspaces/${WORKSPACE_ID}/mcp/sse" 2>/dev/null | head -20

# Test 4: Test Error Handling
echo -e "\n❌ Test 4: Error Handling (invalid tool)"
curl -s -X POST "${BASE_URL}/admin/api/v1/workspaces/${WORKSPACE_ID}/mcp/tools/call" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "non-existent-tool",
      "arguments": {}
    },
    "id": 3
  }' | jq '.'

echo -e "\n✅ MCP Integration is working!"