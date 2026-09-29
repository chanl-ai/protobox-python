#!/bin/bash
# Setup or refresh test cache for API testing
# Uses email as stable identifier, caches all IDs

set -e

# Configuration
CACHE_FILE=".test-cache.json"
TEST_EMAIL="test@protobox.local"
TEST_PASSWORD="testpass123"
TEST_NAME="Test User"
API_BASE="http://localhost:8090/admin/api/v1"
EMULATOR_BASE="http://localhost:9099"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to get or create Firebase user
get_or_create_firebase_user() {
    local email="$1"
    local password="$2"
    
    # Try to sign in first
    signin_response=$(curl -s -X POST \
        "${EMULATOR_BASE}/identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=fake-api-key" \
        -H "Content-Type: application/json" \
        -d "{\"email\": \"${email}\", \"password\": \"${password}\", \"returnSecureToken\": true}")
    
    # Check if sign in was successful
    id_token=$(echo "$signin_response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('idToken', ''))" 2>/dev/null || echo "")
    
    if [ -n "$id_token" ]; then
        echo -e "${GREEN}✓ Using existing Firebase emulator user${NC}" >&2
        echo "$id_token"
        return 0
    fi
    
    # If sign in failed, create new user
    echo -e "${YELLOW}Creating new Firebase emulator user...${NC}" >&2
    signup_response=$(curl -s -X POST \
        "${EMULATOR_BASE}/identitytoolkit.googleapis.com/v1/accounts:signUp?key=fake-api-key" \
        -H "Content-Type: application/json" \
        -d "{\"email\": \"${email}\", \"password\": \"${password}\", \"returnSecureToken\": true}")
    
    # Extract the ID token
    id_token=$(echo "$signup_response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('idToken', ''))" 2>/dev/null || echo "")
    
    if [ -n "$id_token" ]; then
        echo -e "${GREEN}✓ Created new Firebase emulator user${NC}" >&2
        echo "$id_token"
    else
        echo -e "${RED}Failed to create Firebase user${NC}" >&2
        echo "$signup_response" >&2
        echo ""
    fi
}

# Function to exchange Firebase token for JWT
exchange_token() {
    local firebase_token="$1"
    
    response=$(curl -s -X POST "${API_BASE}/auth/exchange" \
        -H "Content-Type: application/json" \
        -d "{\"firebase_token\": \"${firebase_token}\"}")
    
    echo "$response"
}

# Function to get or create workspace
get_or_create_workspace() {
    local token="$1"
    
    # First, try to get existing workspaces
    workspaces=$(curl -s -H "Authorization: Bearer ${token}" \
        "${API_BASE}/workspaces")
    
    # Check if we have any workspaces
    workspace_count=$(echo "$workspaces" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('workspaces', [])))" 2>/dev/null || echo "0")
    
    if [ "$workspace_count" -gt 0 ]; then
        # Use the first workspace
        workspace_id=$(echo "$workspaces" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['workspaces'][0]['id'])" 2>/dev/null)
        workspace_name=$(echo "$workspaces" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['workspaces'][0].get('name', 'Test Workspace'))" 2>/dev/null || echo "Test Workspace")
        workspace_slug=$(echo "$workspaces" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['workspaces'][0].get('slug', 'test-workspace'))" 2>/dev/null || echo "test-workspace")
    else
        # Create a new workspace
        echo -e "${YELLOW}Creating new test workspace...${NC}" >&2
        new_workspace=$(curl -s -X POST -H "Authorization: Bearer ${token}" \
            -H "Content-Type: application/json" \
            "${API_BASE}/workspaces" \
            -d '{"name": "Test Workspace", "description": "Automated test workspace"}')
        
        workspace_id=$(echo "$new_workspace" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('id', ''))" 2>/dev/null)
        workspace_name="Test Workspace"
        workspace_slug="test-workspace"
    fi
    
    echo "{\"id\": \"${workspace_id}\", \"name\": \"${workspace_name}\", \"slug\": \"${workspace_slug}\"}"
}

# Main logic
main() {
    # Force refresh flag - set by make api command
    FORCE_REFRESH="${FORCE_REFRESH:-false}"

    echo -e "${YELLOW}Setting up test cache...${NC}"

    # Check if cache exists and is recent (less than 1 hour old) - ONLY if not forcing refresh
    if [ "$FORCE_REFRESH" != "true" ] && [ -f "$CACHE_FILE" ]; then
        cache_age=$(($(date +%s) - $(date -r "$CACHE_FILE" +%s 2>/dev/null || echo 0)))
        if [ $cache_age -lt 3600 ]; then
            # Check if token is still valid
            cached_token=$(python3 -c "import json; data=json.load(open('$CACHE_FILE')); print(data.get('test_user', {}).get('last_token', ''))" 2>/dev/null || echo "")
            
            if [ -n "$cached_token" ]; then
                # Validate token
                validation=$(curl -s -H "Authorization: Bearer ${cached_token}" \
                    "${API_BASE}/auth/validate")
                
                is_valid=$(echo "$validation" | python3 -c "import sys, json; data=json.load(sys.stdin); print('true' if data.get('valid', False) else 'false')" 2>/dev/null || echo "false")
                
                if [ "$is_valid" = "true" ]; then
                    echo -e "${GREEN}✓ Using cached test configuration${NC}"
                    
                    # Update .test-token for compatibility
                    echo "$cached_token" > .test-token
                    
                    # Also update .test-workspace-id if it exists in cache
                    workspace_id=$(python3 -c "import json; data=json.load(open('$CACHE_FILE')); print(data.get('test_workspace', {}).get('id', ''))" 2>/dev/null || echo "")
                    if [ -n "$workspace_id" ]; then
                        echo "$workspace_id" > .test-workspace-id
                    fi
                    
                    exit 0
                fi
            fi
        fi
    fi
    
    # Create or refresh cache
    echo -e "${YELLOW}Creating new test session...${NC}"
    
    # Get Firebase token (for emulator, this creates user if needed)
    firebase_token=$(get_or_create_firebase_user "$TEST_EMAIL" "$TEST_PASSWORD")
    
    if [ -z "$firebase_token" ]; then
        echo -e "${RED}Failed to get Firebase token${NC}" >&2
        exit 1
    fi
    
    # Exchange for JWT
    auth_response=$(exchange_token "$firebase_token")
    
    # Extract tokens and user info
    access_token=$(echo "$auth_response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('access_token', ''))" 2>/dev/null || echo "")
    firebase_uid=$(echo "$auth_response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('user', {}).get('uid', ''))" 2>/dev/null || echo "")
    
    if [ -z "$access_token" ]; then
        echo -e "${RED}Failed to exchange Firebase token for JWT${NC}" >&2
        echo "Response: $auth_response" >&2
        exit 1
    fi
    
    # Get or create workspace
    workspace_info=$(get_or_create_workspace "$access_token")
    workspace_id=$(echo "$workspace_info" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['id'])")
    
    # Create cache file
    cat > "$CACHE_FILE" <<EOF
{
  "test_user": {
    "email": "${TEST_EMAIL}",
    "firebase_uid": "${firebase_uid}",
    "name": "${TEST_NAME}",
    "last_token": "${access_token}",
    "token_expires": "$(date -u -v +1H '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -u -d '+1 hour' '+%Y-%m-%dT%H:%M:%SZ')"
  },
  "test_workspace": {
    "id": "${workspace_id}",
    "name": "Test Workspace",
    "slug": "test-workspace"
  },
  "last_updated": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
}
EOF
    
    # Also update legacy files for compatibility
    echo "$access_token" > .test-token
    echo "$workspace_id" > .test-workspace-id
    
    echo -e "${GREEN}✓ Test cache created successfully${NC}"
    echo -e "${GREEN}  Email: ${TEST_EMAIL}${NC}"
    echo -e "${GREEN}  Workspace: ${workspace_id}${NC}"
}

# Run main function
main "$@"