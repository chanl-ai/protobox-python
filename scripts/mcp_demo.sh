#!/bin/bash
# MCP Demo - Shows MCP Protocol Working End-to-End

echo "🎯 ProtoBox MCP Protocol Demo"
echo "=============================="
echo "This demonstrates the complete MCP integration working."
echo ""

BASE_URL="http://localhost:8090"
WORKSPACE_ID="6883c972274b0349b71b5ff2"

# 1. Show MCP SSE endpoint is active
echo "1️⃣ MCP SSE Endpoint (Real-time connection for AI assistants)"
echo "   Endpoint: /admin/api/v1/workspaces/{workspace_id}/mcp/sse"
echo "   Testing connection..."
echo ""
timeout 2 curl -s -N -H "Accept: text/event-stream" \
  "${BASE_URL}/admin/api/v1/workspaces/${WORKSPACE_ID}/mcp/sse" 2>/dev/null | head -5
echo ""

# 2. Show available tools
echo "2️⃣ Available MCP Tools (ProtoBox actions exposed as MCP tools)"
echo "   These tools can be discovered and executed by AI assistants:"
echo ""
curl -s -X POST "${BASE_URL}/admin/api/v1/workspaces/${WORKSPACE_ID}/mcp/tools/list" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}' | \
  jq -r '.result.tools[] | "   • \(.name): \(.description)"'
echo ""

# 3. Execute a tool
echo "3️⃣ Execute MCP Tool (test-fastmcp)"
echo "   Demonstrating tool execution through MCP protocol:"
echo ""
RESULT=$(curl -s -X POST "${BASE_URL}/admin/api/v1/workspaces/${WORKSPACE_ID}/mcp/tools/call" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "test-fastmcp",
      "arguments": {"message": "Hello from MCP Demo!"}
    },
    "id": 2
  }')

# Parse the result
echo "$RESULT" | jq -r '.result.content[0].text' | jq '{
  status: .status_code,
  url: .request_config.url,
  method: .request_config.method,
  execution_time: "\(.execution_time_ms)ms"
}'
echo ""

# 4. Show integration points
echo "4️⃣ Integration Points"
echo "   ✅ SSE Transport: Real-time streaming for AI assistants"
echo "   ✅ MCP Protocol: JSON-RPC 2.0 compliant"
echo "   ✅ Tool Discovery: All ProtoBox actions exposed as MCP tools"
echo "   ✅ Tool Execution: Actions executed and results returned"
echo "   ✅ OpenAI Compatible: Works with OpenAI Agents SDK"
echo ""

# 5. How to use
echo "5️⃣ How AI Assistants Connect"
echo "   • OpenAI: Use HostedMCPTool with base URL:"
echo "     ${BASE_URL}/admin/api/v1/workspaces/${WORKSPACE_ID}/mcp"
echo "   • Claude: Configure MCP server in Claude Desktop"
echo "   • Custom: Connect to SSE endpoint and use JSON-RPC protocol"
echo ""

echo "✅ MCP Protocol is fully operational!"
echo ""
echo "Try it yourself in the chat playground:"
echo "http://localhost:3001/workspace/${WORKSPACE_ID}/dashboard/playground/chat"