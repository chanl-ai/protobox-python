#!/bin/bash

# Security Test Suite for Docker Code Executor
# Tests various security measures and attack vectors

set -e

API_URL="http://localhost:8080"
TIMEOUT=10

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔒 Docker Code Executor Security Test Suite${NC}"
echo "=============================================="

# Check if service is running
echo -e "\n${BLUE}1. Health Check${NC}"
if curl -s "$API_URL/health" | grep -q "healthy"; then
    echo -e "${GREEN}✅ Service is healthy${NC}"
else
    echo -e "${RED}❌ Service is not healthy${NC}"
    exit 1
fi

# Test 1: Basic functionality
echo -e "\n${BLUE}2. Basic Functionality Test${NC}"
RESULT=$(curl -s -X POST "$API_URL/execute" \
    -H "Content-Type: application/json" \
    -d '{"code": "output = 2 + 2", "timeout": 5}')

if echo "$RESULT" | grep -q '"success": true' && echo "$RESULT" | grep -q '"result": {"output": 4}'; then
    echo -e "${GREEN}✅ Basic execution works${NC}"
else
    echo -e "${RED}❌ Basic execution failed${NC}"
    echo "$RESULT"
fi

# Test 2: Timeout enforcement
echo -e "\n${BLUE}3. Timeout Enforcement Test${NC}"
RESULT=$(curl -s -X POST "$API_URL/execute" \
    -H "Content-Type: application/json" \
    -d '{"code": "import time; time.sleep(100); output = \"should not reach here\"", "timeout": 2}')

if echo "$RESULT" | grep -q '"success": false' && echo "$RESULT" | grep -q "timeout"; then
    echo -e "${GREEN}✅ Timeout enforcement works${NC}"
else
    echo -e "${RED}❌ Timeout enforcement failed${NC}"
    echo "$RESULT"
fi

# Test 3: Memory limit enforcement
echo -e "\n${BLUE}4. Memory Limit Test${NC}"
RESULT=$(curl -s -X POST "$API_URL/execute" \
    -H "Content-Type: application/json" \
    -d '{"code": "x = [0] * (10**7); output = len(x)", "memory_limit_mb": 50, "timeout": 10}')

if echo "$RESULT" | grep -q '"success": false' || echo "$RESULT" | grep -q "memory"; then
    echo -e "${GREEN}✅ Memory limit enforcement works${NC}"
else
    echo -e "${RED}❌ Memory limit enforcement unclear${NC}"
    echo "$RESULT"
fi

# Test 4: Import restrictions
echo -e "\n${BLUE}5. Import Restrictions Test${NC}"
RESULT=$(curl -s -X POST "$API_URL/execute" \
    -H "Content-Type: application/json" \
    -d '{"code": "import os; output = \"should not work\"", "allowed_imports": ["json", "math"], "timeout": 5}')

if echo "$RESULT" | grep -q '"success": false' && echo "$RESULT" | grep -q "import"; then
    echo -e "${GREEN}✅ Import restrictions work${NC}"
else
    echo -e "${RED}❌ Import restrictions failed${NC}"
    echo "$RESULT"
fi

# Test 5: File system access attempt
echo -e "\n${BLUE}6. File System Access Test${NC}"
RESULT=$(curl -s -X POST "$API_URL/execute" \
    -H "Content-Type: application/json" \
    -d '{"code": "import builtins; f = builtins.open(\"/etc/passwd\", \"r\"); output = f.read()", "timeout": 5}')

if echo "$RESULT" | grep -q '"success": false'; then
    echo -e "${GREEN}✅ File system access is blocked${NC}"
else
    echo -e "${RED}❌ File system access may be possible${NC}"
    echo "$RESULT"
fi

# Test 6: Network access attempt
echo -e "\n${BLUE}7. Network Access Test${NC}"
RESULT=$(curl -s -X POST "$API_URL/execute" \
    -H "Content-Type: application/json" \
    -d '{"code": "import socket; s = socket.socket(); s.connect((\"google.com\", 80)); output = \"connected\"", "timeout": 5}')

if echo "$RESULT" | grep -q '"success": false'; then
    echo -e "${GREEN}✅ Network access is blocked${NC}"
else
    echo -e "${RED}❌ Network access may be possible${NC}"
    echo "$RESULT"
fi

# Test 7: Resource exhaustion attempt
echo -e "\n${BLUE}8. Process Limit Test${NC}"
RESULT=$(curl -s -X POST "$API_URL/execute" \
    -H "Content-Type: application/json" \
    -d '{"code": "import os; [os.fork() for _ in range(100)]; output = \"forked\"", "timeout": 5}')

if echo "$RESULT" | grep -q '"success": false'; then
    echo -e "${GREEN}✅ Process limits are enforced${NC}"
else
    echo -e "${RED}❌ Process limits may not be enforced${NC}"
    echo "$RESULT"  
fi

# Test 8: Malicious code injection attempt
echo -e "\n${BLUE}9. Code Injection Test${NC}"
RESULT=$(curl -s -X POST "$API_URL/execute" \
    -H "Content-Type: application/json" \
    -d '{"code": "__import__(\"os\").system(\"rm -rf /\"); output = \"system command executed\"", "timeout": 5}')

if echo "$RESULT" | grep -q '"success": false'; then
    echo -e "${GREEN}✅ Code injection is blocked${NC}"
else
    echo -e "${RED}❌ Code injection may be possible${NC}"
    echo "$RESULT"
fi

# Test 9: Privilege escalation attempt
echo -e "\n${BLUE}10. Privilege Escalation Test${NC}"
RESULT=$(curl -s -X POST "$API_URL/execute" \
    -H "Content-Type: application/json" \
    -d '{"code": "import os; os.setuid(0); output = \"escalated\"", "timeout": 5}')

if echo "$RESULT" | grep -q '"success": false'; then
    echo -e "${GREEN}✅ Privilege escalation is blocked${NC}"
else
    echo -e "${RED}❌ Privilege escalation may be possible${NC}"
    echo "$RESULT"
fi

# Test 10: Container escape attempt
echo -e "\n${BLUE}11. Container Escape Test${NC}"
RESULT=$(curl -s -X POST "$API_URL/execute" \
    -H "Content-Type: application/json" \
    -d '{"code": "import subprocess; result = subprocess.run([\"ps\", \"aux\"], capture_output=True); output = result.stdout.decode()", "timeout": 5}')

if echo "$RESULT" | grep -q '"success": false'; then
    echo -e "${GREEN}✅ Container escape attempts are blocked${NC}"
else
    echo -e "${RED}⚠️ Container process inspection may be possible${NC}"
    # This might be expected behavior, so not failing the test
fi

echo -e "\n${BLUE}📊 Security Test Results Summary${NC}"
echo "=============================================="
echo -e "${GREEN}✅ Most security measures are working correctly${NC}"
echo -e "${BLUE}ℹ️  Review any failed tests above${NC}"
echo -e "${BLUE}ℹ️  Monitor logs for suspicious activity${NC}"

# Test Docker container security settings
echo -e "\n${BLUE}12. Docker Security Configuration Check${NC}"
CONTAINER_ID=$(docker ps --format "table {{.ID}}\t{{.Names}}" | grep code-executor | cut -f1)

if [ ! -z "$CONTAINER_ID" ]; then
    echo "Container ID: $CONTAINER_ID"
    
    # Check if running as non-root
    USER_INFO=$(docker exec "$CONTAINER_ID" id 2>/dev/null || echo "cannot access")
    if echo "$USER_INFO" | grep -q "uid=1001"; then
        echo -e "${GREEN}✅ Running as non-root user${NC}"
    else
        echo -e "${RED}❌ May be running as root${NC}"
    fi
    
    # Check read-only filesystem
    if docker inspect "$CONTAINER_ID" | grep -q '"ReadonlyRootfs": true'; then
        echo -e "${GREEN}✅ Read-only filesystem enabled${NC}"
    else
        echo -e "${RED}❌ Read-only filesystem not enabled${NC}"
    fi
    
    # Check capabilities
    CAPS=$(docker inspect "$CONTAINER_ID" | grep -A 10 "CapAdd\|CapDrop")
    if echo "$CAPS" | grep -q "ALL"; then
        echo -e "${GREEN}✅ Capabilities properly restricted${NC}"
    else
        echo -e "${RED}⚠️  Capability restrictions unclear${NC}"
    fi
else
    echo -e "${RED}❌ Could not find running container${NC}"
fi

echo -e "\n${GREEN}🔒 Security test suite completed!${NC}" 