"""Notion API key integration."""

from typing import Any

from loguru import logger

from ..models.integration import IntegrationType
from .base_classes import ApiKeyIntegration, IntegrationHealth


class NotionIntegration(ApiKeyIntegration):
    """Notion API key integration implementation."""

    integration_type = IntegrationType.NOTION
    display_name = "Notion"
    description = "Connect to Notion for workspace management and knowledge base"
    category = "productivity"
    
    # Capabilities
    capabilities = []    
    # API key configuration
    api_key_name = "NOTION_API_KEY"
    api_key_header = "Authorization"
    api_key_prefix = "Bearer"
    
    # Notion API requires version header
    additional_headers = {
        "Notion-Version": "2022-06-28"
    }

    async def test_connection(self, credentials: dict[str, Any]) -> IntegrationHealth:
        """Test Notion connection by listing users."""
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
                # Test connection by listing users
                response = await client.get(
                    "https://api.notion.com/v1/users",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Notion-Version": "2022-06-28"
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    users = data.get("results", [])
                    workspace_name = users[0].get("name") if users else "Notion Workspace"
                    
                    return IntegrationHealth(
                        is_healthy=True,
                        error_message=f"Connected to {workspace_name}",
                        details={
                            "user_count": len(users),
                            "workspace_users": [u.get("name", "Unknown") for u in users[:3]],
                            "has_more": data.get("has_more", False)
                        }
                    )
                elif response.status_code == 401:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message="Invalid API key",
                        details={"error": "invalid_api_key", "status": 401}
                    )
                elif response.status_code == 403:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message="API key lacks required permissions",
                        details={"error": "insufficient_permissions", "status": 403}
                    )
                else:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message=f"Notion API error: {response.status_code}",
                        details={"status": response.status_code, "error": response.text}
                    )
                    
        except Exception as e:
            logger.error(f"Error testing Notion connection: {e}")
            return IntegrationHealth(
                is_healthy=False,
                error_message=f"Connection test failed: {str(e)}",
                details={"error": str(e)}
            )

    def get_capabilities(self) -> list[str]:
        """Get Notion integration capabilities."""
        return [
            "create_page",
            "update_page",
            "create_database",
            "query_database",
            "add_database_item",
            "search_content",
            "manage_blocks",
            "manage_comments",
            "sync_content"
        ]

    def get_action_templates(self) -> list[str]:
        """Get available action template IDs for Notion."""
        return [
            "notion_create_page",
            "notion_add_database_item",
            "notion_search_content",
            "notion_update_page"
        ]