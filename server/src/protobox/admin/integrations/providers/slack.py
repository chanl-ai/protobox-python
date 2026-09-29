"""Slack OAuth2 provider implementation."""

import logging
from typing import Any

from ...models.integration import IntegrationType
from ..base import BaseOAuth2Provider

logger = logging.getLogger(__name__)


class SlackOAuth2Provider(BaseOAuth2Provider):
    """Slack OAuth2 provider for workspace integration."""

    @property
    def integration_type(self) -> IntegrationType:
        """Return the integration type."""
        return IntegrationType.SLACK

    @property
    def display_name(self) -> str:
        """Return the display name."""
        return "Slack"

    @property
    def supported_features(self) -> list[str]:
        """Return supported features."""
        return [
            "channel_messaging",
            "direct_messaging",
            "file_sharing",
            "slash_commands",
            "event_subscriptions",
            "user_presence",
            "workspace_info",
        ]

    def get_token_headers(self) -> dict[str, str]:
        """Slack uses different headers for token exchange."""
        return {
            "Content-Type": "application/x-www-form-urlencoded",
        }

    def process_token_response(self, token_data: dict) -> dict:
        """Process Slack-specific token response."""
        # Slack returns data in a different format
        from datetime import UTC, datetime, timedelta
        
        from ...models.integration import OAuth2TokenData
        
        # Slack doesn't provide expires_in, tokens are valid until revoked
        # We'll set a default expiry of 12 hours for caching purposes
        expires_at = datetime.now(UTC) + timedelta(hours=12)
        
        # Extract the access token from Slack's response format
        if token_data.get("ok"):
            access_token = token_data.get("access_token", "")
            # For bot tokens, Slack returns it in a different field
            if not access_token and token_data.get("authed_user"):
                access_token = token_data["authed_user"].get("access_token", "")
        else:
            error = token_data.get("error", "Unknown error")
            raise ValueError(f"Slack OAuth failed: {error}")
        
        return OAuth2TokenData(
            access_token=access_token,
            refresh_token=None,  # Slack doesn't use refresh tokens
            token_type="Bearer",
            expires_in=43200,  # 12 hours in seconds
            expires_at=expires_at,
            scope=token_data.get("scope", ""),
        )

    async def get_workspace_info(self, access_token: str) -> dict[str, Any]:
        """Get Slack workspace information."""
        try:
            response = await self.http_client.get(
                "https://slack.com/api/team.info",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    return data.get("team", {})
                else:
                    logger.error(f"Slack API error: {data.get('error')}")
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting workspace info: {e}")
            return {}

    async def list_channels(self, access_token: str) -> list[dict]:
        """List all channels in the workspace."""
        try:
            response = await self.http_client.get(
                "https://slack.com/api/conversations.list",
                params={
                    "types": "public_channel,private_channel",
                    "exclude_archived": "true",
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    return data.get("channels", [])
                else:
                    logger.error(f"Slack API error: {data.get('error')}")
            
            return []
            
        except Exception as e:
            logger.error(f"Error listing channels: {e}")
            return []

    async def send_message(
        self,
        access_token: str,
        channel: str,
        text: str,
        blocks: list[dict] | None = None,
    ) -> dict | None:
        """Send a message to a Slack channel."""
        try:
            payload = {
                "channel": channel,
                "text": text,
            }
            
            if blocks:
                payload["blocks"] = blocks
            
            response = await self.http_client.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    return data
                else:
                    logger.error(f"Slack API error: {data.get('error')}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return None

    async def upload_file(
        self,
        access_token: str,
        channels: list[str],
        file_content: bytes,
        filename: str,
        title: str | None = None,
    ) -> dict | None:
        """Upload a file to Slack."""
        try:
            files = {"file": (filename, file_content)}
            data = {
                "channels": ",".join(channels),
                "filename": filename,
            }
            
            if title:
                data["title"] = title
            
            response = await self.http_client.post(
                "https://slack.com/api/files.upload",
                headers={"Authorization": f"Bearer {access_token}"},
                data=data,
                files=files,
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    return data.get("file")
                else:
                    logger.error(f"Slack API error: {data.get('error')}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return None

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Get authenticated user information."""
        try:
            response = await self.http_client.get(
                "https://slack.com/api/users.identity",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    return data.get("user", {})
                else:
                    logger.error(f"Slack API error: {data.get('error')}")
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return {}