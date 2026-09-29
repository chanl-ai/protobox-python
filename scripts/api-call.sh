#!/bin/bash
# Environment-aware API call wrapper that uses existing lcurl.sh and handles tokens automatically

# Environment detection
TEST_ENVIRONMENT="${TEST_ENVIRONMENT:-local}"

# Set base URL based on environment
case "$TEST_ENVIRONMENT" in
    "staging")
        BASE_URL="http://localhost:8090"
        ;;
    "production")
        BASE_URL="http://localhost:8090"
        ;;
    "local"|*)
        BASE_URL="http://localhost:8090"
        ;;
esac

# Environment-aware token setup
if [ "$TEST_ENVIRONMENT" = "local" ]; then
    # For local, ensure test cache is fresh (handles token regeneration)
    # Check if cache exists and token is still valid
    if [ -f ".test-cache.json" ]; then
        # Check token expiry
        token_expires=$(python3 -c "import json, datetime; data=json.load(open('.test-cache.json')); exp=data.get('test_user', {}).get('token_expires', ''); print(exp)" 2>/dev/null || echo "")
        now=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
        
        # If token is expired or about to expire (within 5 minutes), refresh
        if [ -z "$token_expires" ] || [ "$token_expires" \< "$now" ]; then
            echo "Refreshing local auth token..." >&2
            ./scripts/setup-test-cache.sh >/dev/null 2>&1
        fi
    else
        echo "Setting up local auth token..." >&2
        ./scripts/setup-test-cache.sh >/dev/null 2>&1
    fi
else
    # For remote environments, ensure remote auth is set up
    echo "Setting up $TEST_ENVIRONMENT auth token..." >&2
    ./scripts/setup-remote-test-auth.sh "$TEST_ENVIRONMENT" >/dev/null 2>&1
fi

# Default values
METHOD="${2:-GET}"
DATA="$3"

# Show usage if no endpoint provided
if [ -z "$1" ]; then
    echo "Usage: [TEST_ENVIRONMENT=local|staging|production] ./scripts/api-call.sh <endpoint> [method] [data]"
    echo ""
    echo "Current environment: $TEST_ENVIRONMENT"
    echo "Current base URL: $BASE_URL"
    echo ""
    echo "Examples:"
    echo "  ./scripts/api-call.sh /admin/api/v1/health"
    echo "  ./scripts/api-call.sh /admin/api/v1/workspaces"
    echo "  TEST_ENVIRONMENT=staging ./scripts/api-call.sh /admin/api/v1/health"
    echo "  TEST_ENVIRONMENT=production ./scripts/api-call.sh /admin/api/v1/workspaces"
    echo "  ./scripts/api-call.sh /admin/api/v1/workspaces/689ce848340dc27cc48dab11/actions"
    echo "  ./scripts/api-call.sh /admin/api/v1/workspaces/689ce848340dc27cc48dab11/actions POST '{\"name\":\"test\",\"type\":\"REST\"}'"
    echo ""
    exit 1
fi

# Set up authentication token for lcurl.sh
if [ "$TEST_ENVIRONMENT" != "local" ]; then
    # For remote environments, extract token from cache file
    CACHE_FILE=".test-cache-${TEST_ENVIRONMENT}.json"
    if [ -f "$CACHE_FILE" ]; then
        export AUTH_TOKEN=$(python3 -c "import json; print(json.load(open('$CACHE_FILE')).get('access_token', ''))" 2>/dev/null || echo "")
    fi
fi

# Make the API call using lcurl.sh
if [ -n "$DATA" ]; then
    ./scripts/lcurl.sh -s -X "$METHOD" "${BASE_URL}${1}" \
        -H "Content-Type: application/json" \
        -d "$DATA" | python3 -m json.tool 2>/dev/null || echo "Request failed"
else
    ./scripts/lcurl.sh -s -X "$METHOD" "${BASE_URL}${1}" \
        -H "Content-Type: application/json" | python3 -m json.tool 2>/dev/null || echo "Request failed"
fi