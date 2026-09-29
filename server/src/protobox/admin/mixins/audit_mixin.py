"""
Audit logging mixin to reduce boilerplate in routers.
"""

import logging
from typing import Any

from ..models.audit_log import AuditAction, AuditLog
from ..services.audit_service import AuditService

logger = logging.getLogger(__name__)


class AuditLoggerMixin:
    """Mixin to simplify audit logging in routers."""

    @staticmethod
    async def audit_create(
        audit_service: AuditService,
        user_id: str,
        workspace_id: str,
        resource_type: str,
        resource_id: str,
        resource_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog | None:
        """Log a CREATE action with error handling."""
        try:
            base_metadata = {}
            if resource_name:
                base_metadata[f"{resource_type}_name"] = resource_name

            if metadata:
                base_metadata.update(metadata)

            return await audit_service.log_action(
                user_id=user_id,
                workspace_id=workspace_id,
                action=AuditAction.CREATE,
                resource_type=resource_type,
                resource_id=resource_id,
                metadata=base_metadata,
            )
        except Exception as e:
            logger.error(f"Failed to create audit log for CREATE {resource_type}: {e}")
            # Don't fail the main operation if audit logging fails
            return None

    @staticmethod
    async def audit_update(
        audit_service: AuditService,
        user_id: str,
        workspace_id: str,
        resource_type: str,
        resource_id: str,
        changes: dict[str, Any],
        resource_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog | None:
        """Log an UPDATE action with error handling."""
        try:
            base_metadata = {}
            if resource_name:
                base_metadata[f"{resource_type}_name"] = resource_name

            if metadata:
                base_metadata.update(metadata)

            return await audit_service.log_action(
                user_id=user_id,
                workspace_id=workspace_id,
                action=AuditAction.UPDATE,
                resource_type=resource_type,
                resource_id=resource_id,
                changes=changes,
                metadata=base_metadata,
            )
        except Exception as e:
            logger.error(f"Failed to create audit log for UPDATE {resource_type}: {e}")
            return None

    @staticmethod
    async def audit_delete(
        audit_service: AuditService,
        user_id: str,
        workspace_id: str,
        resource_type: str,
        resource_id: str,
        resource_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog | None:
        """Log a DELETE action with error handling."""
        try:
            base_metadata = {}
            if resource_name:
                base_metadata[f"{resource_type}_name"] = resource_name

            if metadata:
                base_metadata.update(metadata)

            return await audit_service.log_action(
                user_id=user_id,
                workspace_id=workspace_id,
                action=AuditAction.DELETE,
                resource_type=resource_type,
                resource_id=resource_id,
                metadata=base_metadata,
            )
        except Exception as e:
            logger.error(f"Failed to create audit log for DELETE {resource_type}: {e}")
            return None

    @staticmethod
    async def audit_read(
        audit_service: AuditService,
        user_id: str,
        workspace_id: str,
        resource_type: str,
        resource_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog | None:
        """Log a READ action with error handling."""
        try:
            return await audit_service.log_action(
                user_id=user_id,
                workspace_id=workspace_id,
                action=AuditAction.READ,
                resource_type=resource_type,
                resource_id=resource_id,
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"Failed to create audit log for READ {resource_type}: {e}")
            return None

    @staticmethod
    async def audit_execute(
        audit_service: AuditService,
        user_id: str,
        workspace_id: str,
        resource_type: str,
        resource_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog | None:
        """Log an EXECUTE action with error handling."""
        try:
            return await audit_service.log_action(
                user_id=user_id,
                workspace_id=workspace_id,
                action=AuditAction.EXECUTE,
                resource_type=resource_type,
                resource_id=resource_id,
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"Failed to create audit log for EXECUTE {resource_type}: {e}")
            return None
