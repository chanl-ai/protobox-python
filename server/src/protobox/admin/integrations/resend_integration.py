"""Resend email service API integration."""

from typing import Any

from loguru import logger

from ..models.integration import IntegrationType
from .base_classes import ApiKeyIntegration, IntegrationHealth, IntegrationCapability


class ResendIntegration(ApiKeyIntegration):
    """Resend email API integration for transactional and marketing emails."""

    integration_type = IntegrationType.RESEND
    display_name = "Resend"
    description = "Send beautiful transactional and marketing emails with modern email API"
    
    # Capabilities for email communication
    capabilities = [
        IntegrationCapability.SEND_MESSAGE,
        IntegrationCapability.TRACK_ACTIVITY,
        IntegrationCapability.ANALYZE_DATA,
    ]
    
    # API key configuration
    api_key_name = "RESEND_API_KEY"
    api_key_header = "Authorization"
    api_key_prefix = "Bearer"
    
    # Webhook support for email events
    supports_webhooks = True
    webhook_secret_key = "RESEND_WEBHOOK_SECRET"

    async def test_connection(self, credentials: dict[str, Any]) -> IntegrationHealth:
        """Test Resend connection by sending a test email to self."""
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
                # Get API key details to verify connection
                response = await client.get(
                    "https://api.resend.com/api-keys",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Get domains to show in health check
                    domains_response = await client.get(
                        "https://api.resend.com/domains",
                        headers={"Authorization": f"Bearer {api_key}"},
                        timeout=10.0
                    )
                    domains = domains_response.json() if domains_response.status_code == 200 else {"data": []}
                    
                    return IntegrationHealth(
                        is_healthy=True,
                        error_message=f"Connected to Resend with {len(domains.get('data', []))} domain(s)",
                        details={
                            "api_keys_count": len(data.get("data", [])),
                            "domains": [d.get("name") for d in domains.get("data", [])],
                            "verified_domains": [d.get("name") for d in domains.get("data", []) if d.get("status") == "verified"]
                        }
                    )
                elif response.status_code == 401 or response.status_code == 400:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message="Invalid API key",
                        details={"error": "invalid_api_key", "status": response.status_code}
                    )
                else:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message=f"Resend API error: {response.status_code}",
                        details={"status": response.status_code, "error": response.text}
                    )
                    
        except Exception as e:
            logger.error(f"Error testing Resend connection: {e}")
            return IntegrationHealth(
                is_healthy=False,
                error_message=f"Connection test failed: {str(e)}",
                details={"error": str(e)}
            )

    def get_capabilities(self) -> list[str]:
        """Get Resend integration capabilities."""
        return [
            "send_email",
            "send_batch",
            "send_with_template",
            "track_opens",
            "track_clicks",
            "manage_audiences",
            "manage_domains",
            "webhook_events",
            "email_validation"
        ]
    
    def get_settings_schema(self) -> dict[str, Any]:
        """Get settings schema for Resend integration."""
        return {
            "type": "object",
            "properties": {
                "from_email": {
                    "type": "string",
                    "title": "Default From Email",
                    "description": "Default sender email address",
                    "format": "email",
                    "examples": ["noreply@yourdomain.com"]
                },
                "from_name": {
                    "type": "string",
                    "title": "Default From Name",
                    "description": "Default sender display name",
                    "examples": ["Your Company"]
                },
                "reply_to": {
                    "type": "string",
                    "title": "Reply-To Email",
                    "description": "Default reply-to email address",
                    "format": "email"
                },
                "domain": {
                    "type": "string",
                    "title": "Sending Domain",
                    "description": "Verified domain for sending emails",
                    "examples": ["yourdomain.com"]
                },
                "webhook_events": {
                    "type": "array",
                    "title": "Webhook Events",
                    "description": "Email events to track via webhooks",
                    "items": {
                        "type": "string",
                        "enum": [
                            "email.sent",
                            "email.delivered",
                            "email.delivery_delayed",
                            "email.complained",
                            "email.bounced",
                            "email.opened",
                            "email.clicked"
                        ]
                    },
                    "default": ["email.delivered", "email.bounced", "email.opened", "email.clicked"]
                },
                "tracking": {
                    "type": "object",
                    "title": "Tracking Settings",
                    "properties": {
                        "opens": {
                            "type": "boolean",
                            "title": "Track Opens",
                            "description": "Track when emails are opened",
                            "default": True
                        },
                        "clicks": {
                            "type": "boolean",
                            "title": "Track Clicks",
                            "description": "Track link clicks in emails",
                            "default": True
                        }
                    }
                },
                "tags": {
                    "type": "array",
                    "title": "Default Tags",
                    "description": "Tags to apply to all emails",
                    "items": {
                        "type": "string"
                    },
                    "examples": ["transactional", "marketing"]
                }
            },
            "required": ["from_email", "domain"]
        }
    
    def get_mcp_tools(self) -> list[dict[str, Any]]:
        """Get MCP tools for Resend integration."""
        return [
            {
                "name": "resend_send_email",
                "description": "Send a single transactional or marketing email",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "format": "email", "description": "Recipient email"},
                        "subject": {"type": "string", "description": "Email subject"},
                        "html": {"type": "string", "description": "HTML content"},
                        "text": {"type": "string", "description": "Plain text content"},
                        "from": {"type": "string", "format": "email"},
                        "reply_to": {"type": "string", "format": "email"},
                        "tags": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["to", "subject"]
                }
            },
            {
                "name": "resend_send_batch",
                "description": "Send multiple emails in a single API call",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "emails": {
                            "type": "array",
                            "description": "Array of email objects",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "to": {"type": "string", "format": "email"},
                                    "subject": {"type": "string"},
                                    "html": {"type": "string"},
                                    "text": {"type": "string"}
                                }
                            }
                        }
                    },
                    "required": ["emails"]
                }
            },
            {
                "name": "resend_send_template",
                "description": "Send email using a template with variables",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "format": "email"},
                        "template_id": {"type": "string", "description": "Template identifier"},
                        "variables": {"type": "object", "description": "Template variables"},
                        "tags": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["to", "template_id"]
                }
            },
            {
                "name": "resend_create_audience",
                "description": "Create an email audience/list",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Audience name"},
                        "contacts": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "email": {"type": "string", "format": "email"},
                                    "first_name": {"type": "string"},
                                    "last_name": {"type": "string"},
                                    "unsubscribed": {"type": "boolean"}
                                }
                            }
                        }
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "resend_get_email_stats",
                "description": "Get email sending statistics and metrics",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "date_from": {"type": "string", "format": "date"},
                        "date_to": {"type": "string", "format": "date"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "domain": {"type": "string"}
                    }
                }
            }
        ]