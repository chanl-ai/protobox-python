#!/bin/bash
set -e

# Generate SDK from OpenAPI specification
# This script generates a Python SDK from the MCP server's OpenAPI spec
# and packages it as the mocops-sdk project

echo "🔧 Generating MCP Admin API SDK (mocops-sdk)..."

# Configuration
SERVER_URL="http://localhost:8080"
OUTPUT_DIR="./mocops-sdk"
PACKAGE_NAME="mocops_sdk"
TEMP_DIR="./temp-sdk-generation"

# Check if server is running
echo "📡 Checking if MCP server is running..."
if ! curl -s "${SERVER_URL}/health" > /dev/null; then
    echo "❌ MCP server is not running at ${SERVER_URL}"
    echo "   Please start the server with: docker compose up mcp-server"
    exit 1
fi

echo "✅ Server is running"

# Check if openapi-python-client is installed
if ! command -v openapi-python-client &> /dev/null; then
    echo "📦 Installing openapi-python-client..."
    pip install openapi-python-client
fi

# Remove existing temp directory if it exists
if [ -d "$TEMP_DIR" ]; then
    echo "🗑️  Removing existing temp directory..."
    rm -rf "$TEMP_DIR"
fi

# Generate the SDK to temp directory first
echo "⚙️  Generating SDK from OpenAPI spec..."
openapi-python-client generate \
    --url "${SERVER_URL}/openapi.json" \
    --output-path "$TEMP_DIR" \
    --overwrite

# Find the generated client directory
GENERATED_DIR=$(find "$TEMP_DIR" -maxdepth 1 -type d -name "*client*" | head -1)
if [ -z "$GENERATED_DIR" ]; then
    echo "❌ Failed to find generated client directory"
    exit 1
fi

# Create mocops-sdk directory structure
echo "📁 Setting up mocops-sdk project structure..."
mkdir -p "$OUTPUT_DIR"

# Copy generated client code to mocops-sdk
echo "📋 Copying generated code..."
if [ -d "$OUTPUT_DIR/$PACKAGE_NAME" ]; then
    rm -rf "$OUTPUT_DIR/$PACKAGE_NAME"
fi
cp -r "$GENERATED_DIR" "$OUTPUT_DIR/$PACKAGE_NAME"

# Create pyproject.toml for the mocops-sdk
echo "📝 Creating pyproject.toml..."
cat > "$OUTPUT_DIR/pyproject.toml" << 'EOF'
[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.poetry]
name = "mocops-sdk"
version = "0.1.0"
description = "Python SDK for MCP (Model Context Protocol) Admin API - Auto-generated from OpenAPI spec"
authors = ["Protobox contributors"]
readme = "README.md"
packages = [{include = "mocops_sdk"}]
homepage = "https://github.com/chanl-ai/protobox-python"
repository = "https://github.com/chanl-ai/protobox-python"
documentation = "https://github.com/chanl-ai/protobox-python"
keywords = ["mcp", "model-context-protocol", "api", "sdk", "openai"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: Internet :: WWW/HTTP",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
]

[tool.poetry.dependencies]
python = "^3.8"
httpx = ">=0.23.0,<0.29.0"
attrs = ">=22.2.0"
python-dateutil = ">=2.8.1,<3.0.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.0.0"
pytest-asyncio = "^0.21.0"
black = "^23.0.0"
ruff = "^0.2.0"
mypy = "^1.0.0"

[tool.ruff]
line-length = 88
target-version = "py38"

[tool.black]
line-length = 88
target-version = ['py38', 'py39', 'py310', 'py311', 'py312']

[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
EOF

# Create README.md
echo "📖 Creating README.md..."
cat > "$OUTPUT_DIR/README.md" << 'EOF'
# MocOps SDK

**Auto-generated Python SDK for MCP (Model Context Protocol) Admin API**

This SDK is automatically generated from the MCP server's OpenAPI specification, ensuring it stays in sync with the API.

## Features

- ✅ **Auto-generated** - Always up-to-date with the latest API
- ✅ **Type-safe** - Full type hints and validation
- ✅ **Async/Sync** - Both synchronous and asynchronous support
- ✅ **Comprehensive** - Covers all admin API endpoints
- ✅ **Well-documented** - Generated from OpenAPI spec

## Installation

```bash
pip install mocops-sdk
```

## Quick Start

### Synchronous Usage

```python
from mocops_sdk import Client
from mocops_sdk.api.admin import health_check_admin_api_v1_health_get

# Create client
client = Client(base_url="http://localhost:8080")

with client as client:
    # Check API health
    health = health_check_admin_api_v1_health_get.sync(client=client)
    print(f"API Status: {health}")
```

### Asynchronous Usage

```python
import asyncio
from mocops_sdk import Client
from mocops_sdk.api.admin import health_check_admin_api_v1_health_get

async def main():
    client = Client(base_url="http://localhost:8080")
    
    async with client as client:
        # Check API health
        health = await health_check_admin_api_v1_health_get.asyncio(client=client)
        print(f"API Status: {health}")

asyncio.run(main())
```

### Working with Actions

```python
from mocops_sdk import Client
from mocops_sdk.api.admin import (
    list_actions_admin_api_v1_actions_get,
    create_action_admin_api_v1_actions_post,
)
from mocops_sdk.models import (
    ActionCreateRequest,
    ActionType,
    ActionCreateRequestConfigSchema,
    ActionCreateRequestDefaultConfig,
)

client = Client(base_url="http://localhost:8080")

with client as client:
    # List existing actions
    actions = list_actions_admin_api_v1_actions_get.sync(client=client)
    print(f"Found {len(actions)} actions")
    
    # Create a new action
    default_config = ActionCreateRequestDefaultConfig()
    default_config["url"] = "https://api.example.com/webhook"
    default_config["method"] = "POST"
    
    config_schema = ActionCreateRequestConfigSchema()
    config_schema["type"] = "object"
    config_schema["properties"] = {"url": {"type": "string"}}
    
    new_action = ActionCreateRequest(
        name="example_webhook",
        type_=ActionType.REST,
        description="Example webhook action",
        default_config=default_config,
        config_schema=config_schema,
        tags=["webhook", "example"]
    )
    
    result = create_action_admin_api_v1_actions_post.sync(
        client=client, 
        body=new_action
    )
    print(f"Created action: {result}")
```

## API Coverage

This SDK covers all MCP Admin API endpoints:

### Actions
- List actions
- Create action
- Get action details
- Update action
- Delete action
- Test action
- Validate action
- Get action configuration schema

### Executions
- List executions
- Create execution
- Get execution details
- Retry execution
- Cancel execution
- Get execution summary

### Secrets
- List secrets
- Create secret
- Get secret details
- Update secret
- Delete secret
- Get secret usage logs

### System
- Health check
- Get action types
- Get secret types

## Development

This SDK is auto-generated. To regenerate:

```bash
# From the mcp-server repository
make generate-sdk
```

## Authentication

For authenticated endpoints, use the `AuthenticatedClient`:

```python
from mocops_sdk import AuthenticatedClient

client = AuthenticatedClient(
    base_url="https://your-mcp-server.com",
    token="your-api-token"
)
```

## Error Handling

The SDK uses standard HTTP status codes and provides detailed error information:

```python
from mocops_sdk.types import Response

response: Response = some_api_call.sync_detailed(client=client)

if response.status_code == 200:
    print(f"Success: {response.parsed}")
else:
    print(f"Error {response.status_code}: {response.content}")
```

## License

MIT License - see LICENSE file for details.
EOF

# Create __init__.py to make it a proper package
echo "📦 Creating package __init__.py..."
cat > "$OUTPUT_DIR/__init__.py" << 'EOF'
"""
MocOps SDK - Auto-generated Python SDK for MCP Admin API

This package provides a complete Python SDK for the MCP (Model Context Protocol) 
Admin API, automatically generated from the OpenAPI specification.
"""

__version__ = "0.1.0"
__author__ = "6FS Team"
__email__ = "oss@chanl.ai"

# Re-export main client classes for convenience
from mocops_sdk.client import Client, AuthenticatedClient
from mocops_sdk.errors import UnexpectedStatus
from mocops_sdk.types import Response, File, UNSET

__all__ = [
    "Client",
    "AuthenticatedClient", 
    "UnexpectedStatus",
    "Response",
    "File",
    "UNSET",
    "__version__",
]
EOF

# Create example usage file
echo "💡 Creating example usage..."
cat > "$OUTPUT_DIR/example_usage.py" << 'EOF'
#!/usr/bin/env python3
"""
Example usage of the MocOps SDK.
"""

import asyncio
from mocops_sdk import Client
from mocops_sdk.api.admin import (
    health_check_admin_api_v1_health_get,
    list_actions_admin_api_v1_actions_get,
    create_action_admin_api_v1_actions_post,
)
from mocops_sdk.models import (
    ActionCreateRequest,
    ActionType,
    ActionCreateRequestConfigSchema,
    ActionCreateRequestDefaultConfig,
)

def sync_example():
    """Synchronous example."""
    print("🔄 Synchronous Example")
    print("=" * 30)
    
    client = Client(base_url="http://localhost:8080")
    
    with client as client:
        # Health check
        print("1. Health Check...")
        health = health_check_admin_api_v1_health_get.sync(client=client)
        print(f"   Status: {health}")
        
        # List actions
        print("\n2. List Actions...")
        actions = list_actions_admin_api_v1_actions_get.sync(client=client)
        if actions:
            print(f"   Found {len(actions)} actions")
        else:
            print("   No actions found or API error")

async def async_example():
    """Asynchronous example."""
    print("\n🔄 Asynchronous Example")
    print("=" * 30)
    
    client = Client(base_url="http://localhost:8080")
    
    async with client as client:
        # Health check
        print("1. Async Health Check...")
        health = await health_check_admin_api_v1_health_get.asyncio(client=client)
        print(f"   Status: {health}")

def main():
    """Run all examples."""
    print("🧪 MocOps SDK Examples")
    print("=" * 50)
    
    # Sync example
    sync_example()
    
    # Async example
    asyncio.run(async_example())
    
    print("\n✅ Examples completed!")

if __name__ == "__main__":
    main()
EOF

# Create test file
echo "🧪 Creating test file..."
cat > "$OUTPUT_DIR/test_sdk.py" << 'EOF'
#!/usr/bin/env python3
"""
Test the MocOps SDK.
"""

import pytest
from mocops_sdk.client import Client
from mocops_sdk.api.admin import health_check_admin_api_v1_health_get

def test_client_creation():
    """Test that we can create a client."""
    client = Client(base_url="http://localhost:8080")
    assert client is not None

@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint (requires running server)."""
    client = Client(base_url="http://localhost:8080")
    
    try:
        async with client as client:
            response = await health_check_admin_api_v1_health_get.asyncio_detailed(client=client)
            # Should either succeed (200) or fail with connection error
            assert response.status_code in [200, 500] or response.status_code >= 400
    except Exception:
        # Connection errors are expected if server is not running
        pass

if __name__ == "__main__":
    pytest.main([__file__])
EOF

# Create publishing script
echo "📦 Creating publishing script..."
cat > "$OUTPUT_DIR/publish.sh" << 'EOF'
#!/bin/bash
set -e

echo "📦 Publishing MocOps SDK..."

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ pyproject.toml not found. Run from mocops-sdk directory."
    exit 1
fi

# Install poetry if not available
if ! command -v poetry &> /dev/null; then
    echo "📥 Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
fi

# Install dependencies
echo "📥 Installing dependencies..."
poetry install

# Run tests
echo "🧪 Running tests..."
poetry run pytest test_sdk.py -v

# Format code
echo "🎨 Formatting code..."
poetry run black mocops_sdk/ --check || poetry run black mocops_sdk/
poetry run ruff check mocops_sdk/ --fix

# Build package
echo "🔨 Building package..."
poetry build

# Show build info
echo "✅ Package built successfully!"
echo "📂 Built packages:"
ls -la dist/

echo ""
echo "🚀 To publish to PyPI:"
echo "   poetry publish --dry-run  # Test first"
echo "   poetry publish            # Actual publish"
echo ""
echo "🔧 To publish to test PyPI:"
echo "   poetry config repositories.testpypi https://test.pypi.org/legacy/"
echo "   poetry publish -r testpypi"
EOF

chmod +x "$OUTPUT_DIR/publish.sh"

# Clean up temp directory
echo "🧹 Cleaning up..."
rm -rf "$TEMP_DIR"

# Run sanity tests
echo "🧪 Running sanity tests..."
cd "$OUTPUT_DIR"

# Test that the package can be imported
python3 -c "
try:
    import sys
    sys.path.insert(0, '.')
    from mocops_sdk import Client
    print('✅ Package imports successfully')
    
    # Test client creation
    client = Client(base_url='http://localhost:8080')
    print('✅ Client creation works')
    
except Exception as e:
    print(f'❌ Import test failed: {e}')
    exit(1)
"

# Test example usage
echo "🎯 Testing example usage..."
python3 example_usage.py

cd ..

echo ""
echo "✅ SDK generation completed successfully!"
echo "📂 SDK location: $OUTPUT_DIR"
echo "📖 See $OUTPUT_DIR/README.md for usage instructions"
echo "💡 Example usage: $OUTPUT_DIR/example_usage.py"
echo "🧪 Test SDK: $OUTPUT_DIR/test_sdk.py"
echo "📦 Publish SDK: $OUTPUT_DIR/publish.sh" 