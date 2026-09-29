"""FastAPI router for admin API (embeddable)."""

import os
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPBearer
from loguru import logger
from pydantic import BaseModel, Field

from .actions.rest_executor import RestActionExecutor
from .auth.dependencies import get_current_user, require_authentication

# Import authentication system
from .auth.models import User
from .database.connection import DatabaseConnection, get_database_connection
from .models.action import (
    ActionCreateRequest,
    ActionModel,
    ActionStatus,
    ActionType,
    ActionUpdateRequest,
)
from .models.audit_log import AuditAction
from .models.secret import SecretCreateRequest, SecretListResponse, SecretUpdateRequest
from .models.workspace import WorkspaceCreate
from .routers.admin_config import router as admin_config_router
from .routers.analytics import router as analytics_router

# Import routers
from .routers.actions import router as actions_router
from .routers.assistants import router as assistants_router
from .routers.audit import get_audit_service
from .routers.audit import router as audit_router
from .routers.auth_router import router as auth_router  # Sessionless auth
from .routers.billing_router import router as billing_router
from .routers.chat import router as chat_router
from .routers.integrations import router as integrations_router
from .routers.knowledge_base import router as knowledge_base_router
from .routers.mcp_oauth import router as mcp_oauth_router
from .routers.mcp_tokens import router as mcp_tokens_router
from .routers.mcp_multitenant import router as mcp_multitenant_router
# MCP execution routers moved to root level mounting in server.py
from .routers.monitoring import router as monitoring_router
from .routers.mcp_monitoring import router as mcp_monitoring_router
from .routers.oauth import router as oauth_router
# oauth_clients_router removed - replaced with workspace_oauth_clients
from .routers.workspace_oauth_clients import workspace_oauth_router
from .routers.partners import router as partners_router
from .routers.service_keys import router as service_keys_router
from .routers.prompts import router as prompts_router
from .routers.public_health import router as public_health_router
from .routers.team_management import router as team_management_router
try:
    from .routers.test_auth_router import router as test_auth_router
except ImportError:
    test_auth_router = None
from .routers.users_router import router as users_router
from .routers.workspace import get_current_user as get_workspace_user
from .routers.workspace import workspace_router
from .routers.workspaces_router import router as workspaces_router
from .secrets.encryption import SecretEncryption
from .secrets.types import SECRET_TYPES, SecretType
from .services.audit_service import AuditService
from .services.secret_service import SecretService
from .services.workspace_service_adapter import get_workspace_adapter

# Create the admin router
admin_router = APIRouter(
    responses={404: {"description": "Not found"}, 500: {"description": "Internal server error"}}
)

# Include authentication routes
admin_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])

# Create workspace-scoped sub-routers
workspace_executions_router = APIRouter(
    prefix="/workspaces/{workspace_id}/executions", tags=["Executions"]
)
workspace_secrets_router = APIRouter(prefix="/workspaces/{workspace_id}/secrets", tags=["Secrets"])
# workspace_oauth_clients_router removed - using workspace_oauth_router from workspace_oauth_clients.py instead

# Include routers at the end of the file after endpoints are defined

# Use a default master key for development/testing
encryption = SecretEncryption()
secret_service = SecretService(encryption)
rest_executor = RestActionExecutor(secret_service)

# Initialize security dependencies
security = HTTPBearer(auto_error=False)


# Dependency to get database
async def get_database() -> DatabaseConnection:
    """Get database connection dependency."""
    try:
        logger.info("get_database dependency called")
        db = get_database_connection()
        logger.info(f"Got database connection: {db}")
        logger.info(f"Database is_connected: {db.is_connected}")
        return db
    except RuntimeError as e:
        logger.error(f"Database connection not available: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database service unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_database: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database service error"
        )


def get_database_collection(db: DatabaseConnection, collection_name: str):
    """Safely get a database collection, handling Motor database errors."""
    # Use attribute access like the working version: db.database.actions
    try:
        database = db.database
        return getattr(database, collection_name)
    except Exception as db_error:
        logger.error(f"Error accessing database collection '{collection_name}': {db_error}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service temporarily unavailable",
        )


# Note: We've removed the old get_current_user_and_workspace dependency
# Now using require_authentication from auth.dependencies directly
# This provides proper user authentication without hardcoded TEST_WORKSPACE_ID


# Test endpoint without dependencies
@admin_router.get("/test", tags=["System"])
async def test_endpoint():
    """Simple test endpoint to verify routing works."""
    logger.info("Test endpoint called!")
    return {"status": "ok", "message": "Admin API routing works"}


# Global workspaces endpoint for user workspace discovery
@admin_router.get("/workspaces", response_model=dict[str, Any], tags=["Workspaces"])
async def list_user_workspaces(
    current_user: User = Depends(require_authentication),
    db: DatabaseConnection = Depends(get_database),
) -> dict[str, Any]:
    """List workspaces accessible to the current user."""
    user_id = current_user.id

    try:
        # Get workspace service
        workspace_adapter = get_workspace_adapter()

        # Get user's workspaces from MongoDB
        workspaces = await workspace_adapter.list_user_workspaces(user_id)

        # Convert workspace objects to dicts with proper serialization
        workspace_list = []
        for workspace in workspaces:
            # The MongoBaseModel handles all serialization properly
            workspace_dict = workspace.model_dump(mode="json")
            workspace_list.append(workspace_dict)

        # Get the last workspace ID (if any)
        last_workspace_id = workspace_list[0]["id"] if workspace_list else None

        return {
            "workspaces": workspace_list,
            "user": {"id": user_id, "last_workspace_id": last_workspace_id},
        }

    except Exception as e:
        logger.error(f"Failed to list workspaces for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workspaces",
        )


# Create workspace model that matches frontend expectations
class WorkspaceCreateRequest(BaseModel):
    """Request model for creating a workspace."""

    name: str
    type: str | None = "personal"  # personal or team
    size: str | None = "solo"  # solo, small, medium, large
    industry: str | None = ""
    settings: dict[str, Any] | None = Field(default_factory=dict)


@admin_router.post("/workspaces", response_model=dict[str, Any], tags=["Workspaces"])
async def create_workspace(
    workspace_data: WorkspaceCreateRequest,
    current_user: User = Depends(require_authentication),
    db: DatabaseConnection = Depends(get_database),
) -> dict[str, Any]:
    """Create a new workspace for the current user."""
    user_id = current_user.id

    try:
        # Convert to WorkspaceCreate model
        workspace_create = WorkspaceCreate(
            name=workspace_data.name,
            owner_id=user_id,
            description=f"{workspace_data.type.title()} workspace",
            settings={
                **workspace_data.settings,
                "type": workspace_data.type,
                "size": workspace_data.size,
                "industry": workspace_data.industry,
            },
        )

        # Use the workspace adapter to create the workspace
        adapter = get_workspace_adapter()
        workspace = await adapter.create_workspace(workspace_create)

        # Convert to dict for response using model_dump with mode='json' to handle ObjectIds
        workspace_dict = workspace.model_dump(mode="json")

        # Ensure id field exists for frontend compatibility
        if "_id" in workspace_dict:
            workspace_dict["id"] = workspace_dict["_id"]
        elif "id" not in workspace_dict and workspace.id:
            workspace_dict["id"] = str(workspace.id)

        return workspace_dict

    except Exception as e:
        logger.error(f"Error creating workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create workspace"
        )


# Authentication info endpoint
@admin_router.get("/auth-info", tags=["Authentication"])
async def get_auth_info(current_user: str = Depends(get_current_user)) -> dict[str, Any]:
    """Get authentication information."""
    return {
        "current_user": current_user,
        "auth_methods": ["JWT", "API Key"],
        "endpoints": {
            "signup": "/admin/auth/signup",
            "login": "/admin/auth/login",
            "create_api_key": "/admin/auth/api-keys",
            "list_api_keys": "/admin/auth/api-keys",
            "user_info": "/admin/auth/me",
        },
    }


# Action Type Information Endpoints (must come before /actions/{action_id})


@admin_router.get("/actions/types", response_model=list[dict[str, Any]], tags=["Actions"])
async def get_action_types() -> list[dict[str, Any]]:
    """Get available action types."""
    return [
        {"type": action_type.value, "description": f"{action_type.value} action type"}
        for action_type in ActionType
    ]


class ActionStats(BaseModel):
    """Actions statistics model."""
    total_actions: int = 0
    active_actions: int = 0
    inactive_actions: int = 0
    actions_by_type: dict[str, int] = {}
    recent_executions: int = 0  # Last 24 hours

# Execution Management Endpoints

@workspace_executions_router.get("", response_model=list[dict[str, Any]])
async def list_executions(
    workspace_id: str,  # From URL path
    action_id: str | None = Query(None, description="Filter by action"),
    status: str | None = Query(None, description="Filter by status"),
    user_id: str | None = Query(None, description="Filter by user"),
    limit: int = Query(50, ge=1, le=100, description="Number of executions to return"),
    skip: int = Query(0, ge=0, description="Number of executions to skip"),
    current_user: str = Depends(get_workspace_user),  # Verifies access
) -> list[dict[str, Any]]:
    """List executions with optional filtering."""
    try:
        # Use the workspace_id from URL path
        filter_workspace_id = workspace_id

        from .models.execution import ExecutionStatus
        from .services.execution_service import ExecutionService

        execution_service = ExecutionService()

        # Convert string status to enum if provided
        status_filter = None
        if status:
            try:
                status_filter = ExecutionStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        # Use the enhanced aggregation method with debugging
        return await execution_service.list_executions_with_names(
            workspace_id=filter_workspace_id,
            action_id=action_id,
            status=status_filter,
            skip=skip,
            limit=limit,
        )


    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list executions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve executions")


@workspace_executions_router.post("", response_model=dict[str, Any], status_code=201)
async def create_execution(
    workspace_id: str,  # From URL path
    execution_request: dict[str, Any],
    current_user: str = Depends(get_workspace_user),  # Verifies access
) -> dict[str, Any]:
    """Create and start a new execution."""
    try:
        from .models.execution import ExecutionCreateRequest
        from .services.execution_service import ExecutionService

        execution_service = ExecutionService()

        # Override workspace_id with authenticated one
        execution_request["workspace_id"] = workspace_id

        # Parse request
        create_request = ExecutionCreateRequest(**execution_request)

        # Create execution
        execution_id = await execution_service.create_execution(create_request, current_user)

        # Get the created execution
        execution = await execution_service.get_execution_by_id(execution_id)
        if not execution:
            raise HTTPException(status_code=500, detail="Failed to retrieve created execution")

        logger.info(
            f"Created execution {execution_id} for action {create_request.action_id} by user {current_user}"
        )
        return {
            "id": execution_id,
            "action_id": execution.action_id,
            "status": execution.status,
            "started_at": execution.started_at,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create execution: {e}")
        raise HTTPException(status_code=500, detail="Failed to create execution")


@workspace_executions_router.get("/{execution_id}", response_model=dict[str, Any])
async def get_execution(
    workspace_id: str,  # From URL path
    execution_id: str,
    current_user: str = Depends(get_workspace_user),  # Verifies access
) -> dict[str, Any]:
    """Get execution details."""
    try:
        from .services.execution_service import ExecutionService

        execution_service = ExecutionService()
        execution = await execution_service.get_execution_by_id(execution_id)

        # Verify execution belongs to current workspace
        if not execution or execution.workspace_id != workspace_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")

        return {
            "id": execution.id,
            "action_id": execution.action_id,
            "workspace_id": execution.workspace_id,
            "user_id": execution.user_id,
            "input_data": execution.input_data,
            "output_data": execution.output_data,
            "status": execution.status,
            "execution_time_ms": execution.execution_time_ms,
            "error_message": execution.error_message,
            "started_at": execution.started_at,
            "completed_at": execution.completed_at,
            "execution_context": execution.execution_context,
            "retry_count": execution.retry_count,
            "max_retries": execution.max_retries,
            "can_retry": execution.can_retry(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get execution {execution_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve execution")


@workspace_executions_router.post("/{execution_id}/retry", response_model=dict[str, Any])
async def retry_execution(
    workspace_id: str,  # From URL path
    execution_id: str,
    current_user: str = Depends(get_workspace_user),  # Verifies access
) -> dict[str, Any]:
    """Retry a failed execution."""
    try:
        from .services.execution_service import ExecutionService

        execution_service = ExecutionService()

        # First verify execution belongs to workspace
        execution = await execution_service.get_execution_by_id(execution_id)
        if not execution or execution.workspace_id != workspace_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

        success = await execution_service.retry_execution(execution_id, current_user)

        if not success:
            raise HTTPException(status_code=400, detail="Execution cannot be retried")

        # Get updated execution
        execution = await execution_service.get_execution_by_id(execution_id)

        logger.info(f"Retried execution {execution_id} by user {current_user}")
        return {
            "id": execution_id,
            "status": execution.status,
            "retry_count": execution.retry_count,
            "message": "Execution retry initiated",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry execution {execution_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retry execution")


@workspace_executions_router.delete("/{execution_id}", status_code=204)
async def cancel_execution(
    workspace_id: str,  # From URL path
    execution_id: str,
    current_user: str = Depends(get_workspace_user),  # Verifies access
) -> None:
    """Cancel a running execution."""
    try:
        from .services.execution_service import ExecutionService

        execution_service = ExecutionService()

        # First verify execution belongs to workspace
        execution = await execution_service.get_execution_by_id(execution_id)
        if not execution or execution.workspace_id != workspace_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

        success = await execution_service.cancel_execution(execution_id, current_user)

        if not success:
            raise HTTPException(status_code=400, detail="Execution cannot be cancelled")

        logger.info(f"Cancelled execution {execution_id} by user {current_user}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel execution {execution_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel execution")


@workspace_executions_router.get("/summary", response_model=dict[str, Any], tags=["Executions"])
async def get_execution_summary(
    workspace_id: str,  # From URL path
    action_id: str | None = Query(None, description="Filter by action"),
    current_user: str = Depends(get_workspace_user),  # Verifies access
) -> dict[str, Any]:
    """Get execution summary statistics."""
    try:
        from .services.execution_service import ExecutionService

        execution_service = ExecutionService()
        # Use the workspace_id from URL path
        filter_workspace_id = workspace_id

        summary = await execution_service.get_execution_summary(
            workspace_id=filter_workspace_id, action_id=action_id
        )

        return {
            "total_executions": summary.total_executions,
            "by_status": summary.by_status,
            "avg_execution_time_ms": summary.avg_execution_time_ms,
            "success_rate": summary.success_rate,
        }

    except Exception as e:
        logger.error(f"Failed to get execution summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve execution summary")


# Secret Type Information Endpoints (must come before /secrets/{secret_id})


@admin_router.get("/secrets/types", response_model=dict[str, Any], tags=["Secrets"])
async def get_secret_types() -> dict[str, Any]:
    """Get available secret types and their metadata."""
    # Return static secret types info - no database needed
    return {"secret_types": SECRET_TYPES}


@workspace_secrets_router.get("/types", response_model=list[dict[str, Any]])
async def get_secret_types_workspace(
    workspace_id: str,  # From URL path
    current_user: str = Depends(get_workspace_user),  # Verifies access
) -> list[dict[str, Any]]:
    """Get available secret types for the workspace."""
    # Return secret types in the same format as action types
    return [{"value": secret_type.value, "label": secret_type.value} for secret_type in SecretType]


@workspace_secrets_router.get("", response_model=list[SecretListResponse])
async def list_secrets(
    workspace_id: str,  # From URL path
    secret_type: SecretType | None = Query(None, description="Filter by secret type"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=100, description="Number of secrets to return"),
    skip: int = Query(0, ge=0, description="Number of secrets to skip"),
    current_user: str = Depends(get_workspace_user),  # Verifies access
) -> list[SecretListResponse]:
    """List secrets (without sensitive data)."""
    try:

        secrets = await secret_service.list_secrets(
            workspace_id=workspace_id,
            secret_type=secret_type,
            is_active=is_active,
            skip=skip,
            limit=limit,
        )

        logger.info(f"Listed {len(secrets)} secrets for user {current_user}")
        return secrets

    except Exception as e:
        logger.error(f"Failed to list secrets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve secrets"
        )


@workspace_secrets_router.post(
    "", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED
)
async def create_secret(
    workspace_id: str,  # From URL path
    secret_request: SecretCreateRequest,
    current_user: str = Depends(get_workspace_user),  # Verifies access
) -> dict[str, Any]:
    """Create a new encrypted secret."""
    try:
        # Override the workspace_id from the request with the authenticated one
        secret_request.workspace_id = workspace_id
        secret_id = await secret_service.create_secret(secret_request, current_user)

        # Get the created secret (without sensitive data)
        secret = await secret_service.get_secret_by_id(secret_id, current_user)
        if not secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve created secret",
            )

        logger.info(f"Created secret '{secret.name}' by user {current_user}")
        return {
            "id": secret_id,
            "name": secret.name,
            "secret_type": secret.secret_type,
            "created_at": secret.created_at,
        }

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create secret: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create secret"
        )


@workspace_secrets_router.get("/{secret_id}", response_model=dict[str, Any])
async def get_secret(
    workspace_id: str,  # From URL path
    secret_id: str,
    current_user: str = Depends(get_workspace_user),  # Verifies access
) -> dict[str, Any]:
    """Get secret metadata (without the actual secret value)."""
    try:
        secret = await secret_service.get_secret_by_id(secret_id, current_user)

        # Verify the secret belongs to the current workspace
        if not secret or secret.workspace_id != workspace_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")

        return {
            "id": secret.id,
            "workspace_id": secret.workspace_id,
            "name": secret.name,
            "description": secret.description,
            "secret_type": secret.secret_type,
            "tags": secret.tags,
            "is_active": secret.is_active,
            "created_at": secret.created_at,
            "updated_at": secret.updated_at,
            "expires_at": secret.expires_at,
            "last_used_at": secret.last_used_at,
            "usage_count": secret.usage_count,
            "max_usage_count": secret.max_usage_count,
            "is_expired": secret.is_expired(),
            "is_usage_exceeded": secret.is_usage_exceeded(),
            "can_be_used": secret.can_be_used(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get secret {secret_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve secret"
        )


@workspace_secrets_router.put("/{secret_id}", response_model=dict[str, Any])
async def update_secret(
    workspace_id: str,  # From URL path
    secret_id: str,
    secret_update: SecretUpdateRequest,
    current_user: str = Depends(get_workspace_user),  # Verifies access
) -> dict[str, Any]:
    """Update a secret."""
    try:
        # First check if secret exists and belongs to workspace
        secret = await secret_service.get_secret_by_id(secret_id, current_user)
        if not secret or secret.workspace_id != workspace_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")

        success = await secret_service.update_secret(secret_id, secret_update, current_user)

        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")

        # Return updated secret metadata
        secret = await secret_service.get_secret_by_id(secret_id, current_user)

        logger.info(f"Updated secret {secret_id} by user {current_user}")
        return {"id": secret.id, "name": secret.name, "updated_at": secret.updated_at}

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update secret {secret_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update secret"
        )


@workspace_secrets_router.delete("/{secret_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_secret(
    workspace_id: str,  # From URL path
    secret_id: str,
    current_user: str = Depends(get_workspace_user),  # Verifies access
) -> None:
    """Delete a secret."""
    try:
        # First check if secret exists and belongs to workspace
        secret = await secret_service.get_secret_by_id(secret_id, current_user)
        if not secret or secret.workspace_id != workspace_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")

        success = await secret_service.delete_secret(secret_id, current_user)

        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")

        logger.info(f"Deleted secret {secret_id} by user {current_user}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete secret {secret_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete secret"
        )


@workspace_secrets_router.get("/{secret_id}/usage-logs", response_model=list[dict[str, Any]])
async def get_secret_usage_logs(
    workspace_id: str,  # From URL path
    secret_id: str,
    limit: int = Query(50, ge=1, le=100, description="Number of logs to return"),
    skip: int = Query(0, ge=0, description="Number of logs to skip"),
    current_user: str = Depends(get_workspace_user),  # Verifies access
) -> list[dict[str, Any]]:
    """Get usage logs for a secret."""
    try:
        # First check if secret exists and belongs to workspace
        secret = await secret_service.get_secret_by_id(secret_id, current_user)
        if not secret or secret.workspace_id != workspace_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")
        logs = await secret_service.get_secret_usage_logs(secret_id, skip, limit)

        # Convert to dict format
        return [
            {
                "id": log.id,
                "timestamp": log.timestamp,
                "user_id": log.user_id,
                "access_method": log.access_method,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
            }
            for log in logs
        ]

    except Exception as e:
        logger.error(f"Failed to get usage logs for secret {secret_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage logs",
        )


# Debug endpoint to list all routes
@admin_router.get("/debug/routes", response_model=list[dict[str, Any]], tags=["System"])
async def debug_routes() -> list[dict[str, Any]]:
    """List all registered routes for debugging."""
    routes = []
    for route in admin_router.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            routes.append(
                {
                    "path": route.path,
                    "methods": list(route.methods),
                    "name": getattr(route, "name", "unknown"),
                }
            )
    return sorted(routes, key=lambda x: x["path"])


# Health Check Endpoint


@admin_router.get("/health", response_model=dict[str, Any], tags=["System"])
async def health_check(
    include_smoke_tests: bool = Query(False, description="Include smoke tests in health check"),
    db: DatabaseConnection = Depends(get_database),
) -> dict[str, Any]:
    """Health check endpoint with optional smoke tests."""
    try:
        # Import here to avoid circular imports
        from .health import HealthChecker

        # Get encryption instance from the global secret_service
        health_checker = HealthChecker(
            db_connection=db,
            secret_encryption=secret_service.encryption if secret_service else None,
        )

        # Run health check
        return await health_checker.check_health(include_smoke_tests=include_smoke_tests)

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "error": str(e),
            "components": {"database": {"status": "unhealthy", "error": str(e)}},
        }


# OAuth Clients Stats Endpoint

# OAuth client stats endpoint moved to workspace_oauth_clients.py


# Include debug router in development only
if os.getenv("ENVIRONMENT") in ["development", "dev_test"]:
    from .routers.debug_router import router as debug_router

    admin_router.include_router(debug_router)
    logger.info("Debug router included (development mode)")

# Include workspace-scoped routers AFTER endpoints are defined
logger.info("Including routers...")
admin_router.include_router(assistants_router)
admin_router.include_router(chat_router)
# MCP execution routers moved to root level - no longer under admin
# admin_router.include_router(mcp_router)
# admin_router.include_router(multitenant_router)

# MCP token management remains in admin space (admin-only feature)
admin_router.include_router(mcp_tokens_router)
# MCP execution endpoints moved to root level (/mcp/{workspace_id}/*)
# The working simple implementation is mounted in server.py at root level
# Keep SSE implementations as backup (not included in routing)
# admin_router.include_router(mcp_stateless_router)
# admin_router.include_router(mcp_native_router)

admin_router.include_router(integrations_router)
admin_router.include_router(service_keys_router)

# MCP monitoring (separate from protocol implementation)
admin_router.include_router(mcp_monitoring_router)
# IMPORTANT: OAuth router MUST be mounted under /integrations prefix to match Google Cloud Console configuration
# Current registered URI: http://localhost:8090/admin/api/v1/integrations/oauth/callback/google_calendar
# DO NOT CHANGE this prefix without updating Google Cloud Console redirect URIs
admin_router.include_router(oauth_router, prefix="/integrations")
# OAuth clients management API - for managing MCP OAuth clients
# oauth_clients_router removed - replaced with workspace OAuth clients
admin_router.include_router(workspace_oauth_router)  # Workspace-scoped OAuth clients (full CRUD + stats)
# MCP OAuth 2.1 authorization server for third-party clients - mounted at /oauth for standard OAuth endpoints
admin_router.include_router(mcp_oauth_router, prefix="/oauth")
admin_router.include_router(workspace_router)
admin_router.include_router(users_router)
admin_router.include_router(workspaces_router)
admin_router.include_router(billing_router)
logger.info(f"Executions router has {len(workspace_executions_router.routes)} routes")
admin_router.include_router(workspace_executions_router)
logger.info(f"Secrets router has {len(workspace_secrets_router.routes)} routes")
admin_router.include_router(workspace_secrets_router)
logger.info(f"Actions router has {len(actions_router.routes)} routes")
admin_router.include_router(actions_router)
# Include audit logs router
admin_router.include_router(audit_router)
# Include analytics router
admin_router.include_router(analytics_router)
# Include knowledge base router
admin_router.include_router(knowledge_base_router)
# Include prompts router
admin_router.include_router(prompts_router)
# Include team management router
admin_router.include_router(team_management_router, prefix="/workspaces", tags=["Team Management"])
# Include public MCP router (for health endpoints only)
# Include monitoring router (requires auth)
admin_router.include_router(monitoring_router, prefix="/monitoring")
# Include public health router (no auth, rate limited)
admin_router.include_router(public_health_router)

# Include partner API router
admin_router.include_router(partners_router, prefix="/partner")

# Include test auth router (only in development/test environments)
if test_auth_router:
    admin_router.include_router(test_auth_router)
    logger.warning("⚠️  Test auth router included - DO NOT USE IN PRODUCTION")

# Include admin config router (protected by secret)
admin_router.include_router(admin_config_router)

# Note: Exception handlers should be added to the main FastAPI app, not the router
# The embedding application can add these handlers:
#
# @app.exception_handler(HTTPException)
# async def http_exception_handler(request, exc: HTTPException):
#     return JSONResponse(
#         status_code=exc.status_code,
#         content={"error": exc.detail, "status_code": exc.status_code}
#     )
