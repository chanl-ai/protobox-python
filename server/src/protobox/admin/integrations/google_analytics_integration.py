"""Google Analytics integration for ProtoBox."""

from typing import Any

import httpx

from ..models.integration import IntegrationType
from .base_classes import IntegrationCapability, IntegrationHealth
from .google_base import GoogleOAuth2Integration


class GoogleAnalyticsIntegration(GoogleOAuth2Integration):
    """Google Analytics integration for tracking and reporting."""
    
    integration_type = IntegrationType.GOOGLE_ANALYTICS
    display_name = "Google Analytics"
    description = "Track website traffic, user behavior, and generate reports"
    
    capabilities = [
        IntegrationCapability.TRACK_EVENTS,
        IntegrationCapability.VIEW_REPORTS,
        IntegrationCapability.ANALYZE_TRAFFIC,
        IntegrationCapability.ANALYZE_DATA,
    ]
    
    oauth_scopes = [
        "https://www.googleapis.com/auth/analytics.readonly",
        "https://www.googleapis.com/auth/analytics.edit",
        "https://www.googleapis.com/auth/analytics.manage.users",
    ]
    
    async def test_connection(self, credentials: dict[str, Any]) -> IntegrationHealth:
        """Test Google Analytics connection."""
        if not credentials.get("access_token"):
            return IntegrationHealth(
                is_healthy=False,
                error_message="No access token found"
            )
        
        try:
            # Test by listing GA4 properties
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://analyticsadmin.googleapis.com/v1beta/properties",
                    headers={"Authorization": f"Bearer {credentials['access_token']}"},
                    params={"pageSize": 1}
                )
                
                if response.status_code == 200:
                    return IntegrationHealth(
                        is_healthy=True,
                        details={
                            "connection": "verified",
                            "service": "Google Analytics"
                        }
                    )
                elif response.status_code == 401:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message="Invalid or expired access token"
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
        """Get settings schema for Google Analytics."""
        return {
            "type": "object",
            "properties": {
                "property_id": {
                    "type": "string",
                    "title": "GA4 Property ID",
                    "description": "Your Google Analytics 4 property ID (e.g., 123456789)",
                    "pattern": "^[0-9]+$"
                },
                "default_view_id": {
                    "type": "string",
                    "title": "Default View ID",
                    "description": "Optional default view ID for reporting"
                },
                "enable_realtime": {
                    "type": "boolean",
                    "title": "Enable Real-time Reporting",
                    "description": "Allow access to real-time analytics data",
                    "default": True
                },
                "measurement_id": {
                    "type": "string",
                    "title": "Measurement ID",
                    "description": "GA4 Measurement ID for event tracking (e.g., G-XXXXXXXXXX)",
                    "pattern": "^G-[A-Z0-9]+$"
                }
            },
            "required": ["property_id"]
        }