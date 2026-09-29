"""HubSpot OAuth2 integration for CRM and marketing automation."""

from typing import Any

from loguru import logger

from ..models.integration import IntegrationType
from .base_classes import OAuth2Integration, IntegrationHealth, IntegrationCapability


class HubspotIntegration(OAuth2Integration):
    """HubSpot OAuth2 integration implementation for CRM operations."""

    integration_type = IntegrationType.HUBSPOT
    display_name = "HubSpot"
    description = "Manage contacts, deals, companies, and marketing automation workflows"
    
    # OAuth2 configuration
    oauth_authorize_url = "https://app.hubspot.com/oauth/authorize"
    oauth_token_url = "https://api.hubapi.com/oauth/v1/token"
    oauth_scopes = [
        "oauth",                    # OAuth token management (mandatory)
        "crm.objects.contacts.read",    # Read access to contacts
        "crm.objects.contacts.write",   # Write access to contacts
        "crm.objects.companies.read",   # Read access to companies
        "crm.objects.companies.write",  # Write access to companies
        "crm.objects.deals.read",       # Read access to deals
        "crm.objects.deals.write"       # Write access to deals
    ]
    
    # Capabilities for CRM operations
    capabilities = [
        IntegrationCapability.CREATE_CONTACT,
        IntegrationCapability.UPDATE_CONTACT,
        IntegrationCapability.CREATE_DEAL,
        IntegrationCapability.UPDATE_DEAL,
        IntegrationCapability.CREATE_COMPANY,
        IntegrationCapability.TRACK_ACTIVITY,
    ]
    
    # Additional OAuth parameters
    extra_auth_params = {
        "client_type": "confidential"  # HubSpot requires confidential client type
    }

    async def test_connection(self, credentials: dict[str, Any]) -> IntegrationHealth:
        """Test HubSpot connection by fetching authenticated user and account info."""
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
                # Test with HubSpot account info endpoint
                response = await client.get(
                    "https://api.hubapi.com/oauth/v1/access-tokens/" + access_token,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    hub_id = data.get("hub_id")
                    user_id = data.get("user_id")
                    scopes = data.get("scope", "").split(" ")
                    
                    # Also test contacts endpoint to verify CRM access
                    contacts_response = await client.get(
                        "https://api.hubapi.com/crm/v3/objects/contacts?limit=1",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Content-Type": "application/json"
                        },
                        timeout=10.0
                    )
                    
                    crm_access = contacts_response.status_code == 200
                    
                    return IntegrationHealth(
                        is_healthy=True,
                        error_message=f"Connected to HubSpot Hub {hub_id}",
                        details={
                            "hub_id": hub_id,
                            "user_id": user_id,
                            "scopes": scopes,
                            "crm_access": crm_access,
                            "expires_in": data.get("expires_in"),
                            "token_type": data.get("token_type")
                        }
                    )
                elif response.status_code == 401:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message="Invalid or expired token",
                        details={"error": "invalid_token", "status": 401}
                    )
                else:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message=f"HubSpot API error: {response.status_code}",
                        details={"status": response.status_code, "error": response.text}
                    )
                    
        except Exception as e:
            logger.error(f"Error testing HubSpot connection: {e}")
            return IntegrationHealth(
                is_healthy=False,
                error_message=f"Connection test failed: {str(e)}",
                details={"error": str(e)}
            )

    def get_capabilities(self) -> list[str]:
        """Get HubSpot integration capabilities."""
        return [
            "create_contact",
            "update_contact", 
            "search_contacts",
            "create_deal",
            "update_deal",
            "create_company",
            "get_contact_properties",
            "get_deal_pipeline"
        ]
    
    def get_settings_schema(self) -> dict[str, Any]:
        """Get settings schema for HubSpot integration."""
        return {
            "type": "object",
            "properties": {
                "default_pipeline": {
                    "type": "string",
                    "title": "Default Deal Pipeline",
                    "description": "Default pipeline for new deals",
                    "examples": ["default", "sales", "marketing"]
                },
                "default_stage": {
                    "type": "string",
                    "title": "Default Deal Stage",
                    "description": "Default stage for new deals",
                    "examples": ["appointmentscheduled", "qualifiedtobuy", "presentationscheduled"]
                },
                "contact_owner": {
                    "type": "string",
                    "title": "Default Contact Owner",
                    "description": "Default owner for new contacts (HubSpot user ID)",
                    "pattern": "^[0-9]+$"
                },
                "company_domain_mapping": {
                    "type": "boolean",
                    "title": "Auto-map Company Domains",
                    "description": "Automatically associate contacts with companies based on email domain",
                    "default": True
                },
                "lead_scoring": {
                    "type": "object",
                    "title": "Lead Scoring Rules",
                    "description": "Configure lead scoring for new contacts",
                    "properties": {
                        "email_engagement": {"type": "integer", "default": 10},
                        "website_visits": {"type": "integer", "default": 5},
                        "form_submissions": {"type": "integer", "default": 15},
                        "deal_creation": {"type": "integer", "default": 25}
                    }
                },
                "sync_frequency": {
                    "type": "string",
                    "title": "Sync Frequency",
                    "description": "How often to sync data with HubSpot",
                    "enum": ["realtime", "hourly", "daily"],
                    "default": "hourly"
                },
                "custom_properties": {
                    "type": "object",
                    "title": "Custom Properties",
                    "description": "Map ProtoBox fields to HubSpot custom properties",
                    "properties": {
                        "source": {"type": "string", "default": "protobox"},
                        "campaign": {"type": "string", "default": "ai_assistant"},
                        "priority": {"type": "string", "default": "medium"}
                    }
                },
                "notification_settings": {
                    "type": "object",
                    "title": "Notification Settings",
                    "description": "Configure notifications for integration events",
                    "properties": {
                        "contact_created": {"type": "boolean", "default": True},
                        "deal_created": {"type": "boolean", "default": True},
                        "deal_stage_changed": {"type": "boolean", "default": True},
                        "error_alerts": {"type": "boolean", "default": True}
                    }
                }
            },
            "required": []
        }
    
    def get_mcp_tools(self) -> list[dict[str, Any]]:
        """Get MCP tools for HubSpot integration."""
        return [
            {
                "name": "hubspot_create_contact",
                "description": "Create a new contact in HubSpot CRM",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string", "format": "email", "description": "Contact email address"},
                        "firstname": {"type": "string", "description": "Contact first name"},
                        "lastname": {"type": "string", "description": "Contact last name"},
                        "phone": {"type": "string", "description": "Contact phone number"},
                        "company": {"type": "string", "description": "Company name"},
                        "jobtitle": {"type": "string", "description": "Job title"},
                        "lifecycle_stage": {"type": "string", "enum": ["lead", "opportunity", "customer", "evangelist", "other"]},
                        "lead_status": {"type": "string", "enum": ["new", "open", "in_progress", "qualified", "unqualified"]}
                    },
                    "required": ["email"]
                }
            },
            {
                "name": "hubspot_update_contact",
                "description": "Update an existing contact in HubSpot CRM",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "contact_id": {"type": "string", "description": "HubSpot contact ID"},
                        "email": {"type": "string", "format": "email"},
                        "firstname": {"type": "string"},
                        "lastname": {"type": "string"},
                        "phone": {"type": "string"},
                        "company": {"type": "string"},
                        "lifecycle_stage": {"type": "string", "enum": ["lead", "opportunity", "customer", "evangelist", "other"]},
                        "lead_status": {"type": "string", "enum": ["new", "open", "in_progress", "qualified", "unqualified"]}
                    },
                    "required": ["contact_id"]
                }
            },
            {
                "name": "hubspot_search_contacts",
                "description": "Search for contacts in HubSpot CRM",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query (email, name, company)"},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
                        "properties": {"type": "array", "items": {"type": "string"}, "default": ["email", "firstname", "lastname", "company"]}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "hubspot_create_deal",
                "description": "Create a new deal in HubSpot CRM",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "dealname": {"type": "string", "description": "Name of the deal"},
                        "amount": {"type": "string", "description": "Deal amount (e.g., '10000.00')"},
                        "dealstage": {"type": "string", "description": "Deal stage"},
                        "closedate": {"type": "string", "format": "date", "description": "Expected close date"},
                        "contact_id": {"type": "string", "description": "Associated contact ID"},
                        "company_id": {"type": "string", "description": "Associated company ID"},
                        "pipeline": {"type": "string", "description": "Deal pipeline", "default": "default"}
                    },
                    "required": ["dealname", "amount", "dealstage"]
                }
            },
            {
                "name": "hubspot_update_deal",
                "description": "Update an existing deal in HubSpot CRM",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "deal_id": {"type": "string", "description": "HubSpot deal ID"},
                        "dealname": {"type": "string"},
                        "amount": {"type": "string"},
                        "dealstage": {"type": "string"},
                        "closedate": {"type": "string", "format": "date"},
                        "pipeline": {"type": "string"}
                    },
                    "required": ["deal_id"]
                }
            },
            {
                "name": "hubspot_create_company",
                "description": "Create a new company in HubSpot CRM",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Company name"},
                        "domain": {"type": "string", "description": "Company website domain"},
                        "industry": {"type": "string", "description": "Company industry"},
                        "phone": {"type": "string", "description": "Company phone number"},
                        "city": {"type": "string", "description": "Company city"},
                        "state": {"type": "string", "description": "Company state/province"},
                        "country": {"type": "string", "description": "Company country"},
                        "lifecycle_stage": {"type": "string", "enum": ["lead", "opportunity", "customer", "evangelist", "other"]}
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "hubspot_get_contact_properties",
                "description": "Get available contact properties from HubSpot",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "archived": {"type": "boolean", "description": "Include archived properties", "default": False}
                    }
                }
            },
            {
                "name": "hubspot_get_deal_pipeline",
                "description": "Get deal pipeline stages from HubSpot",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "pipeline_id": {"type": "string", "description": "Pipeline ID (optional, will use default if not specified)"}
                    }
                }
            }
        ]
    