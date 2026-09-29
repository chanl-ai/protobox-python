"""
Audit Log model for tracking all admin API operations.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditAction(str, Enum):
    """Audit action types."""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    READ = "READ"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    INVITE = "INVITE"
    REVOKE = "REVOKE"
    EXECUTE = "EXECUTE"  # For action executions


class AuditLog(BaseModel):
    """Audit log entry model."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={datetime: lambda v: v.isoformat()},
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "timestamp": "2024-01-15T10:30:00Z",
                "user_id": "user123",
                "user_email": "user@example.com",
                "workspace_id": "workspace123",
                "action": "UPDATE",
                "resource_type": "action",
                "resource_id": "action456",
                "changes": {"before": {"name": "Old Action"}, "after": {"name": "New Action"}},
                "metadata": {"ip_address": "192.168.1.1", "user_agent": "Mozilla/5.0..."},
            }
        },
    )

    id: str | None = Field(None, alias="_id")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # User information
    user_id: str
    user_email: str | None = None  # Optional - can be populated later from user table

    # Workspace context
    workspace_id: str

    # Action details
    action: AuditAction
    resource_type: str  # e.g., "action", "workspace", "user", "secret"
    resource_id: str

    # Change tracking for updates
    changes: dict[str, Any] | None = None  # {"before": {...}, "after": {...}}

    # Additional metadata
    metadata: dict[str, Any] = Field(default_factory=dict)
    # Can include: ip_address, user_agent, request_id, etc.
