"""
Service API key authentication for service-to-service communication.
"""

import secrets
from datetime import UTC, datetime

import bcrypt
from bson import ObjectId
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorDatabase

from .models import ServiceAPIKey, ServiceContext


class ServiceKeyAuth:
    """Service API key authentication handler."""

    def __init__(self, db: AsyncIOMotorDatabase):
        """Initialize service key auth with database."""
        self.db = db
        self.collection = db.service_api_keys

    async def create_service_key(
        self,
        service_name: str,
        scopes: list[str],
        created_by: str | None = None,
        description: str | None = None,
    ) -> tuple[ServiceAPIKey, str]:
        """
        Create a new service API key.

        Args:
            service_name: Name of the service (e.g., 'mcp-server')
            scopes: List of permission scopes
            created_by: User ID who created this key
            description: Optional description

        Returns:
            Tuple of (ServiceAPIKey model, plain text secret key)
        """
        # Generate secret key (svc_mcp_...)
        secret_key = f"svc_{service_name.replace('-', '_')}_{secrets.token_urlsafe(32)}"

        # Hash the secret key
        salt = bcrypt.gensalt()
        key_hash = bcrypt.hashpw(secret_key.encode(), salt).decode()

        # Create service key document
        service_key_dict = {
            "service_name": service_name,
            "key_hash": key_hash,
            "scopes": scopes,
            "description": description,
            "created_by": created_by,
            "last_used_at": None,
            "revoked_at": None,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

        # Insert into database
        result = await self.collection.insert_one(service_key_dict)
        service_key_dict["_id"] = result.inserted_id

        # Return model and plain text key (only shown once)
        service_key = ServiceAPIKey.from_mongo(service_key_dict)
        return service_key, secret_key

    async def validate_service_key(self, secret_key: str) -> ServiceAPIKey | None:
        """
        Validate a service API key.

        Args:
            secret_key: Plain text secret key from request header

        Returns:
            ServiceAPIKey if valid, None if invalid
        """
        # Extract service name from key prefix (svc_mcp_server_...)
        if not secret_key.startswith("svc_"):
            logger.warning("Invalid service key format - must start with 'svc_'")
            return None

        # Find all non-revoked service keys
        cursor = self.collection.find({"revoked_at": None})
        async for doc in cursor:
            key_hash = doc.get("key_hash")
            if not key_hash:
                continue

            # Check if key matches
            try:
                if bcrypt.checkpw(secret_key.encode(), key_hash.encode()):
                    # Update last used timestamp
                    await self.collection.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"last_used_at": datetime.now(UTC)}},
                    )

                    # Return service key model
                    return ServiceAPIKey.from_mongo(doc)
            except Exception as e:
                logger.error(f"Error checking service key hash: {e}")
                continue

        logger.warning("Service key validation failed - no matching key found")
        return None

    async def revoke_service_key(self, key_id: str) -> bool:
        """
        Revoke a service API key.

        Args:
            key_id: MongoDB ObjectId as string

        Returns:
            True if revoked, False if not found
        """
        result = await self.collection.update_one(
            {"_id": ObjectId(key_id)},
            {"$set": {"revoked_at": datetime.now(UTC), "updated_at": datetime.now(UTC)}},
        )
        return result.modified_count > 0

    async def list_service_keys(self) -> list[ServiceAPIKey]:
        """
        List all service API keys (active and revoked).

        Returns:
            List of ServiceAPIKey models
        """
        cursor = self.collection.find({})
        keys = []
        async for doc in cursor:
            keys.append(ServiceAPIKey.from_mongo(doc))
        return keys

    async def get_service_key_by_id(self, key_id: str) -> ServiceAPIKey | None:
        """
        Get service key by ID.

        Args:
            key_id: MongoDB ObjectId as string

        Returns:
            ServiceAPIKey if found, None otherwise
        """
        doc = await self.collection.find_one({"_id": ObjectId(key_id)})
        if doc:
            return ServiceAPIKey.from_mongo(doc)
        return None


# Dependency injection helpers
_service_key_auth: ServiceKeyAuth | None = None


def get_service_key_auth() -> ServiceKeyAuth:
    """
    Get ServiceKeyAuth instance (dependency injection).

    Returns:
        ServiceKeyAuth instance
    """
    global _service_key_auth

    if _service_key_auth is None:
        from ..database.connection import get_database_connection
        db = get_database_connection().database
        _service_key_auth = ServiceKeyAuth(db)

    return _service_key_auth
