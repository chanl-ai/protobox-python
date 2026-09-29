"""Slack OAuth2 integration."""

from typing import Any

from loguru import logger

from ..models.integration import IntegrationType
from .base_classes import OAuth2Integration, IntegrationHealth, IntegrationCapability


class SlackIntegration(OAuth2Integration):
    """Slack OAuth2 integration implementation."""

    integration_type = IntegrationType.SLACK
    display_name = "Slack"
    description = "Connect Slack for team collaboration, project updates, and marketing campaigns"
    
    # OAuth2 configuration
    oauth_authorize_url = "https://slack.com/oauth/v2/authorize"
    oauth_token_url = "https://slack.com/api/oauth.v2.access"
    oauth_scopes = [
        "channels:read",
        "channels:write", 
        "chat:write",
        "chat:write.public",
        "users:read",
        "files:write",
        "files:read",
        "channels:manage",
        "groups:read",
        "groups:write",
        "im:write",
        "mpim:write"
    ]
    
    # Capabilities for marketing and project management
    capabilities = [
        IntegrationCapability.SEND_MESSAGE,
        IntegrationCapability.CREATE_PROJECT,
        IntegrationCapability.UPDATE_TASK,
        IntegrationCapability.TRACK_ACTIVITY,
    ]
    
    # Additional Slack-specific OAuth parameters
    extra_auth_params = {
        "user_scope": "identify,read"  # For user-level permissions
    }

    async def test_connection(self, credentials: dict[str, Any]) -> IntegrationHealth:
        """Test Slack connection by calling auth.test endpoint."""
        try:
            import httpx
            
            access_token = credentials.get("access_token")
            if not access_token:
                return IntegrationHealth(
                    is_healthy=False,
                    error_message="Missing access token",
                    details={"error": "no_token"}
                )
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://slack.com/api/auth.test",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                data = response.json()
                
                if data.get("ok"):
                    return IntegrationHealth(
                        is_healthy=True,
                        error_message=f"Connected to {data.get('team', 'Slack workspace')}",
                        details={
                            "team": data.get("team"),
                            "user": data.get("user"),
                            "team_id": data.get("team_id"),
                            "user_id": data.get("user_id")
                        }
                    )
                else:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message=f"Slack API error: {data.get('error', 'Unknown error')}",
                        details=data
                    )
                    
        except Exception as e:
            logger.error(f"Error testing Slack connection: {e}")
            return IntegrationHealth(
                is_healthy=False,
                error_message=f"Connection test failed: {str(e)}",
                details={"error": str(e)}
            )

    def get_capabilities(self) -> list[str]:
        """Get Slack integration capabilities."""
        return [
            "send_message",
            "create_channel",
            "list_channels",
            "get_user_info",
            "post_to_channel",
            "send_direct_message",
            "upload_file",
            "create_reminder"
        ]

    def get_settings_schema(self) -> dict[str, Any]:
        """Get settings schema for Slack integration."""
        return {
            "type": "object",
            "properties": {
                "default_channel": {
                    "type": "string",
                    "title": "Default Channel",
                    "description": "Default channel for notifications (e.g., #general)",
                    "pattern": "^#?[a-z0-9-_]+$"
                },
                "bot_name": {
                    "type": "string",
                    "title": "Bot Display Name",
                    "description": "Display name for the bot in Slack",
                    "default": "ProtoBox"
                },
                "notification_types": {
                    "type": "array",
                    "title": "Enabled Notifications",
                    "description": "Types of notifications to send to Slack",
                    "items": {
                        "type": "string",
                        "enum": ["project_updates", "task_assignments", "marketing_campaigns", "daily_standups", "alerts"]
                    },
                    "default": ["project_updates", "task_assignments"]
                },
                "team_id": {
                    "type": "string",
                    "title": "Slack Team ID",
                    "description": "Your Slack workspace team ID",
                    "readOnly": True
                }
            },
            "required": []
        }
    
    def get_mcp_tools(self) -> list[dict[str, Any]]:
        """Get MCP tools for Slack integration."""
        return [
            {
                "name": "slack_send_message",
                "description": "Send a message to a Slack channel or user",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "channel": {"type": "string", "description": "Channel ID or user ID"},
                        "text": {"type": "string", "description": "Message text"},
                        "blocks": {"type": "array", "description": "Rich message blocks"}
                    },
                    "required": ["channel", "text"]
                }
            },
            {
                "name": "slack_create_channel",
                "description": "Create a new Slack channel for a project",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "pattern": "^[a-z0-9-_]{1,80}$"},
                        "is_private": {"type": "boolean", "default": False},
                        "topic": {"type": "string"}
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "slack_post_update",
                "description": "Post a project or marketing update",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "channel": {"type": "string"},
                        "update_type": {"type": "string", "enum": ["project", "marketing", "standup"]},
                        "content": {"type": "object"}
                    },
                    "required": ["channel", "update_type", "content"]
                }
            }
        ]