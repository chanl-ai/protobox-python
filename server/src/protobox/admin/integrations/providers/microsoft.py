"""Microsoft OAuth2 provider implementation."""

import logging
from typing import Any

from ...models.integration import IntegrationType
from ..base import BaseOAuth2Provider

logger = logging.getLogger(__name__)


class MicrosoftOAuth2Provider(BaseOAuth2Provider):
    """Microsoft OAuth2 provider for Office 365 integration."""

    @property
    def integration_type(self) -> IntegrationType:
        """Return the integration type."""
        # This will need to be added to IntegrationType enum
        return IntegrationType.MICROSOFT_365 if hasattr(IntegrationType, "MICROSOFT_365") else IntegrationType.GOOGLE_CALENDAR

    @property  
    def display_name(self) -> str:
        """Return the display name."""
        return "Microsoft 365"

    @property
    def supported_features(self) -> list[str]:
        """Return supported features."""
        return [
            "outlook_calendar",
            "outlook_mail",
            "teams_messaging",
            "onedrive_files",
            "sharepoint_access",
            "user_profile",
            "contacts",
        ]

    def get_provider_params(self) -> dict[str, str]:
        """Get Microsoft-specific authorization parameters."""
        return {
            "response_mode": "query",
            "prompt": "consent",
        }

    async def get_user_profile(self, access_token: str) -> dict[str, Any]:
        """Get user profile from Microsoft Graph."""
        try:
            response = await self.http_client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code == 200:
                return response.json()
            
            logger.error(f"Failed to get user profile: {response.text}")
            return {}
            
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return {}

    async def list_calendars(self, access_token: str) -> list[dict]:
        """List user's calendars."""
        try:
            response = await self.http_client.get(
                "https://graph.microsoft.com/v1.0/me/calendars",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("value", [])
            
            logger.error(f"Failed to list calendars: {response.text}")
            return []
            
        except Exception as e:
            logger.error(f"Error listing calendars: {e}")
            return []

    async def create_calendar_event(
        self,
        access_token: str,
        calendar_id: str | None,
        event_data: dict,
    ) -> dict | None:
        """Create a calendar event in Outlook."""
        try:
            # Use default calendar if no ID specified
            url = "https://graph.microsoft.com/v1.0/me/events"
            if calendar_id:
                url = f"https://graph.microsoft.com/v1.0/me/calendars/{calendar_id}/events"
            
            response = await self.http_client.post(
                url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=event_data,
            )
            
            if response.status_code in (200, 201):
                return response.json()
            
            logger.error(f"Failed to create event: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return None

    async def send_mail(
        self,
        access_token: str,
        message_data: dict,
        save_to_sent: bool = True,
    ) -> bool:
        """Send an email via Outlook."""
        try:
            payload = {
                "message": message_data,
                "saveToSentItems": save_to_sent,
            }
            
            response = await self.http_client.post(
                "https://graph.microsoft.com/v1.0/me/sendMail",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            
            return response.status_code == 202
            
        except Exception as e:
            logger.error(f"Error sending mail: {e}")
            return False

    async def list_teams(self, access_token: str) -> list[dict]:
        """List user's Microsoft Teams."""
        try:
            response = await self.http_client.get(
                "https://graph.microsoft.com/v1.0/me/joinedTeams",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("value", [])
            
            logger.error(f"Failed to list teams: {response.text}")
            return []
            
        except Exception as e:
            logger.error(f"Error listing teams: {e}")
            return []

    async def send_teams_message(
        self,
        access_token: str,
        team_id: str,
        channel_id: str,
        message_content: str,
    ) -> dict | None:
        """Send a message to a Teams channel."""
        try:
            response = await self.http_client.post(
                f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "body": {
                        "content": message_content,
                    }
                },
            )
            
            if response.status_code in (200, 201):
                return response.json()
            
            logger.error(f"Failed to send Teams message: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"Error sending Teams message: {e}")
            return None

    async def list_onedrive_files(
        self,
        access_token: str,
        folder_path: str = "/",
    ) -> list[dict]:
        """List files in OneDrive."""
        try:
            # Encode the folder path properly
            if folder_path == "/":
                url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
            else:
                url = f"https://graph.microsoft.com/v1.0/me/drive/root:{folder_path}:/children"
            
            response = await self.http_client.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("value", [])
            
            logger.error(f"Failed to list OneDrive files: {response.text}")
            return []
            
        except Exception as e:
            logger.error(f"Error listing OneDrive files: {e}")
            return []