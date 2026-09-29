#!/bin/bash
# Create an assistant with MCP tools

BASE_URL="http://localhost:8090"
WORKSPACE_ID="6883c972274b0349b71b5ff2"

echo "Creating MCP-enabled assistant..."

ASSISTANT_ID=$(curl -s -X POST "${BASE_URL}/admin/api/v1/workspaces/${WORKSPACE_ID}/assistants" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "MCP Test Assistant",
    "instructions": "You are a helpful assistant that can execute ProtoBox actions using MCP tools. When asked, you can list and execute any available actions.",
    "model": "gpt-4o-mini",
    "tools": [{"type": "mcp"}]
  }' | jq -r '.id')

echo "✅ Created assistant: $ASSISTANT_ID"

# Create a thread
THREAD_ID=$(curl -s -X POST "${BASE_URL}/admin/api/v1/workspaces/${WORKSPACE_ID}/assistants/${ASSISTANT_ID}/threads" \
  -H "Content-Type: application/json" \
  -d '{}' | jq -r '.id')

echo "✅ Created thread: $THREAD_ID"

# Send a test message
echo -e "\nSending test message..."
MESSAGE=$(curl -s -X POST "${BASE_URL}/admin/api/v1/workspaces/${WORKSPACE_ID}/assistants/threads/${THREAD_ID}/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Please list the available MCP tools you can use."
  }')

if echo "$MESSAGE" | grep -q "error"; then
  echo "❌ Error sending message:"
  echo "$MESSAGE" | jq '.'
else
  echo "✅ Message sent successfully!"
  echo -e "\n🌐 Open the chat playground to see the response:"
  echo "http://localhost:3001/workspace/${WORKSPACE_ID}/dashboard/playground/chat"
  echo -e "\nSelect the thread: $THREAD_ID"
fi