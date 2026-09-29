"""Salesforce OAuth2 provider implementation."""

import logging
from typing import Any

from ...models.integration import IntegrationType
from ..base import BaseOAuth2Provider

logger = logging.getLogger(__name__)


class SalesforceOAuth2Provider(BaseOAuth2Provider):
    """Salesforce OAuth2 provider for CRM integration."""

    @property
    def integration_type(self) -> IntegrationType:
        """Return the integration type."""
        return IntegrationType.SALESFORCE

    @property
    def display_name(self) -> str:
        """Return the display name."""
        return "Salesforce"

    @property
    def supported_features(self) -> list[str]:
        """Return supported features."""
        return [
            "lead_management",
            "contact_management",
            "opportunity_tracking",
            "account_management",
            "custom_objects",
            "reports",
            "dashboards",
            "chatter",
        ]

    def get_provider_params(self) -> dict[str, str]:
        """Get Salesforce-specific authorization parameters."""
        return {
            "display": "page",  # or "popup", "touch", "mobile"
            "prompt": "consent",
        }

    async def get_user_info(self, access_token: str, instance_url: str) -> dict[str, Any]:
        """Get Salesforce user information."""
        try:
            response = await self.http_client.get(
                f"{instance_url}/services/oauth2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code == 200:
                return response.json()
            
            logger.error(f"Failed to get user info: {response.text}")
            return {}
            
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return {}

    async def query_soql(
        self,
        access_token: str,
        instance_url: str,
        query: str,
    ) -> dict | None:
        """Execute a SOQL query."""
        try:
            response = await self.http_client.get(
                f"{instance_url}/services/data/v58.0/query",
                params={"q": query},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code == 200:
                return response.json()
            
            logger.error(f"SOQL query failed: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"Error executing SOQL: {e}")
            return None

    async def create_lead(
        self,
        access_token: str,
        instance_url: str,
        lead_data: dict,
    ) -> dict | None:
        """Create a new lead in Salesforce."""
        try:
            response = await self.http_client.post(
                f"{instance_url}/services/data/v58.0/sobjects/Lead",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=lead_data,
            )
            
            if response.status_code in (200, 201):
                return response.json()
            
            logger.error(f"Failed to create lead: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"Error creating lead: {e}")
            return None

    async def update_opportunity(
        self,
        access_token: str,
        instance_url: str,
        opportunity_id: str,
        update_data: dict,
    ) -> bool:
        """Update an opportunity."""
        try:
            response = await self.http_client.patch(
                f"{instance_url}/services/data/v58.0/sobjects/Opportunity/{opportunity_id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=update_data,
            )
            
            return response.status_code == 204
            
        except Exception as e:
            logger.error(f"Error updating opportunity: {e}")
            return False

    def process_token_response(self, token_data: dict) -> dict:
        """Process Salesforce-specific token response."""
        from datetime import UTC, datetime, timedelta
        
        from ...models.integration import OAuth2TokenData
        
        # Salesforce includes instance_url in token response
        # Store it in the scope field for now (or we could extend the model)
        instance_url = token_data.get("instance_url", "")
        
        # Salesforce tokens don't expire by default, but we'll set 2 hours for safety
        expires_at = datetime.now(UTC) + timedelta(hours=2)
        
        return OAuth2TokenData(
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=7200,  # 2 hours
            expires_at=expires_at,
            scope=f"instance_url:{instance_url}|{token_data.get('scope', '')}",
        )