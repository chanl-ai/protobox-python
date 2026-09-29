"""LinkedIn OAuth2 provider implementation."""

import logging
from typing import Any

from ...models.integration import IntegrationType
from ..base import BaseOAuth2Provider

logger = logging.getLogger(__name__)


class LinkedInOAuth2Provider(BaseOAuth2Provider):
    """LinkedIn OAuth2 provider for professional networking."""

    @property
    def integration_type(self) -> IntegrationType:
        """Return the integration type."""
        return IntegrationType.LINKEDIN

    @property
    def display_name(self) -> str:
        """Return the display name."""
        return "LinkedIn"

    @property
    def supported_features(self) -> list[str]:
        """Return supported features."""
        return [
            "profile_access",
            "connection_management",
            "messaging",
            "post_sharing",
            "company_pages",
            "lead_generation",
            "analytics",
        ]

    def get_provider_params(self) -> dict[str, str]:
        """Get LinkedIn-specific authorization parameters."""
        return {
            # LinkedIn uses different parameter names
            "response_type": "code",
        }

    async def get_user_profile(self, access_token: str) -> dict[str, Any]:
        """Get LinkedIn user profile."""
        try:
            response = await self.http_client.get(
                "https://api.linkedin.com/v2/me",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Restli-Protocol-Version": "2.0.0",
                },
            )
            
            if response.status_code == 200:
                return response.json()
            
            logger.error(f"Failed to get profile: {response.text}")
            return {}
            
        except Exception as e:
            logger.error(f"Error getting profile: {e}")
            return {}

    async def get_email_address(self, access_token: str) -> str | None:
        """Get user's primary email address."""
        try:
            response = await self.http_client.get(
                "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Restli-Protocol-Version": "2.0.0",
                },
            )
            
            if response.status_code == 200:
                data = response.json()
                elements = data.get("elements", [])
                if elements:
                    return elements[0].get("handle~", {}).get("emailAddress")
            
            logger.error(f"Failed to get email: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting email: {e}")
            return None

    async def share_post(
        self,
        access_token: str,
        author_urn: str,
        text: str,
        visibility: str = "PUBLIC",
    ) -> dict | None:
        """Share a post on LinkedIn."""
        try:
            post_data = {
                "author": author_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": text
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": visibility
                }
            }
            
            response = await self.http_client.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "X-Restli-Protocol-Version": "2.0.0",
                },
                json=post_data,
            )
            
            if response.status_code == 201:
                return response.json()
            
            logger.error(f"Failed to share post: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"Error sharing post: {e}")
            return None

    async def send_message(
        self,
        access_token: str,
        recipient_urn: str,
        subject: str,
        body: str,
    ) -> dict | None:
        """Send a message to a LinkedIn connection."""
        try:
            message_data = {
                "recipients": [recipient_urn],
                "subject": subject,
                "body": body,
                "messageType": "MEMBER_TO_MEMBER"
            }
            
            response = await self.http_client.post(
                "https://api.linkedin.com/v2/messages",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "X-Restli-Protocol-Version": "2.0.0",
                },
                json=message_data,
            )
            
            if response.status_code == 201:
                return response.json()
            
            logger.error(f"Failed to send message: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return None

    async def get_connections(
        self,
        access_token: str,
        start: int = 0,
        count: int = 50,
    ) -> list[dict]:
        """Get user's LinkedIn connections."""
        try:
            response = await self.http_client.get(
                "https://api.linkedin.com/v2/connections",
                params={
                    "q": "viewer",
                    "start": start,
                    "count": count,
                },
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Restli-Protocol-Version": "2.0.0",
                },
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("elements", [])
            
            logger.error(f"Failed to get connections: {response.text}")
            return []
            
        except Exception as e:
            logger.error(f"Error getting connections: {e}")
            return []

    async def get_company_updates(
        self,
        access_token: str,
        company_id: str,
        start: int = 0,
        count: int = 10,
    ) -> list[dict]:
        """Get updates from a company page."""
        try:
            response = await self.http_client.get(
                f"https://api.linkedin.com/v2/organizationalEntityShareStatistics",
                params={
                    "q": "organizationalEntity",
                    "organizationalEntity": f"urn:li:organization:{company_id}",
                    "start": start,
                    "count": count,
                },
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Restli-Protocol-Version": "2.0.0",
                },
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("elements", [])
            
            logger.error(f"Failed to get company updates: {response.text}")
            return []
            
        except Exception as e:
            logger.error(f"Error getting company updates: {e}")
            return []