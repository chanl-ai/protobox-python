"""Secret repository for MongoDB operations."""

from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.errors import DuplicateKeyError

from ...models.secret import SecretModel, SecretUsageLog
from ...secrets.types import SecretType
from ..connection import get_database_connection


class SecretRepository:
    """Repository for secret database operations."""

    def __init__(self):
        """Initialize the repository."""
        self.collection_name = "secrets"
        self.usage_log_collection_name = "secret_usage_logs"

    async def get_collection(self) -> AsyncIOMotorCollection:
        """Get the secrets collection."""
        db_connection = get_database_connection()
        return db_connection.database[self.collection_name]

    async def get_usage_log_collection(self) -> AsyncIOMotorCollection:
        """Get the secret usage logs collection."""
        db_connection = get_database_connection()
        return db_connection.database[self.usage_log_collection_name]

    async def create_secret(self, secret: SecretModel) -> str:
        """Create a new secret in the database.

        Args:
            secret: The secret model to create

        Returns:
            The ID of the created secret

        Raises:
            DuplicateKeyError: If secret with same name exists in workspace
        """
        collection = await self.get_collection()

        # Check for duplicate name in workspace
        existing = await collection.find_one(
            {"workspace_id": secret.workspace_id, "name": secret.name}
        )
        if existing:
            raise DuplicateKeyError("Secret with this name already exists in workspace")

        secret_data = secret.model_dump_for_db()
        result = await collection.insert_one(secret_data)
        return str(result.inserted_id)

    async def get_secret_by_id(self, secret_id: str) -> SecretModel | None:
        """Get a secret by its ID.

        Args:
            secret_id: The secret ID

        Returns:
            The secret model or None if not found
        """
        collection = await self.get_collection()

        try:
            object_id = ObjectId(secret_id)
        except Exception:
            return None

        secret_data = await collection.find_one({"_id": object_id})
        if not secret_data:
            return None

        # Convert ObjectId to string
        secret_data["_id"] = str(secret_data["_id"])
        return SecretModel(**secret_data)

    async def get_secrets_by_workspace(
        self,
        workspace_id: str,
        secret_type: SecretType | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SecretModel]:
        """Get secrets for a workspace with optional filtering.

        Args:
            workspace_id: The workspace ID
            secret_type: Optional secret type filter
            is_active: Optional active status filter
            skip: Number of documents to skip
            limit: Maximum number of documents to return

        Returns:
            List of secret models
        """
        collection = await self.get_collection()

        # Build filter query
        filter_query = {"workspace_id": workspace_id}
        if secret_type:
            filter_query["secret_type"] = secret_type.value
        if is_active is not None:
            filter_query["is_active"] = is_active

        # Execute query
        cursor = collection.find(filter_query).skip(skip).limit(limit)
        secrets = []

        async for secret_data in cursor:
            secret_data["_id"] = str(secret_data["_id"])
            secrets.append(SecretModel(**secret_data))

        return secrets

    async def update_secret(self, secret_id: str, updates: dict[str, Any]) -> bool:
        """Update a secret.

        Args:
            secret_id: The secret ID
            updates: Dictionary of field updates

        Returns:
            True if secret was updated, False if not found
        """
        collection = await self.get_collection()

        try:
            object_id = ObjectId(secret_id)
        except Exception:
            return False

        # Add updated_at timestamp
        from datetime import datetime

        updates["updated_at"] = datetime.utcnow()

        result = await collection.update_one({"_id": object_id}, {"$set": updates})

        return result.modified_count > 0

    async def delete_secret(self, secret_id: str) -> bool:
        """Delete a secret.

        Args:
            secret_id: The secret ID

        Returns:
            True if secret was deleted, False if not found
        """
        collection = await self.get_collection()

        try:
            object_id = ObjectId(secret_id)
        except Exception:
            return False

        result = await collection.delete_one({"_id": object_id})
        return result.deleted_count > 0

    async def get_secret_by_name(self, workspace_id: str, name: str) -> SecretModel | None:
        """Get a secret by workspace and name.

        Args:
            workspace_id: The workspace ID
            name: The secret name

        Returns:
            The secret model or None if not found
        """
        collection = await self.get_collection()

        secret_data = await collection.find_one({"workspace_id": workspace_id, "name": name})

        if not secret_data:
            return None

        secret_data["_id"] = str(secret_data["_id"])
        return SecretModel(**secret_data)

    async def increment_secret_usage(self, secret_id: str) -> bool:
        """Increment the usage count of a secret.

        Args:
            secret_id: The secret ID

        Returns:
            True if updated successfully, False if not found
        """
        collection = await self.get_collection()

        try:
            object_id = ObjectId(secret_id)
        except Exception:
            return False

        from datetime import datetime

        result = await collection.update_one(
            {"_id": object_id},
            {
                "$inc": {"usage_count": 1},
                "$set": {"last_used_at": datetime.utcnow(), "updated_at": datetime.utcnow()},
            },
        )

        return result.modified_count > 0

    async def log_secret_usage(self, usage_log: SecretUsageLog) -> str:
        """Log secret usage.

        Args:
            usage_log: The usage log entry

        Returns:
            The ID of the created usage log entry
        """
        collection = await self.get_usage_log_collection()

        log_data = usage_log.model_dump_for_db()
        result = await collection.insert_one(log_data)
        return str(result.inserted_id)

    async def get_secret_usage_logs(
        self, secret_id: str, skip: int = 0, limit: int = 100
    ) -> list[SecretUsageLog]:
        """Get usage logs for a secret.

        Args:
            secret_id: The secret ID
            skip: Number of documents to skip
            limit: Maximum number of documents to return

        Returns:
            List of usage log entries
        """
        collection = await self.get_usage_log_collection()

        cursor = (
            collection.find({"secret_id": secret_id}).sort("timestamp", -1).skip(skip).limit(limit)
        )
        logs = []

        async for log_data in cursor:
            log_data["_id"] = str(log_data["_id"])
            logs.append(SecretUsageLog(**log_data))

        return logs

    async def count_secrets_by_workspace(
        self,
        workspace_id: str,
        secret_type: SecretType | None = None,
        is_active: bool | None = None,
    ) -> int:
        """Count secrets for a workspace with optional filtering.

        Args:
            workspace_id: The workspace ID
            secret_type: Optional secret type filter
            is_active: Optional active status filter

        Returns:
            Number of matching secrets
        """
        collection = await self.get_collection()

        # Build filter query
        filter_query = {"workspace_id": workspace_id}
        if secret_type:
            filter_query["secret_type"] = secret_type.value
        if is_active is not None:
            filter_query["is_active"] = is_active

        return await collection.count_documents(filter_query)

    async def ensure_indexes(self) -> None:
        """Ensure required database indexes exist."""
        collection = await self.get_collection()
        usage_log_collection = await self.get_usage_log_collection()

        # Secrets collection indexes
        await collection.create_index(
            [("workspace_id", 1), ("name", 1)], unique=True, name="workspace_name_unique"
        )

        await collection.create_index("workspace_id", name="workspace_id_idx")
        await collection.create_index("secret_type", name="secret_type_idx")
        await collection.create_index("is_active", name="is_active_idx")
        await collection.create_index("created_at", name="created_at_idx")
        await collection.create_index("updated_at", name="updated_at_idx")
        await collection.create_index("expires_at", name="expires_at_idx")

        # Usage logs collection indexes
        await usage_log_collection.create_index("secret_id", name="secret_id_idx")
        await usage_log_collection.create_index("workspace_id", name="workspace_id_idx")
        await usage_log_collection.create_index("timestamp", name="timestamp_idx")
        await usage_log_collection.create_index(
            [("secret_id", 1), ("timestamp", -1)], name="secret_timestamp_idx"
        )
