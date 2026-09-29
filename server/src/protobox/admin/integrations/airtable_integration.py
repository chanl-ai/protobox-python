"""Airtable database API integration."""

from typing import Any

from loguru import logger

from ..models.integration import IntegrationType
from .base_classes import ApiKeyIntegration, IntegrationHealth, IntegrationCapability


class AirtableIntegration(ApiKeyIntegration):
    """Airtable API integration for database operations and workflow automation."""

    integration_type = IntegrationType.AIRTABLE
    display_name = "Airtable"
    description = "Connect to Airtable for database operations, project tracking, and workflow automation"
    
    # Capabilities for database operations
    capabilities = [
        IntegrationCapability.CREATE_PROJECT,
        IntegrationCapability.UPDATE_TASK,
        IntegrationCapability.TRACK_ACTIVITY,
        IntegrationCapability.ANALYZE_DATA,
    ]
    
    # API key configuration
    api_key_name = "AIRTABLE_API_KEY"
    api_key_header = "Authorization"
    api_key_prefix = "Bearer"
    
    # Webhook support for automation
    supports_webhooks = True
    webhook_secret_key = "AIRTABLE_WEBHOOK_SECRET"

    async def test_connection(self, credentials: dict[str, Any]) -> IntegrationHealth:
        """Test Airtable connection by fetching user info."""
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
                # Get user info to validate API key
                response = await client.get(
                    "https://api.airtable.com/v0/meta/whoami",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Get bases to show in health check
                    bases_response = await client.get(
                        "https://api.airtable.com/v0/meta/bases",
                        headers={"Authorization": f"Bearer {api_key}"},
                        timeout=10.0
                    )
                    bases = bases_response.json() if bases_response.status_code == 200 else {"bases": []}
                    
                    return IntegrationHealth(
                        is_healthy=True,
                        error_message=f"Connected as {data.get('email', 'Unknown')} with {len(bases.get('bases', []))} base(s)",
                        details={
                            "user_id": data.get("id"),
                            "email": data.get("email"),
                            "bases_count": len(bases.get("bases", [])),
                            "base_names": [b.get("name") for b in bases.get("bases", [])][:5]  # First 5 bases
                        }
                    )
                elif response.status_code == 401:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message="Invalid API key",
                        details={"error": "invalid_api_key", "status": 401}
                    )
                else:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message=f"Airtable API error: {response.status_code}",
                        details={"status": response.status_code, "error": response.text}
                    )
                    
        except Exception as e:
            logger.error(f"Error testing Airtable connection: {e}")
            return IntegrationHealth(
                is_healthy=False,
                error_message=f"Connection test failed: {str(e)}",
                details={"error": str(e)}
            )

    def get_capabilities(self) -> list[str]:
        """Get Airtable integration capabilities."""
        return [
            "create_record",
            "update_record",
            "delete_record",
            "list_records",
            "search_records",
            "create_table",
            "manage_views",
            "webhook_automation",
            "bulk_operations",
            "formula_fields"
        ]
    
    def get_settings_schema(self) -> dict[str, Any]:
        """Get settings schema for Airtable integration."""
        return {
            "type": "object",
            "properties": {
                "base_id": {
                    "type": "string",
                    "title": "Default Base ID",
                    "description": "Default Airtable base to use",
                    "pattern": "^app[a-zA-Z0-9]{14}$",
                    "examples": ["appXXXXXXXXXXXXXX"]
                },
                "table_mappings": {
                    "type": "object",
                    "title": "Table Mappings",
                    "description": "Map entity types to Airtable tables",
                    "properties": {
                        "projects": {"type": "string", "default": "Projects"},
                        "tasks": {"type": "string", "default": "Tasks"},
                        "contacts": {"type": "string", "default": "Contacts"},
                        "deals": {"type": "string", "default": "Deals"}
                    }
                },
                "view_preferences": {
                    "type": "object",
                    "title": "View Preferences",
                    "description": "Default views for different contexts",
                    "properties": {
                        "default_view": {"type": "string", "examples": ["Grid view", "Kanban", "Calendar"]},
                        "filtered_view": {"type": "string"},
                        "grouped_view": {"type": "string"}
                    }
                },
                "webhook_triggers": {
                    "type": "array",
                    "title": "Webhook Triggers",
                    "description": "Events that trigger webhooks",
                    "items": {
                        "type": "string",
                        "enum": [
                            "record_created",
                            "record_updated",
                            "record_deleted",
                            "field_changed",
                            "view_changed"
                        ]
                    },
                    "default": ["record_created", "record_updated"]
                },
                "sync_settings": {
                    "type": "object",
                    "title": "Sync Settings",
                    "properties": {
                        "auto_sync": {
                            "type": "boolean",
                            "title": "Auto Sync",
                            "description": "Automatically sync changes",
                            "default": True
                        },
                        "sync_interval": {
                            "type": "integer",
                            "title": "Sync Interval (minutes)",
                            "minimum": 5,
                            "maximum": 1440,
                            "default": 60
                        },
                        "conflict_resolution": {
                            "type": "string",
                            "enum": ["local_wins", "remote_wins", "manual"],
                            "default": "remote_wins"
                        }
                    }
                },
                "field_mappings": {
                    "type": "object",
                    "title": "Custom Field Mappings",
                    "description": "Map ProtoBox fields to Airtable fields",
                    "additionalProperties": {
                        "type": "string"
                    }
                }
            },
            "required": ["base_id"]
        }
    
    def get_mcp_tools(self) -> list[dict[str, Any]]:
        """Get MCP tools for Airtable integration."""
        return [
            {
                "name": "airtable_create_record",
                "description": "Create a new record in an Airtable base",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "base_id": {"type": "string", "pattern": "^app[a-zA-Z0-9]{14}$"},
                        "table": {"type": "string", "description": "Table name or ID"},
                        "fields": {"type": "object", "description": "Field values for the record"},
                        "typecast": {"type": "boolean", "description": "Auto-convert field types", "default": False}
                    },
                    "required": ["table", "fields"]
                }
            },
            {
                "name": "airtable_update_record",
                "description": "Update an existing record",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "base_id": {"type": "string", "pattern": "^app[a-zA-Z0-9]{14}$"},
                        "table": {"type": "string"},
                        "record_id": {"type": "string", "pattern": "^rec[a-zA-Z0-9]{14}$"},
                        "fields": {"type": "object", "description": "Fields to update"},
                        "replace": {"type": "boolean", "description": "Replace all fields or merge", "default": False}
                    },
                    "required": ["table", "record_id", "fields"]
                }
            },
            {
                "name": "airtable_search_records",
                "description": "Search and filter records",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "base_id": {"type": "string", "pattern": "^app[a-zA-Z0-9]{14}$"},
                        "table": {"type": "string"},
                        "filter_formula": {"type": "string", "description": "Airtable formula for filtering"},
                        "sort": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "field": {"type": "string"},
                                    "direction": {"type": "string", "enum": ["asc", "desc"]}
                                }
                            }
                        },
                        "max_records": {"type": "integer", "minimum": 1, "maximum": 100},
                        "view": {"type": "string", "description": "View name or ID"}
                    },
                    "required": ["table"]
                }
            },
            {
                "name": "airtable_bulk_create",
                "description": "Create multiple records at once",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "base_id": {"type": "string", "pattern": "^app[a-zA-Z0-9]{14}$"},
                        "table": {"type": "string"},
                        "records": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "fields": {"type": "object"}
                                }
                            },
                            "maxItems": 10
                        },
                        "typecast": {"type": "boolean", "default": False}
                    },
                    "required": ["table", "records"]
                }
            },
            {
                "name": "airtable_get_base_schema",
                "description": "Get base structure including tables and fields",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "base_id": {"type": "string", "pattern": "^app[a-zA-Z0-9]{14}$"},
                        "include_field_definitions": {"type": "boolean", "default": True}
                    },
                    "required": ["base_id"]
                }
            },
            {
                "name": "airtable_link_records",
                "description": "Create links between records",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "base_id": {"type": "string", "pattern": "^app[a-zA-Z0-9]{14}$"},
                        "table": {"type": "string"},
                        "record_id": {"type": "string", "pattern": "^rec[a-zA-Z0-9]{14}$"},
                        "link_field": {"type": "string", "description": "Name of the link field"},
                        "linked_record_ids": {
                            "type": "array",
                            "items": {"type": "string", "pattern": "^rec[a-zA-Z0-9]{14}$"}
                        }
                    },
                    "required": ["table", "record_id", "link_field", "linked_record_ids"]
                }
            }
        ]