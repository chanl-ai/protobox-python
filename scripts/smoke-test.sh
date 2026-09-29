#!/bin/bash
# Comprehensive smoke test for ProtoBox deployment

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
BACKEND_URL=${BACKEND_URL:-"http://localhost:8090"}
FRONTEND_URL=${FRONTEND_URL:-"http://localhost:3010"}
ENVIRONMENT=${ENVIRONMENT:-"production"}

echo -e "${YELLOW}🔥 Running Smoke Tests for ${ENVIRONMENT}${NC}"
echo "================================================"
echo "Backend:  $BACKEND_URL"
echo "Frontend: $FRONTEND_URL"
echo ""

# Track test results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Test function
test_endpoint() {
    local url=$1
    local expected_status=$2
    local description=$3
    local check_json=${4:-false}
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -n "Testing $description... "
    
    response=$(curl -s -w "\n%{http_code}" "$url" 2>/dev/null || echo "000")
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$status_code" = "$expected_status" ]; then
        if [ "$check_json" = "true" ] && [ -n "$body" ]; then
            if echo "$body" | jq . >/dev/null 2>&1; then
                echo -e "${GREEN}✅ PASS${NC} (Valid JSON)"
                PASSED_TESTS=$((PASSED_TESTS + 1))
            else
                echo -e "${RED}❌ FAIL${NC} (Invalid JSON)"
                FAILED_TESTS=$((FAILED_TESTS + 1))
                echo "  Response: $body"
            fi
        else
            echo -e "${GREEN}✅ PASS${NC} (HTTP $status_code)"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        fi
    else
        echo -e "${RED}❌ FAIL${NC} (Expected $expected_status, got $status_code)"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        if [ "$status_code" != "000" ] && [ -n "$body" ]; then
            echo "  Response: $body" | head -n 3
        fi
    fi
}

# Backend API Tests
echo -e "${YELLOW}Backend API Tests${NC}"
echo "-----------------------------------"

# Basic health check
test_endpoint "$BACKEND_URL/admin/api/v1/health" "200" "Health endpoint" true

# Check health endpoint details
health_response=$(curl -s "$BACKEND_URL/admin/api/v1/health")
if echo "$health_response" | jq -e '.components.database.status == "healthy"' >/dev/null 2>&1; then
    echo -e "  ✅ Database connection: ${GREEN}healthy${NC}"
else
    echo -e "  ❌ Database connection: ${RED}unhealthy${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Test monitoring endpoints (if monitoring key is available)
echo "  🔍 Testing monitoring endpoints..."
if [ -n "$MCP_MONITORING_API_KEY" ]; then
    TOTAL_TESTS=$((TOTAL_TESTS + 3))
    
    # Test monitoring metrics
    metrics_response=$(curl -s -w "\n%{http_code}" -H "X-Monitoring-Key: $MCP_MONITORING_API_KEY" "$BACKEND_URL/admin/api/v1/monitoring/metrics" 2>/dev/null || echo "000")
    metrics_status=$(echo "$metrics_response" | tail -n1)
    
    if [ "$metrics_status" = "200" ]; then
        echo -e "  ✅ Monitoring metrics: ${GREEN}accessible${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "  ❌ Monitoring metrics: ${RED}failed (HTTP $metrics_status)${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    
    # Test monitoring environment
    env_response=$(curl -s -w "\n%{http_code}" -H "X-Monitoring-Key: $MCP_MONITORING_API_KEY" "$BACKEND_URL/admin/api/v1/monitoring/environment" 2>/dev/null || echo "000")
    env_status=$(echo "$env_response" | tail -n1)
    
    if [ "$env_status" = "200" ]; then
        echo -e "  ✅ Monitoring environment: ${GREEN}accessible${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        
        # Check if CORS is properly configured
        env_body=$(echo "$env_response" | sed '$d')
        if echo "$env_body" | jq -e '.app_protobox_allowed == true' >/dev/null 2>&1; then
            echo -e "  ✅ CORS configuration: ${GREEN}frontend origin allowed${NC}"
        else
            echo -e "  ⚠️  CORS configuration: ${YELLOW}check CORS_ALLOWED_ORIGINS${NC}"
        fi
    else
        echo -e "  ❌ Monitoring environment: ${RED}failed (HTTP $env_status)${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    
    # Test monitoring readiness probe
    ready_response=$(curl -s -w "\n%{http_code}" "$BACKEND_URL/admin/api/v1/monitoring/ready" 2>/dev/null || echo "000")
    ready_status=$(echo "$ready_response" | tail -n1)
    
    if [ "$ready_status" = "200" ]; then
        echo -e "  ✅ Readiness probe: ${GREEN}ready${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "  ❌ Readiness probe: ${RED}not ready (HTTP $ready_status)${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
else
    echo -e "  ⚠️  Monitoring tests skipped: ${YELLOW}MCP_MONITORING_API_KEY not set${NC}"
fi

# API documentation
test_endpoint "$BACKEND_URL/docs" "200" "API documentation"

# Auth endpoints (should require authentication)
test_endpoint "$BACKEND_URL/admin/api/v1/workspaces" "401" "Workspaces (auth required)"

# Client Token Exchange Simulation (as requested)
echo "  🔐 Testing token exchange simulation..."
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Test with invalid token (should fail gracefully)
exchange_response=$(curl -s -w "\n%{http_code}" -X POST "$BACKEND_URL/admin/api/v1/auth/exchange" \
    -H "Content-Type: application/json" \
    -d '{"firebase_token": "invalid_test_token"}' 2>/dev/null || echo "000")

exchange_status=$(echo "$exchange_response" | tail -n1)
exchange_body=$(echo "$exchange_response" | sed '$d')

if [ "$exchange_status" = "401" ] || [ "$exchange_status" = "400" ]; then
    echo -e "  ✅ Token exchange properly rejects invalid tokens (HTTP $exchange_status)"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "  ❌ Token exchange unexpected response (HTTP $exchange_status)"
    FAILED_TESTS=$((FAILED_TESTS + 1))
    if [ "$exchange_status" != "000" ] && [ -n "$exchange_body" ]; then
        echo "    Response: $exchange_body" | head -n 1
    fi
fi

# MCP public endpoints - TODO: Fix MCP endpoint routing in production
# test_endpoint "$BACKEND_URL/mcp/tenants/6883c972274b0349b71b5ff2/sse" "200" "MCP SSE endpoint"
echo "  ⚠️  MCP SSE endpoint test skipped (known issue in production)"

echo ""

# Frontend Tests
echo -e "${YELLOW}Frontend Tests${NC}"
echo "-----------------------------------"

# Basic accessibility
test_endpoint "$FRONTEND_URL" "200" "Homepage"
test_endpoint "$FRONTEND_URL/login" "200" "Login page"
test_endpoint "$FRONTEND_URL/signup" "200" "Signup page"
test_endpoint "$FRONTEND_URL/favicon.ico" "200" "Static assets accessible"

# Check for common issues
echo ""
echo -e "${YELLOW}Configuration Checks${NC}"
echo "-----------------------------------"

# Check if frontend can reach backend
api_check=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/admin/api/v1/health" --max-time 5)
if [ "$api_check" = "200" ]; then
    echo -e "✅ Backend API is reachable"
else
    echo -e "❌ Backend API is not reachable"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Check for CORS headers
cors_check=$(curl -s -I "$BACKEND_URL/admin/api/v1/health" -H "Origin: $FRONTEND_URL" | grep -i "access-control-allow-origin" || echo "")
if [ -n "$cors_check" ]; then
    echo -e "✅ CORS headers present"
else
    echo -e "⚠️  CORS headers might not be configured"
fi

# Summary
echo ""
echo -e "${YELLOW}Test Summary${NC}"
echo "-----------------------------------"
echo "Total Tests: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✅ All smoke tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please investigate before proceeding.${NC}"
    exit 1
fi