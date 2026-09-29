"""Execution models for admin API."""

from datetime import datetime
from enum import Enum
from typing import Any

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field


class ExecutionStatus(str, Enum):
    """Execution status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionModel(BaseModel):
    """Execution data model for MongoDB storage."""

    id: str | None = Field(None, alias="_id", description="Execution ID")
    action_id: str = Field(..., description="ID of the action being executed")
    workspace_id: str = Field(..., description="Workspace ID for multi-tenancy")
    user_id: str = Field(..., description="User who triggered the execution")

    # Execution data
    input_data: dict[str, Any] = Field(
        default_factory=dict, description="Input parameters for execution"
    )
    output_data: dict[str, Any] | None = Field(None, description="Execution output/results")

    # Status tracking
    status: ExecutionStatus = Field(
        default=ExecutionStatus.PENDING, description="Current execution status"
    )
    execution_time_ms: int | None = Field(None, description="Execution time in milliseconds")
    error_message: str | None = Field(None, description="Error message if execution failed")

    # Timestamps
    started_at: datetime = Field(
        default_factory=datetime.utcnow, description="Execution start time"
    )
    completed_at: datetime | None = Field(None, description="Execution completion time")

    # Metadata
    execution_context: dict[str, Any] = Field(
        default_factory=dict, description="Additional execution context"
    )
    retry_count: int = Field(default=0, description="Number of retry attempts")
    max_retries: int = Field(default=3, description="Maximum number of retries allowed")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "action_id": "507f1f77bcf86cd799439011",
                "workspace_id": "workspace_123",
                "user_id": "user_456",
                "input_data": {
                    "url": "https://api.example.com/data",
                    "method": "GET",
                    "headers": {"Authorization": "Bearer token"},
                },
                "status": "completed",
                "execution_time_ms": 1250,
                "output_data": {"status_code": 200, "response_body": {"data": "success"}},
            }
        },
    )

    def model_dump_for_db(self) -> dict[str, Any]:
        """Convert model to dictionary for MongoDB storage."""
        data = self.model_dump(by_alias=True, exclude_none=True)
        # Remove _id if it's None to let MongoDB generate it
        if data.get("_id") is None:
            data.pop("_id", None)
        return data

    def mark_started(self) -> None:
        """Mark execution as started."""
        self.status = ExecutionStatus.RUNNING
        self.started_at = datetime.utcnow()

    def mark_completed(self, output_data: dict[str, Any], execution_time_ms: int) -> None:
        """Mark execution as completed with results."""
        self.status = ExecutionStatus.COMPLETED
        self.output_data = output_data
        self.execution_time_ms = execution_time_ms
        self.completed_at = datetime.utcnow()

    def mark_failed(self, error_message: str, execution_time_ms: int | None = None) -> None:
        """Mark execution as failed with error message."""
        self.status = ExecutionStatus.FAILED
        self.error_message = error_message
        if execution_time_ms is not None:
            self.execution_time_ms = execution_time_ms
        self.completed_at = datetime.utcnow()

    def can_retry(self) -> bool:
        """Check if execution can be retried."""
        return self.status == ExecutionStatus.FAILED and self.retry_count < self.max_retries

    def increment_retry(self) -> None:
        """Increment retry count and reset for retry."""
        self.retry_count += 1
        self.status = ExecutionStatus.PENDING
        self.error_message = None
        self.completed_at = None


class ExecutionCreateRequest(BaseModel):
    """Request model for creating an execution."""

    action_id: str = Field(..., description="ID of the action to execute")
    workspace_id: str = Field(..., description="Workspace ID")
    input_data: dict[str, Any] = Field(default_factory=dict, description="Input parameters")
    execution_context: dict[str, Any] = Field(
        default_factory=dict, description="Additional context"
    )
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")


class ExecutionUpdateRequest(BaseModel):
    """Request model for updating an execution."""

    status: ExecutionStatus | None = Field(None, description="Updated status")
    output_data: dict[str, Any] | None = Field(None, description="Execution output")
    error_message: str | None = Field(None, description="Error message")
    execution_context: dict[str, Any] | None = Field(None, description="Updated context")


class ExecutionSummary(BaseModel):
    """Summary model for execution statistics."""

    total_executions: int = Field(..., description="Total number of executions")
    by_status: dict[str, int] = Field(..., description="Count by execution status")
    avg_execution_time_ms: float | None = Field(None, description="Average execution time")
    success_rate: float = Field(..., description="Success rate as percentage")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_executions": 150,
                "by_status": {"completed": 120, "failed": 25, "running": 3, "pending": 2},
                "avg_execution_time_ms": 1850.5,
                "success_rate": 80.0,
            }
        }
    )
