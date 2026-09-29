"""
MCP SDK - Core MCP Protocol and Admin API Integration

This SDK provides:
- Admin API client for server management (actions, secrets, executions)
- MCP protocol client for tool discovery and execution
- Server configuration utilities for OpenAI and Claude integration
- Type-safe interfaces for all MCP operations

Quick Start:
    # Admin API - Manage your MCP server
    from protobox.sdk import AdminClient
    admin = AdminClient("https://my-server.com")
    await admin.actions.create(action_config)

    # MCP Protocol - Access tools programmatically
    from protobox.sdk import MCPClient
    mcp = MCPClient("https://my-server.com/mcp")
    tools = await mcp.list_tools()
    result = await mcp.call_tool("weather", {"city": "Tokyo"})

    # Server Config - Generate configurations for AI providers
    from protobox.sdk import ServerConfig
    openai_config = ServerConfig.for_openai("https://my-server.com/mcp")
    claude_config = ServerConfig.for_claude("https://my-server.com/mcp")
"""

from .admin_client import AdminClient
from .mcp_client import MCPClient
from .server_config import ServerConfig
from .types import (
    # Admin API types
    ActionConfig,
    ActionType,
    ClaudeServerConfig,
    ExecutionConfig,
    ExecutionStatus,
    # Core types
    MCPTool,
    MCPToolCall,
    MCPToolResult,
    # Server config types
    OpenAIServerConfig,
    SecretConfig,
    SecretType,
)

__version__ = "0.2.0"
__all__ = [
    # Main clients
    "AdminClient",
    "MCPClient",
    "ServerConfig",
    # Core types
    "MCPTool",
    "MCPToolCall",
    "MCPToolResult",
    # Admin types
    "ActionConfig",
    "SecretConfig",
    "ExecutionConfig",
    "ActionType",
    "SecretType",
    "ExecutionStatus",
    # Config types
    "OpenAIServerConfig",
    "ClaudeServerConfig",
]
