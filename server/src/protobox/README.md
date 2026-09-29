# VoiceMan MCP Server

A sophisticated Model Context Protocol (MCP) server implementation for action execution, context management, and resource sharing across multiple chat-based solutions.

## Overview

This MCP server replaces the current HTTP-based action runner with a standardized, protocol-compliant solution that can serve multiple chat applications simultaneously while providing enhanced features like context persistence, resource management, and robust error handling.

## Features

### Core MCP Protocol Support
- ✅ **Tools**: Dynamic tool registration and execution
- ✅ **Resources**: Resource management and access
- ✅ **Context Management**: Persistent context across sessions
- ✅ **Multiple Transports**: stdio, HTTP, WebSocket
- ✅ **Progress Notifications**: Long-running operation support
- ✅ **Error Handling**: Robust error reporting and recovery

### Enhanced Features
- **Multi-protocol Support**: HTTP, GraphQL, Database, File System adapters
- **Retry Logic**: Configurable retry strategies with exponential backoff
- **Circuit Breaker**: Prevent cascading failures
- **Rate Limiting**: Prevent API abuse
- **Caching**: Response caching for performance
- **Monitoring**: Metrics and observability

## Quick Start

### Installation

```bash
# Install dependencies using Poetry
make mcp-install

# Or manually with Poetry
cd server && poetry install
```

### Running the Server

#### Stdio Transport (Default)
```bash
make mcp-server
# or
cd server && poetry run mcp-server stdio
```

#### HTTP Transport
```bash
make mcp-server-http
# or 
cd server && poetry run mcp-server http --host 0.0.0.0 --port 8080
```

#### WebSocket Transport
```bash
make mcp-server-ws
# or
cd server && poetry run mcp-server websocket --host 0.0.0.0 --port 8081
```

#### Debug Mode
```bash
make mcp-server-debug
# or
cd server && poetry run mcp-server stdio --debug
```

## Architecture

### Directory Structure
```
server/mcp/
├── __init__.py              # Main package
├── server.py                # Core MCP server
├── cli.py                   # Command-line interface
├── protocol/
│   ├── handlers.py          # Protocol message handlers
│   ├── transport.py         # Transport layer (stdio, HTTP, WebSocket)
│   └── messages.py          # MCP message types
├── actions/
│   ├── executor.py          # Action execution engine
│   └── registry.py          # Action registry
├── context/
│   └── manager.py           # Context management
├── tools/
│   ├── base.py              # Base tool implementation
│   ├── discovery.py         # Tool discovery
│   └── validation.py        # Tool validation
└── resources/
    └── manager.py           # Resource management
```

### Core Components

#### 1. MCPServer
Main server class that coordinates all components:
- Transport management
- Tool registry
- Message routing
- Context coordination

#### 2. Transport Layer
Supports multiple transport methods:
- **StdioTransport**: Standard input/output (default for MCP)
- **HTTPTransport**: RESTful HTTP endpoints
- **WebSocketTransport**: Real-time WebSocket communication

#### 3. Tools System
- **MCPTool**: Abstract base class for tools
- **RestActionTool**: REST API integration
- **EchoTool**: Simple testing tool
- Tool validation and argument checking

#### 4. Context Management
- Session-based context storage
- Persistent data across tool calls
- Metadata and shared data management

## Tool Development

### Creating a Custom Tool

```python
from mcp.tools.base import MCPTool, MCPContext

class CustomTool(MCPTool):
    def __init__(self):
        super().__init__(
            name="custom_tool",
            description="Description of what the tool does",
            input_schema={
                "type": "object",
                "properties": {
                    "param1": {
                        "type": "string",
                        "description": "First parameter"
                    },
                    "param2": {
                        "type": "number",
                        "description": "Second parameter"
                    }
                },
                "required": ["param1"]
            }
        )
    
    async def execute(self, arguments: dict, context: MCPContext):
        # Tool implementation
        param1 = arguments["param1"]
        param2 = arguments.get("param2", 0)
        
        # Use context for state management
        call_count = context.get("call_count", 0) + 1
        context.set("call_count", call_count)
        
        return f"Processed {param1} with {param2} (call #{call_count})"
```

### REST API Tool

```python
from mcp.tools.base import RestActionTool

# Create a REST API tool
api_tool = RestActionTool(
    name="api_call",
    description="Call external API",
    input_schema={
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "description": "User ID"}
        },
        "required": ["user_id"]
    },
    url="https://api.example.com/users/{user_id}",
    method="GET",
    headers={"Authorization": "Bearer TOKEN"},
    timeout=30,
    retries=3
)
```

## Integration with Existing Agents

### Voice Agent Integration

```python
from mcp.tools.base import MCPTool
from app.core.agents.actions.base_action import BaseAction

class MCPVoiceActionAdapter(BaseAction):
    def __init__(self, mcp_client, tool_config):
        self.mcp_client = mcp_client
        self.tool_config = tool_config
        super().__init__(
            name=tool_config.name,
            description=tool_config.description,
            parameters=self._convert_parameters(tool_config.input_schema),
            agent=agent,
            register=register
        )
    
    async def execute(self, input_variables: dict):
        return await self.mcp_client.call_tool(
            self.tool_config.name,
            input_variables
        )
```

### Text Agent Integration

```python
from langchain.tools import StructuredTool

class MCPLangchainTool(StructuredTool):
    def __init__(self, mcp_client, tool_config):
        self.mcp_client = mcp_client
        super().__init__(
            name=tool_config.name,
            description=tool_config.description,
            func=self._execute,
            args_schema=self._create_schema(tool_config.input_schema)
        )
    
    async def _execute(self, **kwargs):
        result = await self.mcp_client.call_tool(self.name, kwargs)
        return result.content
```

## Configuration

### Server Configuration

```yaml
# mcp_server.yaml
server:
  name: "voiceman-action-server"
  version: "1.0.0"
  transports:
    - type: "stdio"
    - type: "http"
      port: 8080
    - type: "websocket"
      port: 8081

tools:
  discovery:
    auto_register: true
    config_path: "tools/"
  
  execution:
    timeout: 300
    retries: 3

context:
  storage:
    type: "memory"  # or "redis"
    ttl: 3600
```

## Testing

### Running Tests

```bash
# Test the server with sample tools
make mcp-test
# or
cd server && poetry run mcp-test-client

# Run with MCP Inspector (requires Node.js)
make mcp-inspector
# or
cd server && npx @modelcontextprotocol/inspector poetry run mcp-server stdio

# Quick debug test (starts server and runs test client)
make mcp-debug
```

### Manual Testing

1. Start the server:
   ```bash
   make mcp-server-debug
   # or
   cd server && poetry run mcp-server stdio --debug
   ```

2. Send test requests:
   ```json
   {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "clientInfo": {"name": "test", "version": "1.0.0"}}}
   {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
   {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "echo", "arguments": {"message": "Hello!"}}}
   ```

## Migration from Current System

### Phase 1: Parallel Implementation
1. Keep existing action system running
2. Implement MCP server alongside
3. Create adapter layer for compatibility

### Phase 2: Gradual Migration
1. Migrate voice agents to use MCP adapter
2. Migrate text agents to use MCP tools
3. Update action definitions to MCP format

### Phase 3: Full Migration
1. Remove old action system
2. Update all configurations
3. Deploy to production

## Monitoring and Observability

### Metrics
- Tool execution counts
- Response times
- Error rates
- Context usage

### Logging
- Structured logging with loguru
- Request/response tracing
- Error tracking
- Performance metrics

### Health Checks
- `/health` endpoint for HTTP transport
- Tool availability checks
- Context storage health

## Contributing

### Development Setup

```bash
# Clone repository
git clone <repository-url>
cd voiceman-v2

# Install dependencies
make mcp-install

# Run in development mode
make mcp-server-debug

# Show all available commands
make help
```

### Adding New Features

1. Create feature branch
2. Implement changes with tests
3. Update documentation
4. Submit pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review the MCP specification: https://modelcontextprotocol.io 