"""
MCP Context Package

Provides context management and persistence for the MCP server.
"""

from .manager import ContextManager

__all__ = [
    "ContextManager",
]
