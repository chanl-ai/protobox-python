"""
Custom JWT validation for ProtoBox authentication.

Validates JWT tokens issued by the Next.js platform using shared secret.
This module ONLY validates tokens - user management is handled by Next.js.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from loguru import logger

from ..config import settings
from .models import AuthProvider, JWTClaims, TokenType


class JWTAuth:
    """Custom JWT validation using shared secret.

    This class ONLY validates JWT tokens. It does NOT:
    - Create users
    - Manage workspaces
    - Handle billing

    All platform operations are handled by the Next.js platform.
    """

    def __init__(self, jwt_secret: str = None):
        self.jwt_secret = jwt_secret or settings.jwt_secret
        self.algorithm = settings.jwt_algorithm
        self.access_token_expire_minutes = settings.access_token_expire_minutes
        self.refresh_token_expire_days = settings.refresh_token_expire_days

        # Test mode configuration (only in development)
        self.test_mode = settings.auth_test_mode
        self.environment = settings.environment

        # Only allow test mode in development/test environments
        if self.test_mode and self.environment not in ["development", "dev", "test", "local"]:
            logger.warning(
                "Test mode is only allowed in development environments. Disabling test mode."
            )
            self.test_mode = False

        if not self.jwt_secret and not self.test_mode:
            raise ValueError(
                "JWT_SECRET is required for authentication (or enable test mode in development)"
            )

        if self.test_mode:
            logger.warning("⚠️  JWT Auth running in TEST MODE - DO NOT USE IN PRODUCTION")
            # Use a fixed test secret in test mode
            self.jwt_secret = self.jwt_secret or "test-secret-key-do-not-use-in-production"

        logger.info(
            f"JWTAuth initialized {'in TEST MODE' if self.test_mode else 'with shared secret'}"
        )

    async def validate_jwt_token(self, token: str) -> JWTClaims | None:
        """
        Validate JWT token and extract user info.

        Args:
            token: JWT token string

        Returns:
            JWTClaims object if valid, None if invalid
        """
        # Handle test tokens in test mode
        if self.test_mode and token == "test-token":
            logger.debug("Using test token in test mode")
            return JWTClaims(
                uid="test-user-123",
                email="test@example.com",
                email_verified=True,
                workspace_id="test-workspace-123",
                role="admin",
                permissions=["read", "write", "admin"],
                token_type=TokenType.ACCESS,
                provider=AuthProvider.FIREBASE,
                metadata={"test": True},
            )

        try:
            # Decode and verify JWT
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])

            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, tz=UTC) < datetime.now(tz=UTC):
                logger.warning("JWT token has expired")
                return None

            # Extract user info - support both uid and sub fields
            # IMPORTANT: Use Firebase UID for workspace membership (team authentication)
            # Database ID is stored in metadata for other purposes
            uid = payload.get("uid")      # Firebase UID (primary for workspace membership)
            sub = payload.get("sub")      # Standard JWT subject claim
            db_id = payload.get("db_id")  # Internal MongoDB user ID (stored in metadata)

            # CRITICAL: Reject tokens without a valid user ID
            # Use Firebase UID as primary identifier for workspace membership
            user_id = uid or sub
            if not user_id:
                logger.error("JWT token missing user ID (uid/sub) - rejecting as invalid")
                return None

            user_info = JWTClaims(
                # IMPORTANT: Use Firebase UID as primary identifier for workspace membership
                uid=uid,           # Firebase UID (primary for workspace membership)
                sub=sub,           # Standard JWT subject claim
                email=payload.get("email"),
                workspace_id=payload.get("workspace_id"),
                role=payload.get("role"),
                permissions=payload.get("permissions", []),
                metadata={
                    **payload.get("metadata", {}),
                    "db_id": db_id,  # Store db_id in metadata for reference
                },
                token_type=(
                    TokenType(payload.get("token_type", "access"))
                    if payload.get("token_type")
                    else TokenType.ACCESS
                ),
                provider=(
                    AuthProvider(payload.get("provider", "firebase"))
                    if payload.get("provider")
                    else AuthProvider.JWT
                ),
                exp=exp,
                iat=payload.get("iat"),
            )

            logger.debug(f"JWT token validated for user: {user_info.email} (uid={user_id})")
            return user_info

        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error validating JWT token: {e}")
            return None

    def create_access_token(
        self,
        uid: str,
        email: str | None = None,
        workspace_id: str | None = None,
        additional_claims: dict[str, Any] | None = None,
    ) -> str:
        """
        Create an access token (short-lived).

        Args:
            uid: User ID
            email: User email
            workspace_id: Associated workspace
            additional_claims: Additional JWT claims

        Returns:
            JWT access token
        """
        now = datetime.now(UTC)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)

        payload = {
            "uid": uid,
            "email": email,
            "workspace_id": workspace_id,
            "token_type": "access",
            "iat": now,
            "exp": expire,
            **(additional_claims or {}),
        }

        return jwt.encode(payload, self.jwt_secret, algorithm=self.algorithm)

    def create_refresh_token(self, uid: str, email: str | None = None, workspace_id: str | None = None) -> str:
        """
        Create a refresh token (long-lived).

        Args:
            uid: User ID
            email: User email
            workspace_id: Current workspace ID

        Returns:
            JWT refresh token
        """
        now = datetime.now(UTC)
        expire = now + timedelta(days=self.refresh_token_expire_days)

        payload = {
            "uid": uid,
            "email": email,
            "workspace_id": workspace_id,
            "token_type": "refresh",
            "iat": now,
            "exp": expire
        }

        return jwt.encode(payload, self.jwt_secret, algorithm=self.algorithm)

    def create_test_token(
        self,
        uid: str = "test-user-123",
        email: str = "test@example.com",
        workspace_id: str | None = "test-workspace-123",
        role: str = "admin",
        permissions: list[str] | None = None,
    ) -> str:
        """
        Create a test token for development/testing.

        Args:
            uid: Test user ID
            email: Test user email
            workspace_id: Test workspace ID
            role: Test user role
            permissions: Test user permissions

        Returns:
            JWT test token

        Raises:
            ValueError: If not in test mode
        """
        if not self.test_mode:
            raise ValueError("Test tokens can only be created in test mode")

        logger.warning(f"Creating test token for user: {email}")

        return self.create_access_token(
            uid=uid,
            email=email,
            workspace_id=workspace_id,
            additional_claims={
                "role": role,
                "permissions": permissions or ["read", "write", "admin"],
                "test": True,
                "provider": AuthProvider.FIREBASE.value,
            },
        )

    def validate_refresh_token(self, token: str) -> dict[str, Any] | None:
        """
        Validate a refresh token.

        Args:
            token: JWT refresh token

        Returns:
            Token payload if valid, None if invalid
        """
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.algorithm])

            # Verify it's a refresh token
            if payload.get("token_type") != "refresh":
                logger.warning("Token is not a refresh token")
                return None

            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, tz=UTC) < datetime.now(tz=UTC):
                logger.warning("Refresh token has expired")
                return None

            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Refresh token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid refresh token: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error validating refresh token: {e}")
            return None

    async def validate_token(self, token: str) -> dict[str, Any] | None:
        """
        Validate a JWT token and return a dictionary with validation result.
        This method is used by the middleware for Bearer token authentication.

        Args:
            token: JWT token to validate

        Returns:
            Dictionary with validation result including user info
        """
        # Use the existing validate_jwt_token method
        claims = await self.validate_jwt_token(token)
        if not claims:
            return None

        return {
            "valid": True,
            "uid": claims.uid,
            "email": claims.email,
            "workspace_id": claims.workspace_id,
            "role": claims.role,
            "permissions": claims.permissions,
            "token_type": claims.token_type.value,
            "provider": claims.provider.value,
            "exp": claims.exp,
            "iat": claims.iat,
        }


# Singleton instance
_jwt_auth_instance: JWTAuth | None = None


def get_jwt_auth() -> JWTAuth:
    """Get or create JWT auth instance."""
    global _jwt_auth_instance

    if _jwt_auth_instance is None:
        _jwt_auth_instance = JWTAuth()

    return _jwt_auth_instance
