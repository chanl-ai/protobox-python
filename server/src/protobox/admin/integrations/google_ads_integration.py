"""Google Ads integration for ProtoBox."""

from typing import Any

import httpx

from ..models.integration import IntegrationType
from .base_classes import IntegrationCapability, IntegrationHealth
from .google_base import GoogleOAuth2Integration


class GoogleAdsIntegration(GoogleOAuth2Integration):
    """Google Ads integration for campaign management and advertising."""
    
    integration_type = IntegrationType.GOOGLE_ADS
    display_name = "Google Ads"
    description = "Manage advertising campaigns, track performance, and optimize ad spend"
    
    capabilities = [
        IntegrationCapability.MANAGE_CAMPAIGNS,
        IntegrationCapability.VIEW_REPORTS,
        IntegrationCapability.ANALYZE_DATA,
        IntegrationCapability.TRACK_EVENTS,
    ]
    
    oauth_scopes = [
        "https://www.googleapis.com/auth/adwords",
    ]
    
    async def test_connection(self, credentials: dict[str, Any]) -> IntegrationHealth:
        """Test Google Ads connection."""
        if not credentials.get("access_token"):
            return IntegrationHealth(
                is_healthy=False,
                error_message="No access token found"
            )
        
        try:
            # Test by getting accessible customers
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://googleads.googleapis.com/v15/customers:listAccessibleCustomers",
                    headers={
                        "Authorization": f"Bearer {credentials['access_token']}",
                        "developer-token": credentials.get("developer_token", ""),
                    }
                )
                
                if response.status_code == 200:
                    return IntegrationHealth(
                        is_healthy=True,
                        details={
                            "connection": "verified",
                            "service": "Google Ads"
                        }
                    )
                elif response.status_code == 401:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message="Invalid or expired access token"
                    )
                elif response.status_code == 403:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message="Missing or invalid developer token"
                    )
                else:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message=f"API error: {response.status_code}"
                    )
                    
        except Exception as e:
            return IntegrationHealth(
                is_healthy=False,
                error_message=f"Connection error: {str(e)}"
            )
    
    def get_settings_schema(self) -> dict[str, Any]:
        """Get settings schema for Google Ads."""
        return {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "title": "Customer ID",
                    "description": "Your Google Ads customer ID (without dashes)",
                    "pattern": "^[0-9]{10}$"
                },
                "developer_token": {
                    "type": "string",
                    "title": "Developer Token",
                    "description": "Your Google Ads API developer token",
                    "format": "password"
                },
                "manager_account_id": {
                    "type": "string",
                    "title": "Manager Account ID",
                    "description": "Optional manager account ID for MCC accounts",
                    "pattern": "^[0-9]{10}$"
                },
                "enable_test_account": {
                    "type": "boolean",
                    "title": "Use Test Account",
                    "description": "Use Google Ads test account for development",
                    "default": False
                },
                "refresh_token": {
                    "type": "string",
                    "title": "Refresh Token",
                    "description": "OAuth2 refresh token for offline access",
                    "format": "password"
                }
            },
            "required": ["customer_id", "developer_token"]
        }
    
    def get_setup_instructions(self) -> dict[str, Any]:
        """Get setup instructions for Google Ads."""
        base_instructions = super().get_setup_instructions()
        base_instructions["additional_steps"] = [
            "Apply for Google Ads API access",
            "Obtain a developer token from Google Ads API Center",
            "Configure OAuth2 consent screen",
            "Add your customer ID (found in Google Ads UI)",
            "For production use, request production access for developer token"
        ]
        base_instructions["prerequisites"] = [
            "Active Google Ads account",
            "Google Ads API developer token",
            "OAuth2 credentials configured"
        ]
        return base_instructions