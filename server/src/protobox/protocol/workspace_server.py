"""
Workspace-Aware MCP Server

Provides workspace isolation for MCP servers, ensuring that each workspace
has its own isolated set of tools and resources.
"""

import asyncio
from typing import Any, Dict, List, Optional

from loguru import logger

from .handlers import MCPHandler
from .messages import (
    MCPError,
    MCPErrorCode,
    MCPException,
    MCPRequest,
    MCPResponse,
    ToolCallRequest,
    ToolInfo,
    ToolsListRequest,
    ToolsListResponse,
)
from .redis_cache import get_redis_cache


class WorkspaceAwareMCPServer(MCPHandler):
    """
    DEPRECATED: MCP Handler with workspace isolation capabilities and official MCP compliance.
    
    This class is deprecated in favor of the new multi-tenant MCP architecture in 
    mcp_multitenant.py which provides better workspace isolation and security.
    
    Current usage:
    - workspace_manager.py: Used for workspace-scoped MCP server instances
    - This should be migrated to use the new multi-tenant router directly
    
    DO NOT USE this class for new implementations.
    """
    
    def __init__(self, workspace_id: str):
        import warnings
        warnings.warn(
            "WorkspaceAwareMCPServer is deprecated. Use mcp_multitenant.py router instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Initialize with workspace-specific name and instructions
        super().__init__(
            name=f"protobox-mcp-{workspace_id}",
            version="1.0.0", 
            instructions=f"ProtoBox MCP server for workspace {workspace_id} with isolated tools and resources"
        )
        self.workspace_id = workspace_id
        self._workspace_tools: Dict[str, Any] = {}
        self._tool_registry = None  # Will be injected
        self._auth_context = None  # For efficient auth-aware operations
        
        # Register workspace-specific handlers that override the official ones
        self._register_workspace_handlers()
    
    def set_tool_registry(self, tool_registry):
        """Inject the workspace tool registry."""
        self._tool_registry = tool_registry
    
    def set_auth_context(self, auth_context):
        """Set auth context for efficient auth-aware operations."""
        self._auth_context = auth_context
    
    def _register_workspace_handlers(self):
        """Register workspace-specific MCP handlers that override official ones for workspace isolation."""
        # Override the official handlers with workspace-aware versions
        # These will take precedence over the bridge handlers in the parent MCPHandler
        self.register_request_handler("initialize", self._workspace_initialize_handler)
        self.register_request_handler("tools/list", self._workspace_tools_list_handler)
        self.register_request_handler("tools/call", self._workspace_tools_call_handler)
        self.register_notification_handler("initialized", self._workspace_initialized_handler)
        
        # Note: The parent MCPHandler already registered official bridge handlers,
        # but these workspace-specific handlers will override them for workspace isolation
    
    async def _workspace_initialize_handler(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle MCP initialize request for workspace."""
        logger.info(f"Workspace MCP initialize request for workspace {self.workspace_id}")
        
        # Return workspace-specific server capabilities
        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": {
                "name": f"protobox-mcp-{self.workspace_id}",
                "version": "1.0.0",
                "description": f"ProtoBox MCP server for workspace {self.workspace_id}"
            },
            "capabilities": {
                "tools": {"listChanged": True},
                "resources": {"subscribe": True, "listChanged": True},
                "prompts": {},
                "logging": {},
            },
        }
    
    async def _workspace_initialized_handler(self, notification):
        """Handle MCP initialized notification for workspace."""
        logger.info(f"MCP client initialized for workspace {self.workspace_id}")
        # Can trigger workspace-specific initialization here
        if self._tool_registry:
            await self._tool_registry.refresh_workspace_tools(self.workspace_id)
    
    async def _workspace_tools_list_handler(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle tools/list request with workspace isolation."""
        try:
            if not self._tool_registry:
                logger.warning(f"No tool registry available for workspace {self.workspace_id}")
                return {"tools": []}
            
            # Get tools for this specific workspace
            tools = await self._tool_registry.get_workspace_tools(self.workspace_id)
            
            # Convert to MCP tool format
            mcp_tools = []
            for tool in tools:
                mcp_tool = self._convert_to_mcp_tool(tool)
                mcp_tools.append(mcp_tool)
            
            logger.debug(f"Returning {len(mcp_tools)} tools for workspace {self.workspace_id}")
            return {"tools": mcp_tools}
            
        except Exception as e:
            logger.error(f"Error listing tools for workspace {self.workspace_id}: {e}")
            raise MCPException(
                code=MCPErrorCode.INTERNAL_ERROR,
                message="Failed to list tools",
                data=str(e)
            )
    
    async def _workspace_tools_call_handler(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle tools/call request with workspace isolation."""
        try:
            if not self._tool_registry:
                raise MCPException(
                    code=MCPErrorCode.INTERNAL_ERROR,
                    message="Tool registry not available"
                )
            
            params = request.params or {}
            tool_name = params.get("name")
            tool_arguments = params.get("arguments", {})
            
            if not tool_name:
                raise MCPException(
                    code=MCPErrorCode.INVALID_PARAMS,
                    message="Tool name is required"
                )
            
            # Execute tool within workspace context with auth awareness for efficient responses
            result = await self._tool_registry.execute_tool(
                workspace_id=self.workspace_id,
                tool_name=tool_name,
                arguments=tool_arguments,
                auth_context=self._auth_context
            )
            
            # Format result for MCP
            if result.get("success"):
                content = [
                    {
                        "type": "text",
                        "text": str(result.get("data", result.get("result", "")))
                    }
                ]
                return {
                    "content": content,
                    "isError": False
                }
            else:
                content = [
                    {
                        "type": "text", 
                        "text": f"Tool execution failed: {result.get('error', 'Unknown error')}"
                    }
                ]
                return {
                    "content": content,
                    "isError": True
                }
            
        except MCPException:
            raise
        except Exception as e:
            logger.error(f"Error executing tool {params.get('name')} in workspace {self.workspace_id}: {e}")
            raise MCPException(
                code=MCPErrorCode.INTERNAL_ERROR,
                message="Tool execution failed",
                data=str(e)
            )
    
    def _convert_to_mcp_tool(self, action) -> Dict[str, Any]:
        """Convert ProtoBox action to MCP tool format."""
        # Build parameters schema from action variables
        properties = {}
        required = []
        
        if hasattr(action, "variables") and action.variables:
            for var in action.variables:
                properties[var.name] = {
                    "type": var.type,
                    "description": var.description or f"Parameter {var.name}",
                }
                if var.required:
                    required.append(var.name)
        
        return {
            "name": action.name,
            "description": action.description or f"Execute {action.name} action",
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False
            }
        }
    
    async def refresh_tools(self):
        """Refresh tools from the database."""
        if self._tool_registry:
            await self._tool_registry.refresh_workspace_tools(self.workspace_id)
            logger.debug(f"Refreshed tools for workspace {self.workspace_id}")


class WorkspaceToolRegistry:
    """Registry for managing workspace-specific tools with Redis caching for scalability."""
    
    def __init__(self, action_service=None, secret_service=None):
        self.action_service = action_service
        self.secret_service = secret_service
        self._cache_ttl = 300  # 5 minutes
        # Remove in-memory cache - using Redis instead
    
    async def get_workspace_tools(self, workspace_id: str) -> List[Any]:
        """Get all tools for a specific workspace with Redis caching."""
        redis_cache = await get_redis_cache()
        
        # Try Redis cache first
        cached_tools = await redis_cache.get_workspace_tools(workspace_id)
        if cached_tools is not None:
            logger.debug(f"Redis cache hit for workspace {workspace_id} tools")
            # Convert dict back to action objects
            return await self._deserialize_tools(cached_tools)
        
        # Fetch fresh data
        tools = await self._fetch_workspace_tools(workspace_id)
        
        # Cache in Redis
        serialized_tools = await self._serialize_tools(tools)
        await redis_cache.set_workspace_tools(workspace_id, serialized_tools, self._cache_ttl)
        
        # Track activity
        await redis_cache.track_workspace_activity(workspace_id)
        
        logger.debug(f"Fetched {len(tools)} tools for workspace {workspace_id}")
        return tools
    
    async def _fetch_workspace_tools(self, workspace_id: str) -> List[Any]:
        """Fetch tools from database for the workspace."""
        if not self.action_service:
            logger.warning("Action service not available")
            return []
        
        try:
            # Get all actions for this workspace
            actions = await self.action_service.list_actions(workspace_id)
            
            # Add built-in tools
            all_tools = list(actions)
            
            # Add knowledge base search tool if available
            kb_search_tool = self._create_kb_search_tool()
            all_tools.append(kb_search_tool)
            
            return all_tools
            
        except Exception as e:
            logger.error(f"Error fetching tools for workspace {workspace_id}: {e}")
            return []
    
    def _create_kb_search_tool(self):
        """Create a built-in knowledge base search tool."""
        class KBSearchTool:
            name = "search_knowledge_base"
            description = "Search the workspace knowledge base for relevant information"
            variables = [
                type('Variable', (), {
                    'name': 'query',
                    'type': 'string',
                    'description': 'Search query',
                    'required': True
                }),
                type('Variable', (), {
                    'name': 'max_results',
                    'type': 'integer', 
                    'description': 'Maximum results to return',
                    'required': False
                }),
                type('Variable', (), {
                    'name': 'search_type',
                    'type': 'string',
                    'description': 'Search type: semantic, keyword, or hybrid',
                    'required': False
                })
            ]
        
        return KBSearchTool()
    
    async def execute_tool(self, workspace_id: str, tool_name: str, arguments: Dict[str, Any], auth_context=None) -> Dict[str, Any]:
        """Execute a tool within the workspace context with auth awareness."""
        try:
            # Handle built-in tools
            if tool_name == "search_knowledge_base":
                return await self._execute_kb_search(workspace_id, arguments)
            
            # Handle regular actions
            if not self.action_service:
                return {
                    "success": False,
                    "error": "Action service not available"
                }
            
            # Get the action
            actions = await self.action_service.list_actions(workspace_id)
            action = next((a for a in actions if a.name == tool_name), None)
            
            if not action:
                return {
                    "success": False,
                    "error": f"Tool '{tool_name}' not found in workspace {workspace_id}"
                }
            
            # Execute the action with auth context
            result = await self._execute_action(workspace_id, action, arguments, auth_context)
            return result
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name} in workspace {workspace_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_kb_search(self, workspace_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute knowledge base search."""
        query = arguments.get("query", "")
        max_results = arguments.get("max_results", 5)
        search_type = arguments.get("search_type", "hybrid")
        
        if not query:
            return {
                "success": False,
                "error": "Query parameter is required"
            }
        
        try:
            # Import knowledge base models and service
            from ..admin.models.knowledge_base import QueryRequest, QueryFilters, SearchType
            from ..admin.services.knowledge_document_service import KnowledgeDocumentService
            from ..admin.services.embedding_service import EmbeddingService
            from ..admin.database.connection import get_database
            
            # Get database and embedding service
            db = await get_database()
            embedding_service = EmbeddingService()
            
            # Create knowledge document service
            kb_service = KnowledgeDocumentService(db, embedding_service)
            
            # Map search type string to enum
            search_type_map = {
                "semantic": SearchType.SEMANTIC,
                "keyword": SearchType.KEYWORD,
                "hybrid": SearchType.HYBRID
            }
            search_type_enum = search_type_map.get(search_type.lower(), SearchType.HYBRID)
            
            # Create query request
            query_request = QueryRequest(
                query=query,
                filters=QueryFilters(
                    search_type=search_type_enum,
                    max_results=max_results,
                    min_relevance=0.1
                )
            )
            
            # Execute search
            response = await kb_service.query_documents(workspace_id, query_request)
            
            # Format results for MCP
            results_text = f"Found {response.total_results} results for '{query}' (type: {search_type}):\n\n"
            
            for i, result in enumerate(response.results[:max_results], 1):
                results_text += f"{i}. {result.document_title}\n"
                results_text += f"   Relevance: {result.relevance_score:.3f}\n"
                results_text += f"   Content: {result.content_snippet}\n"
                if result.category:
                    results_text += f"   Category: {result.category}\n"
                results_text += "\n"
            
            if not response.results:
                results_text += "No matching documents found."
            
            return {
                "success": True,
                "data": results_text
            }
            
        except Exception as e:
            logger.error(f"Knowledge base search failed: {e}")
            return {
                "success": False,
                "error": f"Knowledge base search failed: {str(e)}"
            }
    
    async def _execute_action(self, workspace_id: str, action, arguments: Dict[str, Any], auth_context=None) -> Dict[str, Any]:
        """Execute a ProtoBox action with auth context awareness."""
        try:
            from ..admin.actions.rest_executor import RestActionExecutor
            from ..admin.models.execution import ExecutionModel, ExecutionStatus
            from datetime import datetime
            
            # Create executor with secret service
            executor = RestActionExecutor(secret_service=self.secret_service)
            
            # Get user ID from auth context for efficient tracing
            user_id = "mcp_user"  # Default fallback
            if auth_context and hasattr(auth_context, 'user_id') and auth_context.user_id:
                user_id = auth_context.user_id
            
            # Create execution model with auth context information
            execution = ExecutionModel(
                action_id=getattr(action, 'id', f"action_{action.name}"),
                workspace_id=workspace_id,
                user_id=user_id,  # Use actual user ID from MCP token for efficient responses
                input_data=arguments,
                status=ExecutionStatus.RUNNING,
                started_at=datetime.utcnow()
            )
            
            # Execute action
            output_data, error_message = await executor.execute(action, execution)
            
            if error_message:
                return {
                    "success": False,
                    "error": error_message,
                    "data": output_data
                }
            else:
                return {
                    "success": True,
                    "data": output_data,
                    "error": None
                }
            
        except Exception as e:
            logger.error(f"Error executing action {action.name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _serialize_tools(self, tools: List[Any]) -> List[Dict[str, Any]]:
        """Serialize tools for Redis storage."""
        serialized = []
        for tool in tools:
            tool_data = {
                "name": getattr(tool, "name", ""),
                "description": getattr(tool, "description", ""),
                "type": getattr(tool, "type", "REST"),
                "variables": []
            }
            
            # Serialize variables
            if hasattr(tool, "variables") and tool.variables:
                for var in tool.variables:
                    var_data = {
                        "name": getattr(var, "name", ""),
                        "type": getattr(var, "type", "string"),
                        "description": getattr(var, "description", ""),
                        "required": getattr(var, "required", False)
                    }
                    tool_data["variables"].append(var_data)
            
            serialized.append(tool_data)
        
        return serialized
    
    async def _deserialize_tools(self, serialized_tools: List[Dict[str, Any]]) -> List[Any]:
        """Deserialize tools from Redis storage."""
        tools = []
        for tool_data in serialized_tools:
            # Create a mock tool object with the cached data
            class CachedTool:
                def __init__(self, data):
                    self.name = data.get("name", "")
                    self.description = data.get("description", "")
                    self.type = data.get("type", "REST")
                    self.variables = []
                    
                    # Deserialize variables
                    for var_data in data.get("variables", []):
                        var = type('Variable', (), {
                            'name': var_data.get("name", ""),
                            'type': var_data.get("type", "string"),
                            'description': var_data.get("description", ""),
                            'required': var_data.get("required", False)
                        })
                        self.variables.append(var)
            
            tools.append(CachedTool(tool_data))
        
        return tools
    
    async def refresh_workspace_tools(self, workspace_id: str):
        """Refresh tools cache for a specific workspace."""
        redis_cache = await get_redis_cache()
        await redis_cache.invalidate_workspace_tools(workspace_id)
        
        # Force reload
        await self.get_workspace_tools(workspace_id)
    
    async def clear_cache(self):
        """Clear all cached tools."""
        redis_cache = await get_redis_cache()
        # Note: This would clear ALL workspace caches - use with caution
        logger.warning("clear_cache called - this affects all workspaces")