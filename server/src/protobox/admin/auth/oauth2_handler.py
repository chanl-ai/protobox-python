"""OAuth2 authentication handler for integrations."""

import json
import os
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
from loguru import logger

from ..models.integration import IntegrationType, OAuth2TokenData


class OAuth2Handler:
    """Handles OAuth2 flows for various integrations."""

    def __init__(self):
        # OAuth2 configurations for different services
        base_url = os.getenv('MCP_SERVER_URL', 'http://localhost:8090')
        self.configs = {
            IntegrationType.GOOGLE_CALENDAR: {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "scopes": [
                    "https://www.googleapis.com/auth/calendar",
                    "https://www.googleapis.com/auth/calendar.readonly",
                ],
                # IMPORTANT: This redirect URI path MUST match what's registered in Google Cloud Console
                # Current registered URI: http://localhost:8090/admin/api/v1/integrations/oauth/callback/google
                # For all google integrations, the redirect URI is the same
                # DO NOT CHANGE without updating Google Cloud Console configuration
                "redirect_uri": f"{base_url}/admin/api/v1/integrations/oauth/callback/google",
            },
            IntegrationType.GMAIL: {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),  # Same as Google Calendar
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),  # Same as Google Calendar
                "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "scopes": [
                    "https://www.googleapis.com/auth/gmail.send",
                    "https://www.googleapis.com/auth/gmail.readonly",
                    "https://www.googleapis.com/auth/gmail.compose",
                    "https://www.googleapis.com/auth/gmail.modify",
                ],
                "redirect_uri": f"{base_url}/admin/api/v1/integrations/oauth/callback/google",
            },
            IntegrationType.GOOGLE_DRIVE: {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "scopes": [
                    "https://www.googleapis.com/auth/drive",
                    "https://www.googleapis.com/auth/drive.readonly",
                    "https://www.googleapis.com/auth/drive.metadata",
                    "https://www.googleapis.com/auth/drive.metadata.readonly",
                ],
                "redirect_uri": f"{base_url}/admin/api/v1/integrations/oauth/callback/google",
            },
            IntegrationType.GOOGLE_SHEETS: {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "scopes": [
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/spreadsheets.readonly",
                ],
                "redirect_uri": f"{base_url}/admin/api/v1/integrations/oauth/callback/google",
            },
            IntegrationType.GOOGLE_DOCS: {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "scopes": [
                    "https://www.googleapis.com/auth/documents",
                    "https://www.googleapis.com/auth/documents.readonly",
                ],
                "redirect_uri": f"{base_url}/admin/api/v1/integrations/oauth/callback/google",
            },
            IntegrationType.GOOGLE_ANALYTICS: {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "scopes": [
                    "https://www.googleapis.com/auth/analytics",
                    "https://www.googleapis.com/auth/analytics.readonly",
                ],
                "redirect_uri": f"{base_url}/admin/api/v1/integrations/oauth/callback/google",
            },
            IntegrationType.GOOGLE_ADS: {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "scopes": [
                    "https://www.googleapis.com/auth/adsense",
                    "https://www.googleapis.com/auth/adsense.readonly",
                ],
                "redirect_uri": f"{base_url}/admin/api/v1/integrations/oauth/callback/google",
            },
            IntegrationType.GITHUB: {
                "client_id": os.getenv("GITHUB_CLIENT_ID"),
                "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
                "authorize_url": "https://github.com/login/oauth/authorize",
                "token_url": "https://github.com/login/oauth/access_token",
                "scopes": [
                    "repo",
                    "user",
                    "read:org",
                    "workflow",
                    "issues:write",
                    "pull_requests:write",
                ],
                "redirect_uri": f"{base_url}/admin/api/v1/integrations/oauth/callback/github",
            },
            IntegrationType.SLACK: {
                "client_id": os.getenv("SLACK_CLIENT_ID"),
                "client_secret": os.getenv("SLACK_CLIENT_SECRET"),
                "authorize_url": "https://slack.com/oauth/v2/authorize",
                "token_url": "https://slack.com/api/oauth.v2.access",
                "scopes": [
                    "chat:write",
                    "channels:manage",
                    "channels:read",
                    "users:read",
                    "users:read.email",
                ],
                "redirect_uri": f"{base_url}/admin/api/v1/integrations/oauth/callback/slack",
            },
            IntegrationType.HUBSPOT: {
                "client_id": os.getenv("HUBSPOT_CLIENT_ID"),
                "client_secret": os.getenv("HUBSPOT_CLIENT_SECRET"),
                "authorize_url": "https://app.hubspot.com/oauth/authorize",
                "token_url": "https://api.hubapi.com/oauth/v1/token",
                "scopes": [
                    "oauth",
                    "crm.objects.contacts.read",
                    "crm.objects.contacts.write",
                    "crm.objects.companies.read",
                    "crm.objects.companies.write",
                    "crm.objects.deals.read",
                    "crm.objects.deals.write"
                ],
                "redirect_uri": f"{base_url}/admin/api/v1/integrations/oauth/callback/hubspot",
            },
        }

    def get_authorization_url(
        self, integration_type: IntegrationType, workspace_id: str, user_id: str
    ) -> str:
        """Generate OAuth2 authorization URL."""

        config = self.configs.get(integration_type)
        if not config:
            raise ValueError(f"OAuth2 not configured for {integration_type.value}")

        if not config["client_id"] or not config["client_secret"]:
            raise ValueError(f"OAuth2 credentials not configured for {integration_type.value}")

        # Generate state parameter for security
        state = self._generate_state(workspace_id, user_id, integration_type)

        params = {
            "client_id": config["client_id"],
            "redirect_uri": config["redirect_uri"],
            "scope": " ".join(config["scopes"]),
            "response_type": "code",
            "access_type": "offline",  # For Google, to get refresh token
            "prompt": "consent",  # Force consent to get refresh token
            "state": state,
        }

        url = f"{config['authorize_url']}?{urlencode(params)}"
        logger.info(f"Generated OAuth2 URL for {integration_type}")
        return url

    async def exchange_code_for_tokens(
        self, integration_type: IntegrationType, authorization_code: str
    ) -> OAuth2TokenData:
        """Exchange authorization code for access and refresh tokens."""

        config = self.configs.get(integration_type)
        if not config:
            raise ValueError(f"OAuth2 not configured for {integration_type}")

        try:
            async with httpx.AsyncClient() as client:
                data = {
                    "client_id": config["client_id"],
                    "client_secret": config["client_secret"],
                    "code": authorization_code,
                    "grant_type": "authorization_code",
                    "redirect_uri": config["redirect_uri"],
                }

                response = await client.post(
                    config["token_url"],
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    logger.error(f"OAuth2 token exchange failed: {response.text}")
                    raise ValueError(f"Failed to exchange authorization code: {response.text}")

                # Dynamically detect and parse response format based on Content-Type header
                content_type = response.headers.get('content-type', '').lower()
                
                if 'application/x-www-form-urlencoded' in content_type or 'text/plain' in content_type:
                    # Parse URL-encoded form data (common for OAuth2 token endpoints)
                    try:
                        from urllib.parse import parse_qs
                        parsed_data = parse_qs(response.text)
                        token_data = {key: value[0] if value else None for key, value in parsed_data.items()}
                        logger.info(f"Parsed URL-encoded OAuth response for {integration_type}: {token_data}")
                    except Exception as e:
                        logger.error(f"Failed to parse URL-encoded response: {e}")
                        logger.error(f"Response content: {response.text}")
                        raise ValueError(f"Invalid URL-encoded response: {response.text}")
                        
                elif 'application/json' in content_type:
                    # Parse JSON response
                    try:
                        token_data = response.json()
                        logger.info(f"Parsed JSON OAuth response for {integration_type}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON response: {e}")
                        logger.error(f"Response content: {response.text}")
                        raise ValueError(f"Invalid JSON response: {response.text}")
                        
                else:
                    # Try JSON first, then fallback to URL-encoded if that fails
                    try:
                        token_data = response.json()
                        logger.info(f"Parsed JSON OAuth response for {integration_type} (auto-detected)")
                    except json.JSONDecodeError:
                        try:
                            from urllib.parse import parse_qs
                            parsed_data = parse_qs(response.text)
                            token_data = {key: value[0] if value else None for key, value in parsed_data.items()}
                            logger.info(f"Parsed URL-encoded OAuth response for {integration_type} (fallback)")
                        except Exception as e:
                            logger.error(f"Failed to parse response in any format: {e}")
                            logger.error(f"Response content: {response.text}")
                            logger.error(f"Content-Type: {content_type}")
                            raise ValueError(f"Unable to parse OAuth response in any supported format: {response.text}")

                # Calculate expiry time
                expires_at = None
                if token_data.get("expires_in"):
                    expires_at = datetime.now(UTC) + timedelta(
                        seconds=token_data["expires_in"]
                    )

                oauth_data = OAuth2TokenData(
                    access_token=token_data["access_token"],
                    refresh_token=token_data.get("refresh_token"),
                    token_type=token_data.get("token_type", "Bearer"),
                    expires_in=token_data.get("expires_in"),
                    expires_at=expires_at,
                    scope=token_data.get("scope"),
                )

                logger.info(f"Successfully exchanged OAuth2 code for {integration_type}")
                return oauth_data

        except Exception as e:
            logger.error(f"Error exchanging OAuth2 code: {e}")
            raise

    async def refresh_access_token(
        self, integration_type: IntegrationType, refresh_token: str
    ) -> OAuth2TokenData:
        """Refresh an expired access token using refresh token."""

        config = self.configs.get(integration_type)
        if not config:
            raise ValueError(f"OAuth2 not configured for {integration_type}")

        try:
            async with httpx.AsyncClient() as client:
                data = {
                    "client_id": config["client_id"],
                    "client_secret": config["client_secret"],
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                }

                response = await client.post(
                    config["token_url"],
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    logger.error(f"OAuth2 token refresh failed: {response.text}")
                    raise ValueError(f"Failed to refresh token: {response.text}")

                token_data = response.json()

                # Calculate expiry time
                expires_at = None
                if token_data.get("expires_in"):
                    expires_at = datetime.now(UTC) + timedelta(
                        seconds=token_data["expires_in"]
                    )

                oauth_data = OAuth2TokenData(
                    access_token=token_data["access_token"],
                    refresh_token=refresh_token,  # Keep original refresh token
                    token_type=token_data.get("token_type", "Bearer"),
                    expires_in=token_data.get("expires_in"),
                    expires_at=expires_at,
                    scope=token_data.get("scope"),
                )

                logger.info(f"Successfully refreshed OAuth2 token for {integration_type}")
                return oauth_data

        except Exception as e:
            logger.error(f"Error refreshing OAuth2 token: {e}")
            raise

    def parse_state_parameter(self, state: str) -> dict[str, str]:
        """Parse the state parameter to extract workspace_id, user_id, and integration_type."""

        try:
            # State format: workspace_id:user_id:integration_type:random
            parts = state.split(":")
            if len(parts) != 4:
                raise ValueError("Invalid state parameter format")

            return {
                "workspace_id": parts[0],
                "user_id": parts[1],
                "integration_type": parts[2],
                "random": parts[3],
            }

        except Exception as e:
            logger.error(f"Error parsing state parameter: {e}")
            raise ValueError("Invalid state parameter")

    def _generate_state(
        self, workspace_id: str, user_id: str, integration_type: IntegrationType
    ) -> str:
        """Generate a secure state parameter for OAuth2 flow."""

        # Generate random component for security
        random_part = secrets.token_urlsafe(16)

        # Combine with workspace/user info for callback processing
        return f"{workspace_id}:{user_id}:{integration_type.value}:{random_part}"


    async def validate_token(
        self, integration_type: IntegrationType, oauth_data: OAuth2TokenData
    ) -> bool:
        """Validate that an OAuth2 token is still valid."""

        try:
            # Check if token is expired
            if oauth_data.expires_at and oauth_data.expires_at <= datetime.now(UTC):
                return False

            # For Google Calendar, make a simple API call to validate
            if integration_type == IntegrationType.GOOGLE_CALENDAR:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://www.googleapis.com/calendar/v3/users/me/calendarList",
                        headers={"Authorization": f"Bearer {oauth_data.access_token}"},
                    )
                    return response.status_code == 200

            return True

        except Exception as e:
            logger.error(f"Error validating OAuth2 token: {e}")
            return False
