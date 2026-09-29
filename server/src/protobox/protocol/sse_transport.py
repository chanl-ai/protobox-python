"""
Enhanced SSE Transport for MCP

Provides FastMCP-compatible Server-Sent Events transport with proper
JSON-RPC 2.0 message handling and workspace isolation using official MCP library.
"""

import asyncio
import json
import time
import weakref
from typing import Any, Dict, Optional, Set

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse
from loguru import logger
from mcp.server.sse import SseServerTransport
from starlette.types import Scope, Receive, Send

from .handlers import MCPHandler
from .messages import MCPMessage, MCPNotification, MCPRequest, MCPResponse
from .transport import Transport


class ConnectionManager:
    """Manages SSE connections with proper cleanup and timeout handling."""
    
    def __init__(self, connection_timeout: int = 300):  # 5 minutes default
        self._connections: Dict[str, asyncio.Queue] = {}
        self._connection_tasks: Dict[str, asyncio.Task] = {}
        self._connection_timestamps: Dict[str, float] = {}
        self._connection_timeout = connection_timeout
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown = False
    
    def add_connection(self, connection_id: str, queue: asyncio.Queue, task: asyncio.Task):
        """Add a new connection with tracking."""
        self._connections[connection_id] = queue
        self._connection_tasks[connection_id] = task
        self._connection_timestamps[connection_id] = time.time()
        logger.info(f"➕ Added SSE connection: {connection_id} (total: {len(self._connections)})")
        
        # Start cleanup task if not running
        if self._cleanup_task is None or self._cleanup_task.done():
            logger.debug(f"🧹 Starting periodic cleanup task")
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    def remove_connection(self, connection_id: str):
        """Remove connection and cleanup resources."""
        if connection_id in self._connections:
            del self._connections[connection_id]
        if connection_id in self._connection_tasks:
            task = self._connection_tasks.pop(connection_id)
            if not task.done():
                logger.debug(f"🛑 Cancelling task for removed connection: {connection_id}")
                task.cancel()
        if connection_id in self._connection_timestamps:
            del self._connection_timestamps[connection_id]
        logger.info(f"➖ Removed SSE connection: {connection_id} (total: {len(self._connections)})")
    
    def update_activity(self, connection_id: str):
        """Update connection activity timestamp."""
        if connection_id in self._connection_timestamps:
            self._connection_timestamps[connection_id] = time.time()
    
    async def _periodic_cleanup(self):
        """Periodically cleanup idle connections."""
        while not self._shutdown:
            try:
                await asyncio.sleep(60)  # Check every minute
                current_time = time.time()
                stale_connections = []
                
                for conn_id, timestamp in self._connection_timestamps.items():
                    if current_time - timestamp > self._connection_timeout:
                        stale_connections.append(conn_id)
                
                for conn_id in stale_connections:
                    logger.info(f"Cleaning up stale SSE connection: {conn_id}")
                    self.remove_connection(conn_id)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in SSE connection cleanup: {e}")
    
    async def shutdown(self):
        """Shutdown connection manager and cleanup all connections."""
        self._shutdown = True
        
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all connection tasks
        for task in self._connection_tasks.values():
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete with timeout
        if self._connection_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._connection_tasks.values(), return_exceptions=True),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.warning("Some SSE connections did not close gracefully")
        
        self._connections.clear()
        self._connection_tasks.clear()
        self._connection_timestamps.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        current_time = time.time()
        active_connections = len(self._connections)
        connection_ages = [current_time - ts for ts in self._connection_timestamps.values()]
        
        return {
            "active_connections": active_connections,
            "average_age_seconds": sum(connection_ages) / len(connection_ages) if connection_ages else 0,
            "oldest_connection_seconds": max(connection_ages) if connection_ages else 0,
            "cleanup_task_running": self._cleanup_task is not None and not self._cleanup_task.done(),
        }


class SSETransport(Transport):
    """Server-Sent Events transport for MCP with enhanced resource management using official MCP library."""
    
    def __init__(self, message_path: str = "/message"):
        super().__init__()
        self._connection_handlers: Dict[str, MCPHandler] = {}
        self._connection_manager = ConnectionManager()
        
        # Store message path for proper routing
        self._message_path = message_path
        
        # Initialize official MCP SSE transport with the message path  
        # For multi-tenant setup, we'll create workspace-specific transports as needed
        self._official_sse = SseServerTransport(message_path)
        self._workspace_sse_transports: Dict[str, SseServerTransport] = {}
        
        # Timeouts configuration
        self._heartbeat_interval = 30  # seconds
        self._connection_timeout = 300  # 5 minutes
        self._message_timeout = 60     # 1 minute for message processing
    
    def register_workspace_handler(self, workspace_id: str, handler: MCPHandler):
        """Register an MCP handler for a specific workspace."""
        self._connection_handlers[workspace_id] = handler
        logger.debug(f"Registered MCP handler for workspace {workspace_id}")
    
    def get_workspace_sse_transport(self, workspace_id: str) -> SseServerTransport:
        """Get or create workspace-specific SSE transport with correct message path."""
        if workspace_id not in self._workspace_sse_transports:
            # Create workspace-specific message path that matches the SSE endpoint
            workspace_message_path = f"/mcp/{workspace_id}/sse"
            self._workspace_sse_transports[workspace_id] = SseServerTransport(workspace_message_path)
            logger.debug(f"Created workspace-specific SSE transport for {workspace_id} with path {workspace_message_path}")
        
        return self._workspace_sse_transports[workspace_id]
    
    async def create_official_sse_connection(
        self,
        scope: Scope,
        receive: Receive, 
        send: Send,
        workspace_id: str,
        auth_context: Optional[Any] = None
    ):
        """Create MCP-compliant SSE connection using official transport."""
        
        # Get workspace handler
        handler = self._connection_handlers.get(workspace_id)
        if not handler:
            raise HTTPException(
                status_code=404,
                detail=f"No MCP handler found for workspace {workspace_id}"
            )
        
        # Set auth context if provided
        if hasattr(handler, 'set_auth_context') and auth_context:
            handler.set_auth_context(auth_context)
        
        logger.info(f"🔄 Starting official MCP SSE connection for workspace {workspace_id}")
        
        try:
            # Get workspace-specific SSE transport with correct message path
            workspace_sse = self.get_workspace_sse_transport(workspace_id)
            
            # Use workspace-specific MCP SSE transport - this provides bidirectional communication
            async with workspace_sse.connect_sse(scope, receive, send) as streams:
                logger.debug(f"🤝 Official SSE streams established for workspace {workspace_id}")
                
                # The official transport gives us read/write streams that are MCP-compliant
                read_stream = streams[0]
                write_stream = streams[1]
                
                # Create a bridge to connect our workspace handler to the official streams
                await self._bridge_workspace_handler_to_streams(
                    handler, 
                    read_stream, 
                    write_stream, 
                    workspace_id
                )
                
        except Exception as e:
            logger.error(f"❌ Official SSE connection error for workspace {workspace_id}: {e}")
            raise
        finally:
            logger.info(f"🔚 Official SSE connection closed for workspace {workspace_id}")
    
    async def _bridge_workspace_handler_to_streams(
        self,
        handler: MCPHandler,
        read_stream,
        write_stream,
        workspace_id: str
    ):
        """Bridge workspace handler to official MCP streams using server.run() method."""
        try:
            logger.debug(f"🌉 Starting MCP server bridge for workspace {workspace_id}")
            
            # Get the MCP server from the handler
            if hasattr(handler, 'mcp_server'):
                mcp_server = handler.mcp_server
                logger.debug(f"✅ Found MCP server in handler for workspace {workspace_id}")
                
                # Use the official MCP server's run method to handle the streams
                # This is the same pattern FastMCP uses
                initialization_options = mcp_server.create_initialization_options()
                logger.debug(f"🚀 Starting MCP server.run() for workspace {workspace_id}")
                
                await mcp_server.run(
                    read_stream,
                    write_stream, 
                    initialization_options
                )
                
                logger.debug(f"✅ MCP server.run() completed for workspace {workspace_id}")
                
            else:
                logger.error(f"❌ Handler for workspace {workspace_id} has no mcp_server attribute")
                # Fallback to the placeholder implementation
                logger.debug(f"⚠️ Using fallback implementation for workspace {workspace_id}")
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            logger.debug(f"🚫 Stream bridge cancelled for workspace {workspace_id}")
        except Exception as e:
            logger.error(f"❌ Stream bridge error for workspace {workspace_id}: {e}")
            raise
    
    async def handle_post_message(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        workspace_id: str,
        auth_context: Optional[Any] = None
    ):
        """Handle POST messages to the message endpoint for workspace."""
        try:
            # Get workspace handler
            handler = self._connection_handlers.get(workspace_id)
            if not handler:
                raise HTTPException(
                    status_code=404,
                    detail=f"No MCP handler found for workspace {workspace_id}"
                )
            
            # Set auth context if provided
            if hasattr(handler, 'set_auth_context') and auth_context:
                handler.set_auth_context(auth_context)
            
            logger.debug(f"🔄 Handling POST message for workspace {workspace_id}")
            
            # Get workspace-specific SSE transport and use its message handler
            workspace_sse = self.get_workspace_sse_transport(workspace_id)
            await workspace_sse.handle_post_message(scope, receive, send)
            
        except Exception as e:
            logger.error(f"❌ POST message error for workspace {workspace_id}: {e}")
            raise
    
    async def create_sse_response(
        self, 
        request: Request, 
        workspace_id: str,
        auth_context: Optional[Any] = None
    ) -> StreamingResponse:
        """Create FastMCP-compatible SSE response."""
        
        # Get workspace handler
        handler = self._connection_handlers.get(workspace_id)
        if not handler:
            raise HTTPException(
                status_code=404,
                detail=f"No MCP handler found for workspace {workspace_id}"
            )
        
        # Create connection queue and tracking
        connection_id = f"{workspace_id}:{id(request)}"
        connection_queue = asyncio.Queue()
        
        async def event_stream():
            """Generate SSE event stream with enhanced resource management."""
            processor_task = None
            try:
                logger.info(f"🔄 Starting SSE connection for workspace {workspace_id}, connection_id: {connection_id}")
                logger.debug(f"🔧 SSE Request headers: {dict(request.headers)}")
                logger.debug(f"🔧 SSE Request client: {request.client}")
                
                # 🔄 MCP Protocol: Wait for client to send 'initialize' request first
                # According to MCP protocol, the client must send an initialize request,
                # then the server responds with capabilities. Server must NOT send unsolicited responses.
                logger.debug(f"🤝 SSE connection established, waiting for client 'initialize' request...")
                
                # Send a non-MCP connection ready event for debugging (not parsed by MCP client)
                ready_event = {
                    "type": "connection_ready",
                    "workspace_id": workspace_id,
                    "timestamp": time.time(),
                    "message": "SSE connection established, ready for MCP requests"
                }
                logger.debug(f"📤 Sending connection ready event: {ready_event}")
                yield self._format_sse_event(ready_event)
                
                # Create message processor task
                processor_task = asyncio.create_task(
                    self._process_incoming_messages(request, handler, connection_id)
                )
                
                # Register connection with manager
                self._connection_manager.add_connection(connection_id, connection_queue, processor_task)
                
                # Main event loop with enhanced timeout handling
                logger.debug(f"🔄 Starting main event loop for connection {connection_id}")
                while True:
                    try:
                        # Wait for message with heartbeat timeout
                        logger.debug(f"⏳ Waiting for message (timeout: {self._heartbeat_interval}s)...")
                        message = await asyncio.wait_for(
                            connection_queue.get(), 
                            timeout=self._heartbeat_interval
                        )
                        
                        # Update activity and send message
                        logger.debug(f"📨 Got message: {message}")
                        self._connection_manager.update_activity(connection_id)
                        yield self._format_sse_event(message)
                        
                    except asyncio.TimeoutError:
                        # Send heartbeat and update activity
                        logger.debug(f"💓 Sending heartbeat for connection {connection_id}")
                        self._connection_manager.update_activity(connection_id)
                        heartbeat_msg = {
                            "type": "heartbeat",
                            "timestamp": time.time(),
                            "connection_id": connection_id
                        }
                        yield self._format_sse_event(heartbeat_msg)
                        
            except asyncio.CancelledError:
                logger.warning(f"🚫 SSE connection cancelled for workspace {workspace_id}, connection_id: {connection_id}")
                logger.debug(f"🔍 Connection cancelled - processor_task status: {processor_task.done() if processor_task else 'None'}")
            except Exception as e:
                logger.error(f"❌ SSE error for workspace {workspace_id}: {e}")
                logger.exception(f"Full SSE error traceback:")
                yield self._format_sse_event({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": "Server error",
                        "data": str(e)
                    }
                })
            finally:
                # Enhanced cleanup with timeout
                logger.debug(f"🧹 Starting cleanup for connection {connection_id}")
                if processor_task and not processor_task.done():
                    logger.debug(f"🛑 Cancelling processor task for {connection_id}")
                    processor_task.cancel()
                    try:
                        await asyncio.wait_for(processor_task, timeout=2.0)
                        logger.debug(f"✅ Processor task cancelled successfully")
                    except (asyncio.TimeoutError, asyncio.CancelledError):
                        logger.debug(f"⏰ Processor task cleanup timed out or was already cancelled")
                
                # Remove from connection manager
                self._connection_manager.remove_connection(connection_id)
                logger.info(f"🔚 SSE connection closed for workspace {workspace_id}, connection_id: {connection_id}")
        
        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable Nginx buffering
            }
        )
    
    async def _process_incoming_messages(
        self, 
        request: Request, 
        handler: MCPHandler, 
        connection_id: str
    ):
        """Process incoming HTTP requests as MCP messages."""
        try:
            # This is a placeholder for processing incoming messages
            # In a full implementation, this would handle WebSocket-like 
            # bidirectional communication over SSE + HTTP POST
            
            # For FastMCP compatibility, the client will send JSON-RPC requests
            # via separate HTTP POST requests to trigger responses via SSE
            pass
            
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error processing messages for connection {connection_id}: {e}")
    
    async def shutdown(self):
        """Shutdown SSE transport and cleanup resources."""
        logger.info("Shutting down SSE transport")
        await self._connection_manager.shutdown()
        self._connection_handlers.clear()
        logger.info("SSE transport shutdown complete")
    
    def get_transport_stats(self) -> Dict[str, Any]:
        """Get transport statistics including connection stats."""
        return {
            "transport_type": "sse",
            "registered_handlers": len(self._connection_handlers),
            "connection_stats": self._connection_manager.get_stats(),
            "timeouts": {
                "heartbeat_interval": self._heartbeat_interval,
                "connection_timeout": self._connection_timeout,
                "message_timeout": self._message_timeout,
            }
        }

    async def handle_json_rpc_request(
        self, 
        workspace_id: str, 
        request_data: Dict[str, Any],
        auth_context: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Handle JSON-RPC request with timeout and auth context awareness."""
        
        handler = self._connection_handlers.get(workspace_id)
        if not handler:
            return {
                "jsonrpc": "2.0",
                "id": request_data.get("id"),
                "error": {
                    "code": -32001,
                    "message": f"No handler for workspace {workspace_id}"
                }
            }
        
        try:
            # Set auth context on handler for efficient auth-aware operations
            if hasattr(handler, 'set_auth_context') and auth_context:
                handler.set_auth_context(auth_context)
            
            # Parse message
            if "method" in request_data and "id" in request_data:
                message = MCPRequest(**request_data)
            elif "method" in request_data:
                message = MCPNotification(**request_data)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_data.get("id"),
                    "error": {
                        "code": -32600,
                        "message": "Invalid request format"
                    }
                }
            
            # Process message with timeout
            try:
                response = await asyncio.wait_for(
                    handler.handle_message(message),
                    timeout=self._message_timeout
                )
            except asyncio.TimeoutError:
                logger.warning(f"Message handling timed out for workspace {workspace_id}")
                return {
                    "jsonrpc": "2.0",
                    "id": request_data.get("id"),
                    "error": {
                        "code": -32000,
                        "message": "Request timeout",
                        "data": f"Operation timed out after {self._message_timeout} seconds"
                    }
                }
            
            # Send via SSE if there are active connections
            if response:
                response_data = response.model_dump()
                await self._send_to_workspace_connections(workspace_id, response_data)
                return response_data
            
            # Return success for notifications
            if isinstance(message, MCPNotification):
                return {"jsonrpc": "2.0", "result": "ok"}
                
            return {
                "jsonrpc": "2.0",
                "id": request_data.get("id"),
                "result": None
            }
            
        except Exception as e:
            logger.error(f"Error handling JSON-RPC request: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_data.get("id"),
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": str(e)
                }
            }
    
    async def _send_to_workspace_connections(self, workspace_id: str, message: Dict[str, Any]):
        """Send message to all active SSE connections for a workspace."""
        connections_to_remove = []
        
        for connection_id, queue in self._connection_manager._connections.items():
            if connection_id.startswith(f"{workspace_id}:"):
                try:
                    await asyncio.wait_for(queue.put(message), timeout=1.0)
                    self._connection_manager.update_activity(connection_id)
                except asyncio.TimeoutError:
                    logger.warning(f"Message send timeout to connection {connection_id}")
                    connections_to_remove.append(connection_id)
                except Exception as e:
                    logger.error(f"Failed to send message to connection {connection_id}: {e}")
                    connections_to_remove.append(connection_id)
        
        # Clean up dead connections
        for connection_id in connections_to_remove:
            self._connection_manager.remove_connection(connection_id)
    
    def _format_sse_event(self, data: Dict[str, Any]) -> str:
        """Format data as SSE event."""
        json_data = json.dumps(data)
        return f"data: {json_data}\n\n"
    
    async def start(self):
        """Start SSE transport (no-op as it's HTTP-based)."""
        pass
    
    async def stop(self):
        """Stop SSE transport and close all connections."""
        for queue in self._connections.values():
            try:
                await queue.put({"type": "disconnect"})
            except Exception:
                pass
        self._connections.clear()
    
    async def send_message(self, message: MCPMessage):
        """Send message (implemented via SSE queues)."""
        # This is handled by the queue system
        pass
    
    async def receive_message(self) -> MCPMessage | None:
        """Receive message (handled by HTTP requests)."""
        # Messages are received via HTTP POST requests
        return None


class WorkspaceSSEManager:
    """Manager for workspace-specific SSE connections."""
    
    def __init__(self, message_path: str = "/message"):
        # Initialize SSE transport with workspace-specific message path
        self._sse_transport = SSETransport(message_path=message_path)
        self._workspace_servers: Dict[str, Any] = {}
    
    def register_workspace_server(self, workspace_id: str, server):
        """Register a workspace server with SSE transport."""
        self._workspace_servers[workspace_id] = server
        self._sse_transport.register_workspace_handler(workspace_id, server)
    
    async def create_sse_response(
        self, 
        request: Request, 
        workspace_id: str,
        auth_context: Optional[Any] = None
    ) -> StreamingResponse:
        """Create SSE response for workspace (legacy method)."""
        return await self._sse_transport.create_sse_response(
            request, workspace_id, auth_context
        )
    
    async def create_official_sse_connection(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        workspace_id: str,
        auth_context: Optional[Any] = None
    ):
        """Create MCP-compliant SSE connection using official transport."""
        return await self._sse_transport.create_official_sse_connection(
            scope, receive, send, workspace_id, auth_context
        )
    
    async def handle_post_message(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        workspace_id: str,
        auth_context: Optional[Any] = None
    ):
        """Handle POST messages to the message endpoint for workspace."""
        return await self._sse_transport.handle_post_message(
            scope, receive, send, workspace_id, auth_context
        )
    
    async def handle_json_rpc_request(
        self, 
        workspace_id: str, 
        request_data: Dict[str, Any],
        auth_context: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Handle JSON-RPC request for workspace with auth context awareness."""
        return await self._sse_transport.handle_json_rpc_request(
            workspace_id, request_data, auth_context
        )
    
    def get_workspace_server(self, workspace_id: str):
        """Get workspace server if exists."""
        return self._workspace_servers.get(workspace_id)
    
    async def refresh_workspace_tools(self, workspace_id: str):
        """Refresh tools for a workspace server."""
        server = self._workspace_servers.get(workspace_id)
        if server and hasattr(server, 'refresh_tools'):
            await server.refresh_tools()
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        transport_stats = self._sse_transport.get_transport_stats()
        return {
            "registered_workspaces": len(self._workspace_servers),
            "workspace_ids": list(self._workspace_servers.keys()),
            "transport_stats": transport_stats,
        }

    async def shutdown(self):
        """Shutdown all connections and cleanup resources."""
        logger.info("Shutting down WorkspaceSSEManager")
        await self._sse_transport.shutdown()
        self._workspace_servers.clear()
        logger.info("WorkspaceSSEManager shutdown complete")