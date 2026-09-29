# MCP Server Testing Guide

This guide explains how to test the MCP server with OpenAI across different environments (local, staging, production).

## Prerequisites

- OpenAI API key
- Python 3.11+ with dependencies installed
- Docker (for local MongoDB)
- MCP server deployed (for staging/production)

## Testing Environments

### 1. Local Testing

Test against a locally running MCP server:

```bash
# Start MongoDB
make db-start

# Start MCP server
make run

# In another terminal, setup actions
make example-setup-local

# Test with OpenAI
export OPENAI_API_KEY="your-openai-api-key"
make example-openai-local
```

**What happens:**
- Server runs at `http://localhost:8080`
- No authentication required
- Actions are stored in local MongoDB
- OpenAI discovers tools via MCP protocol

### 2. Staging Testing

Test against a staging server:

```bash
# Set environment variables
export MCP_SERVER_URL="https://staging.your-server.com"
export MCP_API_KEY="staging-api-key"
export OPENAI_API_KEY="your-openai-api-key"

# Setup actions on staging
make example-setup-staging

# Test with OpenAI
make example-openai-staging
```

**What happens:**
- Connects to remote staging server
- Uses API key for authentication
- Actions persist in staging database
- Tests integration before production

### 3. Production Testing

Test against production server:

```bash
# Set environment variables
export MCP_SERVER_URL="https://your-mcp-server.fly.dev"
export MCP_API_KEY="production-api-key"
export OPENAI_API_KEY="your-openai-api-key"

# Setup actions (if needed)
make example-setup-prod

# Test with OpenAI
make example-openai-prod
```

**What happens:**
- Connects to production server
- Uses production API key
- Verifies production functionality
- Real-world testing

## Understanding the Test Flow

### 1. Action Setup (`setup-mcp-actions.py`)

Creates sample actions via Admin API:
- **calculate**: Python code execution
- **get_weather**: Weather API integration
- **search_web**: Web search functionality

### 2. OpenAI Client Test (`openai-mcp-client.py`)

Tests MCP integration:
1. Connects to MCP server
2. OpenAI discovers available tools
3. Sends test prompt: "What tools are available? Then calculate fibonacci..."
4. OpenAI calls MCP tools
5. Results displayed

## Expected Output

### Successful Test

```
🤖 OpenAI MCP Client Example
📡 Environment: LOCAL
🔗 Server URL: http://localhost:8080
==================================================

🔄 Sending request to OpenAI...

📤 Response:

💬 Assistant: I can see the following tools are available:
1. calculate - Perform mathematical calculations using Python
2. get_weather - Get current weather for a city
3. search_web - Search the web for information

Now let me calculate the Fibonacci sequence up to 10:

🔧 Tool Call: calculate
   Args: {"code": "# Calculate Fibonacci sequence\nfib = [0, 1]\nwhile len(fib) < 10:\n    fib.append(fib[-1] + fib[-2])\nresult = fib"}
   Result: [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]

💬 Assistant: The Fibonacci sequence up to 10 numbers is: [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]

✅ Example complete!
```

### Common Errors

1. **Server Not Running**
```
❌ Error: Connection refused
💡 Troubleshooting tips:
   - Make sure the MCP server is running: make run
   - Check if MongoDB is running: make db-start
```

2. **Authentication Failed**
```
❌ Error: 401 Unauthorized
💡 Troubleshooting tips:
   - Check if API key is required for staging/production
   - Verify MCP_API_KEY is set correctly
```

3. **No Tools Found**
```
💬 Assistant: I don't see any tools available.
💡 Troubleshooting tips:
   - Run setup script: make example-setup-local
   - Check Admin API: curl http://localhost:8080/admin/api/v1/actions
```

## Debugging

### Check Server Health

```bash
# Local
curl http://localhost:8080/admin/api/v1/health

# Staging/Production
curl -H "Authorization: Bearer $MCP_API_KEY" \
  $MCP_SERVER_URL/admin/api/v1/health
```

### List Actions

```bash
# Local
curl http://localhost:8080/admin/api/v1/actions

# Staging/Production
curl -H "Authorization: Bearer $MCP_API_KEY" \
  $MCP_SERVER_URL/admin/api/v1/actions
```

### Test MCP Protocol

```bash
# Test tool discovery
curl -X POST $MCP_SERVER_URL/mcp/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MCP_API_KEY" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "params": {},
    "id": 1
  }'
```

## Environment Variables Reference

| Variable | Description | Required For |
|----------|-------------|--------------|
| `MCP_SERVER_URL` | MCP server URL | All environments |
| `MCP_API_KEY` | API key for auth | Staging/Production |
| `OPENAI_API_KEY` | OpenAI API key | All environments |

## Next Steps

1. **Add Custom Actions**: Modify `setup-mcp-actions.py` to add your own actions
2. **Test Different Prompts**: Try various OpenAI prompts to test tool usage
3. **Monitor Logs**: Use `make logs` or `fly logs` to debug issues
4. **Scale Testing**: Test with multiple concurrent requests
5. **Claude Integration**: Configure Claude Desktop with your server 