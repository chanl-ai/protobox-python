"""
Workspace authentication and isolation middleware.

This module provides middleware for authenticating requests and ensuring
proper workspace isolation.
"""

import os
import re

import jwt
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger

from ...config.workspace_settings import WorkspaceIsolationMode, get_workspace_config


class WorkspaceAuthMiddleware:
    """Middleware for workspace authentication and isolation."""

    def __init__(self):
        self.config = get_workspace_config()
        self.security = HTTPBearer(auto_error=False)

    async def get_current_user_and_workspace(
        self, request: Request, credentials: HTTPAuthorizationCredentials | None = None
    ) -> tuple[str, str]:
        """
        Extract user ID and workspace ID from the request.

        Returns:
            Tuple of (user_id, workspace_id)

        Raises:
            HTTPException: If authentication fails or workspace cannot be determined
        """
        config = self.config

        # Since AuthMode is deprecated, always use Firebase authentication
        # In development, check if we're in test mode
        if os.getenv("ENVIRONMENT", "development") == "development" and os.getenv("AUTH_TEST_MODE") == "true":
            # Development/test mode - use defaults from environment
            test_user_id = os.getenv("TESTING_USER_ID", "dev_user")
            test_workspace_id = os.getenv(
                "TEST_WORKSPACE_ID", config.workspace.default_workspace or "default_workspace"
            )
            return test_user_id, test_workspace_id

        # Production mode - this should delegate to the main auth system
        # This middleware is for legacy workspace-specific auth patterns
        # In the new system, authentication is handled by the main auth dependencies
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Workspace auth middleware is deprecated. Use main authentication system.",
        )

        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"Authentication mode {config.authentication.mode} not implemented",
        )

    async def _handle_api_key_auth(
        self, request: Request, credentials: HTTPAuthorizationCredentials | None
    ) -> tuple[str, str]:
        """Handle API key authentication."""
        if not credentials or not credentials.credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        api_key = credentials.credentials

        # Extract workspace from API key if embedded
        # Format: pb_key_{workspace_id}_{random_token}
        workspace_match = re.match(r"pb_key_([^_]+)_(.+)", api_key)
        if workspace_match and self.config.authentication.require_workspace_in_token:
            workspace_id = workspace_match.group(1)
            user_id = f"api_key_user_{workspace_id}"
        else:
            # Try to get workspace from header
            workspace_id = request.headers.get(self.config.workspace.workspace_header)
            if (
                not workspace_id
                and self.config.workspace.isolation_mode == WorkspaceIsolationMode.STRICT
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Workspace ID required in header or API key",
                )
            workspace_id = (
                workspace_id or self.config.workspace.default_workspace or "default_workspace"
            )
            user_id = "api_key_user"

        # TODO: Validate API key against database
        # For now, we'll accept any properly formatted key

        return user_id, workspace_id

    async def _handle_supabase_auth(
        self, request: Request, credentials: HTTPAuthorizationCredentials | None
    ) -> tuple[str, str]:
        """Handle Supabase JWT authentication."""
        if not credentials or not credentials.credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="JWT token required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = credentials.credentials

        try:
            # Decode JWT token
            # TODO: Use proper JWT secret from Supabase
            if self.config.authentication.supabase_jwt_secret:
                payload = jwt.decode(
                    token,
                    self.config.authentication.supabase_jwt_secret,
                    algorithms=["HS256"],
                    options={"verify_aud": False},
                )
            else:
                # For development, decode without verification
                payload = jwt.decode(token, options={"verify_signature": False})

            user_id = payload.get("sub", "unknown_user")

            # Extract workspace from token or header
            workspace_id = payload.get("workspace_id") or request.headers.get(
                self.config.workspace.workspace_header
            )

            if (
                not workspace_id
                and self.config.workspace.isolation_mode == WorkspaceIsolationMode.STRICT
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Workspace ID required in token or header",
                )

            workspace_id = (
                workspace_id or self.config.workspace.default_workspace or "default_workspace"
            )

            return user_id, workspace_id

        except jwt.InvalidTokenError as e:
            logger.error(f"JWT validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid JWT token"
            )

    def require_workspace_access(self, user_workspace: str, resource_workspace: str) -> None:
        """
        Verify that a user has access to a specific workspace resource.

        Args:
            user_workspace: The user's workspace ID
            resource_workspace: The workspace ID of the resource

        Raises:
            HTTPException: If access is denied
        """
        if self.config.workspace.isolation_mode == WorkspaceIsolationMode.DISABLED:
            return

        if user_workspace != resource_workspace:
            # Check if admin access is allowed
            if not self.config.workspace.allow_cross_workspace_admin:
                logger.warning(
                    f"Access denied: User from workspace {user_workspace} "
                    f"attempted to access resource in workspace {resource_workspace}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Cannot access resources from other workspaces",
                )


# Global middleware instance
_middleware: WorkspaceAuthMiddleware | None = None


def get_workspace_auth() -> WorkspaceAuthMiddleware:
    """Get the workspace auth middleware singleton."""
    global _middleware
    if _middleware is None:
        _middleware = WorkspaceAuthMiddleware()
    return _middleware
