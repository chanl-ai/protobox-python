"""Unit tests for audit log models - simplified version."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from protobox.admin.models.audit_log import AuditAction, AuditLog


class TestAuditAction:
    """Test AuditAction enumeration."""

    def test_audit_actions(self):
        """Test that audit actions are defined."""
        # Check some common actions exist
        assert hasattr(AuditAction, "CREATE")
        assert hasattr(AuditAction, "UPDATE")
        assert hasattr(AuditAction, "DELETE")
        assert hasattr(AuditAction, "READ")


class TestAuditLog:
    """Test AuditLog model."""

    def test_audit_log_creation(self):
        """Test creating an audit log entry."""
        log = AuditLog(
            workspace_id="ws_123",
            user_id="user_456",
            action=AuditAction.CREATE,
            resource_type="secret",
            resource_id="secret_789",
            timestamp=datetime.utcnow(),
        )

        assert log.workspace_id == "ws_123"
        assert log.user_id == "user_456"
        assert log.action == AuditAction.CREATE
        assert log.resource_type == "secret"
        assert log.resource_id == "secret_789"
        assert isinstance(log.timestamp, datetime)

    def test_audit_log_with_metadata(self):
        """Test audit log with additional metadata."""
        log = AuditLog(
            workspace_id="ws_123",
            user_id="user_456",
            action=AuditAction.UPDATE,
            resource_type="action",
            resource_id="action_789",
            timestamp=datetime.utcnow(),
            metadata={"ip_address": "192.168.1.1", "user_agent": "Mozilla/5.0"},
        )

        assert log.metadata["ip_address"] == "192.168.1.1"
        assert log.metadata["user_agent"] == "Mozilla/5.0"

    def test_audit_log_validation(self):
        """Test that required fields are validated."""
        # Should fail without required fields
        with pytest.raises(ValidationError):
            AuditLog()

        with pytest.raises(ValidationError):
            AuditLog(
                workspace_id="ws_123",
                user_id="user_456",
                # Missing action and other required fields
            )
