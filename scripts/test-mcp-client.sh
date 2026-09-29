#!/bin/bash
set -e

# MCP Client Testing Script
# Tests MCP endpoints directly as an MCP client would

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration - Environment aware
ENV_NAME=${ENV:-local}

if [[ "$ENV_NAME" == "staging" ]]; then
    BASE_URL="http://localhost:8090"
elif [[ "$ENV_NAME" == "production" ]]; then
    BASE_URL="http://localhost:8090"
else
    BASE_URL="http://localhost:8090"
fi

ADMIN_API_URL="$BASE_URL/admin/api/v1"

# Usage function
usage() {
    echo "Usage: $0 [workspace_id] [command] [args...]"
    echo ""
    echo "Commands:"
    echo "  info                    - Get MCP server info"
    echo "  list-tools              - List available MCP tools"
    echo "  call-tool <name> [args] - Call a specific tool"
    echo "  search-kb <query>       - Search knowledge base"
    echo "  test-action <name>      - Test a workspace action"
    echo "  full-test              - Run comprehensive MCP test suite"
    echo ""
    echo "Examples:"
    echo "  $0 689ce93ac66218cb8cff5637 info"
    echo "  $0 689ce93ac66218cb8cff5637 list-tools"
    echo "  $0 689ce93ac66218cb8cff5637 call-tool test-dummy-action"
    echo "  $0 689ce93ac66218cb8cff5637 search-kb 'authentication guide'"
    echo "  $0 689ce93ac66218cb8cff5637 full-test"
    echo ""
    echo "Environment variables:"
    echo "  MCP_TOKEN - MCP authentication token (auto-generated if not set)"
    echo "  JWT_TOKEN - JWT token for admin API access (auto-generated if not set)"
    exit 1
}

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}" >&2
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}" >&2
}

log_error() {
    echo -e "${RED}❌ $1${NC}" >&2
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" >&2
}

# Get authentication tokens
get_auth_tokens() {
    local workspace_id="$1"
    
    if [[ -z "$JWT_TOKEN" ]]; then
        if [[ "$ENV_NAME" == "local" ]]; then
            log_info "Getting JWT token from Firebase emulator..."
            if [[ -f ".test-token" ]]; then
                JWT_TOKEN=$(cat .test-token | tr -d '\n')
                log_success "Using cached JWT token"
            else
                log_error "No JWT token found. Run: ./scripts/setup-auth-token.sh"
                exit 1
            fi
        else
            # For staging/production, use cached token from remote auth setup
            local cache_file=".test-cache-${ENV_NAME}.json"
            log_info "Getting JWT token from ${ENV_NAME} cache..."
            if [[ -f "$cache_file" ]]; then
                JWT_TOKEN=$(jq -r '.access_token' "$cache_file")
                if [[ "$JWT_TOKEN" == "null" || -z "$JWT_TOKEN" ]]; then
                    log_error "No valid access token in $cache_file. Run: ./scripts/setup-remote-test-auth.sh $ENV_NAME"
                    exit 1
                fi
                log_success "Using cached JWT token from $cache_file"
            else
                log_error "No auth cache found: $cache_file. Run: ./scripts/setup-remote-test-auth.sh $ENV_NAME"
                exit 1
            fi
        fi
    fi
    
    if [[ -z "$MCP_TOKEN" ]]; then
        log_info "Creating MCP token for workspace $workspace_id..."
        local response=$(curl -s -X POST "$ADMIN_API_URL/workspaces/$workspace_id/mcp-tokens/" \
            -H "Authorization: Bearer $JWT_TOKEN" \
            -H "Content-Type: application/json" \
            -d '{"name": "mcp-test-client-token"}')
        
        if echo "$response" | grep -q '"token"'; then
            MCP_TOKEN=$(echo "$response" | jq -r '.token')
            log_success "Created MCP token: ${MCP_TOKEN:0:20}..."
        else
            log_error "Failed to create MCP token: $response"
            exit 1
        fi
    fi
}

# Get MCP server info
mcp_info() {
    local workspace_id="$1"
    log_info "Getting MCP server info..." >&2
    
    curl -s -X GET "$BASE_URL/mcp/$workspace_id/" \
        -H "Authorization: Bearer $MCP_TOKEN" \
        -H "Content-Type: application/json" | jq .
}

# List available tools
mcp_list_tools() {
    local workspace_id="$1"
    log_info "Listing available MCP tools..." >&2
    
    curl -s -X POST "$BASE_URL/mcp/$workspace_id/tools/list" \
        -H "Authorization: Bearer $MCP_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 1}' | jq '.result.tools'
}

# Call a specific tool
mcp_call_tool() {
    local workspace_id="$1"
    local tool_name="$2"
    local tool_args="${3:-{}}"
    
    log_info "Calling MCP tool: $tool_name" >&2
    
    # Parse tool_args if it's a string of key=value pairs
    if [[ "$tool_args" != "{"* ]]; then
        local json_args="{"
        local first=true
        IFS=',' read -ra PAIRS <<< "$tool_args"
        for pair in "${PAIRS[@]}"; do
            if [[ $pair =~ ^([^=]+)=(.+)$ ]]; then
                local key="${BASH_REMATCH[1]}"
                local value="${BASH_REMATCH[2]}"
                if [[ $first == true ]]; then
                    first=false
                else
                    json_args+=","
                fi
                json_args+="\"$key\": \"$value\""
            fi
        done
        json_args+="}"
        tool_args="$json_args"
    fi
    
    local payload=$(cat << EOF
{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "$tool_name",
        "arguments": $tool_args
    },
    "id": $(date +%s)
}
EOF
    )
    
    curl -s -X POST "$BASE_URL/mcp/$workspace_id/tools/call" \
        -H "Authorization: Bearer $MCP_TOKEN" \
        -H "Content-Type: application/json" \
        -d "$payload" | jq .
}

# Search knowledge base
mcp_search_kb() {
    local workspace_id="$1"
    local query="$2"
    local max_results="${3:-5}"
    
    log_info "Searching knowledge base: '$query'"
    
    mcp_call_tool "$workspace_id" "search_knowledge_base" "{\"query\": \"$query\", \"max_results\": $max_results}"
}

# Test a workspace action
mcp_test_action() {
    local workspace_id="$1"
    local action_name="$2"
    local action_args="${3:-{}}"
    
    log_info "Testing workspace action: $action_name"
    
    mcp_call_tool "$workspace_id" "$action_name" "$action_args"
}

# Run comprehensive test suite
mcp_full_test() {
    local workspace_id="$1"
    
    log_info "Running comprehensive MCP test suite..."
    echo "======================================================="
    
    # Test 1: Server info
    echo -e "\n${BLUE}1. MCP Server Info${NC}"
    echo "-------------------"
    mcp_info "$workspace_id"
    
    # Test 2: List tools
    echo -e "\n${BLUE}2. Available Tools${NC}"
    echo "-------------------"
    local tools=$(mcp_list_tools "$workspace_id")
    echo "$tools"
    
    # Test 3: Count tools
    local tool_count=$(echo "$tools" | jq '. | length')
    log_success "Found $tool_count available tools"
    
    # Test 4: Test each tool (safely)
    echo -e "\n${BLUE}3. Tool Testing${NC}"
    echo "----------------"
    
    # Get tool names
    local tool_names=$(echo "$tools" | jq -r '.[].name')
    
    while IFS= read -r tool_name; do
        case "$tool_name" in
            "search_knowledge_base")
                log_info "Testing KB search..."
                mcp_search_kb "$workspace_id" "test query" 3 > /dev/null 2>&1
                if [[ $? -eq 0 ]]; then
                    log_success "KB search tool working"
                else
                    log_warning "KB search tool failed (may be expected if no KB content)"
                fi
                ;;
            *"dummy"*|*"test"*)
                log_info "Testing action: $tool_name"
                local result=$(mcp_test_action "$workspace_id" "$tool_name" "{}" 2>/dev/null)
                if echo "$result" | grep -q '"result"'; then
                    log_success "Action $tool_name executed successfully"
                else
                    log_warning "Action $tool_name failed or returned error"
                fi
                ;;
            *)
                log_info "Skipping tool: $tool_name (not safe to auto-test)"
                ;;
        esac
    done <<< "$tool_names"
    
    # Test 5: Error handling
    echo -e "\n${BLUE}4. Error Handling${NC}"
    echo "------------------"
    
    log_info "Testing invalid tool call..."
    local error_result=$(mcp_call_tool "$workspace_id" "nonexistent-tool" "{}" 2>/dev/null)
    if echo "$error_result" | grep -q '"error"'; then
        log_success "Error handling working correctly"
    else
        log_warning "Unexpected response to invalid tool call"
    fi
    
    echo -e "\n${GREEN}✅ MCP Test Suite Complete${NC}"
    echo "======================================================="
}

# Main script logic
main() {
    if [[ $# -lt 2 ]]; then
        usage
    fi
    
    local workspace_id="$1"
    local command="$2"
    shift 2
    
    # Validate workspace ID format
    if [[ ! "$workspace_id" =~ ^[a-f0-9]{24}$ ]]; then
        log_error "Invalid workspace ID format: $workspace_id"
        log_error "Expected 24-character hexadecimal MongoDB ObjectId"
        exit 1
    fi
    
    # Get authentication tokens
    get_auth_tokens "$workspace_id"
    
    # Execute command
    case "$command" in
        "info")
            mcp_info "$workspace_id"
            ;;
        "list-tools")
            mcp_list_tools "$workspace_id"
            ;;
        "call-tool")
            if [[ $# -lt 1 ]]; then
                log_error "Tool name required"
                exit 1
            fi
            mcp_call_tool "$workspace_id" "$1" "${2:-{}}"
            ;;
        "search-kb")
            if [[ $# -lt 1 ]]; then
                log_error "Search query required"
                exit 1
            fi
            mcp_search_kb "$workspace_id" "$1" "${2:-5}"
            ;;
        "test-action")
            if [[ $# -lt 1 ]]; then
                log_error "Action name required"
                exit 1
            fi
            mcp_test_action "$workspace_id" "$1" "${2:-{}}"
            ;;
        "full-test")
            mcp_full_test "$workspace_id"
            ;;
        *)
            log_error "Unknown command: $command"
            usage
            ;;
    esac
}

# Run main function
main "$@"