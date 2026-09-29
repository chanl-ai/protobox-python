"""Authorization decorators for MCP endpoints."""

import logging
from collections.abc import Callable
from datetime import UTC
from functools import wraps

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials

from .mcp_bearer import bearer_scheme

logger = logging.getLogger(__name__)


class AuthContext:
    """Authentication context for requests."""

    def __init__(self, auth_info: dict):
        """Initialize auth context from auth info."""
        self.type = auth_info.get("type")  # jwt, mcp_token, api_key
        self.user_id = auth_info.get("user_id")
        self.token_id = auth_info.get("token_id")
        self.workspace_id = auth_info.get("workspace_id")
        self.scopes = auth_info.get("scopes", [])
        self.claims = auth_info.get("claims", {})
        self.rate_limit = auth_info.get("rate_limit", 100)
        self.name = auth_info.get("name")  # Token name for efficient identification

    def has_scope(self, scope: str) -> bool:
        """Check if context has a specific scope."""
        return scope in self.scopes

    def has_any_scope(self, scopes: list[str]) -> bool:
        """Check if context has any of the specified scopes."""
        return any(scope in self.scopes for scope in scopes)

    def has_all_scopes(self, scopes: list[str]) -> bool:
        """Check if context has all specified scopes."""
        return all(scope in self.scopes for scope in scopes)


def require_auth(func: Callable) -> Callable:
    """
    Require any valid authentication.

    Usage:
        @router.get("/protected")
        @require_auth
        async def protected_endpoint(request: Request):
            auth = request.state.auth
            return {"user": auth.user_id}
    """

    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        # Check if auth is already set (by dependency)
        if hasattr(request.state, "auth"):
            return await func(request, *args, **kwargs)

        # Try to get bearer token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Authentication required")

        # For now, just check token exists
        # In production, validate with bearer provider
        token = auth_header[7:]
        if not token:
            raise HTTPException(status_code=401, detail="Invalid authentication token")

        # Set basic auth context
        request.state.auth = AuthContext(
            {"type": "bearer", "user_id": "unknown", "scopes": []}  # Would be extracted from token
        )

        # Call downstream using keyword to avoid positional arg collisions
        return await func(*args, **{**kwargs, "request": request})

    return wrapper


def require_scope(*required_scopes: str) -> Callable:
    """
    Require specific OAuth scopes.

    Usage:
        @router.get("/admin")
        @require_scope("admin", "write:actions")
        async def admin_endpoint(request: Request):
            return {"status": "admin access granted"}
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Ensure authenticated first
            if not hasattr(request.state, "auth"):
                raise HTTPException(status_code=401, detail="Authentication required")

            auth: AuthContext = request.state.auth

            # Check all required scopes
            missing_scopes = [scope for scope in required_scopes if not auth.has_scope(scope)]

            if missing_scopes:
                raise HTTPException(
                    status_code=403, detail=f"Missing required scopes: {', '.join(missing_scopes)}"
                )

            # Call downstream using keyword to avoid positional arg collisions
            return await func(*args, **{**kwargs, "request": request})

        return wrapper

    return decorator


def require_any_scope(*scopes: str) -> Callable:
    """
    Require at least one of the specified scopes.

    Usage:
        @router.get("/data")
        @require_any_scope("read:actions", "admin")
        async def data_endpoint(request: Request):
            return {"data": "..."}
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Ensure authenticated first
            if not hasattr(request.state, "auth"):
                raise HTTPException(status_code=401, detail="Authentication required")

            auth: AuthContext = request.state.auth

            # Check if has any of the required scopes
            if not auth.has_any_scope(list(scopes)):
                raise HTTPException(status_code=403, detail=f"Requires one of: {', '.join(scopes)}")

            # Call downstream using keyword to avoid positional arg collisions
            return await func(*args, **{**kwargs, "request": request})

        return wrapper

    return decorator


def require_workspace_access(func: Callable) -> Callable:
    """
    Require access to the workspace in the path.

    Usage:
        @router.get("/workspaces/{workspace_id}/actions")
        @require_workspace_access
        async def workspace_actions(request: Request, workspace_id: str):
            return {"workspace": workspace_id}
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Find request and workspace_id in args/kwargs
        request = None
        workspace_id = None

        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break

        if not request:
            request = kwargs.get("request")

        workspace_id = kwargs.get("workspace_id")

        if not request or not workspace_id:
            raise HTTPException(status_code=500, detail="Invalid endpoint configuration")

        # Ensure authenticated
        if not hasattr(request.state, "auth"):
            raise HTTPException(status_code=401, detail="Authentication required")

        auth: AuthContext = request.state.auth

        # Check workspace access
        # For MCP tokens, workspace is already validated
        if auth.type == "mcp_token":
            if auth.workspace_id != workspace_id:
                raise HTTPException(status_code=403, detail="Token not valid for this workspace")
        else:
            # For JWT tokens, check workspace membership
            # This would query the database in production
            from ..database.connection import get_database_connection

            async def check_access():
                from bson import ObjectId
                db = get_database_connection()
                workspace = await db.database["workspaces"].find_one({
                    "_id": ObjectId(workspace_id),
                    "$or": [
                        {"owner_id": auth.user_id}, 
                        {"members.user_id": auth.user_id}
                    ],
                })
                return workspace is not None

            # SECURITY: Enforce workspace access control
            if not await check_access():
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: You don't have permission to access this workspace"
                )

        return await func(*args, **kwargs)

    return wrapper


def require_rate_limit(max_requests: int = 100, window_seconds: int = 60) -> Callable:
    """
    Apply rate limiting to an endpoint.

    Usage:
        @router.post("/execute")
        @require_rate_limit(max_requests=10, window_seconds=60)
        async def execute_action(request: Request):
            return {"status": "executed"}
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get client identifier
            client_id = None
            if hasattr(request.state, "auth"):
                auth: AuthContext = request.state.auth
                client_id = auth.token_id or auth.user_id

            if not client_id:
                # Use IP address as fallback
                client_id = request.client.host if request.client else "unknown"

            # In production, this would use Redis or similar
            # For now, we'll just log and pass through
            logger.info(f"Rate limit check: {client_id} - " f"{max_requests}/{window_seconds}s")

            # TODO: Implement actual rate limiting with Redis
            # Example:
            # key = f"rate_limit:{client_id}:{request.url.path}"
            # count = await redis.incr(key)
            # if count == 1:
            #     await redis.expire(key, window_seconds)
            # if count > max_requests:
            #     raise HTTPException(
            #         status_code=429,
            #         detail=f"Rate limit exceeded: {max_requests} per {window_seconds}s"
            #     )

            # Call downstream using keyword to avoid positional arg collisions
            return await func(*args, **{**kwargs, "request": request})

        return wrapper

    return decorator


def audit_log(action: str, resource_type: str | None = None) -> Callable:
    """
    Log audit events for sensitive operations.

    Usage:
        @router.post("/actions/{action_id}/execute")
        @audit_log("execute", "action")
        async def execute_action(request: Request, action_id: str):
            return {"executed": action_id}
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find request in args
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                request = kwargs.get("request")

            # Get auth context
            auth = None
            if request and hasattr(request.state, "auth"):
                auth = request.state.auth

            # Get resource ID from kwargs
            resource_id = None
            for key in ["action_id", "tool_id", "workspace_id", "id"]:
                if key in kwargs:
                    resource_id = kwargs[key]
                    break

            # Log audit event
            audit_entry = {
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "user_id": auth.user_id if auth else None,
                "auth_type": auth.type if auth else None,
                "ip_address": request.client.host if request and request.client else None,
                "user_agent": request.headers.get("user-agent") if request else None,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            logger.info(f"Audit: {json.dumps(audit_entry)}")

            # In production, store in database
            # from ..database.connection import get_database_connection
            # db = get_database_connection()
            # await db.database["audit_logs"].insert_one(audit_entry)

            # Execute the function
            try:
                result = await func(*args, **kwargs)

                # Log success
                logger.info(f"Audit: {action} succeeded for {resource_id}")

                return result

            except Exception as e:
                # Log failure
                logger.error(f"Audit: {action} failed for {resource_id}: {e}")
                raise

        return wrapper

    return decorator


# Dependency injection helpers
async def get_auth_context(
    request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)
) -> AuthContext | None:
    """
    FastAPI dependency to get auth context.

    Usage:
        @router.get("/me")
        async def get_current_user(
            auth: AuthContext = Depends(get_auth_context)
        ):
            if not auth:
                raise HTTPException(401, "Not authenticated")
            return {"user_id": auth.user_id}
    """
    if not credentials:
        return None

    # In production, validate token with bearer provider
    # For now, create basic context
    return AuthContext(
        {"type": "bearer", "user_id": "test-user", "scopes": ["read:actions", "execute:actions"]}
    )


async def require_auth_dependency(
    auth: AuthContext | None = Depends(get_auth_context),
) -> AuthContext:
    """
    FastAPI dependency that requires authentication.

    Usage:
        @router.get("/protected")
        async def protected_endpoint(
            auth: AuthContext = Depends(require_auth_dependency)
        ):
            return {"user": auth.user_id}
    """
    if not auth:
        raise HTTPException(status_code=401, detail="Authentication required")
    return auth


def require_scopes_dependency(*scopes: str):
    """
    Create a FastAPI dependency that requires specific scopes.

    Usage:
        AdminAuth = require_scopes_dependency("admin", "write:all")

        @router.delete("/dangerous")
        async def dangerous_operation(
            auth: AuthContext = Depends(AdminAuth)
        ):
            return {"deleted": "everything"}
    """

    async def dependency(auth: AuthContext = Depends(require_auth_dependency)) -> AuthContext:
        missing = [s for s in scopes if not auth.has_scope(s)]
        if missing:
            raise HTTPException(
                status_code=403, detail=f"Missing required scopes: {', '.join(missing)}"
            )
        return auth

    return dependency


# Common auth dependencies
ReadActionsAuth = require_scopes_dependency("read:actions")
ExecuteActionsAuth = require_scopes_dependency("execute:actions")
WriteActionsAuth = require_scopes_dependency("write:actions")
AdminAuth = require_scopes_dependency("admin")


import json
from datetime import datetime
