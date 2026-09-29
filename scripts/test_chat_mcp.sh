#!/bin/bash
# Test Chat Playground with MCP Tools

BASE_URL="http://localhost:8090"
WORKSPACE_ID="6883c972274b0349b71b5ff2"

echo "🤖 Testing Chat Playground MCP Integration"
echo "=========================================="

# Step 1: Get assistants
echo -e "\n📋 Step 1: Checking for assistants with MCP tools"
ASSISTANTS=$(curl -s "${BASE_URL}/admin/api/v1/workspaces/${WORKSPACE_ID}/assistants")
echo "$ASSISTANTS" | jq -r '.[] | "Assistant: \(.name)\nModel: \(.model)\nTools: \(.tools | length)"' | head -20

# Get first assistant ID
ASSISTANT_ID=$(echo "$ASSISTANTS" | jq -r '.[0].id // empty')

if [ -z "$ASSISTANT_ID" ]; then
  echo "⚠️  No assistants found. Let's create one with MCP tools..."
  
  # Create assistant with MCP tools
  ASSISTANT_ID=$(curl -s -X POST "${BASE_URL}/admin/api/v1/workspaces/${WORKSPACE_ID}/assistants" \
    -H "Content-Type: application/json" \
    -d '{
      "name": "MCP Test Assistant",
      "instructions": "You are a helpful assistant that can execute ProtoBox actions using MCP tools.",
      "model": "gpt-4o-mini",
      "tools": [{"type": "mcp"}]
    }' | jq -r '.id')
    
  echo "✅ Created assistant: $ASSISTANT_ID"
fi

# Step 2: Create a thread
echo -e "\n📝 Step 2: Creating chat thread"
THREAD_ID=$(curl -s -X POST "${BASE_URL}/admin/api/v1/workspaces/${WORKSPACE_ID}/assistants/${ASSISTANT_ID}/threads" \
  -H "Content-Type: application/json" \
  -d '{}' | jq -r '.id')
echo "✅ Created thread: $THREAD_ID"

# Step 3: Send a message asking to use MCP tools
echo -e "\n💬 Step 3: Sending message to use MCP tools"
MESSAGE_RESPONSE=$(curl -s -X POST "${BASE_URL}/admin/api/v1/workspaces/${WORKSPACE_ID}/assistants/threads/${THREAD_ID}/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Please execute the test-fastmcp action to test the integration."
  }')
echo "✅ Message sent"

# Step 4: Run the assistant (this triggers MCP tool usage)
echo -e "\n🏃 Step 4: Running assistant (this will use MCP tools)"
RUN_ID=$(curl -s -X POST "${BASE_URL}/admin/api/v1/workspaces/${WORKSPACE_ID}/assistants/threads/${THREAD_ID}/runs" \
  -H "Content-Type: application/json" \
  -d "{\"assistant_id\": \"$ASSISTANT_ID\"}" | jq -r '.id')
echo "✅ Run started: $RUN_ID"

# Step 5: Check run status (wait for completion)
echo -e "\n⏳ Step 5: Waiting for assistant to complete..."
for i in {1..10}; do
  sleep 2
  STATUS=$(curl -s "${BASE_URL}/admin/api/v1/workspaces/${WORKSPACE_ID}/assistants/threads/${THREAD_ID}/runs/${RUN_ID}" | jq -r '.status')
  echo "   Status: $STATUS"
  if [ "$STATUS" = "completed" ]; then
    break
  fi
done

# Step 6: Get messages to see the result
echo -e "\n📬 Step 6: Getting conversation messages"
MESSAGES=$(curl -s "${BASE_URL}/admin/api/v1/workspaces/${WORKSPACE_ID}/assistants/threads/${THREAD_ID}/messages")
echo "$MESSAGES" | jq -r '.[] | "[\(.role)]: \(.content[0].text.value)"' | tail -10

echo -e "\n✅ Chat Playground MCP Integration Test Complete!"
echo "You can also test manually at: http://localhost:3001/workspace/${WORKSPACE_ID}/dashboard/playground/chat"