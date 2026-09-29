"""Secret service for managing encrypted secrets."""

from typing import Any

from ..database.repositories.secret_repository import SecretRepository
from ..models.secret import (
    SecretCreateRequest,
    SecretListResponse,
    SecretModel,
    SecretUpdateRequest,
    SecretUsageLog,
)
from ..secrets.encryption import SecretEncryption
from ..secrets.types import SecretType
from ..secrets.validator import SecretValidator


class SecretService:
    """Service for managing encrypted secrets."""

    def __init__(self, encryption: SecretEncryption):
        """Initialize the service.

        Args:
            encryption: The encryption service instance
        """
        self.repository = SecretRepository()
        self.encryption = encryption
        self.validator = SecretValidator()

    async def create_secret(self, request: SecretCreateRequest, user_id: str) -> str:
        """Create a new encrypted secret.

        Args:
            request: The secret creation request
            user_id: ID of the user creating the secret

        Returns:
            The ID of the created secret

        Raises:
            ValueError: If secret validation fails
            DuplicateKeyError: If secret name already exists
        """
        # Validate secret value format
        self.validator.validate_secret_value(request.secret_type, request.secret_value)

        # Encrypt the secret value
        encrypted_data = await self.encryption.encrypt_secret(request.secret_value)

        # Create secret model
        secret = SecretModel(
            workspace_id=request.workspace_id,
            user_id=user_id,
            name=request.name,
            description=request.description,
            secret_type=request.secret_type,
            encrypted_value=encrypted_data["encrypted_value"],
            salt=encrypted_data["salt"],
            iv=encrypted_data["iv"],
            tag=encrypted_data["tag"],
            tags=request.tags,
            expires_at=request.expires_at,
            max_usage_count=request.max_usage_count,
        )

        # Save to database
        secret_id = await self.repository.create_secret(secret)

        # Log the creation
        await self._log_secret_access(
            secret_id=secret_id,
            workspace_id=request.workspace_id,
            user_id=user_id,
            access_method="create",
        )

        return secret_id

    async def get_secret_by_id(self, secret_id: str, user_id: str) -> SecretModel | None:
        """Get a secret by ID (without decrypting the value).

        Args:
            secret_id: The secret ID
            user_id: ID of the user requesting the secret

        Returns:
            The secret model or None if not found
        """
        secret = await self.repository.get_secret_by_id(secret_id)
        if secret:
            # Log the access
            await self._log_secret_access(
                secret_id=secret_id,
                workspace_id=secret.workspace_id,
                user_id=user_id,
                access_method="read_metadata",
            )

        return secret

    async def decrypt_secret_value(self, secret_id: str, user_id: str) -> str | None:
        """Decrypt and return a secret value.

        Args:
            secret_id: The secret ID
            user_id: ID of the user requesting the secret

        Returns:
            The decrypted secret value or None if not found/unusable
        """
        secret = await self.repository.get_secret_by_id(secret_id)
        if not secret:
            return None

        # Check if secret can be used
        if not secret.can_be_used():
            return None

        # Decrypt the value
        encrypted_data = {
            "encrypted_value": secret.encrypted_value,
            "salt": secret.salt,
            "iv": secret.iv,
            "tag": secret.tag,
        }
        decrypted_value = await self.encryption.decrypt_secret(encrypted_data)

        # Increment usage count
        await self.repository.increment_secret_usage(secret_id)

        # Log the access
        await self._log_secret_access(
            secret_id=secret_id,
            workspace_id=secret.workspace_id,
            user_id=user_id,
            access_method="decrypt_value",
        )

        return decrypted_value

    async def list_secrets(
        self,
        workspace_id: str,
        secret_type: SecretType | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SecretListResponse]:
        """List secrets for a workspace (without sensitive data).

        Args:
            workspace_id: The workspace ID
            secret_type: Optional secret type filter
            is_active: Optional active status filter
            skip: Number of secrets to skip
            limit: Maximum number of secrets to return

        Returns:
            List of secret list responses
        """
        secrets = await self.repository.get_secrets_by_workspace(
            workspace_id=workspace_id,
            secret_type=secret_type,
            is_active=is_active,
            skip=skip,
            limit=limit,
        )

        # Convert to list response format
        secret_list = []
        for secret in secrets:
            secret_list.append(
                SecretListResponse(
                    id=secret.id,
                    workspace_id=secret.workspace_id,
                    user_id=secret.user_id,
                    name=secret.name,
                    description=secret.description,
                    secret_type=secret.secret_type,
                    tags=secret.tags,
                    is_active=secret.is_active,
                    created_at=secret.created_at,
                    updated_at=secret.updated_at,
                    expires_at=secret.expires_at,
                    last_used_at=secret.last_used_at,
                    usage_count=secret.usage_count,
                    max_usage_count=secret.max_usage_count,
                    is_expired=secret.is_expired(),
                    is_usage_exceeded=secret.is_usage_exceeded(),
                    can_be_used=secret.can_be_used(),
                )
            )

        return secret_list

    async def update_secret(
        self, secret_id: str, request: SecretUpdateRequest, user_id: str
    ) -> bool:
        """Update a secret.

        Args:
            secret_id: The secret ID
            request: The update request
            user_id: ID of the user updating the secret

        Returns:
            True if updated successfully, False if not found
        """
        # Get existing secret
        existing_secret = await self.repository.get_secret_by_id(secret_id)
        if not existing_secret:
            return False

        # Prepare updates
        updates = {}

        # Update non-encrypted fields
        if request.name is not None:
            updates["name"] = request.name
        if request.description is not None:
            updates["description"] = request.description
        if request.tags is not None:
            updates["tags"] = request.tags
        if request.is_active is not None:
            updates["is_active"] = request.is_active
        if request.expires_at is not None:
            updates["expires_at"] = request.expires_at
        if request.max_usage_count is not None:
            updates["max_usage_count"] = request.max_usage_count

        # Handle secret value update (requires re-encryption)
        if request.secret_value is not None:
            # Validate new secret value
            self.validator.validate_secret_value(existing_secret.secret_type, request.secret_value)

            # Re-encrypt with new value
            encrypted_data = await self.encryption.encrypt_secret(request.secret_value)
            updates["encrypted_value"] = encrypted_data["encrypted_value"]
            updates["salt"] = encrypted_data["salt"]
            updates["iv"] = encrypted_data["iv"]
            updates["tag"] = encrypted_data["tag"]

        # Update in database
        success = await self.repository.update_secret(secret_id, updates)

        if success:
            # Log the update
            await self._log_secret_access(
                secret_id=secret_id,
                workspace_id=existing_secret.workspace_id,
                user_id=user_id,
                access_method="update",
            )

        return success

    async def delete_secret(self, secret_id: str, user_id: str) -> bool:
        """Delete a secret.

        Args:
            secret_id: The secret ID
            user_id: ID of the user deleting the secret

        Returns:
            True if deleted successfully, False if not found
        """
        # Get existing secret for logging
        existing_secret = await self.repository.get_secret_by_id(secret_id)
        if not existing_secret:
            return False

        # Delete from database
        success = await self.repository.delete_secret(secret_id)

        if success:
            # Log the deletion
            await self._log_secret_access(
                secret_id=secret_id,
                workspace_id=existing_secret.workspace_id,
                user_id=user_id,
                access_method="delete",
            )

        return success

    async def get_secret_by_name(self, workspace_id: str, name: str) -> SecretModel | None:
        """Get a secret by workspace and name.

        Args:
            workspace_id: The workspace ID
            name: The secret name

        Returns:
            The secret model or None if not found
        """
        return await self.repository.get_secret_by_name(workspace_id, name)

    async def get_secret_usage_logs(
        self, secret_id: str, skip: int = 0, limit: int = 100
    ) -> list[SecretUsageLog]:
        """Get usage logs for a secret.

        Args:
            secret_id: The secret ID
            skip: Number of logs to skip
            limit: Maximum number of logs to return

        Returns:
            List of usage log entries
        """
        return await self.repository.get_secret_usage_logs(secret_id, skip, limit)

    async def count_secrets(
        self,
        workspace_id: str,
        secret_type: SecretType | None = None,
        is_active: bool | None = None,
    ) -> int:
        """Count secrets for a workspace.

        Args:
            workspace_id: The workspace ID
            secret_type: Optional secret type filter
            is_active: Optional active status filter

        Returns:
            Number of matching secrets
        """
        return await self.repository.count_secrets_by_workspace(
            workspace_id=workspace_id, secret_type=secret_type, is_active=is_active
        )

    async def get_secret_types_info(self) -> dict[str, Any]:
        """Get information about available secret types.

        Returns:
            Dictionary with secret type information
        """
        return {
            "types": [
                {
                    "value": secret_type.value,
                    "name": secret_type.name,
                    "description": self.validator.get_type_description(secret_type),
                    "validation_rules": self.validator.get_type_validation_rules(secret_type),
                }
                for secret_type in SecretType
            ]
        }

    async def _log_secret_access(
        self,
        secret_id: str,
        workspace_id: str,
        user_id: str,
        access_method: str,
        additional_context: dict[str, Any] | None = None,
    ) -> None:
        """Log secret access for audit trail.

        Args:
            secret_id: The secret ID
            workspace_id: The workspace ID
            user_id: The user ID
            access_method: How the secret was accessed
            additional_context: Additional context information
        """
        usage_log = SecretUsageLog(
            secret_id=secret_id,
            workspace_id=workspace_id,
            user_id=user_id,
            access_method=access_method,
            additional_context=additional_context or {},
        )

        await self.repository.log_secret_usage(usage_log)
