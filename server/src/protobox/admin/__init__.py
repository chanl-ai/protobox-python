"""Admin API module for MCP Server Phase 1A.

This module provides admin functionality including:
- Action management (CRUD operations)
- Secrets management with AES-256 encryption
- Execution tracking and monitoring
- MongoDB integration with Motor async driver
- FastAPI router (embeddable)
"""

from .router import admin_router

__version__ = "1.0.0"
__all__ = ["admin_router"]
