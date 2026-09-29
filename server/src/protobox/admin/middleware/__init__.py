"""Admin middleware components."""

from .workspace_auth import WorkspaceAuthMiddleware, get_workspace_auth

__all__ = ["WorkspaceAuthMiddleware", "get_workspace_auth"]
