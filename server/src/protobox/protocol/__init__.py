"""
MCP Protocol Implementation

Handles the Model Context Protocol communication layer including
message handling, transport abstraction, workspace isolation,
and Redis-backed caching for horizontal scaling.
"""

from .handlers import MCPHandler
from .messages import (
    MCPMessage,
    MCPNotification,
    MCPRequest,
    MCPResponse,
    ResourceRequest,
    ResourceResponse,
    ToolCallRequest,
    ToolCallResponse,
)
from .sse_transport import SSETransport, WorkspaceSSEManager
from .transport import HTTPTransport, StdioTransport, Transport, WebSocketTransport
from .workspace_server import WorkspaceAwareMCPServer, WorkspaceToolRegistry

# Note: workspace_manager and redis_cache not imported at package level to avoid circular imports
# Import directly from modules when needed

__all__ = [
    # Core protocol
    "MCPHandler",
    "Transport",
    "StdioTransport", 
    "HTTPTransport",
    "WebSocketTransport",
    "MCPMessage",
    "MCPRequest",
    "MCPResponse",
    "MCPNotification",
    "ToolCallRequest",
    "ToolCallResponse",
    "ResourceRequest",
    "ResourceResponse",
    
    # Workspace isolation
    "WorkspaceAwareMCPServer",
    "WorkspaceToolRegistry",
    
    # Transport enhancements
    "SSETransport",
    "WorkspaceSSEManager",
]
