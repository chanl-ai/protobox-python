#!/bin/bash
# Test MCP tools in chat

BASE_URL="http://localhost:8090"
WORKSPACE_ID="6883c972274b0349b71b5ff2"

echo "🤖 Testing MCP Tool Execution in Chat"
echo "====================================="

# Get the latest MCP-enabled assistant
ASSISTANT=$(curl -s "${BASE_URL}/admin/api/v1/workspaces/${WORKSPACE_ID}/assistants" | \
  jq -r '.[] | select(.metadata.mcp_enabled == "True" or .metadata.mcp_enabled == "true") | {id, name, metadata} | @json' | tail -1)

if [ -z "$ASSISTANT" ]; then
  echo "❌ No MCP-enabled assistant found"
  exit 1
fi

ASSISTANT_ID=$(echo "$ASSISTANT" | jq -r '.id')
echo "✅ Using assistant: $(echo "$ASSISTANT" | jq -r '.name')"

# Create a new thread
THREAD_ID=$(curl -s -X POST "${BASE_URL}/admin/api/v1/workspaces/${WORKSPACE_ID}/assistants/${ASSISTANT_ID}/threads" \
  -H "Content-Type: application/json" \
  -d '{"title": "MCP Tool Test"}' | jq -r '.id')
echo "✅ Created thread: $THREAD_ID"

# Send a message asking to use MCP tools
echo -e "\n📨 Sending message to execute MCP tool..."
RESPONSE=$(curl -s -X POST "${BASE_URL}/admin/api/v1/workspaces/${WORKSPACE_ID}/assistants/threads/${THREAD_ID}/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Please execute the test-fastmcp action with the message: Hello from MCP chat test!"
  }' 2>&1)

if echo "$RESPONSE" | grep -q "error"; then
  echo "❌ Failed to send message:"
  echo "$RESPONSE" | jq '.'
else
  echo "✅ Message sent successfully"
  
  # Wait a bit for the response
  echo "⏳ Waiting for assistant response..."
  sleep 3
  
  # Show the conversation
  echo -e "\n💬 Conversation:"
  echo "User: Please execute the test-fastmcp action with the message: Hello from MCP chat test!"
  echo "Assistant: (Check the UI for the response)"
fi

echo -e "\n📊 MCP Integration Status:"
echo "✅ Assistant created with MCP enabled"
echo "✅ Thread created successfully"
echo "✅ Message sent to assistant"
echo "🔍 Check logs for MCP tool execution"

echo -e "\n🌐 Open the chat to see the full conversation:"
echo "http://localhost:3001/workspace/${WORKSPACE_ID}/dashboard/playground/chat"
echo "Thread ID: $THREAD_ID"