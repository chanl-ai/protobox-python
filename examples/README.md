# MCP Server Examples

This directory contains examples of using the MCP server as a remote SaaS service with OpenAI and Claude clients.

## Overview

The MCP server is designed to be deployed as a remote service. Both OpenAI and Claude have native MCP client support, which means:

- **No custom code needed** for protocol handling
- **Automatic tool discovery** from the MCP server
- **Native integration** with AI models

## Quick Start

### Local Development

```bash
# 1. Start local server
make db-start
make run-dev

# 2. Setup actions
make example-setup-local

# 3. Test with OpenAI
export OPENAI_API_KEY="your-api-key"
make example-openai-local
```

### Staging Environment

```bash
# 1. Set environment variables
export MCP_SERVER_URL="https://staging.your-server.com"
export MCP_API_KEY="staging-api-key"
export OPENAI_API_KEY="your-openai-api-key"

# 2. Setup actions
make example-setup-staging

# 3. Test with OpenAI
make example-openai-staging
```

### Production Environment

```bash
# 1. Set environment variables
export MCP_SERVER_URL="https://your-mcp-server.fly.dev"
export MCP_API_KEY="production-api-key"
export OPENAI_API_KEY="your-openai-api-key"

# 2. Setup actions
make example-setup-prod

# 3. Test with OpenAI
make example-openai-prod
```

### Claude Desktop

```bash
# Show configuration template
make example-claude-config

# Update the configuration with your server details and add to Claude Desktop
```

## Examples Overview

### OpenAI Native MCP Client

**File**: `openai-mcp-client.py`

Simple example showing OpenAI's native MCP support:

```python
# Configure MCP server
mcp_config = {
    "type": "mcp",
    "server_label": "my-mcp-server",
    "server_url": "https://your-server.fly.dev/mcp/",
    "require_approval": "never"
}

# Use with OpenAI
response = client.responses.create(
    model="gpt-4o",
    tools=[mcp_config],
    input=[{"type": "message", "role": "user", "content": "..."}]
)
```

### Claude Desktop Configuration

**File**: `claude-desktop-config.json`

Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "my-mcp-server": {
      "url": "https://your-server.fly.dev/mcp/sse",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer your-api-key"
      }
    }
  }
}
```

### Action Setup Script

**File**: `setup-mcp-actions.py`

Configure actions on your MCP server via Admin API:

- **calculate**: Python code execution
- **get_weather**: Weather API integration
- **search_web**: Web search functionality

## Development Workflow

### Starting the Environment

```bash
# 1. Start MongoDB
make db-start

# 2. Start MCP server
make run-dev

# 3. Test in another terminal
make example-openai
```

### Debugging

```bash
# Start server in debug mode
make run-debug

# View logs
make logs-dev

# Run tests
make example-test
```

### Stopping Services

```bash
# Stop MongoDB
make db-stop

# Stop server (Ctrl+C)
```

## Configuration

### MCP Server Configuration

The development server uses `config-local-dev.yaml` which includes:

- **Admin API**: Enabled for development
- **Sample Actions**: Pre-configured actions for testing
- **Database**: MongoDB connection
- **Security**: Development-only settings

### Environment Variables

```bash
# Required for OpenAI
export OPENAI_API_KEY="your-openai-api-key"

# Optional for debugging
export DEBUG="true"
```

## Available Actions

The development server includes these sample actions:

### REST Actions
- **get_weather**: Get weather for any city
- **search_news**: Search for news articles
- **httpbin_test**: Test HTTP API calls

### CODE_RUN Actions
- **python_calculator**: Execute Python code
- **echo_test**: Simple echo function

## Troubleshooting

### Common Issues

1. **MCP Server not starting**
   ```bash
   # Check if MongoDB is running
   make db-start
   
   # Check server logs
   make logs-dev
   ```

2. **OpenAI API errors**
   ```bash
   # Verify API key is set
   echo $OPENAI_API_KEY
   
   # Test OpenAI connection
   make example-test
   ```

3. **Claude not connecting**
   ```bash
   # Verify MCP server is running
   curl http://localhost:8080/admin/api/v1/health
   
   # Regenerate Claude config
   make example-claude
   ```

### Debug Mode

```bash
# Start server with debug logging
DEBUG=true make run-dev

# View detailed logs
make logs-dev
```

## API Endpoints

### Health Check
```bash
curl http://localhost:8080/admin/api/v1/health
```

### List Actions
```bash
curl http://localhost:8080/admin/api/v1/actions
```

### Execute Action
```bash
curl -X POST http://localhost:8080/admin/api/v1/executions \
  -H "Content-Type: application/json" \
  -d '{
    "action_id": "action_id_here",
    "input_data": {"city": "London"}
  }'
```

## Next Steps

1. **Custom Actions**: Add your own actions to the configuration
2. **Production Setup**: Configure for production deployment
3. **Advanced Features**: Explore the full MCP protocol capabilities
4. **Integration**: Connect with other AI platforms

## Support

- **Documentation**: See `CLAUDE.md` for detailed development guide
- **Issues**: Check the main project README for troubleshooting
- **Testing**: Use `make example-test` for comprehensive testing 