"""SendGrid API key integration."""

from typing import Any

from loguru import logger

from ..models.integration import IntegrationType
from .base_classes import ApiKeyIntegration, IntegrationHealth


class SendGridIntegration(ApiKeyIntegration):
    """SendGrid API key integration implementation."""

    integration_type = IntegrationType.SENDGRID
    display_name = "SendGrid"
    description = "Send transactional and marketing emails with SendGrid"
    category = "communication"
    
    # Capabilities
    capabilities = []    
    # API key configuration
    api_key_name = "SENDGRID_API_KEY"
    api_key_header = "Authorization"
    api_key_prefix = "Bearer"

    async def test_connection(self, credentials: dict[str, Any]) -> IntegrationHealth:
        """Test SendGrid connection by calling API key scopes endpoint."""
        try:
            import httpx
            
            api_key = credentials.get("api_key")
            if not api_key:
                return IntegrationHealth(
                    is_healthy=False,
                    error_message="Missing API key",
                    details={"error": "no_api_key"}
                )
            
            async with httpx.AsyncClient() as client:
                # Test connection by getting API key scopes
                response = await client.get(
                    "https://api.sendgrid.com/v3/scopes",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    scopes = data.get("scopes", [])
                    return IntegrationHealth(
                        is_healthy=True,
                        error_message=f"Connected to SendGrid ({len(scopes)} scopes available)",
                        details={
                            "scopes_count": len(scopes),
                            "scopes": scopes[:10]  # First 10 scopes
                        }
                    )
                elif response.status_code == 401:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message="Invalid API key",
                        details={"error": "invalid_api_key", "status": 401}
                    )
                elif response.status_code == 403:
                    # API key is valid but has limited permissions - still consider it connected
                    return IntegrationHealth(
                        is_healthy=True,
                        error_message="Connected to SendGrid (limited permissions)",
                        details={"warning": "limited_permissions", "status": 403}
                    )
                else:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message=f"SendGrid API error: {response.status_code}",
                        details={"status": response.status_code, "error": response.text}
                    )
                    
        except Exception as e:
            logger.error(f"Error testing SendGrid connection: {e}")
            return IntegrationHealth(
                is_healthy=False,
                error_message=f"Connection test failed: {str(e)}",
                details={"error": str(e)}
            )

    def get_capabilities(self) -> list[str]:
        """Get SendGrid integration capabilities."""
        return [
            "send_email",
            "send_bulk_email",
            "manage_templates",
            "manage_contacts",
            "create_lists",
            "send_marketing_campaign",
            "track_email_events",
            "manage_suppressions",
            "validate_email"
        ]

    def get_action_templates(self) -> list[str]:
        """Get available action template IDs for SendGrid."""
        return [
            "sendgrid_send_email",
            "sendgrid_send_template_email",
            "sendgrid_add_contact",
            "sendgrid_create_campaign"
        ]