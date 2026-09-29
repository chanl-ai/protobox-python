"""Base OAuth2 provider class for all integrations."""

import hashlib
import logging
import secrets
from abc import ABC, abstractmethod
from base64 import urlsafe_b64encode
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel

from ..models.integration import IntegrationType, OAuth2TokenData

logger = logging.getLogger(__name__)


class OAuth2Config(BaseModel):
    """OAuth2 configuration for a provider."""

    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    revoke_url: str | None = None
    user_info_url: str | None = None
    scopes: list[str]
    redirect_uri: str
    supports_pkce: bool = False
    supports_state: bool = True
    access_type: str | None = None  # For providers like Google that need 'offline'
    prompt: str | None = None  # For providers that need consent prompt


class OAuth2Session(BaseModel):
    """OAuth2 session data for ongoing authorization."""

    state: str
    workspace_id: str
    user_id: str
    integration_type: IntegrationType
    redirect_uri: str
    code_verifier: str | None = None  # For PKCE
    code_challenge: str | None = None  # For PKCE
    nonce: str | None = None  # For OpenID Connect
    created_at: datetime
    expires_at: datetime


class BaseOAuth2Provider(ABC):
    """Base class for OAuth2 providers."""

    def __init__(self, config: OAuth2Config):
        self.config = config
        self.http_client = httpx.AsyncClient(timeout=30.0)

    @property
    @abstractmethod
    def integration_type(self) -> IntegrationType:
        """Return the integration type for this provider."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Return the display name for this provider."""
        pass

    @property
    @abstractmethod
    def supported_features(self) -> list[str]:
        """Return list of supported features."""
        pass

    def generate_state(self, workspace_id: str, user_id: str) -> OAuth2Session:
        """Generate secure state for OAuth2 flow."""
        state = secrets.token_urlsafe(32)
        
        session = OAuth2Session(
            state=state,
            workspace_id=workspace_id,
            user_id=user_id,
            integration_type=self.integration_type,
            redirect_uri=self.config.redirect_uri,
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )

        # Generate PKCE parameters if supported
        if self.config.supports_pkce:
            code_verifier = secrets.token_urlsafe(64)
            code_challenge = urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).decode().rstrip("=")
            
            session.code_verifier = code_verifier
            session.code_challenge = code_challenge

        return session

    def get_authorization_url(self, session: OAuth2Session) -> str:
        """Generate OAuth2 authorization URL."""
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": " ".join(self.config.scopes),
            "response_type": "code",
            "state": session.state,
        }

        # Add PKCE parameters if supported
        if self.config.supports_pkce and session.code_challenge:
            params["code_challenge"] = session.code_challenge
            params["code_challenge_method"] = "S256"

        # Add provider-specific parameters
        if self.config.access_type:
            params["access_type"] = self.config.access_type
        
        if self.config.prompt:
            params["prompt"] = self.config.prompt

        # Add any provider-specific parameters
        params.update(self.get_provider_params())

        url = f"{self.config.authorize_url}?{urlencode(params)}"
        logger.info(f"Generated OAuth2 URL for {self.display_name}")
        return url

    async def exchange_code_for_tokens(
        self, authorization_code: str, session: OAuth2Session
    ) -> OAuth2TokenData:
        """Exchange authorization code for access and refresh tokens."""
        try:
            data = {
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "code": authorization_code,
                "grant_type": "authorization_code",
                "redirect_uri": self.config.redirect_uri,
            }

            # Add PKCE verifier if used
            if self.config.supports_pkce and session.code_verifier:
                data["code_verifier"] = session.code_verifier

            # Add any provider-specific token parameters
            data.update(self.get_token_params())

            response = await self.http_client.post(
                self.config.token_url,
                data=data,
                headers=self.get_token_headers(),
            )

            if response.status_code != 200:
                logger.error(f"Token exchange failed for {self.display_name}: {response.text}")
                raise ValueError(f"Failed to exchange authorization code: {response.text}")

            token_data = response.json()
            
            # Process and normalize token data
            return self.process_token_response(token_data)

        except Exception as e:
            logger.error(f"Error exchanging code for {self.display_name}: {e}")
            raise

    async def refresh_access_token(self, refresh_token: str) -> OAuth2TokenData:
        """Refresh an expired access token."""
        try:
            data = {
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }

            response = await self.http_client.post(
                self.config.token_url,
                data=data,
                headers=self.get_token_headers(),
            )

            if response.status_code != 200:
                logger.error(f"Token refresh failed for {self.display_name}: {response.text}")
                raise ValueError(f"Failed to refresh token: {response.text}")

            token_data = response.json()
            return self.process_token_response(token_data)

        except Exception as e:
            logger.error(f"Error refreshing token for {self.display_name}: {e}")
            raise

    async def revoke_token(self, token: str, token_type: str = "access_token") -> bool:
        """Revoke an access or refresh token."""
        if not self.config.revoke_url:
            logger.warning(f"Revoke not supported for {self.display_name}")
            return False

        try:
            data = self.get_revoke_params(token, token_type)
            
            response = await self.http_client.post(
                self.config.revoke_url,
                data=data,
                headers=self.get_token_headers(),
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Error revoking token for {self.display_name}: {e}")
            return False

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Get user information using access token."""
        if not self.config.user_info_url:
            return {}

        try:
            response = await self.http_client.get(
                self.config.user_info_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code != 200:
                logger.error(f"Failed to get user info for {self.display_name}: {response.text}")
                return {}

            return response.json()

        except Exception as e:
            logger.error(f"Error getting user info for {self.display_name}: {e}")
            return {}

    def process_token_response(self, token_data: dict) -> OAuth2TokenData:
        """Process and normalize token response from provider."""
        # Calculate expiry time
        expires_at = None
        if token_data.get("expires_in"):
            expires_at = datetime.now(UTC) + timedelta(seconds=token_data["expires_in"])

        return OAuth2TokenData(
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data.get("expires_in"),
            expires_at=expires_at,
            scope=token_data.get("scope"),
        )

    # Provider-specific methods to override
    def get_provider_params(self) -> dict[str, str]:
        """Get provider-specific authorization parameters."""
        return {}

    def get_token_params(self) -> dict[str, str]:
        """Get provider-specific token exchange parameters."""
        return {}

    def get_token_headers(self) -> dict[str, str]:
        """Get headers for token requests."""
        return {"Content-Type": "application/x-www-form-urlencoded"}

    def get_revoke_params(self, token: str, token_type: str) -> dict[str, str]:
        """Get provider-specific revoke parameters."""
        return {
            "token": token,
            "token_type_hint": token_type,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close HTTP client."""
        await self.http_client.aclose()