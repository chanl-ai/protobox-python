"""Google OAuth2 provider implementation."""

import logging

from ...models.integration import IntegrationType
from ..base import BaseOAuth2Provider

logger = logging.getLogger(__name__)


class GoogleOAuth2Provider(BaseOAuth2Provider):
    """Google OAuth2 provider for Calendar and Gmail."""

    @property
    def integration_type(self) -> IntegrationType:
        """Return the integration type."""
        return IntegrationType.GOOGLE_CALENDAR

    @property
    def display_name(self) -> str:
        """Return the display name."""
        return "Google Workspace"

    @property
    def supported_features(self) -> list[str]:
        """Return supported features."""
        return [
            "calendar_events",
            "calendar_availability",
            "email_send",
            "email_read",
            "contacts",
            "drive_files",
        ]

    def get_provider_params(self) -> dict[str, str]:
        """Get Google-specific authorization parameters."""
        return {
            "access_type": "offline",  # Get refresh token
            "prompt": "consent",  # Force consent to get refresh token
            "include_granted_scopes": "true",  # Incremental auth
        }

    async def get_calendar_list(self, access_token: str) -> list[dict]:
        """Get list of user's calendars."""
        try:
            response = await self.http_client.get(
                "https://www.googleapis.com/calendar/v3/users/me/calendarList",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("items", [])
            
            logger.error(f"Failed to get calendar list: {response.text}")
            return []
            
        except Exception as e:
            logger.error(f"Error getting calendar list: {e}")
            return []

    async def create_calendar_event(
        self, access_token: str, calendar_id: str, event_data: dict
    ) -> dict | None:
        """Create a calendar event."""
        try:
            response = await self.http_client.post(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=event_data,
            )
            
            if response.status_code == 200:
                return response.json()
            
            logger.error(f"Failed to create calendar event: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return None

    async def check_calendar_availability(
        self,
        access_token: str,
        calendar_id: str,
        time_min: str,
        time_max: str,
    ) -> list[dict]:
        """Check calendar availability for a time range."""
        try:
            response = await self.http_client.get(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                params={
                    "timeMin": time_min,
                    "timeMax": time_max,
                    "singleEvents": "true",
                    "orderBy": "startTime",
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("items", [])
            
            logger.error(f"Failed to check availability: {response.text}")
            return []
            
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return []

    async def send_email(
        self, access_token: str, email_data: dict
    ) -> dict | None:
        """Send an email via Gmail API."""
        try:
            # Note: This would require additional setup for Gmail API
            # and proper email formatting (MIME message)
            logger.warning("Gmail send not fully implemented yet")
            return None
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return None