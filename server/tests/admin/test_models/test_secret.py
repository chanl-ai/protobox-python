"""Unit tests for secret models."""

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from protobox.admin.models.secret import (
    SecretCreateRequest,
    SecretModel,
    SecretUpdateRequest,
)
from protobox.admin.secrets.types import SecretType


class TestSecretModel:
    """Test SecretModel functionality."""

    def test_secret_creation_minimal(self):
        """Test creating a secret with minimal required fields."""
        secret = SecretModel(
            workspace_id="ws_123",
            user_id="user_456",
            name="my_secret",
            secret_type=SecretType.API_KEY,
            encrypted_value="encrypted_data",
            salt="salt_value",
            iv="iv_value",
            tag="tag_value",
        )

        assert secret.workspace_id == "ws_123"
        assert secret.user_id == "user_456"
        assert secret.name == "my_secret"
        assert secret.secret_type == SecretType.API_KEY
        assert secret.encrypted_value == "encrypted_data"
        assert secret.is_active is True
        assert secret.usage_count == 0
        assert secret.tags == []
        assert isinstance(secret.created_at, datetime)
        assert isinstance(secret.updated_at, datetime)

    def test_secret_creation_with_all_fields(self):
        """Test creating a secret with all fields."""
        expires_at = datetime.utcnow() + timedelta(days=30)
        secret = SecretModel(
            _id="secret_789",
            workspace_id="ws_123",
            user_id="user_456",
            name="production_api_key",
            description="API key for production environment",
            secret_type=SecretType.DATABASE_URL,
            encrypted_value="encrypted_data",
            salt="salt_value",
            iv="iv_value",
            tag="tag_value",
            tags=["production", "api", "critical"],
            is_active=True,
            expires_at=expires_at,
            max_usage_count=1000,
        )

        assert secret.id == "secret_789"
        assert secret.description == "API key for production environment"
        assert secret.tags == ["production", "api", "critical"]
        assert secret.expires_at == expires_at
        assert secret.max_usage_count == 1000

    def test_secret_name_validation(self):
        """Test secret name validation."""
        # Valid names
        for name in ["api_key", "api-key", "API Key 123", "test_123"]:
            secret = SecretModel(
                workspace_id="ws_123",
                user_id="user_456",
                name=name,
                secret_type=SecretType.API_KEY,
                encrypted_value="encrypted",
                salt="salt",
                iv="iv",
                tag="tag",
            )
            assert secret.name == name

        # Invalid names
        with pytest.raises(ValidationError):
            SecretModel(
                workspace_id="ws_123",
                user_id="user_456",
                name="api@key#invalid",  # Contains invalid characters
                secret_type=SecretType.API_KEY,
                encrypted_value="encrypted",
                salt="salt",
                iv="iv",
                tag="tag",
            )

    def test_secret_tags_validation(self):
        """Test tags validation."""
        # Valid tags
        secret = SecretModel(
            workspace_id="ws_123",
            user_id="user_456",
            name="my_secret",
            secret_type=SecretType.API_KEY,
            encrypted_value="encrypted",
            salt="salt",
            iv="iv",
            tag="tag",
            tags=["tag1", "tag2", "tag3"],
        )
        assert len(secret.tags) == 3

        # Too many tags
        with pytest.raises(ValidationError):
            SecretModel(
                workspace_id="ws_123",
                user_id="user_456",
                name="my_secret",
                secret_type=SecretType.API_KEY,
                encrypted_value="encrypted",
                salt="salt",
                iv="iv",
                tag="tag",
                tags=["tag" + str(i) for i in range(11)],  # 11 tags, max is 10
            )

        # Tag too long
        with pytest.raises(ValidationError):
            SecretModel(
                workspace_id="ws_123",
                user_id="user_456",
                name="my_secret",
                secret_type=SecretType.API_KEY,
                encrypted_value="encrypted",
                salt="salt",
                iv="iv",
                tag="tag",
                tags=["a" * 51],  # 51 characters, max is 50
            )

    def test_is_expired(self):
        """Test expiration checking."""
        # Not expired (no expiration date)
        secret = SecretModel(
            workspace_id="ws_123",
            user_id="user_456",
            name="my_secret",
            secret_type=SecretType.API_KEY,
            encrypted_value="encrypted",
            salt="salt",
            iv="iv",
            tag="tag",
        )
        assert secret.is_expired() is False

        # Not expired (future date)
        secret.expires_at = datetime.utcnow() + timedelta(days=1)
        assert secret.is_expired() is False

        # Expired (past date)
        secret.expires_at = datetime.utcnow() - timedelta(days=1)
        assert secret.is_expired() is True

    def test_is_usage_exceeded(self):
        """Test usage count checking."""
        secret = SecretModel(
            workspace_id="ws_123",
            user_id="user_456",
            name="my_secret",
            secret_type=SecretType.API_KEY,
            encrypted_value="encrypted",
            salt="salt",
            iv="iv",
            tag="tag",
        )

        # No max usage
        assert secret.is_usage_exceeded() is False

        # Under limit
        secret.max_usage_count = 10
        secret.usage_count = 5
        assert secret.is_usage_exceeded() is False

        # At limit
        secret.usage_count = 10
        assert secret.is_usage_exceeded() is True

        # Over limit
        secret.usage_count = 15
        assert secret.is_usage_exceeded() is True

    def test_can_be_used(self):
        """Test comprehensive usage check."""
        secret = SecretModel(
            workspace_id="ws_123",
            user_id="user_456",
            name="my_secret",
            secret_type=SecretType.API_KEY,
            encrypted_value="encrypted",
            salt="salt",
            iv="iv",
            tag="tag",
        )

        # Can be used (active, not expired, not exceeded)
        assert secret.can_be_used() is True

        # Inactive
        secret.is_active = False
        assert secret.can_be_used() is False
        secret.is_active = True

        # Expired
        secret.expires_at = datetime.utcnow() - timedelta(days=1)
        assert secret.can_be_used() is False
        secret.expires_at = None

        # Usage exceeded
        secret.max_usage_count = 5
        secret.usage_count = 10
        assert secret.can_be_used() is False

    def test_model_dump_for_db(self):
        """Test converting model to database format."""
        secret = SecretModel(
            workspace_id="ws_123",
            user_id="user_456",
            name="my_secret",
            secret_type=SecretType.API_KEY,
            encrypted_value="encrypted",
            salt="salt",
            iv="iv",
            tag="tag",
        )

        db_data = secret.model_dump_for_db()

        # Should not have _id since it wasn't set
        assert "_id" not in db_data
        assert db_data["workspace_id"] == "ws_123"
        assert db_data["user_id"] == "user_456"
        assert db_data["name"] == "my_secret"

        # With ID
        secret.id = "secret_123"
        db_data = secret.model_dump_for_db()
        assert db_data["_id"] == "secret_123"


class TestSecretTypes:
    """Test secret type enumeration."""

    def test_secret_types(self):
        """Test all secret types are available."""
        assert SecretType.API_KEY == "API_KEY"
        assert SecretType.DATABASE_URL == "DATABASE_URL"
        assert SecretType.OAUTH_TOKEN == "OAUTH_TOKEN"
        assert SecretType.BASIC_AUTH == "BASIC_AUTH"
        assert SecretType.CUSTOM == "CUSTOM"


class TestSecretCreateRequest:
    """Test SecretCreateRequest model."""

    def test_create_request_minimal(self):
        """Test creating a secret request with minimal fields."""
        request = SecretCreateRequest(
            workspace_id="ws_123",
            name="my_secret",
            secret_value="secret123",
            secret_type=SecretType.API_KEY,
        )

        assert request.name == "my_secret"
        assert request.secret_value == "secret123"
        assert request.secret_type == SecretType.API_KEY
        assert request.description is None
        assert request.tags == []

    def test_create_request_validation(self):
        """Test create request validation."""
        # Name too short
        with pytest.raises(ValidationError):
            SecretCreateRequest(
                workspace_id="ws_123",
                name="",
                secret_value="secret123",
                secret_type=SecretType.API_KEY,
            )

        # Secret value required
        with pytest.raises(ValidationError):
            SecretCreateRequest(
                workspace_id="ws_123",
                name="my_secret",
                secret_value="",
                secret_type=SecretType.API_KEY,
            )


class TestSecretUpdateRequest:
    """Test SecretUpdateRequest model."""

    def test_update_request_all_optional(self):
        """Test that all fields in update request are optional."""
        request = SecretUpdateRequest()
        assert request.name is None
        assert request.description is None
        assert request.secret_value is None
        assert request.tags is None
        assert request.is_active is None

    def test_update_request_partial(self):
        """Test updating only some fields."""
        request = SecretUpdateRequest(name="new_name", is_active=False)
        assert request.name == "new_name"
        assert request.is_active is False
        assert request.description is None
        assert request.secret_value is None
