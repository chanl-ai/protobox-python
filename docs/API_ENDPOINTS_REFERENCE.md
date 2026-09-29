# API Endpoints Reference

## Authentication Required
All endpoints require a Bearer token in the Authorization header.

## Integration Endpoints

### Available Integrations (Global)
```bash
GET /admin/api/v1/integrations/available
```
Returns list of all available integration types that can be connected.

**Make command**: `make api-integrations-available`

### Workspace Integrations
```bash
GET /admin/api/v1/workspaces/{workspace_id}/integrations
```
Returns list of integrations for a specific workspace.

**Make command**: `make api-integrations`

### Connect Integration
```bash
POST /admin/api/v1/workspaces/{workspace_id}/integrations/{integration_type}/connect
```
Start the OAuth flow or API key setup for an integration.

### Integration Tools/Actions
```bash
GET /admin/api/v1/workspaces/{workspace_id}/integrations/{integration_type}/tools
```
Get available tools/actions for an integration.

### OAuth Callback (Internal)
```bash
GET /admin/api/v1/integrations/oauth/callback/{integration_type}
```
OAuth2 callback endpoint (configured in OAuth providers).

## Template Endpoints

### List Templates
```bash
GET /admin/api/v1/templates
```
Returns all available action templates.

### Get Templates by Category
```bash
GET /admin/api/v1/templates?category={category}
```
Filter templates by category.

### Get Templates for Integration
```bash
GET /admin/api/v1/templates?integration={integration_type}
```
Get templates that use a specific integration.

## Common Issues

### 404 Not Found on `/integrations`
The `/integrations` endpoint doesn't exist at the root level. Use:
- `/admin/api/v1/integrations/available` for available integrations
- `/admin/api/v1/workspaces/{workspace_id}/integrations` for workspace integrations

### Missing Workspace ID
Many endpoints require a workspace ID. Get it using:
```bash
make api-workspaces
```
Then use the ID from the response.

## Testing with Make Commands

### Quick Test All Integrations
```bash
# List available integrations
make api-integrations-available

# List workspace integrations
make api-integrations

# Check specific integration (Google Analytics)
make api-integrations-available | grep -A5 "google_analytics"
```

### Environment-Specific Testing
```bash
# Local (default)
make api-integrations-available

# Staging
make api-integrations-available ENV=staging

# Production
make api-integrations-available ENV=production
```