#!/bin/bash

# Git Worktree Port Manager
# Automatically assigns ports based on branch name to avoid conflicts
# Can be overridden by .env.local settings

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get current branch name
BRANCH=$(git branch --show-current 2>/dev/null)

if [ -z "$BRANCH" ]; then
    echo -e "${RED}Error: Not in a git repository${NC}"
    exit 1
fi

# Function to load .env.local if it exists
load_env_local() {
    if [ -f ".env.local" ]; then
        echo -e "${CYAN}Loading configuration from .env.local${NC}"
        # Export variables from .env.local, ignoring comments and empty lines
        set -a
        source <(grep -v '^#' .env.local | grep -v '^$' | sed 's/\r$//')
        set +a
        return 0
    fi
    return 1
}

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to find next available port
find_next_port() {
    local base_port=$1
    local port=$base_port
    while check_port $port; do
        port=$((port + 1))
    done
    echo $port
}

# Load .env.local first to check for overrides
load_env_local

# Check if ports are already defined in .env.local
if [ -n "$WORKTREE_BACKEND_PORT" ]; then
    echo -e "${CYAN}Using backend port from .env.local: $WORKTREE_BACKEND_PORT${NC}"
    BASE_BACKEND_PORT=$WORKTREE_BACKEND_PORT
elif [ -n "$BACKEND_PORT" ]; then
    echo -e "${CYAN}Using backend port from .env.local: $BACKEND_PORT${NC}"
    BASE_BACKEND_PORT=$BACKEND_PORT
else
    # Assign base ports based on branch name
    case "$BRANCH" in
      main)
        BASE_BACKEND_PORT=8090
        BASE_FRONTEND_PORT=3010
        ;;
      develop)
        BASE_BACKEND_PORT=8091
        BASE_FRONTEND_PORT=3011
        ;;
      feature/integrations-management)
        BASE_BACKEND_PORT=8092
        BASE_FRONTEND_PORT=3012
        ;;
      feature/intelligence)
        BASE_BACKEND_PORT=8093
        BASE_FRONTEND_PORT=3013
        ;;
      feature/workflow-manager)
        BASE_BACKEND_PORT=8094
        BASE_FRONTEND_PORT=3014
        ;;
      feature/team-and-user-prefs)
        BASE_BACKEND_PORT=8095
        BASE_FRONTEND_PORT=3015
        ;;
      *)
        # For any other branch, use hash of branch name to generate consistent ports
        HASH=$(echo -n "$BRANCH" | md5sum | cut -c1-4)
        HASH_NUM=$((16#$HASH))
        BASE_BACKEND_PORT=$((8100 + ($HASH_NUM % 100)))
        BASE_FRONTEND_PORT=$((3100 + ($HASH_NUM % 100)))
        ;;
    esac
fi

# Check if frontend port is defined in .env.local
if [ -n "$WORKTREE_FRONTEND_PORT" ]; then
    echo -e "${CYAN}Using frontend port from .env.local: $WORKTREE_FRONTEND_PORT${NC}"
    BASE_FRONTEND_PORT=$WORKTREE_FRONTEND_PORT
elif [ -n "$FRONTEND_PORT" ]; then
    echo -e "${CYAN}Using frontend port from .env.local: $FRONTEND_PORT${NC}"
    BASE_FRONTEND_PORT=$FRONTEND_PORT
fi

# Find available ports starting from base (or use exact if WORKTREE_FORCE_PORTS is set)
if [ "$WORKTREE_FORCE_PORTS" = "true" ]; then
    echo -e "${YELLOW}Force mode: Using exact ports from configuration${NC}"
    BACKEND_PORT=$BASE_BACKEND_PORT
    FRONTEND_PORT=$BASE_FRONTEND_PORT
else
    BACKEND_PORT=$(find_next_port $BASE_BACKEND_PORT)
    FRONTEND_PORT=$(find_next_port $BASE_FRONTEND_PORT)
fi

# Export for use in other scripts
export BACKEND_PORT
export FRONTEND_PORT
export BACKEND_URL="http://localhost:$BACKEND_PORT"
export FRONTEND_URL="http://localhost:$FRONTEND_PORT"

# Function to display current configuration
show_config() {
    echo -e "${BLUE}=== Worktree Port Configuration ===${NC}"
    echo -e "${GREEN}Branch:${NC} $BRANCH"
    echo -e "${GREEN}Backend:${NC} http://localhost:$BACKEND_PORT"
    echo -e "${GREEN}Frontend:${NC} http://localhost:$FRONTEND_PORT"
    
    # Check if preferred ports were available
    if [ "$BACKEND_PORT" != "$BASE_BACKEND_PORT" ]; then
        echo -e "${YELLOW}Note: Backend preferred port $BASE_BACKEND_PORT was busy, using $BACKEND_PORT${NC}"
    fi
    if [ "$FRONTEND_PORT" != "$BASE_FRONTEND_PORT" ]; then
        echo -e "${YELLOW}Note: Frontend preferred port $BASE_FRONTEND_PORT was busy, using $FRONTEND_PORT${NC}"
    fi
    
    echo -e "${BLUE}===================================${NC}"
}

# Function to start backend
start_backend() {
    echo -e "${GREEN}Starting backend on port $BACKEND_PORT...${NC}"
    
    # Create .env.port file with port configuration
    echo "BACKEND_PORT=$BACKEND_PORT" > server/.env.port
    echo "FRONTEND_URL=$FRONTEND_URL" >> server/.env.port
    
    # Start backend with the assigned port
    cd server && uvicorn protobox.admin.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload
}

# Function to start frontend
start_frontend() {
    echo -e "${GREEN}Starting frontend on port $FRONTEND_PORT...${NC}"
    
    # Create .env.local with backend URL
    echo "NEXT_PUBLIC_API_URL=$BACKEND_URL" > client/.env.local
    echo "PORT=$FRONTEND_PORT" >> client/.env.local
    
    # Start frontend with the assigned port
    cd client && PORT=$FRONTEND_PORT npm run dev
}

# Function to start both
start_both() {
    show_config
    echo ""
    echo -e "${GREEN}Starting both services...${NC}"
    echo -e "${YELLOW}Tip: Run these in separate terminals:${NC}"
    echo ""
    echo "  # Terminal 1 - Backend:"
    echo "  $0 backend"
    echo ""
    echo "  # Terminal 2 - Frontend:"
    echo "  $0 frontend"
    echo ""
    echo -e "${BLUE}Or use 'make start' to run both in background${NC}"
}

# Function to show status of all worktree services
status_all() {
    echo -e "${BLUE}=== Worktree Services Status ===${NC}"
    echo ""
    
    # Check common services
    echo -e "${GREEN}Shared Services:${NC}"
    if check_port 27847; then
        echo "  ✅ MongoDB: Running on port 27847"
    else
        echo "  ❌ MongoDB: Not running (start with 'make db-start')"
    fi
    
    if check_port 6381; then
        echo "  ✅ Redis: Running on port 6381"
    else
        echo "  ❌ Redis: Not running (start with 'make db-start')"
    fi
    
    if check_port 9099; then
        echo "  ✅ Firebase Emulator: Running on port 9099"
    else
        echo "  ❌ Firebase Emulator: Not running (start with 'make emulator-start')"
    fi
    
    echo ""
    echo -e "${GREEN}Active Backend Servers:${NC}"
    for port in {8090..8099} {8100..8199}; do
        if check_port $port; then
            echo "  ✅ Backend on port $port"
        fi
    done
    
    echo ""
    echo -e "${GREEN}Active Frontend Servers:${NC}"
    for port in {3010..3015} {3100..3199}; do
        if check_port $port; then
            echo "  ✅ Frontend on port $port"
        fi
    done
}

# Function to kill services for current branch
kill_services() {
    echo -e "${YELLOW}Stopping services for branch: $BRANCH${NC}"
    
    # Try to kill by port
    if check_port $BACKEND_PORT; then
        echo "Stopping backend on port $BACKEND_PORT..."
        lsof -ti:$BACKEND_PORT | xargs kill -9 2>/dev/null
    fi
    
    if check_port $FRONTEND_PORT; then
        echo "Stopping frontend on port $FRONTEND_PORT..."
        lsof -ti:$FRONTEND_PORT | xargs kill -9 2>/dev/null
    fi
    
    echo -e "${GREEN}Services stopped${NC}"
}

# Function to create env template
create_env_template() {
    # Create .env.local template (not checked in)
    cat > .env.local.template << EOF
# Worktree-specific environment variables (.env.local)
# This file is NOT checked into git - copy to .env.local and customize
# Generated for branch: $BRANCH

# Port Configuration - Override automatic port assignment
# Uncomment and modify to use specific ports for this worktree:

# WORKTREE_BACKEND_PORT=8090     # Force specific backend port
# WORKTREE_FRONTEND_PORT=3010    # Force specific frontend port
# WORKTREE_FORCE_PORTS=true      # Use exact ports (don't auto-find free ones)

# OR use standard names (also work):
# BACKEND_PORT=8090
# FRONTEND_PORT=3010

# Current auto-assigned ports for this branch:
BACKEND_PORT=$BACKEND_PORT
FRONTEND_PORT=$FRONTEND_PORT

# API URLs
BACKEND_URL=$BACKEND_URL
FRONTEND_URL=$FRONTEND_URL
NEXT_PUBLIC_API_URL=$BACKEND_URL

# Database Configuration (shared by default, customize to isolate)
MONGODB_URL=mongodb://localhost:27847/mcp_server
REDIS_URL=redis://localhost:6381

# To use a branch-specific database:
# MONGODB_DATABASE=mcp_server_${BRANCH//\//_}

# Firebase Emulator (shared)
FIREBASE_AUTH_EMULATOR_HOST=localhost:9099

# Document Processor (shared)
DOCUMENT_PROCESSOR_URL=https://protobox-doc-processor-staging.fly.dev
# DOCUMENT_PROCESSOR_API_KEY=your-key-here

# Environment-specific settings
ENVIRONMENT=development
# AUTH_TEST_MODE=true  # Uncomment for test mode

# Add any branch-specific overrides below:
# 
EOF
    
    echo -e "${GREEN}Created .env.local.template with port configuration${NC}"
    echo -e "${CYAN}To use custom ports:${NC}"
    echo "  1. Copy to .env.local: ${YELLOW}cp .env.local.template .env.local${NC}"
    echo "  2. Edit .env.local and uncomment/modify port settings"
    echo "  3. The script will automatically use your custom ports"
    echo ""
    echo -e "${BLUE}Priority order:${NC}"
    echo "  1. .env.local overrides (highest priority)"
    echo "  2. Branch-based defaults"
    echo "  3. Auto-find next available port"
}

# Main command handler
case "$1" in
    backend)
        show_config
        start_backend
        ;;
    frontend)
        show_config
        start_frontend
        ;;
    both)
        start_both
        ;;
    config)
        show_config
        ;;
    status)
        status_all
        ;;
    kill)
        kill_services
        ;;
    env)
        create_env_template
        ;;
    *)
        echo "Git Worktree Port Manager"
        echo ""
        echo "Automatically assigns ports based on branch to avoid conflicts"
        echo ""
        echo "Usage: $0 {backend|frontend|both|config|status|kill|env}"
        echo ""
        echo "Commands:"
        echo "  backend   - Start backend with auto-assigned port"
        echo "  frontend  - Start frontend with auto-assigned port"
        echo "  both      - Show commands to start both services"
        echo "  config    - Show port configuration for current branch"
        echo "  status    - Show status of all services across worktrees"
        echo "  kill      - Stop services for current branch"
        echo "  env       - Create .env.worktree template with ports"
        echo ""
        echo "Current branch: $BRANCH"
        echo "Backend would use: http://localhost:$(find_next_port $BASE_BACKEND_PORT)"
        echo "Frontend would use: http://localhost:$(find_next_port $BASE_FRONTEND_PORT)"
        ;;
esac