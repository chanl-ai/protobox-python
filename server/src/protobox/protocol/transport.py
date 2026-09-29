"""
MCP Transport Layer

Provides transport abstractions for different communication methods
including stdio, HTTP, and WebSocket transports.
"""

import asyncio
import json
import sys
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

import websockets
from fastapi import FastAPI
from loguru import logger

from .messages import MCPMessage, MCPNotification, MCPRequest, MCPResponse


class Transport(ABC):
    """Abstract transport base class"""

    def __init__(self):
        self._message_handler: Callable[[MCPMessage], Awaitable[MCPMessage | None]] | None = (
            None
        )

    def set_message_handler(self, handler: Callable[[MCPMessage], Awaitable[MCPMessage | None]]):
        """Set the message handler for incoming messages"""
        self._message_handler = handler

    @abstractmethod
    async def start(self):
        """Start the transport"""
        pass

    @abstractmethod
    async def stop(self):
        """Stop the transport"""
        pass

    @abstractmethod
    async def send_message(self, message: MCPMessage):
        """Send a message"""
        pass

    @abstractmethod
    async def receive_message(self) -> MCPMessage | None:
        """Receive a message"""
        pass


class StdioTransport(Transport):
    """Standard input/output transport for MCP"""

    def __init__(self):
        super().__init__()
        self._running = False
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def start(self):
        """Start stdio transport"""
        logger.info("Starting stdio transport")
        self._running = True

        # Create reader for stdin
        self._reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(self._reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        # For stdout, we'll write directly to sys.stdout
        # This is simpler and more compatible across Python versions

        # Start message processing loop
        asyncio.create_task(self._message_loop())

    async def stop(self):
        """Stop stdio transport"""
        logger.info("Stopping stdio transport")
        self._running = False
        # No need to close stdout

    async def send_message(self, message: MCPMessage):
        """Send message to stdout"""
        if not self._running:
            raise RuntimeError("Transport not started")

        message_json = message.model_dump_json()
        logger.debug(f"Sending message: {message_json}")

        # Write directly to stdout
        sys.stdout.write(message_json + "\n")
        sys.stdout.flush()

    async def receive_message(self) -> MCPMessage | None:
        """Receive message from stdin"""
        if not self._reader:
            raise RuntimeError("Transport not started")

        try:
            line = await self._reader.readline()
            if not line:
                return None

            message_data = json.loads(line.decode().strip())
            logger.debug(f"Received message: {message_data}")

            # Parse message based on type
            if "method" in message_data and "id" in message_data:
                return MCPRequest(**message_data)
            if "method" in message_data:
                return MCPNotification(**message_data)
            if "id" in message_data:
                return MCPResponse(**message_data)
            logger.warning(f"Unknown message format: {message_data}")
            return None

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON message: {e}")
            return None
        except Exception as e:
            logger.error(f"Error receiving message: {e}")
            return None

    async def _message_loop(self):
        """Main message processing loop"""
        while self._running:
            try:
                message = await self.receive_message()
                if message and self._message_handler:
                    response = await self._message_handler(message)
                    if response:
                        await self.send_message(response)
            except Exception as e:
                logger.error(f"Error in message loop: {e}")
                break


class HTTPTransport(Transport):
    """HTTP transport for MCP with remote server capabilities"""

    def __init__(self, host: str = "localhost", port: int = 8080):
        super().__init__()
        self.host = host
        self.port = port
        # Define OpenAPI tags for better documentation organization
        tags_metadata = [
            {
                "name": "System",
                "description": "System health checks and debugging endpoints",
            },
            {
                "name": "Authentication",
                "description": "User authentication and API key management",
            },
            {
                "name": "Workspaces",
                "description": "Workspace management and discovery",
            },
            {
                "name": "Actions",
                "description": "ProtoBox actions - reusable operations that can be executed via MCP, assistants, or APIs",
            },
            {
                "name": "Assistants",
                "description": "OpenAI assistant integration with MCP tool support",
            },
            {
                "name": "Chat",
                "description": "Chat threads and message management with AI assistant integration",
            },
            {
                "name": "MCP (Model Context Protocol)",
                "description": "Model Context Protocol endpoints for tool discovery and execution",
            },
            {
                "name": "FastMCP",
                "description": "FastMCP integration for simplified MCP server creation",
            },
            {
                "name": "Executions",
                "description": "Action execution history and management",
            },
            {
                "name": "Secrets",
                "description": "Secure storage for API keys and sensitive configuration",
            },
        ]

        self.app = FastAPI(
            title="ProtoBox MCP Server",
            version="1.0.0",
            description="ProtoBox enables AI assistants to execute custom actions through the Model Context Protocol (MCP)",
            redirect_slashes=False,  # Don't redirect trailing slashes
            openapi_tags=tags_metadata,
        )
        self._setup_routes()
        self._setup_cors()

    def _setup_cors(self):
        """Setup CORS for remote access"""
        from fastapi.middleware.cors import CORSMiddleware

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # For Phase 1X (no auth), allow all origins
            allow_credentials=False,  # No auth in Phase 1X
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )

    def _setup_routes(self):
        """Setup HTTP routes for remote MCP"""

        async def mcp_handler(request_data: dict):
            """Handle standard MCP HTTP request"""
            try:
                # Parse request
                if "method" in request_data and "id" in request_data:
                    message = MCPRequest(**request_data)
                elif "method" in request_data:
                    message = MCPNotification(**request_data)
                else:
                    message = MCPResponse(**request_data)

                # Process message
                if self._message_handler:
                    response = await self._message_handler(message)
                    if response:
                        return response.model_dump()

                return {"jsonrpc": "2.0", "id": request_data.get("id"), "result": None}

            except Exception as e:
                logger.error(f"Error handling HTTP request: {e}")
                return {
                    "jsonrpc": "2.0",
                    "id": request_data.get("id"),
                    "error": {"code": -32603, "message": "Internal error", "data": str(e)},
                }

        # Register both with and without trailing slash
        self.app.post("/mcp")(mcp_handler)
        self.app.post("/mcp/")(mcp_handler)

        @self.app.get("/mcp/sse")
        async def handle_mcp_sse():
            """Handle MCP Server-Sent Events for streaming responses"""
            from fastapi.responses import StreamingResponse

            async def event_stream():
                # For Phase 1X, basic SSE implementation
                yield 'data: {"jsonrpc": "2.0", "method": "initialized"}\n\n'

                # Keep connection alive
                while True:
                    await asyncio.sleep(30)
                    yield 'data: {"type": "heartbeat"}\n\n'

            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                },
            )

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint for monitoring"""
            return {
                "status": "healthy",
                "transport": "http",
                "version": "1.0.0",
                "capabilities": {"streaming": True, "sse": True, "remote": True},
            }

        @self.app.get("/mcp/capabilities")
        async def mcp_capabilities():
            """MCP server capabilities endpoint"""
            return {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "voiceman-remote-mcp-server", "version": "1.0.0"},
                "capabilities": {
                    "tools": {"listChanged": True},
                    "resources": {"subscribe": True, "listChanged": True},
                    "streaming": True,
                    "remoteAccess": True,
                },
            }

        @self.app.get("/")
        async def root():
            """Root endpoint with server info"""
            return {
                "name": "VoiceMan Remote MCP Server",
                "version": "1.0.0",
                "status": "running",
                "endpoints": {
                    "mcp": "/mcp",
                    "sse": "/mcp/sse",
                    "health": "/health",
                    "capabilities": "/mcp/capabilities",
                },
                "documentation": "https://github.com/voiceman/mcp-server",
            }

    async def start(self):
        """Start HTTP server"""
        logger.info(f"Starting HTTP transport on {self.host}:{self.port}")

        # Suppress websockets deprecation warnings as we don't use WebSockets
        import warnings

        warnings.filterwarnings("ignore", category=DeprecationWarning, module="websockets")
        warnings.filterwarnings(
            "ignore", category=DeprecationWarning, module="uvicorn.protocols.websockets"
        )

        import uvicorn

        config = uvicorn.Config(app=self.app, host=self.host, port=self.port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    async def stop(self):
        """Stop HTTP server"""
        logger.info("Stopping HTTP transport")
        # Server shutdown is handled by uvicorn

    async def send_message(self, message: MCPMessage):
        """Send message via HTTP (not applicable for server)"""
        # HTTP transport is server-only, messages are sent as responses
        pass

    async def receive_message(self) -> MCPMessage | None:
        """Receive message via HTTP (handled by routes)"""
        # HTTP transport receives messages via route handlers
        return None


class WebSocketTransport(Transport):
    """WebSocket transport for MCP"""

    def __init__(self, host: str = "localhost", port: int = 8081):
        super().__init__()
        self.host = host
        self.port = port
        self._clients: dict[str, websockets.WebSocketServerProtocol] = {}
        self._server = None

    async def start(self):
        """Start WebSocket server"""
        logger.info(f"Starting WebSocket transport on {self.host}:{self.port}")

        async def handle_client(websocket, path):
            """Handle WebSocket client connection"""
            client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
            self._clients[client_id] = websocket
            logger.info(f"WebSocket client connected: {client_id}")

            try:
                async for message_data in websocket:
                    try:
                        message_json = json.loads(message_data)
                        logger.debug(f"Received WebSocket message: {message_json}")

                        # Parse message
                        if "method" in message_json and "id" in message_json:
                            message = MCPRequest(**message_json)
                        elif "method" in message_json:
                            message = MCPNotification(**message_json)
                        else:
                            message = MCPResponse(**message_json)

                        # Process message
                        if self._message_handler:
                            response = await self._message_handler(message)
                            if response:
                                await websocket.send(response.model_dump_json())

                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse WebSocket message: {e}")
                    except Exception as e:
                        logger.error(f"Error processing WebSocket message: {e}")

            except websockets.exceptions.ConnectionClosed:
                logger.info(f"WebSocket client disconnected: {client_id}")
            finally:
                if client_id in self._clients:
                    del self._clients[client_id]

        self._server = await websockets.serve(handle_client, self.host, self.port)

    async def stop(self):
        """Stop WebSocket server"""
        logger.info("Stopping WebSocket transport")
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def send_message(self, message: MCPMessage):
        """Send message to all connected clients"""
        if not self._clients:
            return

        message_json = message.model_dump_json()
        disconnected_clients = []

        for client_id, websocket in self._clients.items():
            try:
                await websocket.send(message_json)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.append(client_id)
            except Exception as e:
                logger.error(f"Error sending message to client {client_id}: {e}")
                disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            if client_id in self._clients:
                del self._clients[client_id]

    async def receive_message(self) -> MCPMessage | None:
        """Receive message via WebSocket (handled by connection handler)"""
        # WebSocket transport receives messages via connection handlers
        return None
