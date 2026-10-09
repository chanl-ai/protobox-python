"""
MCP Server - A highly configurable Model Context Protocol server

This package provides a complete MCP server implementation with support for:
- Multiple transport protocols (stdio, HTTP, WebSocket)
- Extensible tool system
- Context management
- Resource management
- Configuration-driven setup
"""

__version__ = "1.0.0"
__author__ = "Elemente Corp"
__email__ = ""

# Core exports
from .config.settings import Config, ServerConfig, ToolConfig, TransportConfig
from .protocol.transport import HTTPTransport, StdioTransport, Transport, WebSocketTransport
from .server import MCPServer

# Tool exports
from .tools.base import (
    CalculatorTool,
    EchoTool,
    FetchTool,
    MCPContext,
    MCPResult,
    MCPTool,
    RestActionTool,
    SearchTool,
)

__all__ = [
    # Core classes
    "MCPServer",
    "Config",
    "ServerConfig",
    "TransportConfig",
    "ToolConfig",
    # Tool system
    "MCPTool",
    "MCPContext",
    "MCPResult",
    "EchoTool",
    "RestActionTool",
    # Remote MCP tools (Phase 1X)
    "SearchTool",
    "FetchTool",
    "CalculatorTool",
    # Transport system
    "Transport",
    "StdioTransport",
    "HTTPTransport",
    "WebSocketTransport",
    # Package info
    "__version__",
    "__author__",
    "__email__",
]
