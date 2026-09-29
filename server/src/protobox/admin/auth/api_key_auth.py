"""
API Key authentication and management system.

Handles secure API key generation, validation, and storage in MongoDB.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from bson import ObjectId
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..database.connection import get_database_connection
from .models import (
    APIKey,
    APIKeyInfo,
    AuthProvider,
    CreateAPIKeyRequest,
    CreateAPIKeyResponse,
    User,
)


class APIKeyAuth:
    """API Key authentication and management."""

    def __init__(self, db: AsyncIOMotorDatabase = None):
        self._db = db
        self._db_connection = None

        # Collections will be lazy-loaded
        self.users_collection = None
        self.api_keys_collection = None

        # Create indexes (will be handled when database is available)
        self._create_indexes()

    async def _get_database(self) -> AsyncIOMotorDatabase:
        """Get database connection, creating it if necessary."""
        if self._db is not None:
            return self._db

        if self._db_connection is None:
            self._db_connection = get_database_connection()
            if not self._db_connection.is_connected:
                await self._db_connection.connect()

        db = self._db_connection.database

        # Initialize collections if not already done
        if self.users_collection is None:
            self.users_collection = db["users"]
            self.api_keys_collection = db["api_keys"]

        return db

    def _create_indexes(self):
        """Create necessary database indexes."""
        # Note: In production, create these indexes separately
        # self.api_keys_collection.create_index("key_id", unique=True)
        # self.api_keys_collection.create_index("user_id")
        # self.api_keys_collection.create_index("user_id")
        # self.users_collection.create_index("id", unique=True)
        # self.users_collection.create_index("email", unique=True)
        pass

    def generate_api_key(self) -> tuple[str, str]:
        """
        Generate a new API key pair.

        Returns:
            (key_id, secret_key) tuple
        """
        # Generate secure random key
        secret_key = secrets.token_urlsafe(32)

        # Create key ID (public identifier)
        key_id = f"ak_{secrets.token_urlsafe(16)}"

        return key_id, secret_key

    def hash_secret_key(self, secret_key: str) -> str:
        """Hash a secret key for secure storage."""
        return hashlib.sha256(secret_key.encode()).hexdigest()

    def verify_secret_key(self, secret_key: str, key_hash: str) -> bool:
        """Verify a secret key against its hash."""
        return hashlib.sha256(secret_key.encode()).hexdigest() == key_hash

    async def create_or_get_user(self, user_id: str, email: str) -> User:
        """
        Create or get user by ID.

        Args:
            user_id: User ID
            email: User email

        Returns:
            User object
        """
        # Get database connection
        await self._get_database()

        # Try to find existing user
        user_doc = await self.users_collection.find_one({"id": user_id})

        if user_doc:
            # Convert MongoDB document to User
            if "_id" in user_doc:
                user_doc["id"] = str(user_doc["_id"])
                del user_doc["_id"]
            return User(**user_doc)

        # Create new user
        user = User(
            id=user_id,
            email=email,
            email_verified=True,  # Assuming validated through auth
            provider=AuthProvider.FIREBASE,
            permissions=[],
            metadata={},
        )

        # Insert into database
        result = await self.users_collection.insert_one(user.dict(exclude={"id"}))
        user.id = str(result.inserted_id)

        logger.info(f"Created new user: {email} ({user_id})")
        return user

    async def create_api_key(
        self, user: User, request: CreateAPIKeyRequest
    ) -> CreateAPIKeyResponse:
        """
        Create a new API key for a user.

        Args:
            user: User object
            request: API key creation request

        Returns:
            CreateAPIKeyResponse with key details
        """
        # Generate API key
        key_id, secret_key = self.generate_api_key()
        key_hash = self.hash_secret_key(secret_key)

        # Calculate expiration
        expires_at = None
        if request.expires_days:
            expires_at = datetime.now(UTC) + timedelta(days=request.expires_days)

        # Create API key record
        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            user_id=user.id,
            workspace_id=user.workspace_id or "",  # Get from user or default
            name=request.name,
            permissions=request.permissions,
            expires_at=expires_at,
        )

        # Get database connection
        await self._get_database()

        # Insert into database
        result = await self.api_keys_collection.insert_one(api_key.dict(exclude={"id"}))
        api_key.id = str(result.inserted_id)

        # Update user's API key list
        await self.users_collection.update_one(
            {"_id": ObjectId(user.id)}, {"$push": {"api_keys": api_key.id}}
        )

        logger.info(f"Created API key '{request.name}' for user {user.email}")

        return CreateAPIKeyResponse(
            key_id=key_id,
            secret_key=secret_key,  # Only returned once!
            name=request.name,
            permissions=request.permissions,
            expires_at=expires_at,
            created_at=api_key.created_at,
        )

    async def validate_api_key(self, key_id: str, secret_key: str) -> APIKey | None:
        """
        Validate an API key.

        Args:
            key_id: Public key identifier
            secret_key: Secret key

        Returns:
            APIKey object if valid, None if invalid
        """
        try:
            # Get database connection
            await self._get_database()

            # Find API key by key_id
            key_doc = await self.api_keys_collection.find_one({"key_id": key_id, "is_active": True})

            if not key_doc:
                logger.warning(f"API key not found: {key_id}")
                return None

            api_key = APIKey.from_mongo(key_doc)

            # Check expiration
            if api_key.expires_at and api_key.expires_at < datetime.now(UTC):
                logger.warning(f"API key expired: {key_id}")
                return None

            # Verify secret key
            if not self.verify_secret_key(secret_key, api_key.key_hash):
                logger.warning(f"Invalid secret key for: {key_id}")
                return None

            # Update usage statistics
            await self.api_keys_collection.update_one(
                {"_id": ObjectId(api_key.id)},
                {
                    "$inc": {"usage_count": 1},
                    "$set": {
                        "last_used": datetime.now(UTC),
                        "updated_at": datetime.now(UTC),
                    },
                },
            )

            logger.debug(f"API key validated: {key_id}")
            return api_key

        except Exception as e:
            logger.error(f"Error validating API key: {e}")
            return None

    async def get_user_api_keys(self, user_id: str) -> list[APIKeyInfo]:
        """
        Get all API keys for a user.

        Args:
            user_id: User ID

        Returns:
            List of APIKeyInfo objects
        """
        # Get database connection
        await self._get_database()

        cursor = self.api_keys_collection.find({"user_id": user_id})
        api_keys = []

        async for doc in cursor:
            api_key = APIKey.from_mongo(doc)
            api_keys.append(
                APIKeyInfo(
                    key_id=api_key.key_id,
                    name=api_key.name,
                    permissions=api_key.permissions,
                    is_active=api_key.is_active,
                    last_used=api_key.last_used,
                    usage_count=api_key.usage_count,
                    expires_at=api_key.expires_at,
                    created_at=api_key.created_at,
                )
            )

        return api_keys

    async def revoke_api_key(self, user_id: str, key_id: str) -> bool:
        """
        Revoke an API key.

        Args:
            user_id: User ID (for authorization)
            key_id: Key ID to revoke

        Returns:
            True if revoked, False if not found
        """
        # Get database connection
        await self._get_database()

        result = await self.api_keys_collection.update_one(
            {"key_id": key_id, "user_id": user_id},
            {"$set": {"is_active": False, "updated_at": datetime.now(UTC)}},
        )

        if result.modified_count > 0:
            logger.info(f"Revoked API key: {key_id}")
            return True
        logger.warning(f"API key not found for revocation: {key_id}")
        return False

    async def get_user_by_api_key(self, key_id: str) -> User | None:
        """
        Get user associated with an API key.

        Args:
            key_id: API key ID

        Returns:
            User object if found, None otherwise
        """
        # Get database connection
        await self._get_database()

        # Find API key
        key_doc = await self.api_keys_collection.find_one({"key_id": key_id})
        if not key_doc:
            return None

        # Find user
        user_doc = await self.users_collection.find_one({"_id": ObjectId(key_doc["user_id"])})
        if not user_doc:
            return None

        return User.from_mongo(user_doc)


# Global instance
_api_key_auth: APIKeyAuth | None = None


def get_api_key_auth() -> APIKeyAuth:
    """Get or create global APIKeyAuth instance."""
    global _api_key_auth
    if _api_key_auth is None:
        _api_key_auth = APIKeyAuth()
    return _api_key_auth
