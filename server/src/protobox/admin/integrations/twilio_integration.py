"""Twilio API key integration."""

from typing import Any

from loguru import logger

from ..models.integration import IntegrationType
from .base_classes import ApiKeyIntegration, IntegrationHealth


class TwilioIntegration(ApiKeyIntegration):
    """Twilio API key integration implementation."""

    integration_type = IntegrationType.TWILIO
    display_name = "Twilio"
    description = "Send SMS, make calls, and manage communications with Twilio"
    category = "communication"
    
    # Capabilities
    capabilities = []
    
    # Twilio uses Account SID and Auth Token with Basic Auth
    api_key_name = "TWILIO_AUTH_TOKEN"
    api_key_header = "Authorization"  # Uses Basic Auth
    requires_account_sid = True

    async def test_connection(self, credentials: dict[str, Any]) -> IntegrationHealth:
        """Test Twilio connection by fetching account info."""
        try:
            import httpx
            from base64 import b64encode
            
            account_sid = credentials.get("account_sid")
            auth_token = credentials.get("auth_token")  # Auth token from credentials
            
            if not account_sid or not auth_token:
                return IntegrationHealth(
                    is_healthy=False,
                    error_message="Missing Account SID or Auth Token",
                    details={"error": "missing_credentials"}
                )
            
            # Twilio uses Basic Auth with Account SID as username and Auth Token as password
            auth_string = f"{account_sid}:{auth_token}"
            auth_header = f"Basic {b64encode(auth_string.encode()).decode()}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}.json",
                    headers={"Authorization": auth_header},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return IntegrationHealth(
                        is_healthy=True,
                        error_message=f"Connected to Twilio account: {data.get('friendly_name', account_sid)}",
                        details={
                            "account_sid": data.get("sid"),
                            "friendly_name": data.get("friendly_name"),
                            "status": data.get("status"),
                            "type": data.get("type"),
                            "date_created": data.get("date_created")
                        }
                    )
                elif response.status_code == 401:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message="Invalid Account SID or Auth Token",
                        details={"error": "invalid_credentials", "status": 401}
                    )
                else:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message=f"Twilio API error: {response.status_code}",
                        details={"status": response.status_code, "error": response.text}
                    )
                    
        except Exception as e:
            logger.error(f"Error testing Twilio connection: {e}")
            return IntegrationHealth(
                is_healthy=False,
                error_message=f"Connection test failed: {str(e)}",
                details={"error": str(e)}
            )

    def get_capabilities(self) -> list[str]:
        """Get Twilio integration capabilities."""
        return [
            "send_sms",
            "send_mms",
            "make_call",
            "send_whatsapp",
            "verify_phone",
            "lookup_phone",
            "manage_phone_numbers",
            "conference_calling",
            "voice_recording"
        ]

    def get_action_templates(self) -> list[str]:
        """Get available action template IDs for Twilio."""
        return [
            "twilio_send_sms",
            "twilio_make_call",
            "twilio_send_whatsapp",
            "twilio_verify_phone"
        ]
    
    def get_setup_instructions(self) -> dict[str, Any]:
        """Get setup instructions for Twilio."""
        base_instructions = super().get_setup_instructions()
        base_instructions["steps"] = [
            "Get your Account SID and Auth Token from Twilio",
            "Enter the Account SID and Auth Token in the fields below",
            "Click 'Test Connection' to verify"
        ]
        base_instructions["fields"] = [
            {
                "name": "account_sid",
                "type": "string",
                "label": "Account SID",
                "required": True,
                "placeholder": "Enter your Account SID"
            },
            {
                "name": "auth_token",
                "type": "password",
                "label": "Auth Token",
                "required": True,
                "placeholder": "Enter your Auth Token"
            }
        ]
        return base_instructions
