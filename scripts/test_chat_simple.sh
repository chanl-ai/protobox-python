#!/bin/bash
# Simple test to verify chat is working

BASE_URL="http://localhost:8090"
WORKSPACE_ID="6883c972274b0349b71b5ff2"

echo "🧪 Testing ProtoBox Chat with MCP"
echo "================================="

# Get the latest MCP-enabled assistant
ASSISTANT=$(curl -s "${BASE_URL}/admin/api/v1/workspaces/${WORKSPACE_ID}/assistants" | \
  jq -r '.[] | select(.metadata.mcp_enabled == "True" or .metadata.mcp_enabled == "true") | {id, name, metadata} | @json' | tail -1)

if [ -z "$ASSISTANT" ]; then
  echo "❌ No MCP-enabled assistant found"
  exit 1
fi

ASSISTANT_ID=$(echo "$ASSISTANT" | jq -r '.id')
echo "✅ Using assistant: $(echo "$ASSISTANT" | jq -r '.name')"

# Create a new thread for this assistant
THREAD_ID=$(curl -s -X POST "${BASE_URL}/admin/api/v1/workspaces/${WORKSPACE_ID}/assistants/${ASSISTANT_ID}/threads" \
  -H "Content-Type: application/json" \
  -d '{"title": "MCP Test Chat"}' | jq -r '.id')
echo "✅ Created thread: $THREAD_ID"

# Send a simple message
echo -e "\n📨 Sending test message..."
RESPONSE=$(curl -s -X POST "${BASE_URL}/admin/api/v1/workspaces/${WORKSPACE_ID}/assistants/threads/${THREAD_ID}/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Hello, can you list the available tools?"
  }' 2>&1)

if echo "$RESPONSE" | grep -q "error"; then
  echo "❌ Failed to send message:"
  echo "$RESPONSE" | jq '.'
else
  echo "✅ Message sent successfully"
  echo "$RESPONSE" | jq -r '.content'
fi

echo -e "\n🌐 You can test manually at:"
echo "http://localhost:3001/workspace/${WORKSPACE_ID}/dashboard/playground/chat"