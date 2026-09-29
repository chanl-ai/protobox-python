"""Actions router with proper RESTful workspace-scoped endpoints."""

import os
import json
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from loguru import logger
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field

from ..actions.rest_executor import RestActionExecutor
from ..auth.dependencies import require_authentication
from ..auth.models import User
from ..middleware.team_auth import require_workspace_access
from ..models.team_member import WorkspaceMember
from ..database.connection import DatabaseConnection, get_database_connection
from ..mixins.audit_mixin import AuditLoggerMixin
from ..models.action import (
    ActionCreateRequest,
    ActionModel,
    ActionStatus,
    ActionType,
    ActionUpdateRequest,
    CodeRunConfig,
)
from ..secrets.encryption import SecretEncryption
from ..services.action_service import ActionService
from ..services.audit_service import AuditService
from ..services.openapi_import_service import OpenAPIImportService
from ..services.secret_service import SecretService
from ..services.cloudflare_workers_service import get_cloudflare_workers_service
from ..services.tigris_service import get_tigris_service


# File validation constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_FILES_PER_ACTION = 50
VALID_EXTENSIONS = {
    "javascript": [".js", ".mjs", ".json"],
    "python": [".py", ".txt"]
}


def _create_default_file_content(language: str) -> str:
    """Create default file content for a language."""
    if language == "javascript":
        return '''/**
 * Your main function - this is where your action logic goes.
 */

export async function main(inputs) {
  try {
    // Your main logic here
    // inputs contains the arguments provided by the LLM when executing this action
    
    const result = {
      status: 'success',
      message: 'Action executed successfully',
      inputs: inputs,
    };
    
    return result;
    
  } catch (error) {
    return {
      status: 'error',
      message: error.message,
      error_type: error.constructor.name
    };
  }
}'''
    elif language == "python":
        return '''"""
Your main function - this is where your action logic goes.
"""

def main(inputs):
    """
    Main function for the action.
    
    Args:
        inputs: Dictionary containing the arguments provided by the LLM
        
    Returns:
        Dictionary with the result
    """
    try:
        # Your main logic here
        # inputs contains the arguments provided by the LLM when executing this action
        
        result = {
            "status": "success",
            "message": "Action executed successfully", 
            "inputs": inputs,
        }
        
        return result
        
    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
            "error_type": type(error).__name__
        }
'''
    else:
        raise ValueError(f"Unsupported language: {language}")


def _get_entry_point_filename(language: str) -> str:
    """Get the standard entry point filename for a language."""
    if language == "javascript":
        return "main.js"
    elif language == "python":
        return "main.py"
    else:
        raise ValueError(f"Unsupported language: {language}")


def _validate_file_for_language(filename: str, content: bytes, language: str) -> None:
    """Validate a file for a specific language."""
    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File {filename} exceeds maximum size of {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Check file extension
    from pathlib import Path
    file_ext = Path(filename).suffix.lower()
    valid_extensions = VALID_EXTENSIONS.get(language, [])
    
    if file_ext not in valid_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File {filename} has invalid extension {file_ext}. Valid extensions for {language}: {valid_extensions}"
        )


def _generate_infrastructure_files(worker_name: str, language: str, user_entry_filename: str) -> list[dict[str, Any]]:
    """Generate infrastructure files for Cloudflare Workers.
    
    Args:
        worker_name: The actual worker name assigned by Cloudflare
        language: Programming language (javascript, python)
        user_entry_filename: The user's entry point filename
        
    Returns:
        List of file dictionaries with filename, content, and content_type
    """
    if language == "python":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Python language is not yet supported for CODE_RUN actions"
        )
    
    if language != "javascript":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language: {language}. Only JavaScript is currently supported."
        )
    
    # Generate main.js - Worker wrapper that calls user's main function
    main_js_content = f'''/**
 * Cloudflare Worker entry point
 * This worker wraps the user's code and provides the fetch handler.
 */

// Import the user's main function from their entry file
import {{ main }} from './src/user-main.js';

export default {{
  async fetch(request, env, ctx) {{
    try {{
      // Parse request data
      const url = new URL(request.url);
      const path = url.pathname;
      
      // Handle health check
      if (path === '/health') {{
        return new Response(JSON.stringify({{
          status: 'success',
          message: 'Worker is healthy',
          timestamp: new Date().toISOString()
        }}), {{
          headers: {{ 'Content-Type': 'application/json' }}
        }});
      }}
      
      // Parse request body if present - only pass the input_data from LLM
      let inputs = {{}};
      if (request.method !== 'GET' && request.body) {{
        const body = await request.json();
        // Extract only the input_data field, filter out worker_name and other metadata
        inputs = body.input_data || {{}};
      }}
      
      // Call the user's main function
      const result = await main(inputs);
      
      // Return the result as JSON
      return new Response(JSON.stringify(result), {{
        headers: {{
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        }}
      }});
      
    }} catch (error) {{
      console.error('Worker error:', error);
      return new Response(JSON.stringify({{
        status: 'error',
        message: error.message,
        stack: error.stack
      }}), {{
        status: 500,
        headers: {{ 'Content-Type': 'application/json' }}
      }});
    }}
  }}
}};'''

    # Generate wrangler.toml
    wrangler_toml_content = f'''name = "{worker_name}"
main = "main.js"
compatibility_date = "2024-01-01"
compatibility_flags = ["nodejs_compat"]

[env.development]
name = "{worker_name}-dev"

[env.staging]  
name = "{worker_name}-staging"

[env.production]
name = "{worker_name}-prod"'''

    # Generate package.json
    package_json_content = f'''{{
  "name": "{worker_name}",
  "version": "1.0.0",
  "description": "Cloudflare Worker for ProtoBox Action",
  "main": "main.js",
  "type": "module",
  "scripts": {{
    "dev": "wrangler dev",
    "deploy": "wrangler deploy",
    "deploy:staging": "wrangler deploy --env staging",
    "deploy:production": "wrangler deploy --env production"
  }},
  "keywords": ["cloudflare", "worker", "protobox"],
  "author": "ProtoBox",
  "license": "MIT",
  "dependencies": {{}}
}}'''

    return [
        {
            "filename": "main.js",
            "content": main_js_content.encode('utf-8'),
            "content_type": "application/javascript+module"
        },
        {
            "filename": "wrangler.toml", 
            "content": wrangler_toml_content.encode('utf-8'),
            "content_type": "text/plain"
        },
        {
            "filename": "package.json",
            "content": package_json_content.encode('utf-8'),
            "content_type": "application/json"
        }
    ]


class OpenAPIImportRequest(BaseModel):
    """Request to import actions from an OpenAPI spec (URL or content)."""

    spec_url: str | None = Field(default=None, description="Public URL to the OpenAPI spec")
    spec_content: str | None = Field(
        default=None, description="Raw OpenAPI content (YAML or JSON)"
    )
    include_paths: list[str] | None = Field(default=None)
    exclude_paths: list[str] | None = Field(default=None)
    base_url_override: str | None = Field(default=None)


class CurlImportRequest(BaseModel):
    """Request to import a single action from a cURL command."""

    curl_command: str = Field(..., min_length=8)
    name: str | None = None
    description: str | None = None


class ActionPreviewResponse(BaseModel):
    """Individual action preview with enhanced metadata."""

    name: str
    description: str | None = None
    method: str
    url: str
    variables: list[dict[str, Any]]
    request_example: dict[str, Any] | None = None
    response_examples: dict[str, dict[str, Any]] | None = None
    tags: list[str] | None = None
    security_schemes: list[str] | None = None


class ImportPreviewResponse(BaseModel):
    """Response previewing how many actions will be created and details."""

    actions_count: int
    previews: list[ActionPreviewResponse]


router = APIRouter(prefix="/workspaces/{workspace_id}/actions", tags=["Actions"])

# Security scheme
security = HTTPBearer(auto_error=False)

# Initialize services (will be properly injected in production)
action_service = ActionService()
openapi_import_service = OpenAPIImportService()


async def get_audit_service(request: Request) -> AuditService:
    """Get audit service instance from app state."""
    logger.info(
        f"Getting audit service from actions router. Has app state: {hasattr(request.app.state, 'audit_service')}"
    )
    if hasattr(request.app.state, "audit_service"):
        logger.info("Returning audit service from app state")
        return request.app.state.audit_service
    # Fallback to creating a new instance if not in app state
    logger.warning("Audit service not in app state, creating new instance")
    db = get_database_connection()
    return AuditService(db.database)


encryption = SecretEncryption()
secret_service = SecretService(encryption)
rest_executor = RestActionExecutor(secret_service)


async def get_current_user_id(
    workspace_id: str, auth_context = Depends(require_workspace_access)
) -> str | None:
    """Get current user ID from auth system with workspace membership validation."""
    # For user auth, return user_id
    if hasattr(auth_context, 'user_id'):
        return auth_context.user_id
    # For service auth, return None (services don't have user IDs)
    return None


async def get_current_user_from_jwt(
    current_user: User = Depends(require_authentication)
) -> User:
    """Get current user from JWT authentication."""
    return current_user


async def get_audit_service(request: Request) -> AuditService:
    """Get audit service instance from app state."""
    logger.info(
        f"Getting audit service. Has app state: {hasattr(request.app.state, 'audit_service')}"
    )
    if hasattr(request.app.state, "audit_service"):
        logger.info("Returning audit service from app state")
        return request.app.state.audit_service
    # Fallback to creating a new instance if not in app state
    logger.warning("Audit service not in app state, creating new instance")
    db = get_database_connection()
    return AuditService(db.database)


async def get_database() -> DatabaseConnection:
    """Get database connection dependency."""
    try:
        return get_database_connection()
    except RuntimeError as e:
        logger.error(f"Database connection not available: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database service unavailable"
        )


def _fflag_internal_tools_enabled() -> bool:
    """Feature flag to enable internal tool imports (OpenAPI, cURL)."""
    return os.getenv("MCP_INTERNAL_TOOLS", "false").lower() in ("1", "true", "yes", "on")


@router.get("", response_model=list[dict[str, Any]])
async def list_actions(
    workspace_id: str,
    action_type: ActionType | None = Query(None, description="Filter by action type"),
    status_filter: ActionStatus | None = Query(
        None, alias="status", description="Filter by status"
    ),
    tags: list[str] | None = Query(None, description="Filter by tags"),
    limit: int = Query(50, ge=1, le=100, description="Number of actions to return"),
    skip: int = Query(0, ge=0, description="Number of actions to skip"),
    db: DatabaseConnection = Depends(get_database),
    current_user: str = Depends(get_current_user_id),
) -> list[dict[str, Any]]:
    """
    List all actions in the workspace with optional filtering.

    Actions are the core building blocks of ProtoBox. They define reusable
    operations that can be executed by assistants, MCP clients, or APIs.

    **Query Parameters:**
    - `action_type`: Filter by action type (REST, CODE_RUN, WEBHOOK, etc.)
    - `status`: Filter by status (ACTIVE, INACTIVE, DRAFT)
    - `tags`: Filter by tags (can specify multiple)
    - `limit`: Number of results per page (1-100, default: 50)
    - `skip`: Number of results to skip for pagination

    **Response Example:**
    ```json
    [
        {
            "id": "6883cc77f0dd6dbee6550be8",
            "name": "get-weather",
            "type": "REST",
            "description": "Get current weather for a city",
            "status": "ACTIVE",
            "tags": ["weather", "api"],
            "variables": [
                {
                    "name": "city",
                    "type": "string",
                    "required": true,
                    "description": "City name"
                }
            ],
            "default_config": {
                "url": "https://api.weather.com/v1/current",
                "method": "GET",
                "headers": {"Authorization": "Bearer {{api_key}}"}
            },
            "created_at": "2024-01-01T00:00:00Z",
            "created_by": "user-id"
        }
    ]
    ```

    **Action Types:**
    - `REST`: HTTP/REST API calls
    - `CODE_RUN`: Execute custom code
    - `WEBHOOK`: Handle incoming webhooks
    - `GRAPHQL`: GraphQL queries/mutations
    - `DATABASE`: Database operations

    **Use Cases:**
    - Browse available actions for integration
    - Filter by type for specific operations
    - Check action status before execution
    - Tag-based discovery for related actions
    """
    logger.info(f"Listing actions for workspace {workspace_id}")
    try:
        # Use ActionService to properly handle serialization
        from ..services.action_service import ActionService
        action_service = ActionService()
        
        actions = await action_service.list_actions(
            workspace_id=workspace_id,
            action_type=action_type,
            status=status_filter,
            skip=skip,
            limit=limit,
        )
        
        # Convert ActionModel instances to JSON using proper serialization
        return [action.model_dump(mode="json") for action in actions]

    except Exception as e:
        logger.error(f"Failed to retrieve actions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve actions"
        )


async def _create_rest_action(
    workspace_id: str,
    request: Request,
    db: DatabaseConnection,
    current_user: User,
    audit_service: AuditService,
) -> dict[str, Any]:
    """Create a REST action from JSON request."""
    # Parse JSON body
    body = await request.json()
    action_request = ActionCreateRequest(**body)
    
    # Set workspace_id if not provided in request
    if not action_request.workspace_id:
        action_request.workspace_id = workspace_id
        
    # Handle config vs default_config field mapping
    if action_request.config and not action_request.default_config:
        action_request.default_config = action_request.config
        
    # Use ActionService to create the action (handles audit fields automatically)
    action_id = await action_service.create_action(action_request, current_user.id)
    
    # Get the created action to return full details
    created_action = await action_service.get_action_by_id(action_id)
    if not created_action:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve created action"
        )
    
    logger.info(f"Created REST action {action_id} in workspace {workspace_id}")

    # Log audit entry
    await AuditLoggerMixin.audit_create(
        audit_service=audit_service,
        user_id=current_user.id,
        workspace_id=workspace_id,
        resource_type="action",
        resource_id=action_id,
        resource_name=created_action.name,
        metadata={
            "action_type": created_action.type.value
        },
    )

    # Return the created action as dict for API response
    return created_action.model_dump(mode="json")


async def _create_code_run_action(
    workspace_id: str,
    request: Request,
    db: DatabaseConnection,
    current_user: User,
    audit_service: AuditService,
) -> dict[str, Any]:
    """Create a CODE_RUN action with default file and deploy to Cloudflare."""
    logger.info(f"Creating CODE_RUN action in workspace: {workspace_id}")
    
    # Parse form data (no files expected)
    form = await request.form()
    
    name = form.get("name")
    description = form.get("description", "")
    language = form.get("language")
    timeout = int(form.get("timeout", 30))
    memory_limit_mb = int(form.get("memory_limit_mb", 128))
    allow_network = form.get("allow_network", "false").lower() == "true"
    allow_file_ops = form.get("allow_file_ops", "false").lower() == "true"
    tags = form.get("tags", "")
    
    if not name:
        raise HTTPException(status_code=400, detail="Missing required field: name")
    
    if language not in ["python", "javascript"]:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {language}")
    
    # Get services
    tigris_service = get_tigris_service()
    cloudflare_service = get_cloudflare_workers_service()
    
    if not tigris_service.available:
        raise HTTPException(
            status_code=503,
            detail="File storage service is not available. Please check configuration."
        )
        
    if not cloudflare_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Cloudflare Workers service is not available. Please check configuration."
        )

    # Set up fixed entry point filename
    entry_point = _get_entry_point_filename(language)
    
    # Create action first to get the action ID
    action_data = {
        "workspace_id": workspace_id,
        "name": name,
        "type": ActionType.CODE_RUN,
        "description": description,
        "version": "1.0.0",
        "tags": [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else [] + ["code", language],
        "config_schema": {},
        "default_config": {},
        "secret_refs": [],
        "status": ActionStatus.ACTIVE.value,
        "is_builtin": False,
        "created_by": current_user.id,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    # Check for duplicate name
    collection = db.database.actions
    existing = await collection.find_one({"name": name, "workspace_id": workspace_id})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Action with name '{name}' already exists in this workspace",
        )
    
    # Insert action to get the action ID
    result = await collection.insert_one(action_data)
    action_id = str(result.inserted_id)
    
    try:
        # 1. Create and save default main file to Tigris
        default_content = _create_default_file_content(language)
        default_content_bytes = default_content.encode('utf-8')
        
        file_key = await tigris_service.upload_code_file(
            file_content=default_content_bytes,
            filename=entry_point,
            workspace_id=workspace_id,
            action_id=action_id,
            content_type='text/plain'
        )
        
        logger.info(f"Created default file {entry_point} for action {action_id}")

        # 2. Deploy to Cloudflare
        # Generate worker name
        worker_name = cloudflare_service._generate_worker_name(workspace_id, action_id)
        
        # Generate infrastructure files
        infrastructure_files = _generate_infrastructure_files(worker_name, language, entry_point)
        
        # Convert infrastructure files to UploadFile objects
        from fastapi import UploadFile
        from io import BytesIO
        
        infrastructure_file_objects = []
        for file_data in infrastructure_files:
            file_stream = BytesIO(file_data["content"])
            file_obj = UploadFile(
                filename=file_data["filename"],
                file=file_stream
            )
            infrastructure_file_objects.append(file_obj)
        
        # Convert default file to UploadFile object for Cloudflare
        default_file_stream = BytesIO(default_content_bytes)
        default_file_obj = UploadFile(
            filename="src/user-main.js",  # Standard name for user's entry point
            file=default_file_stream
        )
        
        # Combine infrastructure + default file
        all_cloudflare_files = infrastructure_file_objects + [default_file_obj]
        
        # Create worker
        created_worker_name = await cloudflare_service.create_customer_worker(
            workspace_id=workspace_id,
            action_id=action_id,
            files=all_cloudflare_files,
            language=language,
            entry_point="main"  # Infrastructure main.js is the entry point
        )
        
        logger.info(f"Created and deployed worker: {created_worker_name}")
        
    except Exception as e:
        logger.error(f"Failed to create action or deploy worker: {e}")
        # Clean up the action if creation/deployment fails
        await collection.delete_one({"_id": result.inserted_id})
        # Try to clean up any uploaded files
        try:
            if 'file_key' in locals():
                await tigris_service.delete_file(file_key)
        except Exception as cleanup_error:
            logger.warning(f"Failed to cleanup file during error recovery: {cleanup_error}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create CODE_RUN action: {str(e)}"
        )
    
    # Create action configuration
    config = CodeRunConfig(
        language=language,
        worker_name=created_worker_name,
        dispatch_namespace=cloudflare_service.dispatch_namespace,
        entry_point=entry_point,
        timeout=timeout,
        memory_limit_mb=memory_limit_mb,
        allow_network=allow_network,
        allow_file_ops=allow_file_ops,
    )
    
    # Update action with the configuration
    await collection.update_one(
        {"_id": result.inserted_id},
        {
            "$set": {
                "config_schema": config.model_json_schema(),
                "default_config": config.model_dump()
            }
        }
    )
    
    # Convert ObjectIds to strings for response
    def convert_objectids(obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, dict):
            return {k: convert_objectids(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [convert_objectids(item) for item in obj]
        return obj
    
    action_data["_id"] = result.inserted_id
    action_model = ActionModel.from_mongo(action_data)
    action_dict = action_model.model_dump(mode="python")
    action_dict = convert_objectids(action_dict)
    
    logger.info(f"Created CODE_RUN action: {name} with worker {created_worker_name}")
    
    # Log audit entry
    await AuditLoggerMixin.audit_create(
        audit_service=audit_service,
        user_id=current_user.id,
        workspace_id=workspace_id,
        resource_type="action",
        resource_id=action_id,
        resource_name=name,
        metadata={
            "action_type": "CODE_RUN",
            "language": language,
            "worker_name": created_worker_name,
            "default_file_created": True
        },
    )
    
    return action_dict


@router.post("", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_action(
    workspace_id: str,
    request: Request,
    db: DatabaseConnection = Depends(get_database),
    current_user: User = Depends(get_current_user_from_jwt),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict[str, Any]:
    """
    Create a new action in the workspace.

    Supports both REST actions (JSON) and CODE_RUN actions (FormData with files).
    
    **For REST Actions (JSON):**
    ```json
    {
        "name": "send-email",
        "type": "REST",
        "description": "Send an email notification",
        "version": "1.0.0",
        "tags": ["notification", "email"],
        "default_config": {
            "url": "https://api.sendgrid.com/v3/mail/send",
            "method": "POST",
            "headers": {
                "Authorization": "Bearer {{SENDGRID_API_KEY}}",
                "Content-Type": "application/json"
            }
        }
    }
    ```

    **For CODE_RUN Actions (FormData):**
    - `name`: Action name (required)
    - `description`: Action description (required)
    - `type`: "CODE_RUN" (required)
    - `language`: "python" or "javascript" (required)
    - `entry_point`: Entry point file name (default: "main")
    - `timeout`: Execution timeout in seconds (default: 30)
    - `memory_limit_mb`: Memory limit in MB (default: 128)
    - `allow_network`: Allow network requests (default: false)
    - `allow_file_ops`: Allow file operations (default: false)
    - `tags`: Comma-separated tags (optional)
    - `files`: Code files to upload (required for CODE_RUN)

    **Response:**
    Returns the created action with generated ID and metadata.
    """
    try:
        # Determine request type based on content type
        content_type = request.headers.get("content-type", "")
        
        if "multipart/form-data" in content_type:
            # Handle CODE_RUN action with file uploads
            return await _create_code_run_action(
                workspace_id=workspace_id,
                request=request,
                db=db,
                current_user=current_user,
                audit_service=audit_service
            )
        else:
            # Handle REST action with JSON
            logger.warning(f"Creating rest action: {workspace_id}")
            return await _create_rest_action(
                workspace_id=workspace_id,
                request=request,
                db=db,
                current_user=current_user,
                audit_service=audit_service
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create action: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create action"
        )


@router.get("/types", response_model=list[dict[str, Any]])
async def get_action_types(
    workspace_id: str, current_user: str = Depends(get_current_user_id)
) -> list[dict[str, Any]]:
    """Get available action types."""
    return [{"value": action_type.value, "label": action_type.value} for action_type in ActionType]


@router.get("/code-run/languages")
async def get_supported_languages(
    workspace_id: str, current_user: str = Depends(get_current_user_id)
) -> dict[str, Any]:
    """Get supported programming languages for CODE_RUN actions."""
    return {
        "languages": {
            "python": [".py"],
            "javascript": [".js", ".mjs"]
        }
    }


@router.post("/import/openapi/preview", response_model=ImportPreviewResponse)
async def import_actions_from_openapi_preview(
    workspace_id: str, body: OpenAPIImportRequest, current_user: str = Depends(get_current_user_id)
) -> ImportPreviewResponse:
    """Preview actions parsed from an OpenAPI spec without creating them.

    Controlled by feature flag `MCP_INTERNAL_TOOLS`.
    """
    if not _fflag_internal_tools_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature disabled")

    spec_content: str | None = body.spec_content
    if not spec_content and body.spec_url:
        # Fetch content
        async with aiohttp.ClientSession() as session, session.get(body.spec_url) as resp:
            if resp.status != 200:
                raise HTTPException(
                    status_code=resp.status, detail=f"Failed to fetch spec: {body.spec_url}"
                )
            spec_content = await resp.text()
    if not spec_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Provide spec_url or spec_content"
        )

    previews = openapi_import_service.parse_openapi_spec(
        spec_content=spec_content,
        base_url_override=body.base_url_override,
        include_paths=body.include_paths,
        exclude_paths=body.exclude_paths,
    )

    return ImportPreviewResponse(
        actions_count=len(previews),
        previews=[
            ActionPreviewResponse(
                name=p.name,
                description=p.description,
                method=p.method,
                url=p.url,
                variables=p.variables,
                request_example=p.request_example,
                response_examples=p.response_examples,
                tags=p.tags,
                security_schemes=p.security_schemes,
            )
            for p in previews
        ],
    )


@router.post("/import/openapi/create", response_model=dict[str, Any])
async def import_actions_from_openapi_create(
    workspace_id: str,
    body: OpenAPIImportRequest,
    request: Request,
    db: DatabaseConnection = Depends(get_database),
    current_user: str = Depends(get_current_user_id),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict[str, Any]:
    """Create REST actions from an OpenAPI spec.

    Returns summary with counts and created action IDs. Controlled by feature flag `MCP_INTERNAL_TOOLS`.
    """
    if not _fflag_internal_tools_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature disabled")

    # Parse spec (reuse preview flow)
    preview = await import_actions_from_openapi_preview(workspace_id, body, current_user)  # type: ignore[arg-type]

    created: list[str] = []
    skipped: list[dict[str, Any]] = []

    collection = db.database.actions

    for p in preview.previews:
        # Skip if action with same name exists
        exists = await collection.find_one({"workspace_id": workspace_id, "name": p.name})
        if exists:
            skipped.append({"name": p.name, "reason": "duplicate"})
            continue

        action_doc = {
            "workspace_id": workspace_id,
            "name": p.name,
            "type": ActionType.REST.value,
            "description": p.description or "",
            "version": "1.0.0",
            "tags": ["openapi", "imported"],
            "config_schema": {},
            "default_config": {"url": p.url, "method": p.method, "headers": {}},
            "variables": p.variables or [],
            "secret_refs": [],
            "status": ActionStatus.ACTIVE.value,
            "is_builtin": False,
            "created_by": current_user,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        result = await collection.insert_one(action_doc)
        created.append(str(result.inserted_id))

        # Audit
        await AuditLoggerMixin.audit_create(
            audit_service=audit_service,
            user_id=current_user,
            workspace_id=workspace_id,
            resource_type="action",
            resource_id=str(result.inserted_id),
            resource_name=p.name,
            metadata={"source": "openapi"},
        )

    return {
        "created": created,
        "skipped": skipped,
        "summary": {
            "parsed": preview.actions_count,
            "created": len(created),
            "skipped": len(skipped),
        },
    }


@router.post("/import/curl/preview", response_model=ImportPreviewResponse)
async def import_action_from_curl_preview(
    workspace_id: str, body: CurlImportRequest, current_user: str = Depends(get_current_user_id)
) -> ImportPreviewResponse:
    """Preview an action parsed from a cURL command."""
    if not _fflag_internal_tools_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature disabled")

    preview = openapi_import_service.parse_curl(body.curl_command)
    name = body.name or preview.name
    description = body.description or preview.description

    return ImportPreviewResponse(
        actions_count=1,
        previews=[
            ActionPreviewResponse(
                name=name,
                description=description,
                method=preview.method,
                url=preview.url,
                variables=preview.variables,
                request_example=preview.request_example,
                response_examples=preview.response_examples,
                tags=preview.tags,
                security_schemes=preview.security_schemes,
            )
        ],
    )


@router.post("/import/curl/create", response_model=dict[str, Any])
async def import_action_from_curl_create(
    workspace_id: str,
    body: CurlImportRequest,
    request: Request,
    db: DatabaseConnection = Depends(get_database),
    current_user: str = Depends(get_current_user_id),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict[str, Any]:
    """Create a REST action from a cURL command."""
    if not _fflag_internal_tools_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature disabled")

    preview_resp = await import_action_from_curl_preview(workspace_id, body, current_user)  # type: ignore[arg-type]
    p = preview_resp.previews[0]

    collection = db.database.actions
    exists = await collection.find_one({"workspace_id": workspace_id, "name": p.name})
    if exists:
        return {
            "created": [],
            "skipped": [{"name": p.name, "reason": "duplicate"}],
            "summary": {"parsed": 1, "created": 0, "skipped": 1},
        }

    action_doc = {
        "workspace_id": workspace_id,
        "name": p.name,
        "type": ActionType.REST.value,
        "description": p.description or "",
        "version": "1.0.0",
        "tags": ["curl", "imported"],
        "config_schema": {},
        "default_config": {"url": p.url, "method": p.method, "headers": {}},
        "variables": p.variables or [],
        "secret_refs": [],
        "status": ActionStatus.ACTIVE.value,
        "is_builtin": False,
        "created_by": current_user,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    result = await collection.insert_one(action_doc)

    await AuditLoggerMixin.audit_create(
        audit_service=audit_service,
        user_id=current_user,
        workspace_id=workspace_id,
        resource_type="action",
        resource_id=str(result.inserted_id),
        resource_name=p["name"],
        metadata={"source": "curl"},
    )

    return {
        "created": [str(result.inserted_id)],
        "skipped": [],
        "summary": {"parsed": 1, "created": 1, "skipped": 0},
    }


@router.get("/{action_id}")
async def get_action(
    workspace_id: str,
    action_id: str,
    db: DatabaseConnection = Depends(get_database),
    current_user: str = Depends(get_current_user_id),
):
    """Get action by ID."""
    logger.info(f"Getting action: {action_id} in workspace: {workspace_id}")
    try:
        # Validate ObjectId format
        try:
            object_id = ObjectId(action_id)
        except InvalidId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action ID format"
            )

        collection = db.database.actions
        action_data = await collection.find_one({"_id": object_id, "workspace_id": workspace_id})

        if not action_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")

        # Convert to ActionModel and use its built-in ObjectId serialization
        action_model = ActionModel.from_mongo(action_data)
        action_dict = action_model.model_dump(mode="json")
        if (
            action_model.type == ActionType.REST
            and "body" in action_dict["default_config"]
            and not isinstance(action_dict["default_config"]["body"], str)
        ):
            action_dict["default_config"]["body"] = json.dumps(action_dict["default_config"]["body"], indent=2, ensure_ascii=False)
        return JSONResponse(content=action_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve action {action_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve action"
        )


@router.put("/{action_id}", response_model=dict[str, Any])
async def update_action(
    workspace_id: str,
    action_id: str,
    action_update: ActionUpdateRequest,
    request: Request,
    db: DatabaseConnection = Depends(get_database),
    current_user: str = Depends(get_current_user_id),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict[str, Any]:
    """Update an action."""
    try:
        # Validate ObjectId format
        try:
            object_id = ObjectId(action_id)
        except InvalidId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action ID format"
            )

        collection = db.database.actions

        # Get existing action to verify it exists and user has access
        existing_action = await collection.find_one(
            {"_id": object_id, "workspace_id": workspace_id}
        )

        if not existing_action:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")

        # Build update data - only include non-None fields
        update_data = {}
        if action_update.name is not None:
            update_data["name"] = action_update.name
        if action_update.description is not None:
            update_data["description"] = action_update.description
        if action_update.version is not None:
            update_data["version"] = action_update.version
        if action_update.tags is not None:
            update_data["tags"] = action_update.tags
        if action_update.config_schema is not None:
            update_data["config_schema"] = action_update.config_schema
        if action_update.default_config is not None:
            update_data["default_config"] = action_update.default_config
        if action_update.secret_refs is not None:
            update_data["secret_refs"] = action_update.secret_refs
        if action_update.status is not None:
            update_data["status"] = action_update.status.value

        # Add updated timestamp
        update_data["updated_at"] = datetime.utcnow()

        # Check for name conflicts if name is being updated
        if action_update.name and action_update.name != existing_action["name"]:
            name_conflict = await collection.find_one(
                {
                    "name": action_update.name,
                    "workspace_id": workspace_id,
                    "_id": {"$ne": object_id},
                }
            )
            if name_conflict:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Action with name '{action_update.name}' already exists in this workspace",
                )

        # Update the action
        result = await collection.update_one(
            {"_id": object_id, "workspace_id": workspace_id}, {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")

        # Retrieve and return the updated action
        updated_action_data = await collection.find_one({"_id": object_id})
        action_model = ActionModel.from_mongo(updated_action_data)

        logger.info(f"Updated action {action_id} in workspace {workspace_id}")

        # Log audit entry using the mixin
        await AuditLoggerMixin.audit_update(
            audit_service=audit_service,
            user_id=current_user,
            workspace_id=workspace_id,
            resource_type="action",
            resource_id=action_id,
            changes=update_data,
            resource_name=action_model.name,
            metadata={
                "action_type": (
                    action_model.type.value
                    if hasattr(action_model.type, "value")
                    else str(action_model.type)
                )
            },
        )
        return action_model.model_dump(mode="json")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update action {action_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update action"
        )


@router.delete("/{action_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_action(
    workspace_id: str,
    action_id: str,
    request: Request,
    db: DatabaseConnection = Depends(get_database),
    current_user: str = Depends(get_current_user_id),
    audit_service: AuditService = Depends(get_audit_service),
) -> None:
    """Delete an action."""
    try:
        # Validate ObjectId format
        try:
            object_id = ObjectId(action_id)
        except InvalidId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action ID format"
            )

        collection = db.database.actions

        # Get action details before deleting (for audit log)
        action_data = await collection.find_one({"_id": object_id, "workspace_id": workspace_id})

        if not action_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")

        # Delete the action
        result = await collection.delete_one({"_id": object_id, "workspace_id": workspace_id})

        if result.deleted_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")

        # Clean up customer worker and files if this is a CODE_RUN action
        if action_data.get("type") == ActionType.CODE_RUN.value:
            # Clean up Cloudflare worker
            try:
                config = CodeRunConfig.model_validate(action_data.get("default_config", {}))
                if config.worker_name:
                    cloudflare_service = get_cloudflare_workers_service()
                    if cloudflare_service.is_available():
                        await cloudflare_service.delete_customer_worker(config.worker_name)
                        logger.info(f"Deleted customer worker {config.worker_name} for action {action_id}")
            except Exception as e:
                logger.error(f"Failed to delete customer worker for action {action_id}: {e}")
                # Don't fail the action deletion if worker cleanup fails
            
            # Clean up Tigris files
            try:
                tigris_service = get_tigris_service()
                if tigris_service.available:
                    # List all files for this action
                    files = await tigris_service.list_code_files(workspace_id, action_id)
                    
                    # Delete each file
                    deleted_count = 0
                    for file_info in files:
                        try:
                            success = await tigris_service.delete_file(file_info['key'])
                            if success:
                                deleted_count += 1
                                logger.info(f"Deleted file {file_info['key']} for action {action_id}")
                        except Exception as file_error:
                            logger.warning(f"Failed to delete file {file_info['key']}: {file_error}")
                    
                    logger.info(f"Deleted {deleted_count} files from Tigris for action {action_id}")
                else:
                    logger.warning("Tigris service not available, skipping file cleanup")
            except Exception as e:
                logger.error(f"Failed to delete Tigris files for action {action_id}: {e}")
                # Don't fail the action deletion if file cleanup fails

        logger.info(f"Deleted action {action_id} from workspace {workspace_id}")

        # Log audit entry using the mixin
        await AuditLoggerMixin.audit_delete(
            audit_service=audit_service,
            user_id=current_user,
            workspace_id=workspace_id,
            resource_type="action",
            resource_id=action_id,
            resource_name=action_data.get("name"),
            metadata={"action_type": action_data.get("type", "Unknown")},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete action {action_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete action"
        )


@router.post("/{action_id}/validate", response_model=dict[str, Any])
async def validate_action(
    workspace_id: str,
    action_id: str,
    db: DatabaseConnection = Depends(get_database),
    current_user: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Validate an action's configuration."""
    try:
        # Validate ObjectId format
        try:
            object_id = ObjectId(action_id)
        except InvalidId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action ID format"
            )

        collection = db.database.actions
        action_data = await collection.find_one({"_id": object_id, "workspace_id": workspace_id})

        if not action_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")

        # Convert to ActionModel for validation
        action = ActionModel(**action_data)

        # Perform validation based on action type
        validation_result = await action_service.validate_action(action)

        return {
            "valid": validation_result["valid"],
            "errors": validation_result.get("errors", []),
            "warnings": validation_result.get("warnings", []),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate action {action_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to validate action"
        )


@router.post("/{action_id}/test", response_model=dict[str, Any])
async def test_action(
    workspace_id: str,
    action_id: str,
    test_input: dict[str, Any],
    db: DatabaseConnection = Depends(get_database),
    current_user: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """
    Test an action with sample input data.

    Execute an action in test mode to verify configuration and behavior
    before using it in production. Test executions are not logged as
    regular executions.

    **Request Body:**
    ```json
    {
        "test_variables": {
            "city": "London",
            "units": "metric"
        }
    }
    ```

    **Response Example (Success):**
    ```json
    {
        "success": true,
        "result": {
            "temperature": 15,
            "condition": "Cloudy",
            "humidity": 75
        },
        "execution_time": 250
    }
    ```

    **Response Example (Error):**
    ```json
    {
        "success": false,
        "error": "API key invalid or expired",
        "execution_time": 150
    }
    ```

    **Test Process:**
    1. Validates input variables against action schema
    2. Substitutes variables and secrets into configuration
    3. Executes the action (REST call, code, etc.)
    4. Returns raw result without transformation

    **Common Use Cases:**
    - Verify API credentials are working
    - Test variable substitution logic
    - Debug action configuration
    - Preview action output format

    **Notes:**
    - Secrets are automatically resolved from workspace
    - Test executions have a 30-second timeout
    - Results show raw API responses for debugging
    """
    try:
        # Validate ObjectId format
        try:
            object_id = ObjectId(action_id)
        except InvalidId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action ID format"
            )

        collection = db.database.actions
        action_data = await collection.find_one({"_id": object_id, "workspace_id": workspace_id})

        if not action_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")

        # Convert to ActionModel
        action = ActionModel(**action_data)

        # Extract test variables
        test_variables = test_input.get("test_variables", {})

        # Execute action based on type
        if action.type == ActionType.REST:
            result = await rest_executor.test_action(
                action=action,
                test_input=test_variables,
            )
        elif action.type == ActionType.CODE_RUN:
            from ..actions.code_run_executor import CodeRunActionExecutor
            code_executor = CodeRunActionExecutor(secret_service)
            result = await code_executor.test_action(
                action=action,
                test_input=test_variables,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Testing not implemented for action type: {action.type}",
            )

        return {
            "success": result.get("success", False),
            "result": result.get("output_data"),
            "error": result.get("error_message"),
            "execution_time": result.get("execution_time", 0),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test action {action_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test action: {str(e)}",
        )


@router.get("/{action_id}/configuration-schema", response_model=dict[str, Any])
async def get_action_configuration_schema(
    workspace_id: str,
    action_id: str,
    db: DatabaseConnection = Depends(get_database),
    current_user: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Get the configuration schema for an action type."""
    try:
        # Validate ObjectId format
        try:
            object_id = ObjectId(action_id)
        except InvalidId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action ID format"
            )

        collection = db.database.actions
        action_data = await collection.find_one({"_id": object_id, "workspace_id": workspace_id})

        if not action_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")

        # Get schema based on action type
        action_type = ActionType(action_data["type"])
        return action_service.get_configuration_schema(action_type)


    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get action configuration schema: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get action configuration schema",
        )


@router.patch("/{action_id}/status", response_model=dict[str, Any])
async def toggle_action_status(
    workspace_id: str,
    action_id: str,
    status_update: dict[str, str],
    request: Request,
    db: DatabaseConnection = Depends(get_database),
    current_user: str = Depends(get_current_user_id),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict[str, Any]:
    """Toggle action status (activate/deactivate)."""
    try:
        # Validate ObjectId format
        try:
            object_id = ObjectId(action_id)
        except InvalidId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action ID format"
            )

        # Validate status value
        new_status = status_update.get("status")
        if not new_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Status field is required"
            )

        try:
            status_enum = ActionStatus(new_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {[s.value for s in ActionStatus]}",
            )

        collection = db.database.actions

        # Verify action exists and user has access
        existing_action = await collection.find_one(
            {"_id": object_id, "workspace_id": workspace_id}
        )

        if not existing_action:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")

        # Update the status
        result = await collection.update_one(
            {"_id": object_id, "workspace_id": workspace_id},
            {"$set": {"status": status_enum.value, "updated_at": datetime.utcnow()}},
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")

        # Return updated action
        updated_action_data = await collection.find_one({"_id": object_id})
        action_model = ActionModel.from_mongo(updated_action_data)

        logger.info(
            f"Updated action {action_id} status to {status_enum.value} in workspace {workspace_id}"
        )

        # Log audit entry using the mixin
        await AuditLoggerMixin.audit_update(
            audit_service=audit_service,
            user_id=current_user,
            workspace_id=workspace_id,
            resource_type="action",
            resource_id=action_id,
            changes={
                "before": {"status": existing_action.get("status")},
                "after": {"status": status_enum.value},
            },
            resource_name=action_model.name,
            metadata={
                "action_type": (
                    action_model.type.value
                    if hasattr(action_model.type, "value")
                    else str(action_model.type)
                ),
                "update_type": "status_change",
            },
        )

        return action_model.model_dump(mode="json")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to toggle action status {action_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to toggle action status",
        )


@router.post(
    "/{action_id}/duplicate", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED
)
async def duplicate_action(
    workspace_id: str,
    action_id: str,
    duplicate_request: dict[str, str] | None = None,
    db: DatabaseConnection = Depends(get_database),
    current_user: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """Duplicate an action with optional new name."""
    try:
        # Validate ObjectId format
        try:
            object_id = ObjectId(action_id)
        except InvalidId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action ID format"
            )

        collection = db.database.actions

        # Get the original action
        original_action_data = await collection.find_one(
            {"_id": object_id, "workspace_id": workspace_id}
        )

        if not original_action_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")

        # Create duplicate data
        duplicate_data = original_action_data.copy()

        # Remove the _id to create a new document
        del duplicate_data["_id"]

        # Generate new name if not provided
        new_name = None
        if duplicate_request and duplicate_request.get("name"):
            new_name = duplicate_request["name"]
        else:
            # Auto-generate name with "Copy of" prefix
            original_name = duplicate_data["name"]
            new_name = f"Copy of {original_name}"

            # Handle multiple copies by adding numbers
            counter = 1
            while await collection.find_one({"name": new_name, "workspace_id": workspace_id}):
                counter += 1
                new_name = f"Copy of {original_name} ({counter})"

        # Check if custom name already exists
        if await collection.find_one({"name": new_name, "workspace_id": workspace_id}):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Action with name '{new_name}' already exists in this workspace",
            )

        # Update duplicate data
        duplicate_data["name"] = new_name
        duplicate_data["created_by"] = current_user
        duplicate_data["created_at"] = datetime.utcnow()
        duplicate_data["updated_at"] = datetime.utcnow()

        # Insert the duplicate
        result = await collection.insert_one(duplicate_data)

        # Retrieve and return the new action
        duplicate_data["_id"] = result.inserted_id
        action_model = ActionModel.from_mongo(duplicate_data)

        logger.info(
            f"Duplicated action {action_id} as {result.inserted_id} in workspace {workspace_id}"
        )
        return action_model.model_dump(mode="json")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to duplicate action {action_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to duplicate action"
        )


@router.get("/{action_id}/files", response_model=list[dict[str, Any]])
async def list_action_files(
    workspace_id: str,
    action_id: str,
    db: DatabaseConnection = Depends(get_database),
    current_user: str = Depends(get_current_user_id),
) -> list[dict[str, Any]]:
    """
    List all files associated with a CODE_RUN action.
    
    Returns file metadata from Tigris storage only.
    """
    try:
        # Validate ObjectId format
        try:
            object_id = ObjectId(action_id)
        except InvalidId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action ID format"
            )

        collection = db.database.actions
        action_data = await collection.find_one({"_id": object_id, "workspace_id": workspace_id})

        if not action_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")

        if action_data["type"] != ActionType.CODE_RUN.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Action must be of type CODE_RUN"
            )

        # Get Tigris service
        tigris_service = get_tigris_service()
        if not tigris_service.available:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="File storage service not available"
            )

        try:
            # Get code files from Tigris
            files = await tigris_service.list_code_files(workspace_id, action_id)
            return files
        except Exception as e:
            logger.error(f"Failed to list code files: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list files: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list action files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to list action files"
        )


@router.get("/{action_id}/files/{filename}")
async def get_action_file_content(
    workspace_id: str,
    action_id: str,
    filename: str,
    db: DatabaseConnection = Depends(get_database),
    current_user: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """
    Get a presigned URL for downloading a specific file for a CODE_RUN action.
    
    Returns a presigned URL that can be used to download the file directly from Tigris storage.
    """
    try:
        # Validate ObjectId format
        try:
            object_id = ObjectId(action_id)
        except InvalidId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action ID format"
            )

        collection = db.database.actions
        action_data = await collection.find_one({"_id": object_id, "workspace_id": workspace_id})

        if not action_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")

        if action_data["type"] != ActionType.CODE_RUN.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Action must be of type CODE_RUN"
            )

        # Get Tigris service
        tigris_service = get_tigris_service()
        if not tigris_service.available:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="File storage service not available"
            )

        try:
            # Construct file key
            file_key = f"workspaces/{workspace_id}/code/{action_id}/{filename}"
            
            # Check if file exists first
            file_metadata = await tigris_service.get_file_metadata(file_key)
            if not file_metadata:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail=f"File '{filename}' not found"
                )
            
            # Generate presigned URL (valid for 1 hour)
            presigned_url = tigris_service.generate_presigned_url(
                file_key=file_key,
                expiration=3600,  # 1 hour
                http_method="GET"
            )
            
            # Determine content type based on file extension
            from pathlib import Path
            file_ext = Path(filename).suffix.lower()
            content_type_map = {
                '.js': 'application/javascript',
                '.mjs': 'application/javascript',
                '.py': 'text/x-python',
                '.json': 'application/json',
                '.txt': 'text/plain',
            }
            content_type = content_type_map.get(file_ext, 'text/plain')
            
            return {
                "download_url": presigned_url,
                "filename": filename,
                "content_type": content_type,
                "file_size": file_metadata.get('file_size', 0),
                "expires_in": 3600,
                "expires_at": (datetime.utcnow() + timedelta(seconds=3600)).isoformat()
            }
            
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"File '{filename}' not found"
            )
        except Exception as e:
            logger.error(f"Failed to get file presigned URL: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get file presigned URL: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get action file content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to get action file content"
        )


@router.post("/{action_id}/files", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def upload_action_file(
    workspace_id: str,
    action_id: str,
    file: UploadFile = File(...),
    db: DatabaseConnection = Depends(get_database),
    current_user: str = Depends(get_current_user_id),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict[str, Any]:
    """
    Upload a new file for a CODE_RUN action.
    
    The file will be stored in Tigris storage only. Use the deploy endpoint to deploy to Cloudflare.
    """
    try:
        # Validate ObjectId format
        try:
            object_id = ObjectId(action_id)
        except InvalidId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action ID format"
            )

        collection = db.database.actions
        action_data = await collection.find_one({"_id": object_id, "workspace_id": workspace_id})

        if not action_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")

        if action_data["type"] != ActionType.CODE_RUN.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Action must be of type CODE_RUN"
            )

        # Get action configuration
        config = CodeRunConfig.model_validate(action_data["default_config"])

        # Get Tigris service
        tigris_service = get_tigris_service()
        if not tigris_service.available:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="File storage service not available"
            )

        # Read file content
        content = await file.read()
        
        # Validate file
        _validate_file_for_language(file.filename, content, config.language)
        
        # Check if action already has too many files
        existing_files = await tigris_service.list_code_files(workspace_id, action_id)
        if len(existing_files) >= MAX_FILES_PER_ACTION:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Action already has maximum number of files ({MAX_FILES_PER_ACTION})"
            )

        # Check if file already exists
        existing_file_names = [f.get('original_filename', '') for f in existing_files]
        if file.filename in existing_file_names:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"File '{file.filename}' already exists. Use PUT to update it."
            )

        try:
            # Upload to Tigris
            file_key = await tigris_service.upload_code_file(
                file_content=content,
                filename=file.filename,
                workspace_id=workspace_id,
                action_id=action_id,
                content_type=file.content_type or 'text/plain'
            )

            file_info = {
                'filename': file.filename,
                'file_key': file_key,
                'size': len(content),
                'content_type': file.content_type or 'text/plain'
            }

            # Log audit entry
            await AuditLoggerMixin.audit_create(
                audit_service=audit_service,
                user_id=current_user,
                workspace_id=workspace_id,
                resource_type="action_file",
                resource_id=f"{action_id}/{file.filename}",
                resource_name=file.filename,
                metadata={
                    "action_id": action_id,
                    "action_name": action_data["name"],
                    "file_size": len(content),
                    "file_type": file.content_type or 'text/plain'
                },
            )

            return file_info

        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload action file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to upload action file"
        )


@router.put("/{action_id}/files/{filename}", response_model=dict[str, Any])
async def update_action_file(
    workspace_id: str,
    action_id: str,
    filename: str,
    file: UploadFile = File(...),
    db: DatabaseConnection = Depends(get_database),
    current_user: str = Depends(get_current_user_id),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict[str, Any]:
    """
    Update an existing file for a CODE_RUN action.
    
    The file will be updated in Tigris storage only. Use the deploy endpoint to deploy to Cloudflare.
    """
    try:
        # Validate ObjectId format
        try:
            object_id = ObjectId(action_id)
        except InvalidId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action ID format"
            )

        collection = db.database.actions
        action_data = await collection.find_one({"_id": object_id, "workspace_id": workspace_id})

        if not action_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")

        if action_data["type"] != ActionType.CODE_RUN.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Action must be of type CODE_RUN"
            )

        # Get action configuration
        config = CodeRunConfig.model_validate(action_data["default_config"])

        # Get Tigris service
        tigris_service = get_tigris_service()
        if not tigris_service.available:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="File storage service not available"
            )

        # Ensure the uploaded file has the same name as the URL parameter
        if file.filename != filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Uploaded file name '{file.filename}' does not match URL parameter '{filename}'"
            )

        # Read file content
        content = await file.read()
        
        # Validate file
        _validate_file_for_language(filename, content, config.language)

        # Check if file exists
        file_key = f"workspaces/{workspace_id}/code/{action_id}/{filename}"
        try:
            existing_metadata = await tigris_service.get_file_metadata(file_key)
            if not existing_metadata:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File '{filename}' not found"
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File '{filename}' not found"
            )

        try:
            # Delete existing file
            await tigris_service.delete_file(file_key)
            
            # Upload new version
            new_file_key = await tigris_service.upload_code_file(
                file_content=content,
                filename=filename,
                workspace_id=workspace_id,
                action_id=action_id,
                content_type=file.content_type or 'text/plain'
            )

            file_info = {
                'filename': filename,
                'file_key': new_file_key,
                'size': len(content),
                'content_type': file.content_type or 'text/plain'
            }

            # Log audit entry
            await AuditLoggerMixin.audit_update(
                audit_service=audit_service,
                user_id=current_user,
                workspace_id=workspace_id,
                resource_type="action_file",
                resource_id=f"{action_id}/{filename}",
                changes={"file_size": len(content)},
                resource_name=filename,
                metadata={
                    "action_id": action_id,
                    "action_name": action_data["name"],
                    "file_size": len(content),
                    "file_type": file.content_type or 'text/plain'
                },
            )

            return file_info

        except Exception as e:
            logger.error(f"Failed to update file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update file: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update action file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to update action file"
        )


@router.delete("/{action_id}/files/{filename}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_action_file(
    workspace_id: str,
    action_id: str,
    filename: str,
    db: DatabaseConnection = Depends(get_database),
    current_user: str = Depends(get_current_user_id),
    audit_service: AuditService = Depends(get_audit_service),
) -> None:
    """
    Delete a file from a CODE_RUN action.
    
    The file will be removed from Tigris storage only. Use the deploy endpoint to deploy changes to Cloudflare.
    """
    try:
        # Validate ObjectId format
        try:
            object_id = ObjectId(action_id)
        except InvalidId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action ID format"
            )

        collection = db.database.actions
        action_data = await collection.find_one({"_id": object_id, "workspace_id": workspace_id})

        if not action_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")

        if action_data["type"] != ActionType.CODE_RUN.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Action must be of type CODE_RUN"
            )

        # Get action configuration
        config = CodeRunConfig.model_validate(action_data["default_config"])

        # Get Tigris service
        tigris_service = get_tigris_service()
        if not tigris_service.available:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="File storage service not available"
            )

        # Prevent deletion of the entry point file
        if filename == config.entry_point:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete entry point file '{filename}'"
            )

        # Check if file exists and delete it
        file_key = f"workspaces/{workspace_id}/code/{action_id}/{filename}"
        try:
            success = await tigris_service.delete_file(file_key)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File '{filename}' not found"
                )
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete file: {str(e)}"
            )

        # Log audit entry
        await AuditLoggerMixin.audit_delete(
            audit_service=audit_service,
            user_id=current_user,
            workspace_id=workspace_id,
            resource_type="action_file",
            resource_id=f"{action_id}/{filename}",
            resource_name=filename,
            metadata={
                "action_id": action_id,
                "action_name": action_data["name"]
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete action file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to delete action file"
        )


@router.get("/{action_id}/worker-content")
async def get_worker_content(
    workspace_id: str,
    action_id: str,
    db: DatabaseConnection = Depends(get_database),
    current_user: str = Depends(get_current_user_id),
):
    """Get worker content from Cloudflare Workers for Platforms."""
    try:
        # Validate ObjectId format
        try:
            object_id = ObjectId(action_id)
        except InvalidId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action ID format"
            )

        collection = db.database.actions
        action_data = await collection.find_one({"_id": object_id, "workspace_id": workspace_id})

        if not action_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")

        if action_data["type"] != ActionType.CODE_RUN.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Action must be of type CODE_RUN")

        # Parse configuration
        config = CodeRunConfig.model_validate(action_data["default_config"])

        # Get worker content from Cloudflare
        cloudflare_service = get_cloudflare_workers_service()
        if not cloudflare_service.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cloudflare Workers service not available"
            )

        try:
            # Note: Cloudflare API doesn't provide direct content access
            # Return worker metadata instead
            worker_info = await cloudflare_service.get_customer_worker_info(config.worker_name)
            if not worker_info:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")
            
            return {
                "worker_name": config.worker_name,
                "dispatch_namespace": config.dispatch_namespace,
                "entry_point": config.entry_point,
                "language": config.language,
                "worker_info": worker_info,
                "note": "Worker content is managed by Cloudflare Workers for Platforms"
            }
        except Exception as e:
            logger.error(f"Failed to get worker content: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get worker content"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get worker content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get worker content"
        )


@router.get("/{action_id}/executions", response_model=dict[str, Any])
async def get_action_execution_history(
    workspace_id: str,
    action_id: str,
    status_filter: str | None = Query(None, description="Filter by execution status"),
    start_date: str | None = Query(None, description="Start date filter (ISO format)"),
    end_date: str | None = Query(None, description="End date filter (ISO format)"),
    limit: int = Query(50, ge=1, le=100, description="Number of executions to return"),
    skip: int = Query(0, ge=0, description="Number of executions to skip"),
    db: DatabaseConnection = Depends(get_database),
    current_user: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """
    Get execution history for a specific action.

    Returns detailed execution logs including status, timing, inputs/outputs,
    and error information. Useful for debugging, monitoring, and analytics.

    **Query Parameters:**
    - `status_filter`: Filter by status (completed, failed, running, cancelled)
    - `start_date`: Start of date range (ISO 8601 format)
    - `end_date`: End of date range (ISO 8601 format)
    - `limit`: Results per page (1-100, default: 50)
    - `skip`: Results to skip for pagination

    **Response Example:**
    ```json
    {
        "executions": [
            {
                "id": "exec-123",
                "action_id": "6883cc77f0dd6dbee6550be8",
                "workspace_id": "workspace-id",
                "status": "completed",
                "started_at": "2024-01-15T10:30:00Z",
                "completed_at": "2024-01-15T10:30:02Z",
                "execution_time_ms": 2000,
                "input": {
                    "city": "London",
                    "units": "metric"
                },
                "output": {
                    "temperature": 15,
                    "condition": "Cloudy"
                },
                "triggered_by": "assistant",
                "assistant_id": "asst-123",
                "thread_id": "thread-456"
            },
            {
                "id": "exec-124",
                "action_id": "6883cc77f0dd6dbee6550be8",
                "status": "failed",
                "started_at": "2024-01-15T11:00:00Z",
                "completed_at": "2024-01-15T11:00:01Z",
                "execution_time_ms": 1000,
                "error": {
                    "message": "API rate limit exceeded",
                    "code": "RATE_LIMIT"
                }
            }
        ],
        "pagination": {
            "total": 150,
            "skip": 0,
            "limit": 50,
            "has_more": true
        },
        "summary": {
            "total_executions": 150,
            "by_status": {
                "completed": 140,
                "failed": 8,
                "cancelled": 2
            },
            "avg_execution_time_ms": 1850.5,
            "success_rate": 93.33
        },
        "action": {
            "id": "6883cc77f0dd6dbee6550be8",
            "name": "get-weather",
            "type": "REST"
        }
    }
    ```

    **Execution Status Values:**
    - `pending`: Queued for execution
    - `running`: Currently executing
    - `completed`: Successfully completed
    - `failed`: Failed with error
    - `cancelled`: Cancelled by user/system
    - `timeout`: Exceeded time limit

    **Triggered By Values:**
    - `assistant`: OpenAI assistant via MCP
    - `api`: Direct API call
    - `webhook`: Incoming webhook
    - `schedule`: Scheduled execution
    - `manual`: UI or test execution

    **Use Cases:**
    - Monitor action performance and reliability
    - Debug failed executions
    - Analyze usage patterns
    - Track assistant tool usage
    - Audit action executions
    """
    try:
        # Validate ObjectId format
        try:
            object_id = ObjectId(action_id)
        except InvalidId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action ID format"
            )

        # Verify action exists and user has access
        actions_collection = db.database.actions
        action_data = await actions_collection.find_one(
            {"_id": object_id, "workspace_id": workspace_id}
        )

        if not action_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")

        # Build execution query
        executions_collection = db.database.executions
        query = {"action_id": action_id, "workspace_id": workspace_id}

        # Add status filter if provided
        if status_filter:
            query["status"] = status_filter

        # Add date range filters if provided
        date_query = {}
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                date_query["$gte"] = start_dt
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)",
                )

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                date_query["$lte"] = end_dt
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)",
                )

        if date_query:
            query["started_at"] = date_query

        # Get total count for pagination
        total_count = await executions_collection.count_documents(query)

        # Get executions with pagination, sorted by most recent first
        cursor = executions_collection.find(query).sort("started_at", -1).skip(skip).limit(limit)

        # Convert executions to list
        executions = []
        async for execution_data in cursor:
            # Convert ObjectIds to strings
            if "_id" in execution_data:
                execution_data["id"] = str(execution_data["_id"])
                del execution_data["_id"]

            # Convert other ObjectIds to strings
            for field in ["action_id"]:
                if field in execution_data and isinstance(execution_data[field], ObjectId):
                    execution_data[field] = str(execution_data[field])

            executions.append(execution_data)

        # Calculate pagination info
        has_more = skip + len(executions) < total_count

        # Calculate summary statistics
        summary_pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": 1},
                    "by_status": {"$push": "$status"},
                    "avg_execution_time": {
                        "$avg": {
                            "$cond": [
                                {"$ne": ["$execution_time_ms", None]},
                                "$execution_time_ms",
                                0,
                            ]
                        }
                    },
                    "completed_count": {
                        "$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}
                    },
                }
            },
        ]

        summary_result = await executions_collection.aggregate(summary_pipeline).to_list(1)

        if summary_result:
            summary_data = summary_result[0]

            # Count by status
            status_counts = {}
            for status in summary_data["by_status"]:
                status_counts[status] = status_counts.get(status, 0) + 1

            # Calculate success rate
            total = summary_data["total"]
            completed = summary_data["completed_count"]
            success_rate = (completed / total * 100) if total > 0 else 0

            summary = {
                "total_executions": total,
                "by_status": status_counts,
                "avg_execution_time_ms": (
                    round(summary_data["avg_execution_time"], 2)
                    if summary_data["avg_execution_time"]
                    else None
                ),
                "success_rate": round(success_rate, 2),
            }
        else:
            summary = {
                "total_executions": 0,
                "by_status": {},
                "avg_execution_time_ms": None,
                "success_rate": 0.0,
            }

        return {
            "executions": executions,
            "pagination": {
                "total": total_count,
                "skip": skip,
                "limit": limit,
                "has_more": has_more,
            },
            "summary": summary,
            "action": {"id": action_id, "name": action_data["name"], "type": action_data["type"]},
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get execution history for action {action_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get execution history",
        )


@router.post("/{action_id}/deploy", response_model=dict[str, Any])
async def deploy_action(
    workspace_id: str,
    action_id: str,
    db: DatabaseConnection = Depends(get_database),
    current_user: str = Depends(get_current_user_id),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict[str, Any]:
    """
    Deploy a CODE_RUN action to Cloudflare Workers.
    
    This endpoint:
    1. Fetches all user files from Tigris
    2. Generates infrastructure files (main.js, wrangler.toml, package.json)
    3. Deploys everything to Cloudflare Workers
    
    The deployment includes both infrastructure files and user files.
    """
    try:
        # Validate ObjectId format
        try:
            object_id = ObjectId(action_id)
        except InvalidId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action ID format"
            )

        collection = db.database.actions
        action_data = await collection.find_one({"_id": object_id, "workspace_id": workspace_id})

        if not action_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")

        if action_data["type"] != ActionType.CODE_RUN.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Action must be of type CODE_RUN"
            )
        
        # Parse configuration
        config = CodeRunConfig.model_validate(action_data["default_config"])
        
        # Get services
        tigris_service = get_tigris_service()
        cloudflare_service = get_cloudflare_workers_service()
        
        if not tigris_service.available:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="File storage service is not available. Please check configuration."
            )
            
        if not cloudflare_service.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cloudflare Workers service is not available. Please check configuration."
            )

        try:
            # 1. Get user files from Tigris
            user_files_metadata = await tigris_service.list_code_files(workspace_id, action_id)
            
            if not user_files_metadata:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No files found for deployment. Please upload files first."
                )

            # Get file contents
            user_files = []
            for file_info in user_files_metadata:
                try:
                    content = await tigris_service.get_code_file_content(file_info['key'])
                    user_files.append({
                        "filename": file_info.get('original_filename', ''),
                        "content": content
                    })
                except Exception as e:
                    logger.error(f"Failed to get file content for {file_info['key']}: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to retrieve file: {file_info.get('original_filename', 'unknown')}"
                    )

            # 2. Generate infrastructure files
            infrastructure_files = _generate_infrastructure_files(
                config.worker_name, 
                config.language, 
                config.entry_point
            )
            
            # 3. Convert infrastructure files to UploadFile objects
            from fastapi import UploadFile
            from io import BytesIO
            
            infrastructure_file_objects = []
            for file_data in infrastructure_files:
                file_stream = BytesIO(file_data["content"])
                file_obj = UploadFile(
                    filename=file_data["filename"],
                    file=file_stream
                )
                infrastructure_file_objects.append(file_obj)
            
            # 4. Convert user files to UploadFile objects, putting them in src/ folder
            user_file_objects = []
            for file_data in user_files:
                file_stream = BytesIO(file_data["content"])
                # Put all user files in src/ folder, rename entry point to standard name
                if file_data["filename"] == config.entry_point:
                    filename = "src/user-main.js"  # Standard name for user's entry point
                else:
                    filename = f"src/{file_data['filename']}"  # Put other user files in src/ folder
                
                file_obj = UploadFile(
                    filename=filename,
                    file=file_stream
                )
                user_file_objects.append(file_obj)
            
            # 5. Combine infrastructure files + user files
            all_cloudflare_files = infrastructure_file_objects + user_file_objects
            
            # 6. Deploy to Cloudflare Workers
            if config.worker_name:
                # Update existing worker
                success = await cloudflare_service.update_customer_worker(
                    worker_name=config.worker_name,
                    files=all_cloudflare_files,
                    language=config.language,
                    entry_point="main"  # Infrastructure main.js is the entry point
                )
                if not success:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to update Cloudflare worker"
                    )
                deployed_worker_name = config.worker_name
            else:
                # Create new worker if somehow the worker_name is missing
                deployed_worker_name = await cloudflare_service.create_customer_worker(
                    workspace_id=workspace_id,
                    action_id=action_id,
                    files=all_cloudflare_files,
                    language=config.language,
                    entry_point="main"  # Infrastructure main.js is the entry point
                )
                
                # Update action with worker name
                config.worker_name = deployed_worker_name
                await collection.update_one(
                    {"_id": ObjectId(action_id)},
                    {
                        "$set": {
                            "default_config": config.model_dump(),
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
            
            # Log audit entry
            await AuditLoggerMixin.audit_create(
                audit_service=audit_service,
                user_id=current_user,
                workspace_id=workspace_id,
                resource_type="action_deployment",
                resource_id=f"{action_id}/deploy",
                resource_name=f"Deploy {action_data['name']}",
                metadata={
                    "action_id": action_id,
                    "action_name": action_data["name"],
                    "worker_name": deployed_worker_name,
                    "file_count": len(user_files),
                    "language": config.language
                },
            )
            
            return {
                "success": True,
                "worker_name": deployed_worker_name,
                "deployed_files": len(all_cloudflare_files),
                "user_files": len(user_files),
                "infrastructure_files": len(infrastructure_files),
                "message": "Action deployed successfully to Cloudflare Workers"
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to deploy action {action_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to deploy action: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to deploy action {action_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deploy action"
        )

