"""Tests for execution models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from protobox.admin.models.execution import (
    ExecutionCreateRequest,
    ExecutionModel,
    ExecutionStatus,
    ExecutionSummary,
    ExecutionUpdateRequest,
)


class TestExecutionModel:
    """Test cases for ExecutionModel."""

    def test_execution_model_creation(self):
        """Test execution model creation with valid data."""
        execution_data = {
            "action_id": "507f1f77bcf86cd799439011",
            "workspace_id": "workspace_123",
            "user_id": "user_456",
            "input_data": {"url": "https://api.example.com", "method": "GET"},
        }

        execution = ExecutionModel(**execution_data)

        assert execution.action_id == "507f1f77bcf86cd799439011"
        assert execution.workspace_id == "workspace_123"
        assert execution.user_id == "user_456"
        assert execution.input_data == {"url": "https://api.example.com", "method": "GET"}
        assert execution.status == ExecutionStatus.PENDING  # default
        assert execution.retry_count == 0  # default
        assert execution.max_retries == 3  # default
        assert isinstance(execution.started_at, datetime)
        assert execution.completed_at is None
        assert execution.output_data is None
        assert execution.error_message is None

    def test_execution_model_validation_required_fields(self):
        """Test execution model validation for required fields."""
        # Missing action_id
        with pytest.raises(ValidationError) as exc_info:
            ExecutionModel(workspace_id="workspace_123", user_id="user_456")
        assert "action_id" in str(exc_info.value)

        # Missing workspace_id
        with pytest.raises(ValidationError) as exc_info:
            ExecutionModel(action_id="507f1f77bcf86cd799439011", user_id="user_456")
        assert "workspace_id" in str(exc_info.value)

    def test_execution_status_tracking(self):
        """Test execution status tracking methods."""
        execution = ExecutionModel(
            action_id="507f1f77bcf86cd799439011", workspace_id="workspace_123", user_id="user_456"
        )

        # Test mark_started
        execution.mark_started()
        assert execution.status == ExecutionStatus.RUNNING

        # Test mark_completed
        output_data = {"status_code": 200, "data": "success"}
        execution.mark_completed(output_data, 1500)
        assert execution.status == ExecutionStatus.COMPLETED
        assert execution.output_data == output_data
        assert execution.execution_time_ms == 1500
        assert execution.completed_at is not None

        # Test with new execution for mark_failed
        execution2 = ExecutionModel(
            action_id="507f1f77bcf86cd799439011", workspace_id="workspace_123", user_id="user_456"
        )
        execution2.mark_failed("Connection timeout", 5000)
        assert execution2.status == ExecutionStatus.FAILED
        assert execution2.error_message == "Connection timeout"
        assert execution2.execution_time_ms == 5000
        assert execution2.completed_at is not None

    def test_execution_retry_logic(self):
        """Test execution retry functionality."""
        execution = ExecutionModel(
            action_id="507f1f77bcf86cd799439011",
            workspace_id="workspace_123",
            user_id="user_456",
            max_retries=2,
        )

        # Initially can't retry (not failed)
        assert not execution.can_retry()

        # Mark as failed
        execution.mark_failed("Network error")
        assert execution.can_retry()

        # Increment retry
        execution.increment_retry()
        assert execution.retry_count == 1
        assert execution.status == ExecutionStatus.PENDING
        assert execution.error_message is None
        assert execution.completed_at is None

        # Fail again and retry
        execution.mark_failed("Another error")
        execution.increment_retry()
        assert execution.retry_count == 2

        # Should not be able to retry anymore (reached max_retries)
        execution.mark_failed("Final error")
        assert not execution.can_retry()

    def test_execution_model_dump_for_db(self):
        """Test execution model database serialization."""
        execution = ExecutionModel(
            action_id="507f1f77bcf86cd799439011", workspace_id="workspace_123", user_id="user_456"
        )

        db_data = execution.model_dump_for_db()

        # Should not include _id if it was None
        assert "_id" not in db_data
        assert db_data["action_id"] == "507f1f77bcf86cd799439011"
        assert db_data["workspace_id"] == "workspace_123"
        assert db_data["user_id"] == "user_456"

        # Test with explicit ID
        execution.id = "some_id"
        db_data = execution.model_dump_for_db()
        assert db_data["_id"] == "some_id"


class TestExecutionStatus:
    """Test cases for execution status enumeration."""

    def test_execution_status_enum(self):
        """Test execution status enumeration values."""
        assert ExecutionStatus.PENDING == "pending"
        assert ExecutionStatus.RUNNING == "running"
        assert ExecutionStatus.COMPLETED == "completed"
        assert ExecutionStatus.FAILED == "failed"
        assert ExecutionStatus.CANCELLED == "cancelled"

        # Test all enum values are present
        expected_statuses = {"pending", "running", "completed", "failed", "cancelled"}
        actual_statuses = {status.value for status in ExecutionStatus}
        assert actual_statuses == expected_statuses


class TestExecutionRequests:
    """Test cases for execution request models."""

    def test_execution_create_request(self):
        """Test execution create request model."""
        request_data = {
            "action_id": "507f1f77bcf86cd799439011",
            "workspace_id": "workspace_123",
            "input_data": {"url": "https://example.com"},
        }

        request = ExecutionCreateRequest(**request_data)

        assert request.action_id == "507f1f77bcf86cd799439011"
        assert request.workspace_id == "workspace_123"
        assert request.input_data == {"url": "https://example.com"}
        assert request.max_retries == 3  # default
        assert request.execution_context == {}  # default

    def test_execution_update_request(self):
        """Test execution update request model."""
        request_data = {"status": ExecutionStatus.COMPLETED, "output_data": {"result": "success"}}

        request = ExecutionUpdateRequest(**request_data)

        assert request.status == ExecutionStatus.COMPLETED
        assert request.output_data == {"result": "success"}
        assert request.error_message is None  # optional field
        assert request.execution_context is None  # optional field


class TestExecutionSummary:
    """Test cases for execution summary model."""

    def test_execution_summary(self):
        """Test execution summary model."""
        summary_data = {
            "total_executions": 100,
            "by_status": {"completed": 80, "failed": 15, "running": 3, "pending": 2},
            "avg_execution_time_ms": 1250.5,
            "success_rate": 80.0,
        }

        summary = ExecutionSummary(**summary_data)

        assert summary.total_executions == 100
        assert summary.by_status["completed"] == 80
        assert summary.avg_execution_time_ms == 1250.5
        assert summary.success_rate == 80.0
