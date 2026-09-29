"""Workspace-aware MCP server for ProtoBox with OAuth 2.1 Support.

This module provides a single low-level MCP server instance that handles multiple 
workspaces via header-based routing. It integrates with ProtoBox's action system
and knowledge base to provide dynamic tools per workspace.

## Architecture Overview

### Multi-Tenant MCP Design
- Single MCP server instance handles all workspaces
- Workspace isolation via x-workspace-id header or OAuth token
- Dynamic tool loading from workspace actions
- Tools and data are workspace-scoped for security

### Authentication & Access Methods

1. **Direct JWT Authentication** (Internal clients):
   - Endpoint: `/mcp/{workspace_id}/sse` or `/mcp/{workspace_id}`
   - Requires: JWT Bearer token from Firebase auth
   - Used by: Web app, internal integrations

2. **OAuth 2.1 Flow** (External MCP clients):
   - Discovery: `GET /mcp` returns OAuth metadata
   - Authorization: `GET /authorize` → Frontend OAuth consent page
   - Token Exchange: `POST /token` → OAuth access token with workspace_id
   - MCP Access: `POST /mcp` with OAuth Bearer token

### OAuth Integration Flow for FastMCP

1. **Discovery Phase**:
   - FastMCP calls `GET /mcp` or `/mcp/.well-known/oauth-authorization-server`
   - Receives OAuth endpoints (authorize, token, register)

2. **Dynamic Registration** (Optional):
   - `POST /register` with client metadata
   - Returns client_id for public clients (no secret with PKCE)

3. **Authorization Phase**:
   - FastMCP opens browser to `/authorize?client_id=...&code_challenge=...`
   - Backend redirects (303) to frontend: `http://localhost:3010/oauth/authorize`
   - User logs in (if needed) and approves access
   - Frontend redirects back to FastMCP callback with code

4. **Token Exchange**:
   - FastMCP calls `POST /token` with code and code_verifier
   - Returns access_token with embedded workspace_id
   - Token includes MCP scopes (read, write, execute)

5. **MCP Connection**:
   - FastMCP sends JSON-RPC to `/mcp` with OAuth Bearer token
   - `/mcp` proxy validates token, extracts workspace_id
   - Proxies to `/mcp/{workspace_id}` internally (no redirect!)
   - MCP server handles the request

### Important Notes on Redirects

- **NEVER use 307** for auth flows - loses Authorization headers
- **Use 303** for OAuth authorize redirects (GET to frontend)
- **Use proxying** for internal API routing (not redirects)
- The `/mcp` proxy directly forwards to `/mcp/{workspace_id}`

### MCP Protocol Handlers

The `@server` decorators below register MCP protocol handlers, NOT REST endpoints.
These are called internally when clients send JSON-RPC requests over SSE/HTTP transport.

Key Features:
- Single MCP server handles all workspaces via x-workspace-id header
- Dynamic tool loading from workspace actions using ActionService
- REST action execution via RestActionExecutor
- Knowledge base search integration via KnowledgeDocumentService
- Proper error handling with MCP-compliant responses
"""

import re
import json
from typing import Any, Optional

from loguru import logger
from fastapi import APIRouter
import mcp.types as types
from mcp.server.lowlevel import Server

from ..models.execution import ExecutionModel, ExecutionStatus
from ..models.action import ActionType, ActionModel
from ..models.knowledge_base import QueryRequest, QueryFilters, SearchType
from ..actions.rest_executor import RestActionExecutor
from ..actions.code_run_executor import CodeRunActionExecutor
from ..services.action_service import ActionService, AdminToolManager
from ..services.secret_service import SecretService
from ..services.knowledge_document_service import KnowledgeDocumentService
from ..services.embedding_service import EmbeddingService
from ..secrets.encryption import SecretEncryption


# Create router
router = APIRouter(prefix="/mcp", tags=["MCP (Model Context Protocol)"])


def _sanitize_tool_name(name: str) -> str:
    """Sanitize tool name to comply with MCP tool naming requirements."""
    # Replace spaces and special chars with underscores, keep alphanumeric, underscore, and dash
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    # Remove consecutive underscores and ensure it doesn't start/end with underscore
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    # Ensure it's not empty and starts with a letter
    if not sanitized or not sanitized[0].isalpha():
        sanitized = f"action_{sanitized}" if sanitized else "action"
    return sanitized


async def fetch_workspace_tools(
    workspace_id: str, 
    action_service: ActionService
) -> dict[str, tuple[ActionType, types.Tool, Optional[ActionModel]]]:
    """Fetch tools for a workspace from the database using ActionService."""
    logger.info(f"Fetching tools for workspace: {workspace_id}")
    
    try:
        # Get actions for this workspace
        actions = await action_service.list_actions(workspace_id, status=None)
        
        tools = {}
        
        # Convert actions to MCP tools
        for action in actions:
            tool_name = _sanitize_tool_name(action.name)
            
            # Create input schema based on action type
            if action.type == ActionType.REST or action.type == ActionType.ADMIN or action.type == ActionType.CODE_RUN:
                logger.info(f"Creating input schema for {action.type.value} action: {action.name}")
                
                # Build input schema from the action's inputVariables
                properties = {}
                required = []
                
                # Check if the action has inputVariables in its config_schema
                input_variables = action.config_schema.get("inputVariables", [])
                
                for var in input_variables:
                    var_name = var.get("name")
                    var_type = var.get("type", "string")
                    var_description = var.get("description", "")
                    var_required = var.get("required", False)
                    
                    if var_name:
                        properties[var_name] = {
                            "type": var_type,
                            "description": var_description
                        }
                        
                        if var_required:
                            required.append(var_name)
                
                input_schema = {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": False
                }
                
                # If no inputVariables found, fall back to generic schema
                if not properties:
                    input_schema = {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": True
                    }
            else:
                raise ValueError(f"Unsupported action type: {action.type}")
            
            tool = types.Tool(
                name=tool_name,
                description=action.description or f"Execute {action.name} action",
                inputSchema=input_schema
            )
            
            tools[tool_name] = (action.type, tool, action)
        
        # Always add knowledge base search tool
        kb_tool = types.Tool(
            name="search_knowledge_base",
            description="Search the workspace knowledge base for relevant information",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    },
                    "search_type": {
                        "type": "string",
                        "description": "Type of search to perform",
                        "enum": ["semantic", "keyword", "hybrid"],
                        "default": "semantic"
                    }
                },
                "required": ["query"],
                "additionalProperties": False
            }
        )
        
        tools["search_knowledge_base"] = (ActionType.KNOWLEDGE_BASE, kb_tool, None)
        
        logger.info(f"Found {len(tools)} tools for workspace {workspace_id}")
        return tools
        
    except Exception as e:
        logger.error(f"Error fetching tools for workspace {workspace_id}: {e}")
        # Return at least the knowledge base search tool
        kb_tool = types.Tool(
            name="search_knowledge_base",
            description="Search the workspace knowledge base for relevant information",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        )
        return {"search_knowledge_base": (ActionType.KNOWLEDGE_BASE, kb_tool, None)}


async def handle_rest_action(
    action: ActionModel,
    arguments: dict[str, Any],
    workspace_id: str,
    user_id: str = "mcp_user"
) -> list[types.Content]:
    """Execute a REST action using RestActionExecutor."""
    try:
        logger.info(f"Executing REST action: {action.name}")
        # Get secret service and rest executor
        encryption = SecretEncryption()
        secret_service = SecretService(encryption)
        rest_executor = RestActionExecutor(secret_service)

        execution = ExecutionModel(
            action_id=str(action.id),
            workspace_id=workspace_id,
            user_id=user_id,
            input_data=arguments,
            status=ExecutionStatus.PENDING
        )
        
        # Execute the action
        logger.info(f"Running REST action executor: {action.name}")
        output_data, error_message = await rest_executor.execute(action, execution)
        
        logger.info(f"REST action executor output: {output_data}")
        # Format result as MCP content - focus on actual response data for LLM
        if error_message is None:
            logger.info(f"REST action executor completed successfully: {action.name}")
            # Success case - return only the response content, not technical details
            if isinstance(output_data, dict) and "response_data" in output_data:
                response_data = output_data['response_data']
                if isinstance(response_data, dict) or isinstance(response_data, list):
                    content_text = json.dumps(response_data, indent=2)
                else:
                    content_text = str(response_data)
            elif isinstance(output_data, dict):
                # If no response_data key, try to extract meaningful content
                # Filter out technical fields and return the actual data
                filtered_data = {k: v for k, v in output_data.items() 
                               if k not in ['status_code', 'headers', 'execution_time']}
                if filtered_data:
                    content_text = json.dumps(filtered_data, indent=2)
                else:
                    content_text = "Operation completed successfully"
            else:
                content_text = str(output_data)
        else:
            # Error case
            logger.info(f"REST action executor failed: {action.name}")
            content_text = f"Error: {error_message}"
            
        return [types.TextContent(type="text", text=content_text)]
        
    except Exception as e:
        logger.error(f"Error executing REST action {action.name}: {e}")
        return [types.TextContent(type="text", text=f"❌ Execution error: {str(e)}")]


async def handle_code_run_action(
    action: ActionModel,
    arguments: dict[str, Any],
    workspace_id: str,
    user_id: str = "mcp_user"
) -> list[types.Content]:
    """Execute a code run action using CodeRunActionExecutor."""
    try:
        logger.info(f"Executing code run action: {action.name}")
        # Get secret service and code run executor
        encryption = SecretEncryption()
        secret_service = SecretService(encryption)
        code_executor = CodeRunActionExecutor(secret_service)
        
        execution = ExecutionModel(
            action_id=str(action.id),
            workspace_id=workspace_id,
            user_id=user_id,
            input_data=arguments,
            status=ExecutionStatus.PENDING
        )
        
        success, result, error_message = await code_executor.execute(action, execution)
        logger.info(f"Code run action executor output: {result}")
        if not isinstance(result, str):
            result = json.dumps(result, ensure_ascii=False)
        return [types.TextContent(type="text", text=result)]

    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"Error executing code run action {action.name}: {e}")
        return [types.TextContent(type="text", text=f"❌ Execution error: {str(e)}")]


async def handle_kb_search(
    arguments: dict[str, Any], 
    workspace_id: str
) -> list[types.Content]:
    """Execute a knowledge base search using KnowledgeDocumentService."""
    try:
        # Import database connection function
        from ..database.connection import get_database_connection
        import os
        
        # Get database connection
        db_connection = get_database_connection()
        database = db_connection.database
        
        # Initialize embedding service
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            return [types.TextContent(type="text", text="❌ OpenAI API key not configured for knowledge base search")]
        
        embedding_service = EmbeddingService(api_key=openai_api_key)
        kb_service = KnowledgeDocumentService(database, embedding_service)
        
        # Extract search parameters
        query = arguments.get("query", "")
        max_results = arguments.get("max_results", 10)
        search_type_str = arguments.get("search_type", "semantic")
        
        if not query:
            return [types.TextContent(type="text", text="❌ Search query is required")]
        
        # Map search type
        search_type_map = {
            "semantic": SearchType.SEMANTIC,
            "keyword": SearchType.KEYWORD, 
            "hybrid": SearchType.HYBRID
        }
        search_type = search_type_map.get(search_type_str, SearchType.SEMANTIC)
        
        # Create query request
        query_request = QueryRequest(
            query=query,
            filters=QueryFilters(
                search_type=search_type,
                max_results=max_results,
                min_relevance=0.1
            )
        )
        
        # Perform search
        response = await kb_service.query_documents(workspace_id, query_request)
        
        # Check if response is a dict instead of an object
        if isinstance(response, dict):
            logger.error(f"Response is a dict, not QueryResponse. Keys: {response.keys()}")
            # Try to access results from dict
            if 'results' in response:
                results = response['results']
            elif 'ok' in response:
                logger.error(f"Got MongoDB response directly: {response}")
                return [types.TextContent(type="text", text="Error: Unexpected MongoDB response format")]
            else:
                return [types.TextContent(type="text", text="Error: Invalid response format")]
        elif not hasattr(response, 'results'):
            logger.error(f"Response missing 'results' attribute")
            return [types.TextContent(type="text", text="Error: Invalid response format")]
        
        if not response.results:
            return [types.TextContent(
                type="text", 
                text=f"No results found for: {query}"
            )]
        
        # Format results - focus on content, not metadata
        content_parts = []
        
        for result in response.results[:max_results]:
            # Build clean content for each result
            result_text = f"**{result.document_title}**\n{result.content_snippet}"
            if result.category:
                result_text = f"**{result.document_title}** ({result.category})\n{result.content_snippet}"
            content_parts.append(result_text)
        
        # Join results with clean separators
        content_text = "\n\n---\n\n".join(content_parts)
        
        return [types.TextContent(type="text", text=content_text)]
        
    except Exception as e:
        import traceback
        logger.error(f"Error executing KB search: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]


def create_mcp_server() -> Server:
    """
    Create a workspace-aware MCP server that handles multiple workspaces via headers.
    
    This is the factory function that creates the actual MCP server instance.
    The server created here:
    
    1. Is a SINGLE instance that handles ALL workspaces (multi-tenant)
    2. Uses request headers/state to determine which workspace is active
    3. Dynamically loads tools based on the workspace context
    
    Architecture Notes:
    - This is NOT the same as a REST API router
    - The Server object uses the MCP protocol (JSON-RPC over SSE/WebSocket)
    - The @server decorators register handlers for MCP protocol methods
    - The actual HTTP endpoint that serves this would be elsewhere
    
    Key Point for OAuth/FastMCP:
    - This server expects workspace_id to be provided somehow
    - OAuth clients need to either:
      a) Connect to /mcp/{workspace_id}/ (workspace in URL)
      b) Provide x-workspace-id header
      c) Have middleware set request.state.workspace_id
    
    Without workspace_id, the server returns empty tool lists and errors
    on tool calls, which is why OAuth integration is critical.
    """
    server = Server("protobox-mcp-server")
    
    # Initialize services (will be reused across calls)
    action_service = ActionService()
    admin_tool_manager = AdminToolManager(action_service)
    
    @server.list_tools()
    async def list_tools():
        """
        MCP Handler: List tools available for the current workspace.
        
        This is one of the core MCP protocol handlers. When an MCP client 
        (like FastMCP, Claude Desktop, or OpenAI) connects and requests available
        tools, this method is called.
        
        Authentication/Multi-tenancy:
        - The workspace_id MUST be provided either via:
          1. request.state.workspace_id (set by authentication middleware)
          2. x-workspace-id header (backward compatibility)
        - Each workspace gets its own isolated set of tools
        
        Returns:
        - List of types.Tool objects that the MCP client can call
        - Empty list if workspace_id is missing or on error
        
        Note: This is NOT a REST endpoint - it's called internally by the MCP
        protocol when clients connect via SSE or other MCP transports.
        """
        try:
            # Get workspace_id from request state (set by authentication)
            request = server.request_context.request
            workspace_id = getattr(request.state, 'workspace_id', None)
            
            # Fallback to header if not in state (for backward compatibility)
            if not workspace_id:
                workspace_id = request.headers.get('x-workspace-id')
            
            if not workspace_id:
                logger.error("Missing workspace_id in authentication context or headers")
                return []
            
            logger.info(f"Listing tools for workspace: {workspace_id}")
            tools_data = await fetch_workspace_tools(workspace_id, action_service)
            
            # Return just the Tool objects (not the tuples)
            return [tool for _, tool, _ in tools_data.values()]

        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            return []

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]):
        """
        MCP Handler: Execute a tool for the current workspace with STRICT workspace isolation.
        
        SECURITY: This handler enforces strict workspace isolation to prevent cross-workspace access.
        All tool execution is limited to the authenticated workspace only.
        
        This is the main MCP tool execution handler. When an MCP client
        (like an AI assistant) decides to use a tool, this method handles
        the actual execution.
        
        Authentication/Multi-tenancy:
        - workspace_id MUST be available (same as list_tools)
        - Tools are workspace-specific and isolated
        - CRITICAL: Only tools belonging to the workspace can be executed
        
        Tool Resolution:
        1. Fetches all available tools for the workspace
        2. **SECURITY CHECK**: Verifies the tool exists in this workspace
        3. Routes to appropriate handler based on tool type:
           - REST: External API calls via RestActionExecutor
           - KNOWLEDGE_BASE: Search workspace documents
           - ADMIN: Admin operations via AdminToolManager
        
        Returns:
        - List of types.Content objects (usually TextContent) with results
        - Error messages wrapped in TextContent if execution fails
        
        Security:
        - All operations are scoped to the authenticated workspace
        - Secrets are handled securely via SecretService
        - No cross-workspace access is possible
        - Tools from other workspaces are completely blocked
        
        Note: This is called via MCP protocol, not directly via HTTP.
        The actual HTTP endpoint would be something like:
        - /mcp/{workspace_id}/ for SSE transport
        - /mcp/{workspace_id}/sse for WebSocket transport
        """
        try:
            # Get workspace_id from request state (set by authentication)
            request = server.request_context.request
            workspace_id = getattr(request.state, 'workspace_id', None)
            
            # Fallback to header if not in state (for backward compatibility)
            if not workspace_id:
                workspace_id = request.headers.get('x-workspace-id')
            
            if not workspace_id:
                logger.error("SECURITY: Missing workspace_id in authentication context or headers")
                raise ValueError("Missing workspace_id in authentication context or headers")
            
            logger.info(f"Calling tool '{name}' for workspace {workspace_id} with args: {arguments}")
            
            # SECURITY: Get available tools for THIS SPECIFIC workspace only
            # This is the critical security boundary - only workspace tools are loaded
            tools_data = await fetch_workspace_tools(workspace_id, action_service)
            
            # SECURITY: STRICT workspace isolation check - tool MUST exist in this workspace
            if name not in tools_data:
                logger.warning(f"SECURITY: Attempt to access tool '{name}' not found in workspace {workspace_id}. Available tools: {list(tools_data.keys())}")
                raise ValueError(f"Tool '{name}' not found in workspace {workspace_id}. This workspace has {len(tools_data)} available tools.")
            
            tool_type, tool, action = tools_data[name]
            logger.info(f"SECURITY: Tool '{name}' verified as belonging to workspace {workspace_id} (type: {tool_type})")
            
            # Route to appropriate handler based on tool type
            if tool_type == ActionType.REST:
                if action is None:
                    raise ValueError(f"Action data missing for REST tool '{name}'")
                # SECURITY: Pass workspace_id to ensure action is executed in correct context
                return await handle_rest_action(action, arguments, workspace_id)
                
            elif tool_type == ActionType.KNOWLEDGE_BASE:
                # SECURITY: Knowledge base search is scoped to the workspace
                return await handle_kb_search(arguments, workspace_id)
                
            elif tool_type == ActionType.ADMIN:
                if action is None:
                    raise ValueError(f"Action data missing for admin tool '{name}'")
                # SECURITY: Admin actions are also workspace-scoped
                return await admin_tool_manager.execute_admin_action(action, arguments, workspace_id)
            
            elif tool_type == ActionType.CODE_RUN:
                if action is None:
                    raise ValueError(f"Action data missing for code run tool '{name}'")
                return await handle_code_run_action(action, arguments, workspace_id)
            
            else:
                logger.error(f"SECURITY: Unsupported tool type: {tool_type} for tool '{name}' in workspace {workspace_id}")
                raise ValueError(f"Unsupported tool type: {tool_type}")
                
        except ValueError as e:
            # ValueError indicates a security violation or client error - log and return error
            logger.warning(f"SECURITY: Tool access denied - {str(e)}")
            return [types.TextContent(type="text", text=f"❌ Access denied: {str(e)}")]
        except Exception as e:
            # Unexpected errors
            logger.error(f"Error executing tool '{name}' in workspace {workspace_id}: {e}")
            return [types.TextContent(type="text", text=f"❌ Tool execution failed: {str(e)}")]

    return server


@router.get("/info")
async def get_mcp_info():
    """Get information about the multi-tenant MCP server."""
    return {
        "name": "ProtoBox Multi-tenant MCP",
        "version": "1.0.0",
        "description": "Multi-tenant Model Context Protocol server for ProtoBox",
        "features": [
            "Workspace-based tenant isolation",
            "Dynamic tool loading from actions",
            "Secure authentication per tenant",
            "Tenant-specific logging",
        ],
    }
