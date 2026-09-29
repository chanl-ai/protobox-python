#!/bin/bash

# Build and Test Script for MCP Code Executor Docker Container
# Usage: ./build-and-test.sh [local|prod]

set -e

# Configuration
COMPOSE_FILE="docker-compose.local.yml"
ENVIRONMENT="local"

# Parse arguments
if [ "$1" = "prod" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
    ENVIRONMENT="production"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🐳 MCP Code Executor - Build & Test${NC}"
echo "=============================================="
echo -e "${BLUE}Environment: ${ENVIRONMENT}${NC}"
echo -e "${BLUE}Compose File: ${COMPOSE_FILE}${NC}"
echo

# Change to docker directory
cd "$(dirname "$0")/.."

# Build and start services
echo -e "${YELLOW}📦 Building Docker image...${NC}"
docker-compose -f "$COMPOSE_FILE" build --no-cache

echo -e "${YELLOW}🚀 Starting services...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d

# Wait for service to be ready
echo -e "${YELLOW}⏳ Waiting for service to be ready...${NC}"
RETRIES=0
MAX_RETRIES=30
while [ $RETRIES -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8080/health | grep -q "healthy"; then
        echo -e "${GREEN}✅ Service is ready!${NC}"
        break
    fi
    RETRIES=$((RETRIES + 1))
    echo "Waiting... ($RETRIES/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRIES -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ Service failed to start within timeout${NC}"
    docker-compose -f "$COMPOSE_FILE" logs
    exit 1
fi

# Run security tests
echo -e "\n${YELLOW}🔒 Running security tests...${NC}"
./test_security.sh

# Show container information
echo -e "\n${BLUE}📊 Container Information${NC}"
echo "=============================================="
docker-compose -f "$COMPOSE_FILE" ps

# Show resource usage
echo -e "\n${BLUE}💻 Resource Usage${NC}"
echo "=============================================="
CONTAINER_ID=$(docker ps --format "table {{.ID}}\t{{.Names}}" | grep code-executor | cut -f1)
if [ ! -z "$CONTAINER_ID" ]; then
    docker stats "$CONTAINER_ID" --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
fi

# Display useful commands
echo -e "\n${BLUE}🛠️  Useful Commands${NC}"
echo "=============================================="
echo "View logs:           docker-compose -f $COMPOSE_FILE logs -f"
echo "Stop services:       docker-compose -f $COMPOSE_FILE down"
echo "Restart services:    docker-compose -f $COMPOSE_FILE restart"
echo "Shell access:        docker-compose -f $COMPOSE_FILE exec code-executor /bin/sh"
echo "Test API:            curl -X POST http://localhost:8080/execute -H 'Content-Type: application/json' -d '{\"code\": \"output = 2 + 2\", \"timeout\": 5}'"

# Show API endpoints
echo -e "\n${BLUE}🌐 API Endpoints${NC}"
echo "=============================================="
echo "Health:     http://localhost:8080/health"
echo "Metrics:    http://localhost:8080/metrics"
echo "Execute:    http://localhost:8080/execute (POST)"

if [ "$ENVIRONMENT" = "production" ]; then
    echo "Grafana:    http://localhost:3000 (admin/secure_password_here)"
    echo "Prometheus: http://localhost:9090"
    echo "Traefik:    http://localhost:8080"
fi

echo -e "\n${GREEN}🎉 Build and test completed successfully!${NC}" 