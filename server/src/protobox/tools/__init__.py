"""
MCP Tools Module

Collection of built-in tools for the MCP server, including remote-compatible tools
for ChatGPT and Claude integration.
"""

from .base import (
    CalculatorTool,
    EchoTool,
    FetchTool,
    MCPContext,
    MCPResult,
    MCPTool,
    RestActionTool,
    SearchTool,
)
from .discovery import ToolDiscovery
from .validation import ToolValidator

__all__ = [
    # Base classes
    "MCPTool",
    "MCPContext",
    "MCPResult",
    # Built-in tools
    "EchoTool",
    "RestActionTool",
    # Remote MCP tools (Phase 1X)
    "SearchTool",
    "FetchTool",
    "CalculatorTool",
    # Utilities
    "ToolDiscovery",
    "ToolValidator",
]
