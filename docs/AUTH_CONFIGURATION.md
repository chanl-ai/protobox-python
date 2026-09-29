# Authentication Configuration

## Overview

ProtoBox uses a flexible authentication system that supports multiple modes and can be dynamically switched at runtime. This allows for seamless transitions between development (no auth) and production (full auth) environments without code changes or service restarts.

## Authentication Architecture

### Three-Layer System

1. **Settings Layer** (`config.py`)
   - Centralized configuration management
   - All environment variables loaded once at startup
   - Type-safe settings with validation
   - Production safety checks

2. **Dynamic Config Layer** (`auth_config.py`)
   - Runtime-modifiable authentication settings
   - Can override settings without restart
   - Maintains state across requests
   - Reset capability to environment defaults

3. **Enforcement Layer** (`dependencies.py`)
   - Applies authentication based on current config
   - Supports graceful mode transitions
   - Maintains user identification even when auth is disabled

## Authentication Modes

### 1. ENABLED Mode (Production)
- **Full authentication required**
- JWT tokens validated with signatures
- Firebase tokens verified
- API keys checked against platform
- All security measures active

### 2. NONE Mode (Development)
- **Authentication bypassed for quick development**
- Still attempts to identify users from tokens (without verification)
- Falls back to test user if no token provided
- Maintains same code paths as production
- All permissions granted

### 3. FIREBASE Mode (Legacy - Deprecated)
- Direct Firebase authentication
- Not recommended - use ENABLED mode instead

## Runtime Mode Switching

### How It Works

The authentication mode can be changed at runtime without restarting services:

1. **Initial Configuration**: Settings loaded from environment variables via `Settings` class
2. **Runtime Override**: Admin endpoints allow changing auth config
3. **Request Processing**: Each request checks current auth config
4. **Graceful Transition**: User sessions maintained across mode changes

### Key Benefits

- **Development Efficiency**: Switch to NONE mode for rapid testing
- **E2E Testing**: Use ENABLED mode with test tokens
- **Production Safety**: ENABLED mode enforced in production
- **Zero Downtime**: No service restarts required

## Testing with Firebase Emulator

### Test Cache System (NEW!)

ProtoBox uses an intelligent test cache system that provides consistent test data across sessions:

#### How It Works (`scripts/setup-test-cache.sh`)

The test cache system uses **email as a stable identifier** rather than relying on database IDs:

```bash
# Automatic test cache setup (called by all API commands)
./scripts/setup-test-cache.sh
```

**Cache File Structure (`.test-cache.json`):**
```json
{
  "test_user": {
    "email": "test@protobox.local",
    "firebase_uid": "auto-generated",
    "name": "Test User",
    "last_token": "jwt-token",
    "token_expires": "2025-08-14T00:00:00Z"
  },
  "test_workspace": {
    "id": "auto-created",
    "name": "Test Workspace",
    "slug": "test-workspace"
  },
  "last_updated": "2025-08-13T23:00:00Z"
}
```

**Test User Credentials:**
- **Email**: `test@protobox.local`
- **Password**: `testpass123`
- **Created automatically** in Firebase emulator on first use

**Benefits:**
- **Zero manual setup** - Just run any API command
- **Real Firebase user** - Uses proper authentication flow
- **Survives restarts** - Firebase emulator and MongoDB can restart
- **Consistent data** - Same email = same user across sessions
- **Self-healing** - Recreates data if deleted
- **Fast testing** - Reuses valid tokens from cache

#### Integration with Make Commands

All `make api*` commands now automatically use the test cache:

```bash
# All these commands handle auth and workspace IDs automatically
make api-health          # Health check
make api-workspaces      # List workspaces
make api-audit-logs      # List audit logs
make api-create-action   # Create test action
make api ENDPOINT="..."  # Custom API call

# The workspace ID is auto-loaded from test cache
# No need to manually set WORKSPACE_ID anymore!
```

### Legacy Token Management

For backwards compatibility, the system still supports direct token setup:

```bash
# Manual token setup (usually not needed)
./scripts/setup-auth-token.sh
TOKEN=$(cat .test-token)
```

#### Firebase Emulator Support

When Firebase Auth Emulator is running:
```bash
# Start Firebase emulator
firebase emulators:start --only auth

# All make commands will use emulator tokens
make api-all  # Automatically uses Firebase emulator
```

### Test Tokens

In development environments (`dev_test`, `development`, `test`), test tokens are supported when test mode is enabled:

```bash
# Test tokens are no longer supported - use Firebase emulator instead
# The Firebase emulator provides real authentication for testing

# Get a real token from Firebase emulator
./scripts/setup-auth-token.sh

# Use the generated token for testing
TOKEN=$(cat .test-token)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8090/admin/api/v1/workspaces
```

## MCP Token Authentication

### Current Implementation

ProtoBox provides MCP (Model Context Protocol) tokens for AI assistants to connect to workspaces:

- **Token Format**: `pb_mcp_` prefix with random string
- **Storage**: Hashed with SHA-256 in database
- **Management**: Full CRUD operations via API and UI
- **UI Access**: "MCP Tokens" button in header

### ⚠️ MCP Specification Compliance

**Important**: Our current MCP token implementation is **NOT compliant** with the official MCP specification:

#### Non-Compliance Issues
1. **❌ Token in Query Parameter**: We use `?token=xxx` which is explicitly prohibited
2. **❌ No OAuth Support**: MCP spec requires OAuth 2.1
3. **❌ Custom Token Format**: Not using standard Bearer tokens

#### MCP Specification Requirements
- **MUST use Authorization header**: `Authorization: Bearer <token>`
- **MUST NOT include tokens in URI query string**
- **MUST use HTTPS** for all endpoints

See `docs/MCP_AUTH_ANALYSIS.md` for detailed analysis and migration plan.

## Configuration Management

### Settings Class (`config.py`)

All configuration is centralized in the `Settings` class:

```python
class Settings:
    def __init__(self):
        # Environment
        self.environment = os.getenv("ENVIRONMENT", "development")
        
        # Authentication settings - now always Firebase
        # Removed deprecated AUTH_MODE - now always uses Firebase authentication
        self.auth_test_mode = os.getenv("AUTH_TEST_MODE", "false").lower() == "true"
        
        # JWT settings
        self.jwt_secret = os.getenv("JWT_SECRET", "development-jwt-secret")
        # ... more settings
    
    def is_development(self) -> bool:
        return self.environment in ["development", "dev_test", "test"]
    
    def is_production(self) -> bool:
        return self.environment == "production"
```

### Dynamic Config (`auth_config.py`)

Runtime-modifiable configuration:

```python
class AuthConfig(BaseModel):
    mode: AuthMode = AuthMode.ENABLED
    test_mode: bool = False
    allow_test_tokens: bool = False

# Global auth config instance
_auth_config = AuthConfig()

def get_auth_config() -> AuthConfig:
    return _auth_config

def update_auth_config(new_config: AuthConfig):
    global _auth_config
    _auth_config = new_config
```

## Usage Examples

### Development Workflow

```bash
# 1. Start backend - now always uses Firebase authentication
make backend ENV=dev_test  # Always Firebase auth

# 2. Enable test mode for development
make auth-test-on   # Enable test tokens for development
make auth-test-off  # Disable test tokens

# 3. Test APIs with automatic auth
make api-all        # Tests all endpoints
make test-integration-api  # Runs integration tests
```

### Testing with Real Tokens

```bash
# Option 1: Firebase Emulator
firebase emulators:start --only auth
make api-all  # Automatically uses emulator tokens

# Option 2: Environment variable
export AUTH_TOKEN="your-jwt-token"
make api-all  # Uses provided token

# Option 3: Test mode
make auth-test-on
make api-all  # Uses test tokens
```

### Admin Endpoints

```bash
# Get current config
curl http://localhost:8090/admin/api/v1/admin/config/ \
  -H "X-Admin-Secret: development-secret"

# Update auth mode
curl -X POST http://localhost:8090/admin/api/v1/admin/config/auth \
  -H "X-Admin-Secret: development-secret" \
  -H "Content-Type: application/json" \
  -d '{"mode": "none", "test_mode": false}'
```

## Security Considerations

1. **Production Safety**
   - Test mode automatically disabled in production
   - Admin endpoints require secret in production
   - ENABLED mode enforced in production environment

2. **Token Security**
   - JWTs expire after 1 hour (access) / 30 days (refresh)
   - MCP tokens hashed with SHA-256 before storage
   - Test tokens only work in development with test mode enabled

3. **Best Practices**
   - Always use ENABLED mode for production
   - Use NONE mode only for local development
   - Enable test mode only for integration testing
   - Use Firebase emulator for realistic testing

## Migration Notes

### From Poetry to uv

The project has migrated from Poetry to uv for package management. Firebase dependencies are properly configured in `pyproject.toml`.

### Future Improvements

1. **MCP Compliance**: Migrate to Authorization header for MCP tokens
2. **OAuth 2.1**: Implement full OAuth flow for MCP
3. **Session-based SSE**: Work around EventSource header limitations
4. **Token Rotation**: Automatic token refresh for long-lived connections

## Troubleshooting

### Common Issues

1. **"Invalid Firebase token"**
   - Ensure test mode is enabled: `make auth-test-on`
   - Check environment is development: `dev_test`, `development`, or `test`

2. **Token regenerates every time**
   - Fixed: Script now checks token validity before regenerating
   - Tokens are reused if still valid

3. **Integration tests fail**
   - Make sure Firebase emulator is running: `make emulator-start`
   - Tests will automatically use Firebase emulator for authentication

4. **MCP tokens not working**
   - Ensure you saved the token when created (can't be retrieved later)
   - Check the URL format includes the full token value

## Additional Resources

- [MCP Auth Analysis](./MCP_AUTH_ANALYSIS.md) - Detailed MCP compliance analysis
- [API Testing Guide](../CLAUDE.md) - Quick testing reference
- [Development Workflow](../README.md) - Project setup and commands