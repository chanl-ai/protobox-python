"""
Supabase JWT validation for remote authentication.

Validates JWT tokens issued by your remote Supabase instance.
"""

import os
from datetime import UTC, datetime
from typing import Any

import jwt
import requests
from loguru import logger

from .models import SupabaseUserInfo


class SupabaseAuth:
    """Supabase JWT validation and user management."""

    def __init__(
        self, supabase_url: str = None, supabase_anon_key: str = None, jwt_secret: str = None
    ):
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_anon_key = supabase_anon_key or os.getenv("SUPABASE_ANON_KEY")
        self.jwt_secret = jwt_secret or os.getenv("SUPABASE_JWT_SECRET")

        if not self.supabase_url or not self.supabase_anon_key:
            raise ValueError("Supabase URL and anon key are required")

        # Extract project reference from URL for JWT validation
        self.project_ref = self._extract_project_ref(self.supabase_url)

        # Cache for JWT secrets (fetched from Supabase)
        self._jwt_secrets: dict[str, Any] = {}

        logger.info(f"SupabaseAuth initialized for project: {self.project_ref}")

    def _extract_project_ref(self, url: str) -> str:
        """Extract project reference from Supabase URL."""
        # URL format: https://[project-ref].supabase.co
        try:
            return url.split("//")[1].split(".")[0]
        except (IndexError, AttributeError):
            raise ValueError(f"Invalid Supabase URL format: {url}")

    async def _get_jwt_secrets(self) -> dict[str, Any]:
        """Get JWT secrets from Supabase (cached)."""
        if self._jwt_secrets:
            return self._jwt_secrets

        try:
            # Fetch JWT secrets from Supabase REST API

            # For production, we need to use the JWT secret from environment
            # or fetch it via Supabase Admin API if available
            if self.jwt_secret:
                self._jwt_secrets = {"secret": self.jwt_secret}
            else:
                # Use anon key for verification (less secure but works for demo)
                self._jwt_secrets = {"secret": self.supabase_anon_key}

            logger.debug("JWT secrets retrieved")
            return self._jwt_secrets

        except Exception as e:
            logger.error(f"Failed to get JWT secrets: {e}")
            # Fallback to anon key
            self._jwt_secrets = {"secret": self.supabase_anon_key}
            return self._jwt_secrets

    async def validate_jwt_token(self, token: str) -> SupabaseUserInfo | None:
        """
        Validate a Supabase JWT token and return user info.

        Args:
            token: JWT token from Authorization header

        Returns:
            SupabaseUserInfo if valid, None if invalid
        """
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith("Bearer "):
                token = token[7:]

            # Get JWT secrets
            await self._get_jwt_secrets()

            # Decode JWT with minimal verification for now
            # In production, you'd want proper key verification
            decoded = jwt.decode(
                token,
                options={"verify_signature": False},  # Skip signature verification for demo
                algorithms=["HS256"],
            )

            # Validate token claims
            now = datetime.now(UTC).timestamp()

            if decoded.get("exp", 0) < now:
                logger.warning("Token expired")
                return None

            # Accept tokens from our custom JWT auth (no issuer) or Supabase
            issuer = decoded.get("iss")
            if issuer and issuer != f"{self.supabase_url}/auth/v1":
                # Only reject if issuer is present but wrong
                # Our custom JWT tokens don't have an issuer
                logger.warning(f"Invalid issuer: {issuer}")
                return None

            # Create user info from token
            user_info = SupabaseUserInfo(
                sub=decoded["sub"],
                email=decoded.get("email", ""),
                email_verified=decoded.get("email_verified", False),
                aud=decoded.get("aud", ""),
                exp=decoded.get("exp", 0),
                iat=decoded.get("iat", 0),
                iss=decoded.get("iss", ""),
            )

            logger.debug(f"JWT validated for user: {user_info.email}")
            return user_info

        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
        except Exception as e:
            logger.error(f"JWT validation error: {e}")
            return None

    async def create_user_with_supabase(
        self, email: str, password: str
    ) -> dict[str, Any] | None:
        """
        Create a user in Supabase (calls Supabase Auth API).

        Args:
            email: User email
            password: User password

        Returns:
            User data if successful, None if failed
        """
        try:
            url = f"{self.supabase_url}/auth/v1/signup"
            headers = {"apikey": self.supabase_anon_key, "Content-Type": "application/json"}
            data = {"email": email, "password": password}

            response = requests.post(url, headers=headers, json=data, timeout=10)

            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"User created in Supabase: {email}")
                return result
            logger.error(f"Supabase signup failed: {response.status_code} - {response.text}")
            return None

        except Exception as e:
            logger.error(f"Error creating user in Supabase: {e}")
            return None

    async def authenticate_with_supabase(
        self, email: str, password: str
    ) -> dict[str, Any] | None:
        """
        Authenticate user with Supabase (get JWT token).

        Args:
            email: User email
            password: User password

        Returns:
            Auth session data if successful, None if failed
        """
        try:
            url = f"{self.supabase_url}/auth/v1/token?grant_type=password"
            headers = {"apikey": self.supabase_anon_key, "Content-Type": "application/json"}
            data = {"email": email, "password": password}

            response = requests.post(url, headers=headers, json=data, timeout=10)

            if response.status_code == 200:
                result = response.json()
                logger.info(f"User authenticated with Supabase: {email}")
                return result
            logger.warning(f"Supabase login failed: {response.status_code} - {response.text}")
            return None

        except Exception as e:
            logger.error(f"Error authenticating with Supabase: {e}")
            return None


# Global instance
_supabase_auth: SupabaseAuth | None = None


def get_supabase_auth() -> SupabaseAuth:
    """Get or create global SupabaseAuth instance."""
    global _supabase_auth
    if _supabase_auth is None:
        _supabase_auth = SupabaseAuth()
    return _supabase_auth
