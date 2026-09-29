"""
Audit middleware for automatically logging admin API operations.
"""

import json
import logging
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..models.audit_log import AuditAction
from ..services.audit_service import AuditService

# from ..models.database import Database  # Not needed

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically log admin API operations."""

    # Map HTTP methods to audit actions
    METHOD_TO_ACTION = {
        "POST": AuditAction.CREATE,
        "PUT": AuditAction.UPDATE,
        "PATCH": AuditAction.UPDATE,
        "DELETE": AuditAction.DELETE,
        "GET": AuditAction.READ,
    }

    # Paths to exclude from audit logging
    EXCLUDED_PATHS = {
        "/admin/api/v1/health",
        "/admin/api/v1/docs",
        "/admin/api/v1/openapi.json",
        "/admin/api/v1/audit-logs",  # Prevent recursive logging
    }

    def __init__(self, app: ASGIApp, audit_service: AuditService):
        super().__init__(app)
        self.audit_service = audit_service

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and log audit information."""
        # Skip excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # Skip non-admin API paths
        if not request.url.path.startswith("/admin/api/v1/"):
            return await call_next(request)

        # Extract user info from request (assumes auth middleware sets this)
        user = getattr(request.state, "user", None)
        if not user:
            # No user context, skip audit logging
            return await call_next(request)

        # Capture request body for POST/PUT/PATCH
        request_body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                request_body = json.loads(body) if body else None

                # Re-attach body to request
                async def receive():
                    return {"type": "http.request", "body": body}

                request._receive = receive
            except Exception as e:
                logger.warning(f"Failed to capture request body: {e}")

        # Process the request
        response = await call_next(request)

        # Only log successful operations (2xx status codes)
        if 200 <= response.status_code < 300:
            try:
                await self._log_audit(request, response, user, request_body)
            except Exception as e:
                # Don't fail the request if audit logging fails
                logger.error(f"Failed to log audit: {e}")

        return response

    async def _log_audit(
        self,
        request: Request,
        response: Response,
        user: Any,
        request_body: dict[str, Any] | None,
    ):
        """Log the audit entry."""
        # Extract resource info from path
        path_parts = request.url.path.strip("/").split("/")
        resource_info = self._extract_resource_info(path_parts, request.method)

        if not resource_info:
            return

        # Get action from HTTP method
        action = self.METHOD_TO_ACTION.get(request.method)
        if not action:
            return

        # Extract workspace ID from path or user context
        workspace_id = self._extract_workspace_id(path_parts, user)
        if not workspace_id:
            return

        # Build metadata
        metadata = {
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "request_id": request.headers.get("x-request-id"),
            "method": request.method,
            "path": request.url.path,
        }

        # For updates, try to capture changes (would need before state)
        changes = None
        if action == AuditAction.UPDATE and request_body:
            changes = {
                "after": request_body
                # "before" would need to be captured from the service layer
            }

        # Log the audit entry
        await self.audit_service.log_action(
            user_id=user.id,
            user_email=user.email,
            workspace_id=workspace_id,
            action=action,
            resource_type=resource_info["type"],
            resource_id=resource_info["id"],
            changes=changes,
            metadata=metadata,
        )

    def _extract_resource_info(self, path_parts: list, method: str) -> dict[str, str] | None:
        """Extract resource type and ID from path."""
        # Expected patterns:
        # /admin/api/v1/workspaces/{workspace_id}/actions/{action_id}
        # /admin/api/v1/workspaces/{workspace_id}/secrets/{secret_id}
        # /admin/api/v1/users/{user_id}

        if len(path_parts) < 4:
            return None

        # Skip admin/api/v1
        parts = path_parts[3:]

        if not parts:
            return None

        # Handle different resource patterns
        if parts[0] == "workspaces" and len(parts) >= 3:
            workspace_id = parts[1]
            if len(parts) == 2:
                # Operating on workspace itself
                return {"type": "workspace", "id": workspace_id}

            resource_type = parts[2]  # actions, secrets, etc.
            if len(parts) >= 4:
                # Specific resource
                return {"type": resource_type.rstrip("s"), "id": parts[3]}
            if method == "POST":
                # Creating new resource (ID will be in response)
                return {"type": resource_type.rstrip("s"), "id": "new"}

        elif parts[0] in ["users", "invitations", "api-keys"]:
            resource_type = parts[0].rstrip("s")
            if len(parts) >= 2:
                return {"type": resource_type, "id": parts[1]}
            if method == "POST":
                return {"type": resource_type, "id": "new"}

        return None

    def _extract_workspace_id(self, path_parts: list, user: Any) -> str | None:
        """Extract workspace ID from path or user context."""
        # Check if workspace ID is in the path
        if "workspaces" in path_parts:
            idx = path_parts.index("workspaces")
            if idx + 1 < len(path_parts):
                return path_parts[idx + 1]

        # Fall back to user's current workspace
        return getattr(user, "current_workspace_id", None)
