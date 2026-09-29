"""Gmail integration implementation."""

import logging
from typing import Any, Optional
import httpx

from ..integrations.base_classes import IntegrationCapability, IntegrationHealth
from .google_base import GoogleOAuth2Integration
from ..models.integration import IntegrationType

logger = logging.getLogger(__name__)


class GmailIntegration(GoogleOAuth2Integration):
    """Gmail OAuth2 integration."""
    
    integration_type = IntegrationType.GMAIL
    display_name = "Gmail"
    description = "Connect Gmail to send emails, manage drafts, and search messages"
    category = "communication"
    capabilities = [
        IntegrationCapability.SEND_EMAIL,
        IntegrationCapability.READ_EMAIL,
        IntegrationCapability.SEARCH_EMAIL,
        IntegrationCapability.MANAGE_DRAFTS
    ]
    
    # OAuth2 scopes specific to Gmail
    oauth_scopes = [
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.modify"
    ]
    
    def get_settings_schema(self) -> dict[str, Any]:
        """Get settings schema for Gmail integration."""
        return {
            "type": "object",
            "properties": {
                "email_settings": {
                    "type": "object",
                    "title": "Email Settings",
                    "properties": {
                        "default_from_name": {
                            "type": "string",
                            "title": "Default From Name",
                            "description": "Default sender name for outgoing emails",
                            "examples": ["John Doe", "Customer Support"]
                        },
                        "signature": {
                            "type": "string",
                            "title": "Email Signature",
                            "description": "Default signature for outgoing emails",
                            "format": "textarea",
                            "examples": ["Best regards,\nJohn Doe\nCEO, Acme Corp"]
                        },
                        "reply_to": {
                            "type": "string",
                            "title": "Reply-To Address",
                            "description": "Default reply-to email address",
                            "format": "email"
                        },
                        "send_as_html": {
                            "type": "boolean",
                            "title": "Send as HTML",
                            "description": "Send emails in HTML format by default",
                            "default": True
                        }
                    }
                },
                "filtering": {
                    "type": "object",
                    "title": "Email Filtering",
                    "properties": {
                        "labels_to_sync": {
                            "type": "array",
                            "title": "Labels to Sync",
                            "description": "Gmail labels to include in sync",
                            "items": {
                                "type": "string"
                            },
                            "default": ["INBOX", "SENT", "DRAFT", "IMPORTANT"]
                        },
                        "exclude_spam": {
                            "type": "boolean",
                            "title": "Exclude Spam",
                            "description": "Exclude spam emails from sync",
                            "default": True
                        },
                        "exclude_trash": {
                            "type": "boolean",
                            "title": "Exclude Trash",
                            "description": "Exclude trashed emails from sync",
                            "default": True
                        },
                        "exclude_promotions": {
                            "type": "boolean",
                            "title": "Exclude Promotions",
                            "description": "Exclude promotional emails",
                            "default": False
                        },
                        "max_results": {
                            "type": "integer",
                            "title": "Max Results",
                            "description": "Maximum number of emails to retrieve per query",
                            "minimum": 1,
                            "maximum": 500,
                            "default": 50
                        }
                    }
                },
                "auto_responses": {
                    "type": "object",
                    "title": "Auto-Responses",
                    "properties": {
                        "enable_vacation_responder": {
                            "type": "boolean",
                            "title": "Enable Vacation Responder",
                            "description": "Enable automatic vacation responses",
                            "default": False
                        },
                        "vacation_message": {
                            "type": "string",
                            "title": "Vacation Message",
                            "description": "Automatic response message when away",
                            "format": "textarea"
                        },
                        "enable_auto_reply": {
                            "type": "boolean",
                            "title": "Enable Auto-Reply",
                            "description": "Enable automatic replies to specific senders",
                            "default": False
                        }
                    }
                },
                "templates": {
                    "type": "object",
                    "title": "Email Templates",
                    "properties": {
                        "enable_templates": {
                            "type": "boolean",
                            "title": "Enable Templates",
                            "description": "Use email templates for common responses",
                            "default": True
                        },
                        "template_categories": {
                            "type": "array",
                            "title": "Template Categories",
                            "description": "Categories for organizing templates",
                            "items": {
                                "type": "string"
                            },
                            "default": ["Customer Support", "Sales", "Internal", "Marketing"]
                        }
                    }
                },
                "tracking": {
                    "type": "object",
                    "title": "Email Tracking",
                    "properties": {
                        "track_opens": {
                            "type": "boolean",
                            "title": "Track Opens",
                            "description": "Track when emails are opened",
                            "default": False
                        },
                        "track_clicks": {
                            "type": "boolean",
                            "title": "Track Link Clicks",
                            "description": "Track when links in emails are clicked",
                            "default": False
                        },
                        "send_read_receipts": {
                            "type": "boolean",
                            "title": "Send Read Receipts",
                            "description": "Send read receipts when requested",
                            "default": False
                        }
                    }
                },
                "scheduling": {
                    "type": "object",
                    "title": "Email Scheduling",
                    "properties": {
                        "enable_send_later": {
                            "type": "boolean",
                            "title": "Enable Send Later",
                            "description": "Allow scheduling emails for future delivery",
                            "default": True
                        },
                        "default_send_delay_minutes": {
                            "type": "integer",
                            "title": "Default Send Delay",
                            "description": "Default delay in minutes for scheduled sends",
                            "minimum": 0,
                            "maximum": 10080,  # 1 week
                            "default": 0
                        },
                        "undo_send_period_seconds": {
                            "type": "integer",
                            "title": "Undo Send Period",
                            "description": "Seconds to allow canceling sent emails",
                            "minimum": 0,
                            "maximum": 30,
                            "default": 5
                        }
                    }
                }
            },
            "required": []
        }
    
    async def test_connection_health(self, access_token: str) -> IntegrationHealth:
        """Test Gmail connection by fetching user profile."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/profile",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return IntegrationHealth(
                        is_healthy=True,
                        details={
                            "email_address": data.get("emailAddress"),
                            "messages_total": data.get("messagesTotal"),
                            "threads_total": data.get("threadsTotal")
                        }
                    )
                else:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message=f"Failed to fetch Gmail profile: {response.status_code}",
                        details={"status_code": response.status_code}
                    )
        except Exception as e:
            return IntegrationHealth(
                is_healthy=False,
                error_message=str(e),
                details={"error_type": type(e).__name__}
            )