"""
MCP Server Implementation

Main server class that coordinates all MCP components including
transport, tools, resources, context management, and optional admin API.
"""

import asyncio
from typing import Any

from fastapi import Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from loguru import logger
from mcp.server.lowlevel import NotificationOptions
from mcp.server.models import InitializationOptions

from .actions.executor import ActionExecutor
from .admin.config import settings
from .admin.cors_config import get_cors_origins
from .admin.routers.mcp_multitenant import create_mcp_server
from .config.settings import Config
from .context.manager import ContextManager
from .protocol.custom_sse_transport import CustomSseTransport
from .protocol.messages import (
    MCPErrorCode,
    MCPMessage,
    MCPMethod,
    MCPNotification,
    MCPRequest,
    MCPResponse,
    ToolInfo,
)
from .protocol.transport import HTTPTransport, StdioTransport, Transport
from .resources.manager import ResourceManager
from .tools.base import MCPTool


class MCPServer:
    """Main MCP server implementation with optional admin API support"""

    def __init__(
        self,
        name: str = "protobox-mcp-server",
        version: str = "1.0.0",
        transport: Transport | None = None,
        config: Config | None = None,
    ):
        self.name = name
        self.version = version
        self.transport = transport or StdioTransport()
        self.config = config

        # Core components
        self.action_executor = ActionExecutor()
        self.context_manager = ContextManager()
        self.resource_manager = ResourceManager()

        # Admin API components (optional)
        self.admin_app = None
        self.admin_server = None
        self.db_manager = None
        self.secret_manager = None

        # Tool registry
        self._tools: dict[str, MCPTool] = {}

        # Server state
        self._initialized = False
        self._running = False

        # Setup transport message handler
        self.transport.set_message_handler(self._handle_message)

        logger.info(f"MCP Server initialized: {self.name} v{self.version}")

    async def start(self):
        """Start the MCP server"""
        logger.info("Starting MCP server...")

        # Initialize monitoring
        try:
            import os

            from .monitoring import init_sentry

            init_sentry(environment=os.getenv("ENV", "development"))
        except Exception as e:
            logger.warning(f"Failed to initialize monitoring: {e}")

        try:
            # Initialize components
            await self.action_executor.initialize()
            await self.context_manager.initialize()
            await self.resource_manager.initialize()

            # Initialize admin API if enabled
            await self._initialize_admin_api()

            # Start transport
            await self.transport.start()

            self._running = True
            logger.info("MCP server started successfully")

        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise

    async def stop(self):
        """Stop the MCP server"""
        logger.info("Stopping MCP server...")

        self._running = False

        try:
            # Stop admin API if running
            if self.admin_server:
                await self._stop_admin_api()

            # Stop transport
            await self.transport.stop()

            # Cleanup components
            await self.action_executor.cleanup()
            await self.context_manager.cleanup()
            await self.resource_manager.cleanup()

            # Cleanup admin components
            if self.db_manager:
                await self.db_manager.disconnect()

            logger.info("MCP server stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping MCP server: {e}")

    async def _initialize_admin_api(self):
        """Initialize the admin API components"""
        try:
            import uvicorn
            from fastapi import FastAPI

            from .admin.database.connection import (
                DatabaseConnection,
                initialize_database,
            )
            from .admin.router import admin_router
            from .admin.secrets.encryption import SecretEncryption

            logger.info("Initializing admin API...")

            # Initialize database connection
            # Extract database name from the MongoDB URL
            import urllib.parse

            parsed_url = urllib.parse.urlparse(self.config.admin.mongodb_url)
            database_name = (
                parsed_url.path.lstrip("/").split("?")[0] if parsed_url.path else "mcp_server"
            )

            logger.info(f"Using database name: {database_name}")
            self.db_manager = await initialize_database(
                connection_string=self.config.admin.mongodb_url, database_name=database_name
            )

            # Initialize audit service
            from .admin.services.audit_service import AuditService

            self.audit_service = AuditService(self.db_manager.database)
            await self.audit_service.initialize()
            logger.info("Audit service initialized")

            # Initialize secret encryption
            self.secret_manager = SecretEncryption()

            # Determine host and port for admin API
            admin_host = self.config.admin.host or self.config.transport.host
            admin_port = self.config.admin.port or self.config.transport.port

            # If admin API is on the same port as MCP transport, integrate with HTTP transport
            if (
                isinstance(self.transport, HTTPTransport)
                and admin_host == self.config.transport.host
                and admin_port == self.config.transport.port
            ):
                logger.info("Using integrated mode - admin API on same port as MCP transport")

                # Add CORS middleware
                cors_origins = get_cors_origins()
                logger.info(f"CORS origins configured: {cors_origins}")

                self.transport.app.add_middleware(
                    CORSMiddleware,
                    allow_origins=cors_origins,
                    allow_credentials=True,
                    allow_methods=["*"],
                    allow_headers=["*"],
                )

                # Add dependency injection for admin services
                from .admin.router import get_database

                async def get_db_override():
                    return self.db_manager

                self.transport.app.dependency_overrides[get_database] = get_db_override

                # Include admin router directly in the HTTP transport's app
                logger.info(f"Including admin router with {len(admin_router.routes)} routes")
                self.transport.app.include_router(admin_router, prefix=self.config.admin.prefix)
                logger.info(
                    f"Admin API router included in HTTP transport at {self.config.admin.prefix}"
                )
                logger.info(f"Total app routes after inclusion: {len(self.transport.app.routes)}")

                # Mount MCP execution routers at root level (moved from admin)
                try:
                    from .admin.routers.mcp_multitenant import router as mcp_router
                    from .admin.routers.mcp_multitenant import (
                        router as multitenant_router,
                    )

                    self.transport.app.include_router(mcp_router)
                    self.transport.app.include_router(multitenant_router)
                    logger.info("Mounted MCP execution routers at root level (using SSE implementation from feature/mcp)")
                except Exception as e:
                    logger.warning(f"Failed to mount MCP execution routers: {e}")

                # Mount multi-tenant MCP app
                try:
                    from .admin.routers.mcp_multitenant import mount_multitenant_mcp

                    await mount_multitenant_mcp(self.transport.app)
                    logger.info("Mounted multi-tenant MCP app")
                except Exception as e:
                    logger.warning(f"Failed to mount multi-tenant MCP: {e}")

                # Public MCP app removed; use scoped /mcp/{workspace_id} endpoints only

                # Add detailed error handler in dev_test mode
                await self._setup_error_handlers(self.transport.app)

            else:
                logger.info("Using separate mode - creating separate admin API app")
                # Create separate FastAPI app for admin API
                self.admin_app = FastAPI(
                    title=f"{self.name} Admin API",
                    version=self.version,
                    description="Administrative API for MCP Server",
                )

                # Add CORS middleware
                cors_origins = get_cors_origins()
                logger.info(f"Admin CORS origins configured: {cors_origins}")

                self.admin_app.add_middleware(
                    CORSMiddleware,
                    allow_origins=cors_origins,
                    allow_credentials=True,
                    allow_methods=["*"],
                    allow_headers=["*"],
                )

                # Add dependency injection for admin services
                from .admin.router import get_database

                async def get_db_override_admin():
                    return self.db_manager

                self.admin_app.dependency_overrides[get_database] = get_db_override_admin

                # Include admin router
                self.admin_app.include_router(admin_router, prefix=self.config.admin.prefix)

                # Mount MCP execution routers at root level (moved from admin)
                try:
                    from .admin.routers.mcp_multitenant import router as mcp_router
                    from .admin.routers.mcp_multitenant import (
                        router as multitenant_router,
                    )

                    self.admin_app.include_router(mcp_router)
                    self.admin_app.include_router(multitenant_router)
                    logger.info("Mounted MCP execution routers at root level on separate admin app (using Simple implementation)")
                except Exception as e:
                    logger.warning(f"Failed to mount MCP execution routers: {e}")

                # Add detailed error handler in dev_test mode
                await self._setup_error_handlers(self.admin_app)

                # Start separate server for admin API
                config = uvicorn.Config(
                    self.admin_app, host=admin_host, port=admin_port, log_level="info"
                )
                self.admin_server = uvicorn.Server(config)

                # Start admin server in background
                loop = asyncio.get_event_loop()
                self.admin_task = loop.create_task(self.admin_server.serve())

                logger.info(f"Admin API server started on {admin_host}:{admin_port}")

            logger.info(
                f"Admin API initialized successfully with prefix {self.config.admin.prefix}"
            )

            # Run startup smoke tests
            await self._run_startup_smoke_tests()

        except ImportError as e:
            logger.error(f"Failed to import admin API components: {e}")
            logger.error("Make sure admin API dependencies are installed")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize admin API: {e}")
            raise

    async def _setup_error_handlers(self, app):
        """Setup detailed error handlers for dev_test mode"""
        import os
        import traceback

        from fastapi import Request
        from fastapi.exceptions import HTTPException
        from fastapi.responses import JSONResponse

        # Check if we're in dev_test mode
        env = os.getenv("ENV", "dev")
        is_dev_test = env == "dev_test"

        @app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            """Handle HTTP exceptions with detailed info in dev_test mode"""
            response_content = {"error": exc.detail, "status_code": exc.status_code}

            if is_dev_test:
                # Add detailed information in dev_test mode
                response_content.update(
                    {
                        "path": request.url.path,
                        "method": request.method,
                        "headers": dict(request.headers) if is_dev_test else None,
                    }
                )

            return JSONResponse(status_code=exc.status_code, content=response_content)

        @app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            """Handle general exceptions with detailed info in dev_test mode"""
            logger.error(f"Unhandled exception: {exc}")

            response_content = {"error": "Internal server error", "status_code": 500}

            if is_dev_test:
                # Add detailed error information in dev_test mode
                response_content.update(
                    {
                        "detail": str(exc),
                        "type": type(exc).__name__,
                        "traceback": traceback.format_exc().split("\n"),
                        "path": request.url.path,
                        "method": request.method,
                    }
                )

            return JSONResponse(status_code=500, content=response_content)

    async def _run_startup_smoke_tests(self):
        """Run smoke tests on startup to catch configuration issues early."""
        try:
            from .admin.health import HealthChecker

            logger.info("Running startup smoke tests...")

            health_checker = HealthChecker(
                db_connection=self.db_manager, secret_encryption=self.secret_manager
            )

            # Run smoke tests
            results = await health_checker.run_smoke_tests()

            # Log results
            passed = 0
            failed = 0
            warnings = 0

            for test_name, result in results.items():
                status = result.get("status", "unknown")
                if status == "passed":
                    passed += 1
                    logger.debug(f"✓ {test_name}: {result.get('message', 'Passed')}")
                elif status == "warning":
                    warnings += 1
                    logger.warning(
                        f"⚠ {test_name}: {result.get('message', result.get('error', 'Warning'))}"
                    )
                else:
                    failed += 1
                    logger.error(f"✗ {test_name}: {result.get('error', 'Failed')}")

            logger.info(
                f"Startup smoke tests completed: {passed} passed, {warnings} warnings, {failed} failed"
            )

            # Don't fail startup on smoke test failures, just warn
            if failed > 0:
                logger.warning(
                    "Some smoke tests failed. The server will continue but may have issues."
                )

        except Exception as e:
            logger.error(f"Failed to run startup smoke tests: {e}")
            # Don't fail startup on smoke test errors

    async def _stop_admin_api(self):
        """Stop the admin API server"""
        try:
            if self.admin_server:
                logger.info("Stopping admin API server...")
                self.admin_server.should_exit = True
                if hasattr(self, "admin_task"):
                    await self.admin_task
                logger.info("Admin API server stopped")
        except Exception as e:
            logger.error(f"Error stopping admin API: {e}")

    def register_tool(self, tool: MCPTool):
        """Register a tool with the server"""
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def unregister_tool(self, tool_name: str):
        """Unregister a tool from the server"""
        if tool_name in self._tools:
            del self._tools[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")

    async def _handle_message(self, message: MCPMessage) -> MCPMessage | None:
        """Handle incoming MCP messages"""
        try:
            if isinstance(message, MCPRequest):
                return await self._handle_request(message)
            if isinstance(message, MCPNotification):
                await self._handle_notification(message)
                return None
            logger.warning(f"Received unexpected message type: {type(message)}")
            return None

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            if isinstance(message, MCPRequest):
                return MCPResponse(
                    id=message.id,
                    error={
                        "code": MCPErrorCode.INTERNAL_ERROR,
                        "message": "Internal server error",
                        "data": str(e),
                    },
                )
            return None

    async def _handle_request(self, request: MCPRequest) -> MCPResponse:
        """Handle MCP requests"""
        method = request.method

        try:
            if method == MCPMethod.INITIALIZE:
                return await self._handle_initialize(request)
            if method == MCPMethod.TOOLS_LIST:
                return await self._handle_tools_list(request)
            if method == MCPMethod.TOOLS_CALL:
                return await self._handle_tools_call(request)
            if method == MCPMethod.RESOURCES_LIST:
                return await self._handle_resources_list(request)
            if method == MCPMethod.RESOURCES_READ:
                return await self._handle_resources_read(request)
            return MCPResponse(
                id=request.id,
                error={
                    "code": MCPErrorCode.METHOD_NOT_FOUND,
                    "message": f"Method not found: {method}",
                },
            )

        except Exception as e:
            logger.error(f"Error handling request {method}: {e}")
            return MCPResponse(
                id=request.id,
                error={
                    "code": MCPErrorCode.INTERNAL_ERROR,
                    "message": "Internal server error",
                    "data": str(e),
                },
            )

    async def _handle_notification(self, notification: MCPNotification):
        """Handle MCP notifications"""
        method = notification.method

        try:
            if method == MCPMethod.INITIALIZED:
                await self._handle_initialized(notification)
            elif method == MCPMethod.NOTIFICATIONS_CANCELLED:
                await self._handle_cancelled(notification)
            else:
                logger.warning(f"Unknown notification method: {method}")

        except Exception as e:
            logger.error(f"Error handling notification {method}: {e}")

    async def _handle_initialize(self, request: MCPRequest) -> MCPResponse:
        """Handle initialize request"""
        logger.info("Handling initialize request")

        # Extract client capabilities
        params = request.params or {}
        client_info = params.get("clientInfo", {})

        logger.info(f"Client info: {client_info}")

        # Return server capabilities
        result = {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": self.name, "version": self.version},
            "capabilities": {
                "tools": {"listChanged": True},
                "resources": {"subscribe": True, "listChanged": True},
                "prompts": {"listChanged": True},
                "sampling": {},
            },
        }

        # Add admin API info if enabled
        if self.config and self.config.admin.enabled:
            result["serverInfo"]["admin_api"] = {
                "enabled": True,
                "prefix": self.config.admin.prefix,
                "endpoints": 28,
            }

        self._initialized = True
        return MCPResponse(id=request.id, result=result)

    async def _handle_initialized(self, notification: MCPNotification):
        """Handle initialized notification"""
        logger.info("Client initialized")

    async def _handle_tools_list(self, request: MCPRequest) -> MCPResponse:
        """Handle tools list request"""
        logger.debug("Handling tools list request")

        tools = []
        for tool in self._tools.values():
            tools.append(
                ToolInfo(
                    name=tool.name, description=tool.description, inputSchema=tool.input_schema
                )
            )

        result = {"tools": [tool.model_dump() for tool in tools]}
        return MCPResponse(id=request.id, result=result)

    async def _handle_tools_call(self, request: MCPRequest) -> MCPResponse:
        """Handle tool call request"""
        params = request.params or {}
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        logger.info(f"Handling tool call: {tool_name} with args: {arguments}")

        if tool_name not in self._tools:
            return MCPResponse(
                id=request.id,
                error={
                    "code": MCPErrorCode.TOOL_NOT_FOUND,
                    "message": f"Tool not found: {tool_name}",
                },
            )

        try:
            tool = self._tools[tool_name]

            # Get or create context for this request
            context = await self.context_manager.get_context(
                session_id=str(request.id), tool_name=tool_name
            )

            # Execute tool
            result = await tool.execute(arguments, context)

            # Update context
            await self.context_manager.update_context(context)

            # Format response
            content = []
            if isinstance(result, str):
                content.append({"type": "text", "text": result})
            elif isinstance(result, dict):
                content.append({"type": "text", "text": str(result)})
            else:
                content.append({"type": "text", "text": str(result)})

            response_result = {"content": content, "isError": False}

            return MCPResponse(id=request.id, result=response_result)

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")

            error_content = [{"type": "text", "text": f"Error executing tool: {str(e)}"}]

            response_result = {"content": error_content, "isError": True}

            return MCPResponse(id=request.id, result=response_result)

    async def _handle_resources_list(self, request: MCPRequest) -> MCPResponse:
        """Handle resources list request"""
        logger.debug("Handling resources list request")

        resources = await self.resource_manager.list_resources()
        result = {"resources": [resource.model_dump() for resource in resources]}

        return MCPResponse(id=request.id, result=result)

    async def _handle_resources_read(self, request: MCPRequest) -> MCPResponse:
        """Handle resource read request"""
        params = request.params or {}
        uri = params.get("uri")

        logger.debug(f"Handling resource read request: {uri}")

        if not uri:
            return MCPResponse(
                id=request.id,
                error={
                    "code": MCPErrorCode.INVALID_PARAMS,
                    "message": "Missing required parameter: uri",
                },
            )

        try:
            contents = await self.resource_manager.read_resource(uri)
            result = {"contents": [content.model_dump() for content in contents]}

            return MCPResponse(id=request.id, result=result)

        except Exception as e:
            logger.error(f"Error reading resource {uri}: {e}")
            return MCPResponse(
                id=request.id,
                error={
                    "code": MCPErrorCode.RESOURCE_NOT_FOUND,
                    "message": f"Resource not found: {uri}",
                    "data": str(e),
                },
            )

    async def _handle_cancelled(self, notification: MCPNotification):
        """Handle cancelled notification"""
        params = notification.params or {}
        request_id = params.get("requestId")
        logger.info(f"Request cancelled: {request_id}")

        # TODO: Implement request cancellation logic

    async def send_notification(self, method: str, params: dict[str, Any] | None = None):
        """Send a notification to clients"""
        notification = MCPNotification(method=method, params=params)
        await self.transport.send_message(notification)

    async def run_forever(self):
        """Run the server forever"""
        if not self._running:
            await self.start()

        try:
            while self._running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            await self.stop()


# Convenience function for running the server
async def run_mcp_server(
    transport: Transport | None = None,
    tools: list[MCPTool] | None = None,
    config: Config | None = None,
):
    """Run an MCP server with the specified configuration"""
    server = MCPServer(transport=transport, config=config)

    # Register tools
    if tools:
        for tool in tools:
            server.register_tool(tool)

    # Run server
    await server.run_forever()


def main():
    """Main entry point for running the MCP server."""
    asyncio.run(run_mcp_server())


if __name__ == "__main__":
    main()


# FastAPI app export for direct uvicorn usage
def create_app():
    """Create and configure a FastAPI app instance for direct uvicorn usage"""
    from contextlib import asynccontextmanager

    from fastapi import FastAPI

    from .config.settings import Config

    # Load configuration from environment
    config = Config.from_env()

    # Admin API is always enabled when running the server directly
    # The server IS the admin API - that's its purpose
    config.admin.enabled = True

    # Validate required configuration
    settings.validate_required_secrets()

    if not config.admin.mongodb_url:
        raise ValueError(
            "MCP_MONGODB_URL environment variable is required. See .env.example."
        )

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

    # Create lifespan context manager
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        # Admin is always enabled when running the server
        import urllib.parse

        from .admin.database.connection import initialize_database

        # Parse database name from connection URL
        parsed_url = urllib.parse.urlparse(config.admin.mongodb_url)
        database_name = (
            parsed_url.path.lstrip("/").split("?")[0] if parsed_url.path else "mcp_server"
        )

        # Initialize database
        app.state.db_manager = await initialize_database(
            connection_string=config.admin.mongodb_url, database_name=database_name
        )

        # Initialize audit service
        from .admin.services.audit_service import AuditService

        app.state.audit_service = AuditService(app.state.db_manager.database)
        await app.state.audit_service.initialize()
        logger.info("Audit service initialized")

        # Initialize Firebase Admin SDK
        from .admin.auth.firebase_auth import get_firebase_auth

        app.state.firebase_auth = get_firebase_auth()
        logger.info("Firebase authentication initialized")

        # Schedule startup checks to run AFTER server is fully started
        # We'll run them as a background task after the yield
        app.state.startup_check_results = {"status": "pending", "message": "Startup checks will run after server initialization"}

        # Public MCP app removed; use scoped /mcp/{workspace_id} endpoints only

        # Schedule startup checks to run as a background task AFTER server starts
        async def run_startup_checks_after_startup():
            try:
                # Wait for server to be fully responsive
                import asyncio

                from .admin.startup_checks import (
                    run_startup_checks,
                    validate_startup_check_config,
                )
                await asyncio.sleep(5)  # Wait 5 seconds for server to be fully started
                
                # Validate configuration
                validate_startup_check_config()
                
                # Initialize integrations registry
                logger.info("🔌 Initializing integrations registry...")
                from .admin.integrations import initialize_integrations
                initialize_integrations()
                
                # Run startup checks
                logger.info("🚀 Running startup integration checks (server is now ready)...")
                startup_results = await run_startup_checks()
                app.state.startup_check_results = startup_results
                
                if startup_results.get("status") == "failed":
                    error_msg = startup_results.get('error', 'Check logs for details')
                    logger.error(f"🚨 Startup checks failed: {error_msg}")
                    
                    # Check if we should fail fast and exit
                    if settings.get_bool("STARTUP_CHECKS_FAIL_FAST", False):
                        logger.error("💥 FAIL_FAST enabled - exiting due to startup check failures")
                        import sys
                        sys.exit(1)
                else:
                    logger.info(f"✅ Startup checks completed: {startup_results.get('status')}")
                    
            except Exception as e:
                logger.warning(f"Startup checks failed to run: {e}")
                app.state.startup_check_results = {"status": "error", "error": str(e)}
        
        # Create background task for startup checks (runs after yield when server is ready)
        import asyncio
        asyncio.create_task(run_startup_checks_after_startup())

        yield

        # Shutdown
        if hasattr(app.state, "db_manager"):
            await app.state.db_manager.disconnect()

    # Create FastAPI app with lifespan
    app = FastAPI(
        title=f"{config.server.name} API",
        version=config.server.version,
        description="MCP Server with Admin API - ProtoBox enables AI assistants to execute custom actions through the Model Context Protocol",
        openapi_tags=tags_metadata,
        lifespan=lifespan,
        redirect_slashes=False,  # Prevent automatic redirects that lose auth headers
    )

    # Add CORS middleware
    cors_origins = get_cors_origins()
    logger.info(f"CORS origins configured for admin app: {cors_origins}")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Import authentication dependencies
    from .admin.auth.decorators import AuthContext
    from .admin.auth.mcp_bearer import mcp_bearer_auth
    from .admin.utils.validators import validate_workspace_id
    
    async def get_mcp_auth_context_for_sse(
        request: Request,
        workspace_id: str,
    ) -> AuthContext:
        """
        Authentication dependency for MCP SSE endpoints.
        Validates MCP tokens via JWT authentication in headers and query parameters.
        Ensures the workspace_id path parameter matches the token's workspace_id.
        """
        try:
            # Validate workspace_id format
            validate_workspace_id(workspace_id)
            
            # Extract token from query parameters if present
            query_token = request.query_params.get("token")
            
            # First, validate authentication and extract workspace_id from token
            # This will check both Bearer header and query parameter token
            auth_info = await mcp_bearer_auth.validate_with_auto_workspace(request, token=query_token)
            
            # Security check: Ensure the workspace_id in the path matches the token
            token_workspace_id = auth_info.get("workspace_id")
            if not token_workspace_id:
                logger.error(f"Token missing workspace_id - {auth_info}")
                raise HTTPException(
                    status_code=401,
                    detail="Token does not contain workspace_id information"
                )
            
            if token_workspace_id != workspace_id:
                logger.warning(
                    f"Workspace ID mismatch - Path: {workspace_id}, Token: {token_workspace_id}, "
                    f"User: {auth_info.get('user_id', 'unknown')}"
                )
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied: Token is not valid for workspace {workspace_id}"
                )
            
            # Create auth context and attach to request
            logger.debug(f"Auth info: {auth_info}")
            auth_context = AuthContext(auth_info)
            request.state.token = query_token
            request.state.auth = auth_context
            request.state.workspace_id = workspace_id  # Store for the multitenant server
            
            logger.info(
                f"MCP SSE access granted - Type: {auth_info['type']}, "
                f"Workspace: {workspace_id}, "
                f"User: {auth_info.get('user_id', 'unknown')}, "
                f"Scopes: {auth_info.get('scopes', [])}"
            )
            
            return auth_context
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"MCP SSE authentication error: {e}")
            raise HTTPException(status_code=500, detail="Authentication service error")

    # Create authenticated wrapper for POST message handler
    async def authenticated_message_handler(scope, receive, send):
        """
        Wrapper for SseServerTransport.handle_post_message with authentication.
        Validates JWT tokens and ensures workspace context is properly set.
        Supports both Bearer header and query parameter authentication.
        """
        # Convert ASGI scope to FastAPI request for authentication
        from starlette.requests import Request as StarletteRequest

        # Create request object from ASGI scope
        request = StarletteRequest(scope, receive, send)
        
        # Extract token from query parameters if present
        query_token = request.query_params.get("token")
        
        # Expected path: /mcp/sse/messages
        # Use auto-workspace validation to get workspace_id from token
        try:
            # Authenticate and auto-discover workspace_id from token
            # This will check both Bearer header and query parameter token
            auth_info = await mcp_bearer_auth.validate_with_auto_workspace(request, token=query_token)
            
            # Ensure workspace_id is present in token
            workspace_id = auth_info.get("workspace_id")
            if not workspace_id:
                raise HTTPException(
                    status_code=401,
                    detail="Token must contain workspace_id for MCP access"
                )
            
            # Store workspace_id in request state for the multitenant server
            request.state.workspace_id = workspace_id
            request.state.auth = auth_info
            
            logger.info(
                f"MCP SSE message access granted - Type: {auth_info['type']}, "
                f"Workspace: {workspace_id}, "
                f"User: {auth_info.get('user_id', 'unknown')}"
            )
            
            # If authentication succeeds, proceed with the original handler
            await sse.handle_post_message(scope, receive, send)
            
        except HTTPException as e:
            logger.error(f"Authentication error in message handler: {e}")
            # Send authentication error response
            response_data = {
                "type": "http.response.start",
                "status": e.status_code,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"access-control-allow-origin", b"*"],
                    [b"access-control-allow-methods", b"*"],
                    [b"access-control-allow-headers", b"*"],
                ]
            }
            await send(response_data)
            
            error_message = f'{{"error": "{e.detail}"}}'
            await send({
                "type": "http.response.body",
                "body": error_message.encode("utf-8")
            })
        except Exception as e:
            logger.error(f"Authentication error in message handler: {e}")
            # Send server error response
            response_data = {
                "type": "http.response.start", 
                "status": 500,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"access-control-allow-origin", b"*"],
                ]
            }
            await send(response_data)
            
            error_message = '{"error": "Authentication service error"}'
            await send({
                "type": "http.response.body",
                "body": error_message.encode("utf-8")
            })

    sse = CustomSseTransport("/mcp/sse/messages/")
    app.mount("/mcp/sse/messages/", authenticated_message_handler)
    server = create_mcp_server()

    @app.post("/mcp/{workspace_id}")
    async def mcp_workspace_post_handler(
        workspace_id: str,
        request: Request,
        auth: AuthContext = Depends(get_mcp_auth_context_for_sse)
    ):
        """
        Handle POST requests to /mcp/{workspace_id} for HTTP-based JSON-RPC.
        This is used by FastMCP and other clients that use HTTP POST instead of SSE.
        """
        import json

        from fastapi.responses import JSONResponse

        # Check workspace access
        if auth.workspace_id != workspace_id:
            raise HTTPException(status_code=403, detail="Access denied to workspace")
        
        # Get request body
        try:
            body = await request.body()
            data = json.loads(body) if body else {}
        except Exception as e:
            logger.error(f"Failed to parse MCP request body: {e}")
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid JSON-RPC request"}
            )
        
        # Process the JSON-RPC message through the MCP server
        from mcp.types import JSONRPCNotification, JSONRPCRequest
        try:
            # Check if this is a notification (no id field) or a request
            if "id" in data:
                # It's a request - expects a response
                message = JSONRPCRequest.model_validate(data)
            else:
                # It's a notification - no response expected
                notification = JSONRPCNotification.model_validate(data)
                # Handle notifications (like notifications/initialized)
                logger.info(f"Received notification: {notification.method}")
                # Notifications don't require a response - return empty response
                return Response(content="", status_code=200)
            
            # Set workspace context
            request.state.workspace_id = workspace_id
            request.state.db_manager = app.state.db_manager
            
            # For HTTP POST, we need to handle the request directly
            # The MCP server decorators handle SSE transport, not direct HTTP
            
            # Handle different MCP methods
            if message.method == "initialize":
                return JSONResponse(content={
                    "jsonrpc": "2.0",
                    "id": message.id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {
                            "name": "ProtoBox MCP",
                            "version": "1.0.0"
                        },
                        "capabilities": {
                            "tools": {"listChanged": False},
                            "resources": {"subscribe": False},
                            "prompts": {"listChanged": False}
                        }
                    }
                })
            
            elif message.method == "tools/list":
                # For HTTP POST, return a simple list of available tools
                # In production, this would query the actual tools for the workspace
                tools = [
                    {
                        "name": "test-action",
                        "description": "Execute a test action",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "message": {"type": "string", "description": "Test message"}
                            }
                        }
                    },
                    {
                        "name": "search-knowledge",
                        "description": "Search the knowledge base",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Search query"},
                                "limit": {"type": "integer", "description": "Maximum results", "default": 10}
                            },
                            "required": ["query"]
                        }
                    },
                    {
                        "name": "list-actions",
                        "description": "List available actions in the workspace",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                ]
                
                return JSONResponse(content={
                    "jsonrpc": "2.0",
                    "id": message.id,
                    "result": {
                        "tools": tools
                    }
                })
            
            elif message.method == "tools/call":
                # Tool execution would go here
                tool_name = message.params.get("name") if hasattr(message, 'params') else None
                return JSONResponse(content={
                    "jsonrpc": "2.0",
                    "id": message.id,
                    "error": {
                        "code": -32601,
                        "message": f"Tool execution not yet implemented for HTTP POST: {tool_name}"
                    }
                })
            
            # For other methods, return error
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": message.id if hasattr(message, 'id') else None,
                "error": {
                    "code": -32601,
                    "message": f"Method {message.method} not yet implemented for HTTP POST"
                }
            })
        except Exception as e:
            logger.error(f"Error handling MCP request: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "jsonrpc": "2.0",
                    "id": data.get("id"),
                    "error": {
                        "code": -32603,
                        "message": "Internal error",
                        "data": str(e)
                    }
                }
            )

    @app.get("/mcp/{workspace_id}/sse")
    async def handle_sse(
        request: Request, 
        workspace_id: str,
        auth: AuthContext = Depends(get_mcp_auth_context_for_sse)
    ):
        logger.info(f"Handling authenticated SSE request for workspace: {workspace_id}")
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name=f"workspace-{workspace_id}",
                    server_version="0.1.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
        # Return empty response to avoid NoneType error
        return Response()

    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": config.server.name}

    # Add admin routes (always enabled when running the server)
    from .admin.router import admin_router, get_database

    # Add dependency injection for admin services
    async def get_db_override():
        return app.state.db_manager

    app.dependency_overrides[get_database] = get_db_override

    # Include admin router
    logger.info(f"Mounting admin router at {config.admin.prefix}")
    app.include_router(admin_router, prefix=config.admin.prefix)

    # Note: Public MCP app mounting needs to be done after startup
    # It requires async initialization, so we'll skip it here

    # Add OAuth discovery endpoints at root level for FastMCP compatibility
    @app.get("/.well-known/oauth-protected-resource")
    async def oauth_protected_resource_discovery():
        """OAuth protected resource metadata for MCP server."""
        return {
            "resource": f"{settings.mcp_server_url}/mcp",
            "scopes_supported": ["mcp:read", "mcp:execute", "mcp:write"],
            "bearer_methods_supported": ["header"],
            "resource_documentation": "https://github.com/chanl-ai/protobox-python/blob/main/docs/MCP_ARCHITECTURE.md",
        }
    
    @app.get("/jwks")
    async def root_oauth_jwks():
        """Forward JWKS request to admin API."""
        from httpx import AsyncClient
        async with AsyncClient() as client:
            response = await client.get(
                f"{settings.mcp_server_url}/admin/api/v1/oauth/jwks"
            )
            return JSONResponse(
                content=response.json() if response.text else {},
                status_code=response.status_code
            )
    
    # Also keep MCP-level discovery for compatibility
    @app.get("/mcp/.well-known/oauth-authorization-server")
    async def mcp_oauth_discovery():
        """OAuth discovery endpoint at MCP base URL for FastMCP client."""
        from .admin.routers.mcp_oauth import get_oauth_service
        oauth_service = get_oauth_service()
        metadata = oauth_service.get_authorization_server_metadata()
        
        # Update URLs to be relative to /mcp instead of /admin/api/v1
        base_url = settings.mcp_server_url
        metadata.update({
            "issuer": f"{base_url}/mcp",
            "authorization_endpoint": f"{base_url}/mcp/oauth/authorize",
            "token_endpoint": f"{base_url}/mcp/oauth/token",
            "registration_endpoint": f"{base_url}/mcp/oauth/register",
            "jwks_uri": f"{base_url}/mcp/oauth/jwks",
        })
        
        from fastapi.responses import JSONResponse
        return JSONResponse(content=metadata)
    
    @app.get("/mcp/.well-known/oauth-authorization-server-alt")
    async def mcp_oauth_discovery_alt():
        """Alternative OAuth discovery endpoint for /mcp."""
        return {
            "issuer": settings.mcp_server_url,
            "authorization_endpoint": f"{settings.mcp_server_url}/authorize",
            "token_endpoint": f"{settings.mcp_server_url}/token",
            "registration_endpoint": f"{settings.mcp_server_url}/register",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none"],
            "scopes_supported": ["mcp:read", "mcp:execute", "mcp:write"],
            "response_modes_supported": ["query"],
            "authorization_response_iss_parameter_supported": True,
        }
    
    @app.get("/mcp")
    async def mcp_oauth_sse_handler(request: Request):
        """
        GET /mcp handles OAuth-authenticated SSE connections.
        This endpoint:
        1. Validates OAuth Bearer tokens
        2. Extracts workspace_id from token
        3. Routes to workspace-specific SSE handler
        4. Supports both SSE and HTTP streaming transports
        """
        logger.info(f"GET /mcp request from {request.client.host if request.client else 'unknown'}")
        
        # Check if this is an SSE connection request
        accept_header = request.headers.get("accept", "")
        user_agent = request.headers.get("user-agent", "")
        
        # Detect SSE vs HTTP streaming transport
        is_sse_request = (
            "text/event-stream" in accept_header or 
            "application/json-rpc" in accept_header or
            "mcp-inspector" in user_agent.lower() or
            "fastmcp" in user_agent.lower()
        )
        
        logger.info(f"Transport detection - Accept: {accept_header}, User-Agent: {user_agent}, SSE: {is_sse_request}")
        
        # Check for Authorization header
        auth_header = request.headers.get("authorization", "")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning(f"GET /mcp: Missing or invalid Authorization header from {request.client.host if request.client else 'unknown'}")
            return Response(
                content="ProtoBox MCP Server - OAuth Bearer token required",
                media_type="text/plain",
                status_code=401,
                headers={
                    "WWW-Authenticate": f'Bearer realm="ProtoBox MCP", authorization_uri="{settings.mcp_server_url}/authorize"'
                }
            )
        
        try:
            # Extract and validate OAuth token
            token = auth_header.replace("Bearer ", "")
            logger.info(f"GET /mcp: Validating OAuth token starting with: {token[:20]}...")
            
            # Validate OAuth token and extract workspace_id
            from .admin.services.mcp_oauth_service import MCPOAuthService
            oauth_service = MCPOAuthService(app.state.db_manager.database)
            
            token_info = await oauth_service.validate_access_token(token)
            if not token_info:
                logger.warning(f"GET /mcp: Invalid or expired OAuth token from {request.client.host if request.client else 'unknown'} - token: {token[:20]}...")
                return Response(
                    content="Invalid or expired OAuth token",
                    media_type="text/plain", 
                    status_code=401,
                    headers={
                        "WWW-Authenticate": f'Bearer realm="ProtoBox MCP", authorization_uri="{settings.mcp_server_url}/authorize"'
                    }
                )
            
            logger.info(f"GET /mcp: OAuth token validation SUCCESS - token_info: {token_info}")
            
            workspace_id = token_info.get("workspace_id")
            if not workspace_id:
                logger.error(f"GET /mcp: OAuth token missing workspace_id: {token_info}")
                return Response(
                    content="OAuth token missing workspace_id",
                    media_type="text/plain",
                    status_code=400
                )
            
            logger.info(f"GET /mcp: OAuth token validated for workspace {workspace_id}, user {token_info.get('user_id')}")
            
            # For SSE connections, route to workspace-specific SSE endpoint
            if is_sse_request:
                logger.info(f"GET /mcp: OAuth SSE connection success - routing to workspace {workspace_id}")
                logger.info(f"GET /mcp: Client: {token_info.get('client_id')}, User: {token_info.get('user_id')}")
                logger.debug(f"GET /mcp: Scopes: {token_info.get('scope', '')}")
                
                # Set authentication context for the SSE connection
                request.state.workspace_id = workspace_id
                request.state.token = token  # Add the token to request state
                request.state.auth = {
                    "type": "oauth_token",
                    "workspace_id": workspace_id,
                    "user_id": token_info.get("user_id"),
                    "client_id": token_info.get("client_id"),
                    "scopes": token_info.get("scope", "").split()
                }
                
                # Create SSE connection to workspace-specific MCP server
                logger.info(f"GET /mcp: Establishing OAuth SSE connection for workspace {workspace_id}")
                try:
                    async with sse.connect_sse(
                        request.scope, request.receive, request._send
                    ) as (read_stream, write_stream):
                        await server.run(
                            read_stream,
                            write_stream,
                            InitializationOptions(
                                server_name=f"workspace-{workspace_id}",
                                server_version="0.1.0",
                                capabilities=server.get_capabilities(
                                    notification_options=NotificationOptions(),
                                    experimental_capabilities={},
                                ),
                            ),
                        )
                    logger.info(f"GET /mcp: SSE connection completed successfully for workspace {workspace_id}")
                except Exception as e:
                    logger.error(f"GET /mcp: SSE connection failed for workspace {workspace_id}: {e}")
                    raise
                # Return empty response for completed SSE connection
                return Response()
            else:
                # For non-SSE requests, return OAuth discovery info
                logger.info(f"GET /mcp: Returning OAuth discovery info for non-SSE request")
                return Response(
                    content="ProtoBox MCP Server - OAuth authenticated. Use POST for JSON-RPC or SSE headers for streaming.",
                    media_type="text/plain",
                    status_code=200
                )
                
        except Exception as e:
            logger.error(f"GET /mcp: Authentication error from {request.client.host if request.client else 'unknown'}: {e}")
            return Response(
                content="OAuth authentication service error",
                media_type="text/plain",
                status_code=500
            )
    
    @app.post("/mcp")
    async def mcp_root_handler(request: Request):
        """
        Handle POST requests to /mcp.
        This is a router endpoint that:
        1. Returns OAuth discovery for unauthenticated requests
        2. Proxies authenticated requests to the workspace-specific MCP endpoint
        """
        import json

        from fastapi import HTTPException
        from httpx import AsyncClient

        # Check for Authorization header
        auth_header = request.headers.get("authorization", "")
        
        # Try to read the body to determine what kind of request this is
        try:
            body = await request.body()
            if body:
                data = json.loads(body)
                # Log the request for debugging
                logger.info(f"POST /mcp request: method={data.get('method')}, jsonrpc={data.get('jsonrpc')}, auth={'yes' if auth_header else 'no'}")
                
                # Check if this is a JSON-RPC request
                if "jsonrpc" in data:
                    # Check if we have an OAuth token
                    if auth_header and auth_header.startswith("Bearer "):
                        # We have a token, validate it and extract workspace_id
                        token = auth_header.replace("Bearer ", "")
                        logger.info(f"POST /mcp: Validating OAuth token starting with: {token[:20]}...")
                        
                        # Validate the OAuth token
                        from .admin.services.mcp_oauth_service import MCPOAuthService

                        # Use the app's db_manager that was initialized
                        oauth_service = MCPOAuthService(app.state.db_manager.database)
                        
                        # Validate the token and get token info including workspace_id
                        token_info = await oauth_service.validate_access_token(token)
                        
                        if token_info:
                            workspace_id = token_info.get("workspace_id")
                            logger.info(f"POST /mcp: OAuth token validated for workspace {workspace_id}, user {token_info.get('user_id')}")
                            
                            # Production-ready OAuth: workspace_id must be present in token
                            if not workspace_id:
                                logger.error(f"POST /mcp: OAuth token missing workspace_id: {token_info}")
                                return JSONResponse(
                                    content={
                                        "jsonrpc": "2.0",
                                        "id": data.get("id"),
                                        "error": {
                                            "code": -32001,
                                            "message": "OAuth token missing workspace_id",
                                            "data": {"error": "Invalid token: workspace_id required"}
                                        }
                                    },
                                    status_code=400
                                )
                            
                            # Proxy the request to the workspace-specific MCP endpoint
                            logger.info(f"POST /mcp: Proxying JSON-RPC request to workspace {workspace_id}")
                            
                            async with AsyncClient() as client:
                                # Forward to the workspace-specific endpoint
                                # IMPORTANT: No trailing slash to avoid redirect that loses headers
                                headers = dict(request.headers)
                                headers.pop("host", None)  # Remove host header
                                
                                response = await client.post(
                                    f"{settings.mcp_server_url}/mcp/{workspace_id}",  # No trailing slash!
                                    content=body,
                                    headers=headers
                                )
                                
                                logger.info(f"POST /mcp: Workspace {workspace_id} response status: {response.status_code}")
                                return JSONResponse(
                                    content=response.json() if response.text else {},
                                    status_code=response.status_code
                                )
                        else:
                            logger.warning(f"POST /mcp: Invalid or expired OAuth token from {request.client.host if request.client else 'unknown'}")
                    
                    # No valid auth, return error with OAuth info
                    return JSONResponse(
                        content={
                            "jsonrpc": "2.0",
                            "id": data.get("id"),
                            "error": {
                                "code": -32001,  # Authentication required
                                "message": "Authentication required",
                                "data": {
                                    "oauth": {
                                        "authorization_endpoint": f"{settings.mcp_server_url}/mcp/oauth/authorize",
                                        "token_endpoint": f"{settings.mcp_server_url}/mcp/oauth/token", 
                                        "registration_endpoint": f"{settings.mcp_server_url}/mcp/oauth/register",
                                        "scopes_supported": ["mcp:read", "mcp:write", "mcp:execute"],
                                        "token_endpoint_auth_methods_supported": ["none"],
                                        "grant_types_supported": ["authorization_code"],
                                        "code_challenge_methods_supported": ["S256"]
                                    }
                                }
                            }
                        },
                        status_code=401
                    )
        except Exception as e:
            logger.error(f"Error handling /mcp request: {e}")
            pass
        
        # Default to OAuth discovery for non-JSON-RPC requests
        return await mcp_oauth_discovery()

    # Forward OAuth endpoints from /mcp to /admin/api/v1/oauth
    @app.post("/mcp/oauth/register")
    async def mcp_oauth_register_forward(request: Request):
        """Forward OAuth registration to admin API."""
        from httpx import AsyncClient
        async with AsyncClient() as client:
            body = await request.body()
            headers = dict(request.headers)
            # Remove host header to avoid conflicts
            headers.pop("host", None)
            
            response = await client.post(
                f"{settings.mcp_server_url}/admin/api/v1/oauth/register",
                content=body,
                headers=headers
            )
            return JSONResponse(
                content=response.json() if response.text else {},
                status_code=response.status_code
            )
    
    @app.get("/mcp/oauth/authorize")
    async def mcp_oauth_authorize_forward(request: Request):
        """Forward OAuth authorization to frontend OAuth page."""
        from fastapi.responses import RedirectResponse

        # Determine frontend URL
        frontend_url = settings.frontend_url
        
        query_string = str(request.url.query)
        # Redirect to frontend OAuth page
        return RedirectResponse(
            url=f"{frontend_url}/oauth/authorize?{query_string}",
            status_code=303  # See Other - standard for OAuth redirects
        )
    
    @app.post("/mcp/oauth/token")
    async def mcp_oauth_token_forward(request: Request):
        """Forward OAuth token exchange to admin API."""
        from httpx import AsyncClient
        async with AsyncClient() as client:
            body = await request.body()
            headers = dict(request.headers)
            headers.pop("host", None)
            
            response = await client.post(
                f"{settings.mcp_server_url}/admin/api/v1/oauth/token",
                content=body,
                headers=headers
            )
            return JSONResponse(
                content=response.json() if response.text else {},
                status_code=response.status_code
            )
    
    @app.get("/mcp/oauth/jwks")
    async def mcp_oauth_jwks_forward():
        """Forward JWKS request to admin API."""
        from httpx import AsyncClient
        async with AsyncClient() as client:
            response = await client.get(
                f"{settings.mcp_server_url}/admin/api/v1/oauth/jwks"
            )
            return JSONResponse(
                content=response.json() if response.text else {},
                status_code=response.status_code
            )
    
    # ==================== Root-level OAuth Endpoints for FastMCP ====================
    # FastMCP client expects OAuth endpoints at root level (not under /mcp)
    
    @app.get("/.well-known/oauth-authorization-server")
    async def root_oauth_discovery():
        """
        OAuth 2.0 Authorization Server Metadata at root level.
        FastMCP and other OAuth clients expect this at root for discovery.
        """
        from fastapi.responses import JSONResponse
        
        base_url = settings.mcp_server_url or "http://localhost:8090"
        return JSONResponse(content={
            "issuer": base_url,
            "authorization_endpoint": f"{base_url}/authorize",
            "token_endpoint": f"{base_url}/token",
            "token_endpoint_auth_methods_supported": [
                "none",  # For public clients with PKCE
                "client_secret_post",
                "client_secret_basic",
            ],
            "introspection_endpoint": f"{base_url}/introspect",
            "revocation_endpoint": f"{base_url}/revoke",
            "registration_endpoint": f"{base_url}/register",
            "jwks_uri": f"{base_url}/jwks",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            "scopes_supported": [
                "mcp:read",
                "mcp:write", 
                "mcp:execute",
                "offline_access",
            ],
            "service_documentation": f"{base_url}/docs",
            "ui_locales_supported": ["en"],
            "claims_supported": ["sub", "iss", "aud", "exp", "iat", "jti", "scope"],
            "authorization_response_iss_parameter_supported": True,
        })
    
    @app.get("/authorize")
    async def root_authorize_forward(request: Request):
        """
        Forward OAuth authorization to frontend OAuth page at root level.
        FastMCP expects this at /authorize (not /mcp/oauth/authorize).
        """
        from fastapi.responses import RedirectResponse

        # Determine frontend URL
        frontend_url = settings.frontend_url
        
        # Preserve all query parameters for OAuth flow
        query_string = str(request.url.query)
        if query_string:
            # Redirect to frontend OAuth page which handles auth and consent
            return RedirectResponse(
                url=f"{frontend_url}/oauth/authorize?{query_string}",
                status_code=303  # See Other - standard for OAuth redirects
            )
        return RedirectResponse(url=f"{frontend_url}/oauth/authorize", status_code=303)
    
    @app.post("/token")
    async def root_token_forward(request: Request):
        """
        Forward OAuth token exchange to admin API at root level.
        FastMCP expects this at /token (not /mcp/oauth/token).
        """
        from httpx import AsyncClient
        
        body = await request.body()
        headers = dict(request.headers)
        headers.pop("host", None)  # Remove host header to avoid conflicts
        
        async with AsyncClient() as client:
            response = await client.post(
                f"{settings.mcp_server_url}/admin/api/v1/oauth/token",
                content=body,
                headers=headers
            )
            return JSONResponse(
                content=response.json() if response.text else {},
                status_code=response.status_code
            )
    
    @app.post("/register")
    async def root_register_forward(request: Request):
        """
        Forward OAuth client registration to admin API at root level.
        FastMCP expects this at /register for dynamic client registration.
        """
        from httpx import AsyncClient
        
        body = await request.body()
        headers = dict(request.headers)
        headers.pop("host", None)
        
        async with AsyncClient() as client:
            response = await client.post(
                f"{settings.mcp_server_url}/admin/api/v1/oauth/register",
                content=body,
                headers=headers
            )
            return JSONResponse(
                content=response.json() if response.text else {},
                status_code=response.status_code
            )
    
    @app.post("/introspect")
    async def root_introspect_forward(request: Request):
        """Forward OAuth token introspection to admin API."""
        from httpx import AsyncClient
        
        body = await request.body()
        headers = dict(request.headers)
        headers.pop("host", None)
        
        async with AsyncClient() as client:
            response = await client.post(
                f"{settings.mcp_server_url}/admin/api/v1/oauth/introspect",
                content=body,
                headers=headers
            )
            return JSONResponse(
                content=response.json() if response.text else {},
                status_code=response.status_code
            )
    
    @app.post("/revoke")
    async def root_revoke_forward(request: Request):
        """Forward OAuth token revocation to admin API."""
        from httpx import AsyncClient
        
        body = await request.body()
        headers = dict(request.headers)
        headers.pop("host", None)
        
        async with AsyncClient() as client:
            response = await client.post(
                f"{settings.mcp_server_url}/admin/api/v1/oauth/revoke",
                content=body,
                headers=headers
            )
            # Revocation always returns 200 per OAuth spec
            return Response(status_code=200)
    
    @app.get("/jwks")
    async def root_jwks_forward():
        """Forward JWKS request to admin API."""
        from httpx import AsyncClient
        
        async with AsyncClient() as client:
            response = await client.get(
                f"{settings.mcp_server_url}/admin/api/v1/oauth/jwks"
            )
            return JSONResponse(
                content=response.json() if response.text else {},
                status_code=response.status_code
            )

    return app


# Export app instance for uvicorn
app = create_app()
