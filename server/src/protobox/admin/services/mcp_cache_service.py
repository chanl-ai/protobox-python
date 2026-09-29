"""MCP Cache Service - handles caching and monitoring for MCP servers and sessions.

This service layer keeps caching logic separate from the core MCP protocol implementation.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from loguru import logger

from ..cache.cache_backend import get_cache_manager


class MCPCacheService:
    """Service for managing MCP server and session caching."""
    
    def __init__(self):
        self.cache_manager = get_cache_manager()
        self._server_metadata: Dict[str, Dict[str, Any]] = {}
        self._session_metadata: Dict[str, Dict[str, Any]] = {}
    
    async def track_server_creation(self, workspace_id: str, server_name: str) -> None:
        """Track when an MCP server is created."""
        metadata = {
            "workspace_id": workspace_id,
            "server_name": server_name,
            "created_at": datetime.utcnow().isoformat(),
            "status": "active"
        }
        
        # Store in memory for quick access
        self._server_metadata[workspace_id] = metadata
        
        # Store in Redis for distributed tracking
        await self.cache_manager.set_mcp_server(workspace_id, metadata, ttl=3600)
        logger.debug(f"Tracked MCP server creation for workspace {workspace_id}")
    
    async def track_session_creation(self, session_id: str, workspace_id: str) -> None:
        """Track when an SSE session is created."""
        metadata = {
            "session_id": session_id,
            "workspace_id": workspace_id,
            "created_at": datetime.utcnow().isoformat(),
            "status": "active",
            "initialized": False
        }
        
        # Store in memory for quick access
        self._session_metadata[session_id] = metadata
        
        # Store in Redis for distributed tracking
        await self.cache_manager.set_mcp_session(session_id, metadata, ttl=1800)
        logger.debug(f"Tracked SSE session creation: {session_id}")
    
    async def update_session_initialized(self, session_id: str) -> None:
        """Update session when it's initialized."""
        if session_id in self._session_metadata:
            self._session_metadata[session_id]["initialized"] = True
            self._session_metadata[session_id]["initialized_at"] = datetime.utcnow().isoformat()
            
            # Update in Redis
            await self.cache_manager.set_mcp_session(
                session_id, 
                self._session_metadata[session_id], 
                ttl=1800
            )
            logger.debug(f"Updated session {session_id} as initialized")
    
    async def remove_session(self, session_id: str) -> None:
        """Remove session when it's closed."""
        if session_id in self._session_metadata:
            del self._session_metadata[session_id]
        
        # Remove from Redis
        await self.cache_manager.invalidate_mcp_session(session_id)
        logger.debug(f"Removed session {session_id}")
    
    async def get_active_servers(self) -> List[Dict[str, Any]]:
        """Get information about active MCP servers."""
        servers_info = []
        
        for workspace_id, metadata in self._server_metadata.items():
            # Get additional info from Redis if available
            redis_data = await self.cache_manager.get_mcp_server(workspace_id)
            
            created_at = datetime.fromisoformat(metadata["created_at"])
            age_hours = (datetime.utcnow() - created_at).total_seconds() / 3600
            
            servers_info.append({
                "workspace_id": workspace_id,
                "server_name": metadata["server_name"],
                "created_at": metadata["created_at"],
                "age_hours": age_hours,
                "status": metadata.get("status", "unknown"),
                "redis_cached": redis_data is not None
            })
        
        return servers_info
    
    async def get_active_sessions(self) -> Dict[str, Any]:
        """Get information about active SSE sessions."""
        sessions_info = []
        
        for session_id, metadata in self._session_metadata.items():
            # Get additional info from Redis if available
            redis_data = await self.cache_manager.get_mcp_session(session_id)
            
            sessions_info.append({
                "session_id": session_id,
                "workspace_id": metadata["workspace_id"],
                "created_at": metadata["created_at"],
                "initialized": metadata.get("initialized", False),
                "status": metadata.get("status", "unknown"),
                "redis_cached": redis_data is not None
            })
        
        # Get all sessions from Redis (may include from other instances)
        all_redis_sessions = await self.cache_manager.get_all_mcp_sessions()
        
        return {
            "active_count": len(sessions_info),
            "redis_count": len(all_redis_sessions),
            "sessions": sessions_info
        }
    
    async def cleanup_stale_resources(self, max_age_hours: int = 2) -> Dict[str, int]:
        """Clean up stale servers and sessions."""
        current_time = datetime.utcnow()
        servers_cleaned = 0
        sessions_cleaned = 0
        
        # Clean up stale servers
        servers_to_remove = []
        for workspace_id, metadata in self._server_metadata.items():
            created_at = datetime.fromisoformat(metadata["created_at"])
            age_hours = (current_time - created_at).total_seconds() / 3600
            if age_hours > max_age_hours:
                servers_to_remove.append(workspace_id)
        
        for workspace_id in servers_to_remove:
            del self._server_metadata[workspace_id]
            await self.cache_manager.invalidate_mcp_server(workspace_id)
            servers_cleaned += 1
            logger.info(f"Cleaned up stale MCP server for workspace {workspace_id}")
        
        # Clean up stale sessions
        sessions_to_remove = []
        max_session_age_minutes = max_age_hours * 60
        for session_id, metadata in self._session_metadata.items():
            created_at = datetime.fromisoformat(metadata["created_at"])
            age_minutes = (current_time - created_at).total_seconds() / 60
            if age_minutes > max_session_age_minutes:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self._session_metadata[session_id]
            await self.cache_manager.invalidate_mcp_session(session_id)
            sessions_cleaned += 1
            logger.info(f"Cleaned up stale session {session_id}")
        
        return {
            "servers_cleaned": servers_cleaned,
            "sessions_cleaned": sessions_cleaned
        }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get overall MCP usage statistics."""
        total_servers = len(self._server_metadata)
        total_sessions = len(self._session_metadata)
        initialized_sessions = sum(
            1 for s in self._session_metadata.values() 
            if s.get("initialized", False)
        )
        
        # Calculate average age
        current_time = datetime.utcnow()
        server_ages = []
        for metadata in self._server_metadata.values():
            created_at = datetime.fromisoformat(metadata["created_at"])
            age_hours = (current_time - created_at).total_seconds() / 3600
            server_ages.append(age_hours)
        
        avg_server_age = sum(server_ages) / len(server_ages) if server_ages else 0
        
        return {
            "total_servers": total_servers,
            "total_sessions": total_sessions,
            "initialized_sessions": initialized_sessions,
            "average_server_age_hours": avg_server_age,
            "cache_backend": self.cache_manager.backend.__class__.__name__
        }


# Singleton instance
_mcp_cache_service: Optional[MCPCacheService] = None


def get_mcp_cache_service() -> MCPCacheService:
    """Get or create MCP cache service instance."""
    global _mcp_cache_service
    if _mcp_cache_service is None:
        _mcp_cache_service = MCPCacheService()
    return _mcp_cache_service