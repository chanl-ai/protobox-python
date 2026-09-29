"""Base class for all Google service integrations."""

from typing import Any
import httpx
from loguru import logger

from ..models.integration import IntegrationType, IntegrationStatus, OAuth2TokenData
from ..config import settings
from .base_classes import OAuth2Integration


class GoogleOAuth2Integration(OAuth2Integration):
    """Base class for all Google OAuth2 integrations.
    
    All Google services use the same OAuth2 endpoints and refresh mechanism.
    Each service only needs to define its specific scopes.
    """
    
    # Google OAuth2 endpoints (same for all Google services)
    oauth_authorize_url = "https://accounts.google.com/o/oauth2/v2/auth"
    oauth_token_url = "https://oauth2.googleapis.com/token"
    
    # Common Google OAuth parameters
    oauth_access_type = "offline"  # To get refresh token
    oauth_prompt = "consent"  # Force consent to get refresh token
    oauth_include_granted_scopes = "true"  # Incremental authorization
    
    def get_oauth_url(self, state: str) -> str:
        """Generate OAuth authorization URL with Google-specific parameters."""
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": self.get_redirect_uri(),
            "response_type": "code",
            "scope": " ".join(self.oauth_scopes),
            "state": state,
            "access_type": self.oauth_access_type,
            "prompt": self.oauth_prompt,
            "include_granted_scopes": self.oauth_include_granted_scopes,
        }
        
        # Build URL with parameters
        return f"{self.oauth_authorize_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    
    async def exchange_code_for_token(self, code: str) -> OAuth2TokenData:
        """Exchange authorization code for access token (same for all Google services)."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.oauth_token_url,
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": self.get_redirect_uri(),
                    "grant_type": "authorization_code",
                }
            )
            
            if response.status_code != 200:
                raise ValueError(f"Failed to exchange code: {response.text}")
            
            data = response.json()
            return OAuth2TokenData(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token"),
                token_type=data.get("token_type", "Bearer"),
                expires_in=data.get("expires_in"),
                scope=data.get("scope"),
            )
    
    async def refresh_token(self, refresh_token: str) -> OAuth2TokenData:
        """Refresh access token using refresh token (same for all Google services)."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.oauth_token_url,
                data={
                    "refresh_token": refresh_token,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "grant_type": "refresh_token",
                }
            )
            
            if response.status_code != 200:
                raise ValueError(f"Failed to refresh token: {response.text}")
            
            data = response.json()
            return OAuth2TokenData(
                access_token=data["access_token"],
                refresh_token=refresh_token,  # Google doesn't return new refresh token
                token_type=data.get("token_type", "Bearer"),
                expires_in=data.get("expires_in"),
                scope=data.get("scope"),
            )
    
    async def test_connection(self, access_token: str) -> tuple[bool, str | None]:
        """Test connection using Google's tokeninfo endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://oauth2.googleapis.com/tokeninfo?access_token={access_token}"
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Check if token has required scopes
                    token_scopes = data.get("scope", "").split()
                    required_scopes = set(self.oauth_scopes)
                    if required_scopes.issubset(set(token_scopes)):
                        return True, None
                    else:
                        missing = required_scopes - set(token_scopes)
                        return False, f"Missing required scopes: {', '.join(missing)}"
                else:
                    return False, f"Invalid token: {response.text}"
        except Exception as e:
            return False, str(e)
    
    def get_redirect_uri(self) -> str:
        """Get the redirect URI for this integration."""
        base_url = settings.mcp_server_url or "http://localhost:8090"
        # All Google services can use the same redirect URI with different state
        return f"{base_url}/admin/api/v1/integrations/oauth/callback/google"