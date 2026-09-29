"""MCP-specific authentication for public API access."""

import hashlib
import os
import secrets
import string
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel


class MCPToken(BaseModel):
    """MCP API token model."""

    token_id: str
    token_hash: str  # Store only hash, never plain text
    workspace_id: str
    user_id: str  # User who created the token
    name: str
    description: str | None = None
    scopes: list[str] = []  # e.g., ["read:actions", "execute:actions"]
    rate_limit: int = 100  # requests per minute
    expires_at: datetime | None = None  # None = never expires (long-term)
    created_at: datetime
    last_used_at: datetime | None = None
    usage_count: int = 0
    status: str = "active"  # active, revoked, expired


class MCPAuthService:
    """Service for managing MCP authentication tokens."""

    TOKEN_PREFIX = "pb_mcp_"
    TOKEN_LENGTH = 32

    @classmethod
    def generate_token(cls) -> str:
        """Generate a secure MCP token."""
        alphabet = string.ascii_letters + string.digits
        random_part = "".join(secrets.choice(alphabet) for _ in range(cls.TOKEN_LENGTH))
        return f"{cls.TOKEN_PREFIX}{random_part}"

    @classmethod
    def hash_token(cls, token: str) -> str:
        """Hash a token for secure storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    async def create_mcp_token(
        cls,
        db,
        workspace_id: str,
        user_id: str,
        name: str,
        description: str | None = None,
        expires_in_days: int | None = None,  # None = never expires (long-term default)
        scopes: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new MCP token for a workspace.

        Returns the plain token (only shown once) and token metadata.
        """
        # Generate token
        plain_token = cls.generate_token()
        token_hash = cls.hash_token(plain_token)
        token_id = secrets.token_urlsafe(16)

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        # Default scopes
        if scopes is None:
            scopes = ["read:actions", "execute:actions", "read:secrets"]

        # Create token document
        token_doc = {
            "token_id": token_id,
            "token_hash": token_hash,
            "workspace_id": workspace_id,
            "user_id": user_id,
            "name": name,
            "description": description,
            "scopes": scopes,
            "rate_limit": 100,
            "expires_at": expires_at,
            "created_at": datetime.utcnow(),
            "last_used_at": None,
            "usage_count": 0,
            "status": "active",
        }

        # Store in database
        await db["mcp_tokens"].insert_one(token_doc)

        # Get base URL from settings
        # Import here to avoid circular imports
        from ..config import settings
        
        mcp_base_url = settings.mcp_base_url or "http://localhost:8090"

        # Generate the MCP URL without token in query (security best practice)
        # Token should be passed in Authorization header
        mcp_url = f"{mcp_base_url}/mcp/{workspace_id}/sse"

        return {
            "token": plain_token,  # Only returned once!
            "token_id": token_id,
            "name": name,
            "expires_at": expires_at,
            "scopes": scopes,
            "workspace_id": workspace_id,
            "mcp_url": mcp_url,
        }

    @classmethod
    async def validate_token(cls, db, token: str, workspace_id: str) -> dict[str, Any] | None:
        """
        Validate an MCP token and return token info if valid.
        """
        if not token or not token.startswith(cls.TOKEN_PREFIX):
            return None

        token_hash = cls.hash_token(token)

        # Find token in database
        token_doc = await db["mcp_tokens"].find_one(
            {"token_hash": token_hash, "workspace_id": workspace_id, "status": "active"}
        )

        if not token_doc:
            return None

        # Check expiration
        if token_doc.get("expires_at") and token_doc["expires_at"] < datetime.utcnow():
            # Mark as expired
            await db["mcp_tokens"].update_one(
                {"token_id": token_doc["token_id"]}, {"$set": {"status": "expired"}}
            )
            return None

        # Update usage stats
        await db["mcp_tokens"].update_one(
            {"token_id": token_doc["token_id"]},
            {"$set": {"last_used_at": datetime.utcnow()}, "$inc": {"usage_count": 1}},
        )

        return {
            "token_id": token_doc["token_id"],
            "workspace_id": token_doc["workspace_id"],
            "user_id": token_doc["user_id"],
            "scopes": token_doc["scopes"],
            "rate_limit": token_doc["rate_limit"],
            "name": token_doc["name"],
        }

    @classmethod
    async def validate_token_any_workspace(cls, db, token: str) -> dict[str, Any] | None:
        """
        Validate an MCP token without requiring workspace_id upfront.
        Returns token info including the workspace_id if valid.
        """
        if not token or not token.startswith(cls.TOKEN_PREFIX):
            return None

        token_hash = cls.hash_token(token)

        # Find token in database (any workspace)
        token_doc = await db["mcp_tokens"].find_one(
            {"token_hash": token_hash, "status": "active"}
        )

        if not token_doc:
            return None

        # Check expiration
        if token_doc.get("expires_at") and token_doc["expires_at"] < datetime.utcnow():
            # Mark as expired
            await db["mcp_tokens"].update_one(
                {"token_id": token_doc["token_id"]}, {"$set": {"status": "expired"}}
            )
            return None

        # Update usage stats
        await db["mcp_tokens"].update_one(
            {"token_id": token_doc["token_id"]},
            {"$set": {"last_used_at": datetime.utcnow()}, "$inc": {"usage_count": 1}},
        )

        return {
            "token_id": token_doc["token_id"],
            "workspace_id": token_doc["workspace_id"],
            "scopes": token_doc["scopes"],
            "rate_limit": token_doc["rate_limit"],
        }

    @classmethod
    async def revoke_token(cls, db, token_id: str) -> bool:
        """Revoke an MCP token."""
        result = await db["mcp_tokens"].update_one(
            {"token_id": token_id}, {"$set": {"status": "revoked"}}
        )
        return result.modified_count > 0

    @classmethod
    async def list_tokens(cls, db, workspace_id: str) -> list:
        """List all tokens for a workspace (without exposing the actual tokens)."""
        tokens = await db["mcp_tokens"].find({"workspace_id": workspace_id}).to_list(length=100)

        # Remove sensitive data
        for token in tokens:
            token.pop("token_hash", None)
            token.pop("_id", None)

        return tokens
