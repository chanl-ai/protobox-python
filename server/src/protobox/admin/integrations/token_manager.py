"""Token management system for OAuth2 integrations."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from ..models.integration import IntegrationType, OAuth2TokenData
from ..services.secret_service import SecretService
from .registry import get_provider_registry

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages OAuth2 tokens with auto-refresh capabilities."""

    def __init__(self, secret_service: SecretService):
        self.secret_service = secret_service
        self.provider_registry = get_provider_registry()
        self._token_cache: dict[str, OAuth2TokenData] = {}

    def _get_cache_key(self, workspace_id: str, integration_type: IntegrationType) -> str:
        """Generate cache key for token storage."""
        return f"{workspace_id}:{integration_type.value}"

    async def get_valid_token(
        self,
        workspace_id: str,
        integration_type: IntegrationType,
        force_refresh: bool = False,
    ) -> OAuth2TokenData | None:
        """Get a valid access token, refreshing if necessary."""
        try:
            cache_key = self._get_cache_key(workspace_id, integration_type)
            
            # Check cache first
            if not force_refresh and cache_key in self._token_cache:
                cached_token = self._token_cache[cache_key]
                if self._is_token_valid(cached_token):
                    logger.debug(f"Using cached token for {integration_type}")
                    return cached_token

            # Get token from storage
            token_data = await self._get_stored_token(workspace_id, integration_type)
            if not token_data:
                logger.warning(f"No token found for {integration_type} in workspace {workspace_id}")
                return None

            # Check if token needs refresh
            if force_refresh or not self._is_token_valid(token_data):
                logger.info(f"Token expired or force refresh for {integration_type}, refreshing...")
                token_data = await self._refresh_token(workspace_id, integration_type, token_data)
                if not token_data:
                    return None

            # Update cache
            self._token_cache[cache_key] = token_data
            return token_data

        except Exception as e:
            logger.error(f"Error getting valid token for {integration_type}: {e}")
            return None

    async def store_token(
        self,
        workspace_id: str,
        integration_type: IntegrationType,
        token_data: OAuth2TokenData,
    ) -> bool:
        """Store OAuth2 token securely."""
        try:
            # Store in secret service
            clean_integration_type = str(integration_type).replace("IntegrationType.", "").lower()
            secret_name = f"{clean_integration_type}_oauth_token"
            
            # Check if secret exists
            existing_secret = await self.secret_service.get_secret_by_name(workspace_id, secret_name)
            
            if existing_secret:
                # Update existing secret
                from ..models.secret import SecretUpdateRequest
                
                update_request = SecretUpdateRequest(secret_value=token_data.model_dump_json())
                await self.secret_service.update_secret(existing_secret.id, update_request, "system")
            else:
                # Create new secret
                from ..models.secret import SecretCreateRequest, SecretType
                
                secret_request = SecretCreateRequest(
                    workspace_id=workspace_id,
                    name=secret_name,
                    description=f"OAuth2 token for {integration_type} integration",
                    secret_type=SecretType.OAUTH_TOKEN,
                    secret_value=token_data.model_dump_json(),
                    tags=[str(integration_type), "oauth2", "integration"],
                )
                await self.secret_service.create_secret(secret_request, "system")

            # Update cache
            cache_key = self._get_cache_key(workspace_id, integration_type)
            self._token_cache[cache_key] = token_data
            
            logger.info(f"Stored token for {integration_type} in workspace {workspace_id}")
            return True

        except Exception as e:
            logger.error(f"Error storing token for {integration_type}: {e}")
            return False

    async def revoke_token(
        self,
        workspace_id: str,
        integration_type: IntegrationType,
    ) -> bool:
        """Revoke OAuth2 token with the provider."""
        try:
            # Get token
            token_data = await self._get_stored_token(workspace_id, integration_type)
            if not token_data:
                logger.warning(f"No token to revoke for {integration_type}")
                return True

            # Get provider
            provider = self.provider_registry.get_provider(integration_type)
            if not provider:
                logger.error(f"Provider not found for {integration_type}")
                return False

            # Revoke with provider
            success = await provider.revoke_token(token_data.access_token)
            
            if success:
                # Delete from storage
                clean_integration_type = str(integration_type).replace("IntegrationType.", "").lower()
                secret_name = f"{clean_integration_type}_oauth_token"
                
                secret = await self.secret_service.get_secret_by_name(workspace_id, secret_name)
                if secret:
                    await self.secret_service.delete_secret(workspace_id, secret.id)

                # Clear cache
                cache_key = self._get_cache_key(workspace_id, integration_type)
                self._token_cache.pop(cache_key, None)
                
                logger.info(f"Revoked token for {integration_type} in workspace {workspace_id}")

            return success

        except Exception as e:
            logger.error(f"Error revoking token for {integration_type}: {e}")
            return False

    async def _get_stored_token(
        self,
        workspace_id: str,
        integration_type: IntegrationType,
    ) -> OAuth2TokenData | None:
        """Get token from secure storage."""
        try:
            clean_integration_type = str(integration_type).replace("IntegrationType.", "").lower()
            secret_name = f"{clean_integration_type}_oauth_token"
            
            secret = await self.secret_service.get_secret_by_name(workspace_id, secret_name)
            if not secret:
                return None

            # Decrypt and parse
            decrypted_value = await self.secret_service.decrypt_secret_value(secret)
            return OAuth2TokenData.model_validate_json(decrypted_value)

        except Exception as e:
            logger.error(f"Error getting stored token: {e}")
            return None

    async def _refresh_token(
        self,
        workspace_id: str,
        integration_type: IntegrationType,
        token_data: OAuth2TokenData,
    ) -> OAuth2TokenData | None:
        """Refresh an expired token."""
        try:
            # Check if we have a refresh token
            if not token_data.refresh_token:
                logger.warning(f"No refresh token available for {integration_type}")
                return None

            # Get provider
            provider = self.provider_registry.get_provider(integration_type)
            if not provider:
                logger.error(f"Provider not found for {integration_type}")
                return None

            # Refresh token
            new_token_data = await provider.refresh_access_token(token_data.refresh_token)
            
            # Store new token
            if new_token_data:
                # Preserve refresh token if not provided in response
                if not new_token_data.refresh_token and token_data.refresh_token:
                    new_token_data.refresh_token = token_data.refresh_token
                
                await self.store_token(workspace_id, integration_type, new_token_data)
                logger.info(f"Successfully refreshed token for {integration_type}")
                return new_token_data

            return None

        except Exception as e:
            logger.error(f"Error refreshing token for {integration_type}: {e}")
            return None

    def _is_token_valid(self, token_data: OAuth2TokenData) -> bool:
        """Check if token is still valid."""
        if not token_data.expires_at:
            # If no expiry, assume valid for providers that don't expire tokens
            return True
        
        # Add 5 minute buffer before expiry
        buffer = timedelta(minutes=5)
        return datetime.now(UTC) < (token_data.expires_at - buffer)

    def clear_cache(self, workspace_id: str | None = None) -> None:
        """Clear token cache."""
        if workspace_id:
            # Clear specific workspace
            keys_to_remove = [
                key for key in self._token_cache.keys()
                if key.startswith(f"{workspace_id}:")
            ]
            for key in keys_to_remove:
                del self._token_cache[key]
        else:
            # Clear all
            self._token_cache.clear()

    async def get_token_info(
        self,
        workspace_id: str,
        integration_type: IntegrationType,
    ) -> dict[str, Any] | None:
        """Get information about a stored token."""
        try:
            token_data = await self._get_stored_token(workspace_id, integration_type)
            if not token_data:
                return None

            return {
                "has_refresh_token": bool(token_data.refresh_token),
                "expires_at": token_data.expires_at.isoformat() if token_data.expires_at else None,
                "is_valid": self._is_token_valid(token_data),
                "scopes": token_data.scope.split(" ") if token_data.scope else [],
                "token_type": token_data.token_type,
            }

        except Exception as e:
            logger.error(f"Error getting token info: {e}")
            return None