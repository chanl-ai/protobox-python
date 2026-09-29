"""
Enhanced MCP Protocol Handlers

Handles MCP protocol message processing and routing with official MCP library integration.
"""

import asyncio
from typing import Any, Dict, List, Optional, Union

from loguru import logger
from mcp.server.lowlevel.server import Server as MCPLowLevelServer, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.types

from .messages import MCPMessage, MCPNotification, MCPRequest, MCPResponse, MCPException


class MCPHandler:
    """Enhanced MCP handler with official MCP library integration"""

    def __init__(self, name: str = "protobox-mcp", version: str = "1.0.0", instructions: str | None = None):
        # Keep existing custom handler interface
        self._request_handlers: dict[str, callable] = {}
        self._notification_handlers: dict[str, callable] = {}
        
        # Add official MCP server for protocol compliance
        self._mcp_server = MCPLowLevelServer(
            name=name,
            version=version,
            instructions=instructions
        )
        
        # Setup official MCP handlers
        self._setup_official_mcp_handlers()
        
        # Track workspace context for auth-aware operations
        self._auth_context: Optional[Any] = None

    @property
    def mcp_server(self):
        """Access to the underlying official MCP server"""
        return self._mcp_server

    def register_request_handler(self, method: str, handler: callable):
        """Register a request handler"""
        self._request_handlers[method] = handler
        logger.debug(f"Registered request handler for method: {method}")
    
    def set_auth_context(self, auth_context: Any):
        """Set auth context for efficient auth-aware operations"""
        self._auth_context = auth_context

    def register_notification_handler(self, method: str, handler: callable):
        """Register a notification handler"""
        self._notification_handlers[method] = handler
        logger.debug(f"Registered notification handler for method: {method}")

    async def handle_message(self, message: MCPMessage) -> MCPMessage | None:
        """Handle incoming MCP message"""
        try:
            if isinstance(message, MCPRequest):
                return await self._handle_request(message)
            if isinstance(message, MCPNotification):
                await self._handle_notification(message)
                return None
            logger.warning(f"Unknown message type: {type(message)}")
            return None

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            if isinstance(message, MCPRequest):
                return MCPResponse(
                    id=message.id,
                    error={"code": -32603, "message": "Internal error", "data": str(e)},
                )
            return None

    async def _handle_request(self, request: MCPRequest) -> MCPResponse:
        """Handle MCP request"""
        method = request.method

        if method in self._request_handlers:
            try:
                handler = self._request_handlers[method]
                result = await handler(request)
                return MCPResponse(id=request.id, result=result)
            except MCPException as e:
                logger.error(f"MCP error in request handler for {method}: {e}")
                return MCPResponse(
                    id=request.id,
                    error=e.to_error_dict(),
                )
            except Exception as e:
                logger.error(f"Error in request handler for {method}: {e}")
                return MCPResponse(
                    id=request.id,
                    error={"code": -32603, "message": "Handler error", "data": str(e)},
                )
        else:
            return MCPResponse(
                id=request.id, error={"code": -32601, "message": f"Method not found: {method}"}
            )

    async def _handle_notification(self, notification: MCPNotification):
        """Handle MCP notification"""
        method = notification.method

        if method in self._notification_handlers:
            try:
                handler = self._notification_handlers[method]
                await handler(notification)
            except Exception as e:
                logger.error(f"Error in notification handler for {method}: {e}")
        else:
            logger.warning(f"No handler for notification method: {method}")

    def _setup_official_mcp_handlers(self):
        """Setup bridge handlers that connect our custom interface to official MCP server"""
        # Bridge standard MCP methods to official server
        self.register_request_handler("initialize", self._official_initialize_handler)
        self.register_request_handler("tools/list", self._official_list_tools_handler)
        self.register_request_handler("tools/call", self._official_call_tool_handler)
        self.register_request_handler("resources/list", self._official_list_resources_handler)
        self.register_request_handler("resources/read", self._official_read_resource_handler)
        self.register_request_handler("prompts/list", self._official_list_prompts_handler)
        self.register_request_handler("prompts/get", self._official_get_prompt_handler)
        
        # Handle notifications
        self.register_notification_handler("initialized", self._official_initialized_handler)
        self.register_notification_handler("notifications/cancelled", self._official_cancelled_handler)

    async def _official_initialize_handler(self, request: MCPRequest) -> dict:
        """Bridge initialize requests to official MCP server"""
        try:
            # Convert our MCPRequest to official mcp.types format
            init_request = mcp.types.InitializeRequest(
                id=request.id,
                method="initialize",
                params=mcp.types.InitializeRequestParams(
                    protocolVersion=request.params.get("protocolVersion", "2024-11-05"),
                    capabilities=mcp.types.ClientCapabilities(
                        **request.params.get("capabilities", {})
                    ),
                    clientInfo=mcp.types.Implementation(
                        **request.params.get("clientInfo", {"name": "unknown", "version": "1.0.0"})
                    )
                )
            )
            
            # Use official server's initialization
            result = await self._mcp_server.handle_initialize(init_request)
            
            # Convert back to our format
            return {
                "protocolVersion": result.protocolVersion,
                "capabilities": result.capabilities.model_dump() if result.capabilities else {},
                "serverInfo": result.serverInfo.model_dump() if result.serverInfo else {}
            }
        except Exception as e:
            logger.error(f"Error in official initialize handler: {e}")
            raise MCPException(-32603, f"Initialize error: {str(e)}")

    async def _official_list_tools_handler(self, request: MCPRequest) -> dict:
        """Bridge tools/list requests to official MCP server"""
        try:
            # Create official request
            tools_request = mcp.types.ListToolsRequest(
                id=request.id,
                method="tools/list",
                params=mcp.types.ListToolsRequestParams()
            )
            
            # Use official server's tool listing
            result = await self._mcp_server.handle_list_tools(tools_request)
            
            # Convert tools to our format
            tools = []
            if result.tools:
                for tool in result.tools:
                    tools.append({
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema
                    })
            
            return {"tools": tools}
        except Exception as e:
            logger.error(f"Error in official list tools handler: {e}")
            raise MCPException(-32603, f"List tools error: {str(e)}")

    async def _official_call_tool_handler(self, request: MCPRequest) -> dict:
        """Bridge tools/call requests to official MCP server"""
        try:
            # Create official request
            call_request = mcp.types.CallToolRequest(
                id=request.id,
                method="tools/call",
                params=mcp.types.CallToolRequestParams(
                    name=request.params.get("name"),
                    arguments=request.params.get("arguments", {})
                )
            )
            
            # Use official server's tool calling
            result = await self._mcp_server.handle_call_tool(call_request)
            
            # Convert result to our format
            content = []
            if result.content:
                for item in result.content:
                    content.append(item.model_dump())
            
            return {
                "content": content,
                "isError": getattr(result, 'isError', False)
            }
        except Exception as e:
            logger.error(f"Error in official call tool handler: {e}")
            raise MCPException(-32603, f"Call tool error: {str(e)}")

    async def _official_list_resources_handler(self, request: MCPRequest) -> dict:
        """Bridge resources/list requests to official MCP server"""
        try:
            # Create official request
            resources_request = mcp.types.ListResourcesRequest(
                id=request.id,
                method="resources/list",
                params=mcp.types.ListResourcesRequestParams()
            )
            
            # Use official server's resource listing
            result = await self._mcp_server.handle_list_resources(resources_request)
            
            # Convert resources to our format
            resources = []
            if result.resources:
                for resource in result.resources:
                    resources.append({
                        "uri": resource.uri,
                        "name": resource.name,
                        "description": resource.description,
                        "mimeType": resource.mimeType
                    })
            
            return {"resources": resources}
        except Exception as e:
            logger.error(f"Error in official list resources handler: {e}")
            raise MCPException(-32603, f"List resources error: {str(e)}")

    async def _official_read_resource_handler(self, request: MCPRequest) -> dict:
        """Bridge resources/read requests to official MCP server"""
        try:
            # Create official request
            read_request = mcp.types.ReadResourceRequest(
                id=request.id,
                method="resources/read",
                params=mcp.types.ReadResourceRequestParams(
                    uri=request.params.get("uri")
                )
            )
            
            # Use official server's resource reading
            result = await self._mcp_server.handle_read_resource(read_request)
            
            # Convert contents to our format
            contents = []
            if result.contents:
                for content in result.contents:
                    contents.append(content.model_dump())
            
            return {"contents": contents}
        except Exception as e:
            logger.error(f"Error in official read resource handler: {e}")
            raise MCPException(-32603, f"Read resource error: {str(e)}")

    async def _official_list_prompts_handler(self, request: MCPRequest) -> dict:
        """Bridge prompts/list requests to official MCP server"""
        try:
            # Create official request
            prompts_request = mcp.types.ListPromptsRequest(
                id=request.id,
                method="prompts/list",
                params=mcp.types.ListPromptsRequestParams()
            )
            
            # Use official server's prompt listing
            result = await self._mcp_server.handle_list_prompts(prompts_request)
            
            # Convert prompts to our format
            prompts = []
            if result.prompts:
                for prompt in result.prompts:
                    prompts.append({
                        "name": prompt.name,
                        "description": prompt.description,
                        "arguments": [arg.model_dump() for arg in prompt.arguments] if prompt.arguments else []
                    })
            
            return {"prompts": prompts}
        except Exception as e:
            logger.error(f"Error in official list prompts handler: {e}")
            raise MCPException(-32603, f"List prompts error: {str(e)}")

    async def _official_get_prompt_handler(self, request: MCPRequest) -> dict:
        """Bridge prompts/get requests to official MCP server"""
        try:
            # Create official request
            get_request = mcp.types.GetPromptRequest(
                id=request.id,
                method="prompts/get",
                params=mcp.types.GetPromptRequestParams(
                    name=request.params.get("name"),
                    arguments=request.params.get("arguments", {})
                )
            )
            
            # Use official server's prompt getting
            result = await self._mcp_server.handle_get_prompt(get_request)
            
            # Convert messages to our format
            messages = []
            if result.messages:
                for message in result.messages:
                    messages.append(message.model_dump())
            
            return {
                "description": result.description,
                "messages": messages
            }
        except Exception as e:
            logger.error(f"Error in official get prompt handler: {e}")
            raise MCPException(-32603, f"Get prompt error: {str(e)}")

    async def _official_initialized_handler(self, notification: MCPNotification):
        """Handle initialized notification"""
        logger.debug("MCP server initialized")
        # Could trigger additional setup here

    async def _official_cancelled_handler(self, notification: MCPNotification):
        """Handle cancelled notification"""
        request_id = notification.params.get("requestId") if notification.params else None
        logger.debug(f"Request cancelled: {request_id}")
        # Could implement cancellation logic here
