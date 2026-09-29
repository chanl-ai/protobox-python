# MCP SDK v0.2.0

A Python SDK for the Model Context Protocol (MCP) that provides clean, type-safe interfaces for server management and tool execution.

## 🚀 Features

- **Admin API Client**: Full CRUD operations for actions, secrets, and executions
- **MCP Protocol Client**: Tool discovery and execution via MCP protocol
- **Server Configuration**: Generate configurations for OpenAI and Claude integration
- **Type Safety**: Complete type definitions with proper validation
- **Async Support**: Modern async/await patterns throughout
- **Error Handling**: Comprehensive error handling with detailed messages

## 📦 Installation

The SDK is included in the MCP server project. For standalone use:

```python
# Add the src directory to your Python path
import sys
from pathlib import Path
sys.path.insert(0, str(Path("path/to/mcp-server/src")))

from mcp.sdk import AdminClient, MCPClient, ServerConfig
```

## 🔧 Quick Start

### Admin API Client

Manage your MCP server programmatically:

```python
import asyncio
from mcp.sdk import AdminClient
from mcp.sdk.types import ActionConfig, ActionType

async def manage_server():
    async with AdminClient("http://localhost:8080") as admin:
        # Check server health
        health = await admin.health()
        print(f"Server status: {health.status}")
        
        # List existing actions
        actions = await admin.actions.list()
        print(f"Found {len(actions)} actions")
        
        # Create a new action
        action = ActionConfig(
            name="weather_api",
            type=ActionType.REST,
            description="Get weather data",
            default_config={
                "url": "https://api.weather.com/v1/current",
                "method": "GET",
                "timeout": 30
            }
        )
        
        created = await admin.actions.create(action)
        print(f"Created action: {created.name}")

asyncio.run(manage_server())
```

### MCP Protocol Client

Discover and execute tools:

```python
import asyncio
from mcp.sdk import MCPClient

async def use_tools():
    async with MCPClient("http://localhost:8080/mcp") as mcp:
        # Initialize connection
        await mcp.initialize()
        
        # Discover available tools
        tools = await mcp.list_tools()
        print(f"Available tools: {[t.name for t in tools]}")
        
        # Execute a tool
        result = await mcp.call_tool("calculator", {
            "expression": "2 + 3 * 4"
        })
        print(f"Result: {result.content}")

asyncio.run(use_tools())
```

### Server Configuration

Generate configurations for AI providers:

```python
from mcp.sdk import ServerConfig

# OpenAI configuration
openai_config = ServerConfig.for_openai(
    url="http://localhost:8080/mcp",
    name="my-mcp-server",
    description="My MCP Server"
)

# Claude Desktop configuration
claude_config = ServerConfig.for_claude(
    command=["python", "-m", "src.mcp.cli"],
    args=["--config", "config.yaml", "http"]
)

# Save configurations
ServerConfig.save_openai_config(
    openai_config, 
    "~/.openai/mcp_servers.json",
    "my-server"
)

ServerConfig.save_claude_config(
    claude_config,
    "~/claude_desktop_config.json", 
    "my-server"
)
```

## 📚 Core Components

### AdminClient

The `AdminClient` provides access to the MCP server's admin API:

- **Actions**: `admin.actions.create()`, `list()`, `get()`, `update()`, `delete()`
- **Secrets**: `admin.secrets.create()`, `list()`, `delete()`
- **Executions**: `admin.executions.create()`, `list()`, `get()`
- **Health**: `admin.health()`, `admin.ping()`

### MCPClient

The `MCPClient` implements the MCP protocol for tool interaction:

- **Initialization**: `mcp.initialize()`
- **Tool Discovery**: `mcp.list_tools()`
- **Tool Execution**: `mcp.call_tool(name, arguments)`
- **Server Info**: `mcp.get_server_info()`, `mcp.get_capabilities()`

### ServerConfig

The `ServerConfig` utility generates configurations for AI providers:

- **OpenAI**: `ServerConfig.for_openai()`
- **Claude**: `ServerConfig.for_claude()`
- **Validation**: `ServerConfig.validate_config()`
- **File Management**: `save_openai_config()`, `load_claude_config()`

## 🏗️ Architecture

```
src/mcp/sdk/
├── __init__.py          # Main exports
├── admin_client.py      # Admin API client
├── mcp_client.py        # MCP protocol client
├── server_config.py     # Configuration utilities
└── types.py            # Type definitions
```

### Type System

The SDK provides complete type definitions:

```python
from mcp.sdk.types import (
    # Core MCP types
    MCPTool, MCPToolCall, MCPToolResult,
    
    # Admin API types
    ActionConfig, SecretConfig, ExecutionConfig,
    ActionType, SecretType, ExecutionStatus,
    
    # Response types
    ActionResponse, ExecutionResponse, HealthResponse,
    
    # Configuration types
    OpenAIServerConfig, ClaudeServerConfig
)
```

## 🔒 Error Handling

The SDK provides comprehensive error handling:

```python
from mcp.sdk.admin_client import AdminAPIError
from mcp.sdk.mcp_client import MCPProtocolError

try:
    async with AdminClient("http://localhost:8080") as admin:
        action = await admin.actions.get("invalid-id")
except AdminAPIError as e:
    print(f"API Error: {e}")
    print(f"Status Code: {e.status_code}")
    print(f"Response: {e.response_data}")

try:
    async with MCPClient("http://localhost:8080/mcp") as mcp:
        result = await mcp.call_tool("invalid-tool", {})
except MCPProtocolError as e:
    print(f"Protocol Error: {e}")
    print(f"Error Code: {e.error_code}")
    print(f"Error Data: {e.error_data}")
```

## 🧪 Testing

Run the test suite:

```bash
# Basic functionality test
python test-new-sdk.py

# Comprehensive demo
python examples/sdk-comprehensive-demo.py
```

Expected output:
```
🚀 Testing New MCP SDK v0.2.0
...
Total: 4/4 tests passed
🎉 All tests passed! SDK is working correctly.
```

## 📖 Examples

See the `examples/` directory for comprehensive examples:

- **`test-new-sdk.py`**: Basic functionality test
- **`examples/sdk-comprehensive-demo.py`**: Complete real-world demonstration

## 🔄 Migration from Old SDK

The new SDK replaces the previous auto-generated SDK with a clean, hand-written implementation:

### Before (Old SDK)
```python
# Auto-generated with broken attributes
from mocops_sdk import SomeClient
client = SomeClient()
# AttributeError: 'SomeClient' object has no attribute 'name'
```

### After (New SDK)
```python
# Clean, type-safe implementation
from mcp.sdk import AdminClient
async with AdminClient("http://localhost:8080") as admin:
    health = await admin.health()  # Always works!
```

## 🚀 Future Public Release

When ready for public release, the SDK can be extracted to a standalone package:

1. Copy `src/mcp/sdk/` to new repository
2. Create standalone `pyproject.toml`
3. Publish to PyPI as `mcp-sdk`
4. Install via `pip install mcp-sdk`

## 📄 License

Same license as the main MCP server project.

## 🤝 Contributing

1. Make changes to `src/mcp/sdk/`
2. Run tests: `python test-new-sdk.py`
3. Run demo: `python examples/sdk-comprehensive-demo.py`
4. Ensure 100% test success rate
5. Update documentation as needed

## 🆘 Support

For issues and questions:
1. Check the comprehensive demo for usage examples
2. Review type definitions in `types.py`
3. Examine error handling patterns
4. Test with the basic test suite 