# Public MCP Endpoints Documentation

## Overview

The public MCP endpoints provide a short, user-friendly URL for connecting ProtoBox workspaces to AI assistants like Claude Desktop and ChatGPT. These endpoints use simple token-based authentication via query parameters.

## Endpoints

### Health Check
- **URL**: `/mcp/health`
- **Method**: GET
- **Description**: General health check for public MCP system

### Workspace Health Check
- **URL**: `/mcp/{workspace_id}/health`
- **Method**: GET
- **Description**: Health check for specific workspace MCP endpoint

### SSE Connection
- **URL**: `/mcp/{workspace_id}/sse?token=YOUR_API_KEY`
- **Method**: GET
- **Description**: Server-Sent Events connection for MCP communication
- **Authentication**: API key passed as `token` query parameter

### Messages
- **URL**: `/mcp/{workspace_id}/messages?token=YOUR_API_KEY`
- **Method**: POST
- **Description**: JSON-RPC message endpoint for MCP commands
- **Authentication**: API key passed as `token` query parameter

## Authentication

The public MCP endpoints use a simple token-based authentication system:

1. Users create an API key through the ProtoBox UI
2. The API key is passed as a `token` query parameter
3. In dev_test mode, the test API key `test_api_key_12345` is accepted

## Claude Desktop Configuration

To connect ProtoBox to Claude Desktop, users would add this configuration:

```json
{
  "mcpServers": {
    "protobox": {
      "command": "npx",
      "args": [
        "@modelcontextprotocol/server-sse-client", 
        "https://protobox.example.com/mcp/YOUR_WORKSPACE_ID/sse?token=YOUR_API_KEY"
      ]
    }
  }
}
```

## ChatGPT Custom GPT Configuration

For ChatGPT custom GPTs, users would:

1. Create a custom GPT
2. Add an action with OpenAPI schema pointing to the MCP endpoints
3. Use the API key for authentication

## Implementation Notes

### Current Status

The public MCP endpoints are implemented in `/server/src/protobox/admin/routers/mcp_public.py` but require the full MCP server to be running with HTTP transport. When running via uvicorn (as in development), these endpoints are not available.

### How It Works

1. The `mount_public_mcp()` function is called during server initialization
2. It creates a dynamic routing system that handles `/mcp/{workspace_id}/*` requests
3. Each workspace gets its own MCP server instance with:
   - All workspace actions as MCP tools
   - Knowledge Base search tool
   - Proper SSE transport handling

### Testing

- Unit tests: `server/tests/unit/test_public_mcp_router.py`
- Integration tests: `server/tests/integration/test_public_mcp.py`
- Manual test script: `scripts/test_public_mcp_manual.py`

### Security Considerations

1. API keys should be kept secure and not shared
2. Each API key is scoped to specific workspaces
3. All connections are logged for audit purposes
4. Token validation happens before any MCP operations

## Future Enhancements

1. OAuth 2.0 support for more secure authentication
2. Rate limiting per API key
3. Usage analytics and quotas
4. WebSocket support as an alternative to SSE