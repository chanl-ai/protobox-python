"""MCP Monitoring and Admin endpoints - separate from the core MCP protocol router.

This keeps the MCP protocol implementation clean and isolated.
"""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger

from ..auth.dependencies import User, require_authentication
from ..cache.cache_backend import get_cache_manager
from ..services.mcp_cache_service import MCPCacheService

# Create monitoring router
router = APIRouter(
    prefix="/admin/api/v1/mcp-monitoring",
    tags=["MCP Monitoring"]
)

# Initialize cache service
mcp_cache_service = MCPCacheService()


@router.get("/servers")
async def get_active_servers(
    current_user: User = Depends(require_authentication)
):
    """Get information about active MCP servers (admin only)."""
    servers_info = await mcp_cache_service.get_active_servers()
    
    return JSONResponse({
        "total_servers": len(servers_info),
        "servers": servers_info
    })


@router.get("/sessions")
async def get_active_sessions(
    current_user: User = Depends(require_authentication)
):
    """Get information about active SSE sessions (admin only)."""
    sessions_info = await mcp_cache_service.get_active_sessions()
    
    return JSONResponse({
        "total_active_sessions": sessions_info["active_count"],
        "total_redis_sessions": sessions_info["redis_count"],
        "sessions": sessions_info["sessions"]
    })


@router.post("/cleanup")
async def cleanup_stale_resources(
    max_age_hours: int = 2,
    current_user: User = Depends(require_authentication)
):
    """Clean up stale servers and sessions (admin only)."""
    result = await mcp_cache_service.cleanup_stale_resources(max_age_hours)
    
    return JSONResponse({
        "servers_cleaned": result["servers_cleaned"],
        "sessions_cleaned": result["sessions_cleaned"],
        "message": f"Cleaned up {result['servers_cleaned']} servers and {result['sessions_cleaned']} sessions"
    })


@router.get("/stats")
async def get_mcp_stats(
    current_user: User = Depends(require_authentication)
):
    """Get overall MCP usage statistics."""
    stats = await mcp_cache_service.get_statistics()
    
    return JSONResponse(stats)