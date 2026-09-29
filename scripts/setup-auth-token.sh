#!/bin/bash
# Setup authentication token for API testing
# Uses setup-test-cache.sh to manage test user and workspace

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Simply delegate to setup-test-cache.sh which handles everything
exec "$SCRIPT_DIR/setup-test-cache.sh" "$@"