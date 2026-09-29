# OAuth 2.1 Implementation Guide

ProtoBox implements a complete OAuth 2.1 authorization server that is fully compatible with FastMCP clients, Claude Custom Connectors, and other standard OAuth clients.

## Quick Start

### Using the UI (Recommended for Claude, ChatGPT, Cursor)

1. Go to Settings → Security → OAuth Clients
2. Click "AI Assistants" button
3. Select your platform tab (Claude, ChatGPT, Cursor, or Custom)
4. Click "Generate Credentials"
5. Copy the Client ID and Client Secret
6. Follow the platform-specific setup instructions shown in the UI

The UI provides guided setup with pre-configured settings for each platform:
- **Claude**: Confidential client with `client_secret_basic` authentication
- **ChatGPT**: Confidential client with `client_secret_post` authentication  
- **Cursor**: Public client with PKCE (no client secret)
- **Custom**: Advanced configuration for other integrations

## Quick Start (Programmatic)

### For FastMCP Clients

```python
from fastmcp import Client
from fastmcp.client.auth import OAuth

oauth = OAuth(
    mcp_url="http://localhost:8090",  # Or https://protobox.example.com for production
    scopes=["mcp:read", "mcp:execute", "mcp:write"],
    client_name="My FastMCP Client"
)

async with Client("http://localhost:8090/mcp", auth=oauth) as client:
    tools = await client.list_tools()
```

### For Claude Custom Connectors

1. Register a confidential client:
```bash
curl -X POST http://localhost:8090/register \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "Claude Custom Connector",
    "redirect_uris": ["https://claude.ai/callback"],
    "token_endpoint_auth_method": "client_secret_basic",
    "client_type": "confidential"
  }'
```

2. Use the returned `client_id` and `client_secret` in Claude's custom connector settings.

## OAuth Endpoints Overview

ProtoBox implements two sets of OAuth endpoints:

### 1. MCP OAuth Protocol Endpoints (Root Level)
These endpoints implement the OAuth 2.1 protocol for client authentication:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/.well-known/oauth-authorization-server` | GET | OAuth 2.0 discovery metadata |
| `/register` | POST | Dynamic client registration (RFC 7591) |
| `/authorize` | GET | Authorization endpoint (user login/consent) |
| `/token` | POST | Token exchange endpoint |
| `/introspect` | POST | Token introspection (RFC 7662) |
| `/revoke` | POST | Token revocation (RFC 7009) |
| `/jwks` | GET | JSON Web Key Set |

### 2. Admin API Endpoints (For Managing OAuth Clients)
These endpoints are for users to manage their OAuth clients through the UI or API:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/admin/api/v1/integrations/oauth/clients?workspace_id={id}` | GET | List all OAuth clients for a workspace |
| `/admin/api/v1/integrations/oauth/clients?workspace_id={id}` | POST | Create a new OAuth client |
| `/admin/api/v1/integrations/oauth/clients/{client_id}?workspace_id={id}` | DELETE | Revoke/delete an OAuth client |

**Note**: 
- The admin endpoints require authentication with your ProtoBox user token (JWT), not OAuth tokens.
- Currently using `?workspace_id=` query parameter. This will be migrated to `/workspaces/{workspace_id}/integrations/oauth/clients` pattern to match other APIs.

## Client Types

### Public Clients (Default)
- No client secret required
- Must use PKCE for security
- Suitable for FastMCP, SPAs, mobile apps

```json
{
  "client_name": "My Public Client",
  "token_endpoint_auth_method": "none"
}
```

### Confidential Clients
- Returns client_id and client_secret
- Required for Claude Custom Connectors
- Suitable for server-side applications

```json
{
  "client_name": "My Confidential Client",
  "token_endpoint_auth_method": "client_secret_basic",
  "client_type": "confidential"
}
```

## Complete End-to-End OAuth Flow

### Understanding the Two-Layer System

ProtoBox uses a two-layer authentication system:
1. **User Authentication** (Firebase/JWT) - Who is the user?
2. **Client Authorization** (OAuth) - What application is accessing on behalf of the user?

### Visual Flow Diagram

```
┌─────────────┐         ┌─────────────────┐         ┌──────────────┐
│   User      │         │   ProtoBox      │         │ Application  │
│ (Browser)   │         │   Server        │         │ (FastMCP)    │
└─────────────┘         └─────────────────┘         └──────────────┘
      │                          │                          │
      │  1. Login to ProtoBox    │                          │
      │  (Firebase Auth)         │                          │
      ├─────────────────────────>│                          │
      │<─────────────────────────│                          │
      │  JWT Token               │                          │
      │                          │                          │
      │  2. Create OAuth Client  │                          │
      │  POST /admin/api/v1/     │                          │
      │  integrations/oauth/     │                          │
      │  clients?workspace_id=   │                          │
      ├─────────────────────────>│                          │
      │<─────────────────────────│                          │
      │  client_id, client_secret│                          │
      │                          │                          │
      │                          │  3. App starts OAuth     │
      │                          │     OR registers itself  │
      │                          │     POST /register       │
      │                          │<─────────────────────────│
      │                          │─────────────────────────>│
      │                          │     client_id            │
      │                          │                          │
      │  4. Authorization Request│                          │
      │<─────────────────────────────────────────────────│
      │     GET /authorize?client_id=xxx                   │
      │                          │                          │
      │  5. User Consent Screen  │                          │
      ├─────────────────────────>│                          │
      │<─────────────────────────│                          │
      │  6. Redirect with code   │                          │
      │─────────────────────────────────────────────────>│
      │                          │                          │
      │                          │  7. Token Exchange       │
      │                          │     POST /token          │
      │                          │<─────────────────────────│
      │                          │─────────────────────────>│
      │                          │  access_token,           │
      │                          │  refresh_token          │
      │                          │                          │
      │                          │  8. MCP API Calls        │
      │                          │<─────────────────────────│
      │                          │  Bearer: access_token    │
      │                          │─────────────────────────>│
      │                          │  MCP Response            │
```

### Step-by-Step Flow

#### Step 1: User Creates OAuth Client (Admin API)
First, the ProtoBox user creates an OAuth client for their application:

```bash
# Authenticate as a ProtoBox user (get JWT token)
TOKEN=$(cat .test-cache-dev_test.json | jq -r '.access_token')
WORKSPACE_ID="your-workspace-id"

# Create an OAuth client for your application
curl -X POST "http://localhost:8090/admin/api/v1/integrations/oauth/clients?workspace_id=$WORKSPACE_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "My FastMCP Application",
    "redirect_uris": ["http://localhost:8765/callback"],
    "scopes": ["mcp:read", "mcp:execute"],
    "client_type": "public"
  }'

# Response:
{
  "client_id": "mcp_xxxxxxxxxxxx",
  "client_secret": null,  // null for public clients
  "message": "OAuth client created successfully"
}
```

#### Step 2: Application Uses OAuth to Get Access Token
The application (e.g., FastMCP client) uses the OAuth flow to get an access token:

##### Option A: Dynamic Registration (One-time setup)
```bash
# The application registers itself dynamically
curl -X POST http://localhost:8090/register \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "My Application",
    "redirect_uris": ["http://localhost:8765/callback"]
  }'
# Returns: client_id
```

##### Option B: Use Pre-created Client (From Step 1)
Use the `client_id` from the admin API creation.

#### Step 3: OAuth Authorization Flow

##### 3a. Authorization Request
The application redirects the user to ProtoBox for authorization:

```
GET /authorize?
  response_type=code&
  client_id=mcp_xxxxxxxxxxxx&
  redirect_uri=http://localhost:8765/callback&
  scope=mcp:read mcp:execute&
  state=random_state&
  code_challenge=challenge&
  code_challenge_method=S256
```

The user:
1. Logs in with their ProtoBox credentials (if not already logged in)
2. Sees consent screen showing what the application is requesting
3. Clicks "Authorize"
4. Gets redirected back to the application with an authorization code

##### 3b. Token Exchange
The application exchanges the authorization code for an access token:

```bash
POST /token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&
code=auth_code_xxxxx&
redirect_uri=http://localhost:8765/callback&
code_verifier=verifier&
client_id=mcp_xxxxxxxxxxxx
```

Response:
```json
{
  "access_token": "mcp_oauth_xxxxx",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "mcp_refresh_xxxxx",
  "scope": "mcp:read mcp:execute"
}
```

#### Step 4: Use the Access Token
The application can now use the access token to call MCP endpoints:

```bash
curl -H "Authorization: Bearer mcp_oauth_xxxxx" \
  http://localhost:8090/mcp/{workspace_id}/sse
```

### Alternative: Dynamic Registration Flow

If you don't want to pre-create clients via the Admin API, applications can register themselves dynamically using the `/register` endpoint (shown in Option A above). This is useful for:
- FastMCP clients that auto-register
- Development and testing
- Applications that don't need persistent client credentials

Response:
```json
{
  "access_token": "mcp_oauth_xxxxx",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "mcp_refresh_xxxxx",
  "scope": "mcp:read mcp:execute"
}
```

## Scopes

Available OAuth scopes:

- `mcp:read` - Read access to MCP tools and resources
- `mcp:write` - Write access to modify configurations
- `mcp:execute` - Execute MCP tools and actions
- `offline_access` - Get refresh tokens for long-lived access

## Security Features

- **PKCE Required**: All public clients must use PKCE
- **State Parameter**: Prevents CSRF attacks
- **Secure Token Storage**: Bcrypt-hashed secrets
- **Token Expiration**: Access tokens expire in 1 hour
- **Refresh Tokens**: 30-day validity for offline access

## Integration with Firebase Auth

ProtoBox OAuth works alongside Firebase authentication:
- Firebase handles user authentication
- OAuth handles client authorization
- Tokens include workspace context

## Testing

### Test Scripts

```bash
# Test dynamic registration
python scripts/test_dynamic_registration.py

# Test OAuth flow with browser
python scripts/fastmcp_oauth_browser.py

# Test OAuth with FastMCP client
python scripts/test_oauth_flow.py
```

### Using with Make Commands

```bash
# Test OAuth discovery
make api ENDPOINT="/.well-known/oauth-authorization-server"

# Register a client
make api ENDPOINT="/register" METHOD="POST" \
  DATA='{"client_name":"Test Client"}'
```

## Production URLs

- **OAuth Server**: https://protobox.example.com
- **MCP Endpoint**: https://protobox.example.com/mcp
- **Discovery**: https://protobox.example.com/.well-known/oauth-authorization-server

## Troubleshooting

### "Client not found" Error
- Ensure client was registered successfully
- Check client_id is correct
- Verify client hasn't been revoked

### "Invalid redirect_uri" Error  
- Redirect URI must match exactly what was registered
- Include protocol (http:// or https://)
- Check for trailing slashes

### "Invalid code_verifier" Error
- PKCE is required for public clients
- Ensure code_verifier matches code_challenge
- Use S256 method only

### Token Expired
- Access tokens expire in 1 hour
- Use refresh token to get new access token
- Re-authenticate if refresh token expired

## Migration from Previous Auth Systems

If you were using direct Firebase tokens or API keys:

1. Register an OAuth client using `/register`
2. Update your code to use OAuth flow
3. Tokens now include proper workspace context
4. All MCP endpoints require OAuth tokens

## Testing Guide

### Manual Testing

#### 1. Test Dynamic Registration
```bash
# Register a public client (for FastMCP)
curl -X POST http://localhost:8090/register \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "Test Public Client",
    "redirect_uris": ["http://localhost:8765/callback"],
    "token_endpoint_auth_method": "none"
  }'

# Register a confidential client (for Claude)
curl -X POST http://localhost:8090/register \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "Claude Connector",
    "redirect_uris": ["https://claude.ai/callback"],
    "token_endpoint_auth_method": "client_secret_basic",
    "client_type": "confidential"
  }'
# Save the returned client_id and client_secret
```

#### 2. Test with FastMCP Browser Flow
```bash
# This opens your browser for authentication
python scripts/fastmcp_oauth_browser.py
```

#### 3. Test Programmatically
```bash
# Quick registration test
python scripts/test_dynamic_registration.py

# Full OAuth flow test (requires test token)
python scripts/test_oauth_flow.py
```

### Testing with Claude Custom Connector

#### Step 1: Register a Client for Claude
```bash
curl -X POST https://protobox.example.com/register \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "Claude MCP Connector",
    "redirect_uris": ["https://claude.ai/api/auth/callback/custom"],
    "scope": "mcp:read mcp:write mcp:execute",
    "token_endpoint_auth_method": "client_secret_basic",
    "client_type": "confidential"
  }'
```

Save the response:
```json
{
  "client_id": "mcp_xxxxxxxxxxxxx",
  "client_secret": "xxxxxxxxxxxxxxxxx"
}
```

#### Step 2: Configure Claude Custom Connector

1. Go to Claude settings → Custom Connectors
2. Click "Add Custom Connector"
3. Configure as follows:

**Basic Settings:**
- Name: `ProtoBox MCP`
- Description: `Connect to ProtoBox MCP Server`

**OAuth Settings:**
- Authorization URL: `https://protobox.example.com/authorize`
- Token URL: `https://protobox.example.com/token`
- Client ID: `[Your client_id from step 1]`
- Client Secret: `[Your client_secret from step 1]`
- Scope: `mcp:read mcp:write mcp:execute`

**API Settings:**
- Base URL: `https://protobox.example.com/mcp`
- Authentication: `Bearer Token`

#### Step 3: Test the Connection

1. Click "Connect" in Claude
2. You'll be redirected to ProtoBox login
3. Authorize the connection
4. Claude will receive the OAuth token
5. Test by asking Claude to use your MCP tools

### Testing OAuth Endpoints Individually

```bash
# 1. Discovery
curl http://localhost:8090/.well-known/oauth-authorization-server | jq

# 2. Register Client
CLIENT_RESPONSE=$(curl -s -X POST http://localhost:8090/register \
  -H "Content-Type: application/json" \
  -d '{"client_name": "Test Client"}')
CLIENT_ID=$(echo $CLIENT_RESPONSE | jq -r '.client_id')

# 3. Get Authorization Code (requires browser)
open "http://localhost:8090/authorize?response_type=code&client_id=$CLIENT_ID&redirect_uri=http://localhost:8765/callback&scope=mcp:read&state=test123&code_challenge=challenge123&code_challenge_method=S256"

# 4. Exchange Code for Token (after getting auth code)
curl -X POST http://localhost:8090/token \
  -d "grant_type=authorization_code&code=AUTH_CODE&redirect_uri=http://localhost:8765/callback&code_verifier=verifier123&client_id=$CLIENT_ID"

# 5. Introspect Token
curl -X POST http://localhost:8090/introspect \
  -u "$CLIENT_ID:$CLIENT_SECRET" \
  -d "token=ACCESS_TOKEN"

# 6. Revoke Token
curl -X POST http://localhost:8090/revoke \
  -u "$CLIENT_ID:$CLIENT_SECRET" \
  -d "token=ACCESS_TOKEN"
```

### Verify Everything Works

```bash
# Check all OAuth endpoints are available
make api ENDPOINT="/.well-known/oauth-authorization-server" | jq '.authorization_endpoint, .token_endpoint, .registration_endpoint'

# Should output:
# "http://localhost:8090/authorize"
# "http://localhost:8090/token"
# "http://localhost:8090/register"
```

## Key Concepts to Remember

### Two Types of Clients
1. **OAuth Clients** - Applications that want to access ProtoBox MCP APIs (FastMCP, Claude, etc.)
2. **ProtoBox Users** - Human users who log in with Firebase and manage their workspaces

### Two Sets of Endpoints
1. **OAuth Protocol Endpoints** (`/register`, `/authorize`, `/token`) - Used by applications during OAuth flow
2. **Admin API Endpoints** (`/admin/api/v1/integrations/oauth/clients`) - Used by ProtoBox users to manage their OAuth clients

### Two Types of Tokens
1. **JWT Tokens** - For ProtoBox users (from Firebase auth exchange)
2. **OAuth Tokens** - For applications accessing MCP on behalf of users

### Workspace Context
- OAuth clients belong to workspaces
- Currently using `?workspace_id=` query parameter (will migrate to path parameter)
- Each workspace can have multiple OAuth clients
- OAuth tokens include workspace context

## Common Use Cases

### For Claude Custom Connector
1. User creates confidential OAuth client via Admin API
2. User configures Claude with client_id and client_secret
3. Claude uses OAuth flow to get access token
4. Claude calls MCP endpoints with OAuth token

### For FastMCP Development
1. FastMCP auto-registers as public client via `/register`
2. FastMCP uses PKCE flow (no client_secret)
3. User authorizes in browser
4. FastMCP gets access token and calls MCP endpoints

### For Production Applications
1. User creates OAuth client via Admin API (UI or programmatically)
2. Application stores client_id (and client_secret if confidential)
3. Application implements standard OAuth 2.1 flow
4. Application uses access token for all MCP API calls

## Implementation Status

### ✅ Completed Features

1. **MCP-Compliant OAuth Endpoints** (at root level as per spec)
   - `GET /.well-known/oauth-authorization-server` - OAuth discovery
   - `POST /register` - Dynamic client registration
   - `GET /authorize` - Authorization endpoint
   - `POST /token` - Token exchange
   - `POST /introspect` - Token introspection
   - `POST /revoke` - Token revocation
   - `GET /jwks` - JSON Web Key Set

2. **Admin API Endpoints** (for managing OAuth clients)
   - `GET /admin/api/v1/integrations/oauth/clients?workspace_id={id}` - List OAuth clients
   - `POST /admin/api/v1/integrations/oauth/clients?workspace_id={id}` - Create OAuth client
   - `DELETE /admin/api/v1/integrations/oauth/clients/{client_id}?workspace_id={id}` - Delete OAuth client

3. **Client Type Support**
   - **Public clients** (FastMCP) - No client_secret, uses PKCE
   - **Confidential clients** (Claude) - Returns client_id and client_secret

4. **OAuth 2.1 Features**
   - Authorization Code Flow with PKCE (required)
   - Dynamic Client Registration (RFC 7591)
   - Token introspection (RFC 7662)
   - Token revocation (RFC 7009)
   - Refresh token support

5. **Compatibility**
   - FastMCP client compatible
   - Claude Custom Connector compatible (with client_id + client_secret)
   - Standard OAuth 2.1 clients compatible

### 📁 Documentation Structure

- **Single Source of Truth**: This document (`OAUTH_IMPLEMENTATION.md`)
- **Archived Docs**: Old OAuth docs moved to `docs/archive/oauth-old/`
- **Related Docs**: 
  - `AUTH_CONFIGURATION.md` - General auth system (not OAuth-specific)
  - `GOOGLE_OAUTH_SETUP.md` - Google integration OAuth

### 🧹 Code Cleanup

- Removed unused HTML template generation code
- Fixed deprecated `.dict()` → `.model_dump()` calls
- Removed unused imports
- Simplified authorization flow for non-owner users

## Additional Resources

- [MCP OAuth Specification](https://modelcontextprotocol.io/specification/2025-03-26/basic/authorization)
- [OAuth 2.1 Specification](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-07)
- [RFC 7591 - Dynamic Client Registration](https://datatracker.ietf.org/doc/html/rfc7591)
- [RFC 7636 - PKCE](https://datatracker.ietf.org/doc/html/rfc7636)