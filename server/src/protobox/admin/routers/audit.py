"""
Audit log API endpoints.
"""

from datetime import datetime, timedelta
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from ..auth.dependencies import get_current_user
from ..auth.models import User
from ..database.connection import get_database_connection
from ..models.audit_log import AuditAction, AuditLog
from ..services.audit_service import AuditService

router = APIRouter(prefix="/workspaces/{workspace_id}/audit-logs", tags=["audit"])


class ResourceType(str, Enum):
    """Valid resource types for audit logs."""

    USER = "user"
    WORKSPACE = "workspace"
    ACTION = "action"
    SECRET = "secret"
    EXECUTION = "execution"
    AUDIT_LOG = "audit_log"


async def get_audit_service(request: Request) -> AuditService:
    """Get audit service instance from app state."""
    from loguru import logger

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


class AuditLogResponse(BaseModel):
    """Response model for audit logs."""

    logs: list[AuditLog]
    total: int
    offset: int
    limit: int


class AuditStatistics(BaseModel):
    """Audit statistics response."""

    by_resource: dict
    total_actions: int
    unique_users: int
    period: dict


@router.get("", response_model=AuditLogResponse)
async def get_audit_logs(
    workspace_id: str,  # Path parameter from router prefix
    user_id: str | None = Query(
        None, min_length=1, max_length=100, description="Filter by user ID"
    ),
    resource_type: ResourceType | None = Query(None, description="Filter by resource type"),
    action: AuditAction | None = Query(None, description="Filter by action"),
    start_date: datetime | None = Query(None, description="Start date filter"),
    end_date: datetime | None = Query(None, description="End date filter"),
    offset: int = Query(0, ge=0, le=10000, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=200, description="Limit for pagination"),
    current_user: User = Depends(get_current_user),
    audit_service: AuditService = Depends(get_audit_service),
):
    """Get audit logs for a workspace."""
    # TODO: Add proper role-based access control
    # For now, users can only see logs for their workspaces

    # Validate date range
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=400, detail="Start date must be before or equal to end date"
        )

    # Limit date range to prevent excessive queries (max 1 year)
    if start_date and end_date:
        date_diff = end_date - start_date
        if date_diff.days > 365:
            raise HTTPException(status_code=400, detail="Date range cannot exceed 365 days")

    logs = await audit_service.get_logs(
        workspace_id=workspace_id,
        user_id=user_id,
        resource_type=resource_type,
        action=action,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )

    # Get total count for pagination
    # In production, this would be a separate count query
    total = len(logs)

    return AuditLogResponse(logs=logs, total=total, offset=offset, limit=limit)


@router.get("/resource/{resource_type}/{resource_id}", response_model=list[AuditLog])
async def get_resource_audit_history(
    workspace_id: str,
    resource_type: str,
    resource_id: str,
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    audit_service: AuditService = Depends(get_audit_service),
):
    """Get audit history for a specific resource."""
    # TODO: Add proper role-based access control

    logs = await audit_service.get_resource_history(
        resource_type=resource_type, resource_id=resource_id, limit=limit
    )

    # Filter by workspace to ensure user can only see their workspace's logs
    return [log for log in logs if log.workspace_id == workspace_id]



@router.get("/user/{user_id}", response_model=list[AuditLog])
async def get_user_activity(
    workspace_id: str,
    user_id: str,
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    audit_service: AuditService = Depends(get_audit_service),
):
    """Get activity logs for a specific user."""
    # TODO: Add proper role-based access control
    # For now, users can only view their own activity
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="You can only view your own activity")

    return await audit_service.get_user_activity(
        user_id=user_id, workspace_id=workspace_id, limit=limit
    )



@router.get("/statistics", response_model=AuditStatistics)
async def get_audit_statistics(
    workspace_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    audit_service: AuditService = Depends(get_audit_service),
):
    """Get audit log statistics for a workspace."""
    # TODO: Add proper role-based access control

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    stats = await audit_service.get_statistics(
        workspace_id=workspace_id, start_date=start_date, end_date=end_date
    )

    stats["period"] = {"start": start_date.isoformat(), "end": end_date.isoformat(), "days": days}

    return AuditStatistics(**stats)


@router.get("/{log_id}", response_model=AuditLog)
async def get_audit_log(
    workspace_id: str,
    log_id: str,
    current_user: User = Depends(get_current_user),
    audit_service: AuditService = Depends(get_audit_service),
):
    """Get a specific audit log entry."""
    # TODO: Add proper role-based access control

    log = await audit_service.get_log_by_id(log_id)

    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")

    # Ensure log belongs to the workspace
    if log.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Audit log not found")

    return log
