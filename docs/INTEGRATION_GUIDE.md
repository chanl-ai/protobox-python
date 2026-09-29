# ProtoBox Integration System Guide

## Overview

ProtoBox supports third-party integrations using a registry-based architecture with support for OAuth2, API Key, and Webhook authentication. The system automatically manages integration lifecycles, settings, and MCP action templates.

## Architecture Components

### 1. Base Classes (`integrations/base_classes.py`)
- **BaseIntegration**: Abstract base for all integrations
- **OAuth2Integration**: OAuth2 authentication flows  
- **ApiKeyIntegration**: API key authentication
- **WebhookIntegration**: Webhook-based integrations
- **DualAuthIntegration**: Multiple auth methods

### 2. Integration Registry (`integrations/registry.py`)
- Singleton pattern for managing integration instances
- Auto-discovery and registration on startup
- Provides integration metadata and capabilities

### 3. Integration Models (`models/integration.py`)
- **IntegrationType**: Enum of supported integrations
- **IntegrationModel**: MongoDB document for workspace integrations
- **IntegrationStatus**: Connection states (not_connected, connected, error)
- **AuthType**: Authentication methods (oauth2, api_key, webhook)

### 4. Template System (`services/template_manager.py`)
- JSON templates define available actions for each integration
- Templates are loaded from `data/action_templates/`
- Templates define requirements, configuration, and transformations

## Integration Flow

### OAuth2 Integrations (Google Calendar, Gmail, etc.)

1. **User clicks "Connect"**
   - Frontend calls `POST /workspaces/{id}/integrations/{type}/connect`
   - Backend generates OAuth authorization URL with state parameter
   - Returns: `{"type": "oauth2", "authorization_url": "..."}`

2. **User authorizes in popup**
   - Redirected to provider's OAuth consent screen
   - User grants permissions
   - Provider redirects to callback URL

3. **OAuth callback**
   - `GET /oauth/callback/{type}` exchanges code for tokens
   - Tokens stored as encrypted secrets
   - Integration marked as connected

4. **Actions auto-created**
   - System loads action templates for the integration
   - Creates MCP actions with proper authentication headers

### API Key Integrations (OpenAI, Stripe, etc.)

1. **User clicks "Connect"** 
   - Frontend calls `POST /workspaces/{id}/integrations/{type}/connect`
   - Returns: 
   ```json
   {
     "type": "api_key",
     "display_name": "OpenAI",
     "instructions": ["Get API key from OpenAI", "Enter below", "Test connection"],
     "fields": [{"name": "api_key", "type": "password", "label": "API Key", "required": true}]
   }
   ```

2. **User enters API key**
   - Frontend shows modal with input fields
   - User enters credentials
   - Frontend calls `POST /workspaces/{id}/integrations/{type}/credentials`

3. **Credentials validated**
   - Backend tests connection with provided credentials
   - If valid, stores as encrypted secret
   - Integration marked as connected

4. **Actions auto-created**
   - Same as OAuth2 flow

## Settings Management

Each integration can define custom settings schema:

```python
def get_settings_schema(self) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "default_calendar": {
                "type": "string",
                "title": "Default Calendar",
                "default": "primary"
            },
            "reminder_minutes": {
                "type": "integer",
                "minimum": 0,
                "maximum": 120,
                "default": 10
            }
        }
    }
```

Settings endpoints:
- `GET /workspaces/{id}/integrations/{type}/settings` - Get schema and current values
- `PUT /workspaces/{id}/integrations/{type}/settings` - Update settings
- `POST /workspaces/{id}/integrations/{type}/validate` - Validate settings

## Action Templates

Templates define available actions for each integration:

```json
{
  "id": "google_calendar_create_event",
  "name": "Create Calendar Event",
  "description": "Create a new event in Google Calendar",
  "category": "productivity",
  "required_integrations": ["google_calendar"],
  "action_type": "REST",
  "default_config": {
    "method": "POST",
    "url": "https://www.googleapis.com/calendar/v3/calendars/{{calendar_id}}/events",
    "headers": {
      "Authorization": "Bearer ${secret:google_calendar_oauth.access_token}",
      "Content-Type": "application/json"
    },
    "body": {
      "summary": "{{title}}",
      "start": {"dateTime": "{{start_time}}"},
      "end": {"dateTime": "{{end_time}}"}
    }
  },
  "config_schema": {
    "properties": {
      "calendar_id": {"type": "string", "default": "primary"},
      "title": {"type": "string"},
      "start_time": {"type": "string", "format": "date-time"},
      "end_time": {"type": "string", "format": "date-time"}
    }
  }
}
```

## Adding a New Integration

### 1. Create Integration Class

```python
# integrations/new_service_integration.py
from ..models.integration import IntegrationType
from .base_classes import ApiKeyIntegration, IntegrationCapability, IntegrationHealth

class NewServiceIntegration(ApiKeyIntegration):
    integration_type = IntegrationType.NEW_SERVICE
    display_name = "New Service"
    description = "Connect to New Service"
    category = "productivity"
    
    # API key configuration
    api_key_header = "X-API-Key"
    
    # Capabilities this integration provides
    capabilities = [
        IntegrationCapability.CREATE_TASK,
        IntegrationCapability.UPDATE_TASK
    ]
    
    def get_settings_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "workspace_id": {
                    "type": "string",
                    "title": "Workspace ID",
                    "description": "Your New Service workspace ID"
                }
            }
        }
    
    async def test_connection(self, credentials: dict[str, Any]) -> IntegrationHealth:
        # Test API key validity
        api_key = credentials.get("api_key")
        if not api_key:
            return IntegrationHealth(
                is_healthy=False,
                error_message="API key required"
            )
        
        # Make test API call
        # ...
        
        return IntegrationHealth(is_healthy=True)
```

### 2. Register Integration

```python
# integrations/__init__.py
from .new_service_integration import NewServiceIntegration

def initialize_integrations():
    registry = get_integration_registry()
    
    integrations_to_register = [
        # ... existing integrations ...
        NewServiceIntegration,
    ]
    
    for integration_class in integrations_to_register:
        registry.register(integration_class)
```

### 3. Add Integration Type

```python
# models/integration.py
class IntegrationType(str, Enum):
    # ... existing types ...
    NEW_SERVICE = "new_service"
```

### 4. Create Action Templates

```json
// data/action_templates/new_service_create_task.json
{
  "id": "new_service_create_task",
  "name": "Create Task",
  "description": "Create a new task in New Service",
  "category": "productivity",
  "required_integrations": ["new_service"],
  "action_type": "REST",
  "default_config": {
    "method": "POST",
    "url": "https://api.newservice.com/v1/tasks",
    "headers": {
      "X-API-Key": "${secret:new_service_api_key.api_key}",
      "Content-Type": "application/json"
    },
    "body": {
      "title": "{{title}}",
      "description": "{{description}}",
      "workspace_id": "${settings:workspace_id}"
    }
  }
}
```

## Security Considerations

1. **OAuth State Parameter**: Contains workspace_id, user_id, and CSRF token
2. **Encrypted Secrets**: All credentials use AES-256-GCM encryption
3. **Token Refresh**: Automatic refresh for OAuth2 tokens
4. **Scope Validation**: Only requested scopes are used
5. **Audit Logging**: All integration events are logged

## API Endpoints

### Available Integrations
- `GET /integrations/available` - List all available integrations

### Workspace Integrations
- `GET /workspaces/{id}/integrations` - List workspace integrations
- `POST /workspaces/{id}/integrations/initialize` - Create all integration records
- `GET /workspaces/{id}/integrations/{type}` - Get specific integration
- `POST /workspaces/{id}/integrations/{type}/connect` - Start connection flow
- `POST /workspaces/{id}/integrations/{type}/credentials` - Save API key credentials
- `DELETE /workspaces/{id}/integrations/{type}` - Disconnect integration

### Settings Management
- `GET /workspaces/{id}/integrations/{type}/settings` - Get settings schema and values
- `PUT /workspaces/{id}/integrations/{type}/settings` - Update settings
- `POST /workspaces/{id}/integrations/{type}/validate` - Validate settings

### Tools/Actions Management
- `GET /workspaces/{id}/integrations/{type}/tools` - List available tools
- `POST /workspaces/{id}/integrations/{type}/tools/{tool_id}/enable` - Enable tool
- `POST /workspaces/{id}/integrations/{type}/tools/{tool_id}/disable` - Disable tool

## Testing

```bash
# Test OAuth2 flow (Google Calendar)
make api ENDPOINT="/admin/api/v1/workspaces/{id}/integrations/google_calendar/connect" METHOD="POST"

# Test API key flow (OpenAI)
make api ENDPOINT="/admin/api/v1/workspaces/{id}/integrations/openai/connect" METHOD="POST"
make api ENDPOINT="/admin/api/v1/workspaces/{id}/integrations/openai/credentials" METHOD="POST" DATA='{"api_key":"sk-..."}'

# Test settings
make api ENDPOINT="/admin/api/v1/workspaces/{id}/integrations/google_calendar/settings" METHOD="GET"
make api ENDPOINT="/admin/api/v1/workspaces/{id}/integrations/google_calendar/settings" METHOD="PUT" DATA='{"default_calendar":"work"}'
```