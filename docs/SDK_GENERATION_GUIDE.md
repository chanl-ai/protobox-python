# MocOps SDK Generation Guide

## Overview

This guide documents the automated SDK generation process for the MCP (Model Context Protocol) Admin API. The SDK is automatically generated from the OpenAPI specification, ensuring it stays perfectly in sync with the API.

## ✅ What We've Built

### 1. Auto-Generated SDK (`mocops-sdk/`)
- **Fully automated** - Generated from OpenAPI spec
- **Type-safe** - Complete type hints and validation
- **Async/Sync support** - Both synchronous and asynchronous clients
- **Comprehensive** - Covers all admin API endpoints
- **Production-ready** - Proper package structure with Poetry

### 2. Generation Infrastructure
- **Generation script** (`scripts/generate-sdk.sh`)
- **Makefile targets** for easy usage
- **Automated testing** and validation
- **Publishing pipeline** for PyPI

### 3. Developer Experience
- **One-command generation** - `make generate-sdk`
- **Automated testing** - `make test-sdk`
- **Example usage** - `make sdk-example`
- **Publishing ready** - `make publish-sdk`

## 🚀 Quick Start

### Generate SDK
```bash
# Start the MCP server
docker compose up mcp-server

# Generate the SDK
make generate-sdk
```

### Test SDK
```bash
# Run automated tests
make test-sdk

# Run example usage
make sdk-example
```

### Publish SDK
```bash
# Test publishing (dry run)
make publish-sdk-test

# Publish to PyPI
make publish-sdk
```

## 📁 SDK Structure

```
mocops-sdk/
├── mocops_sdk/              # Generated SDK package
│   ├── api/                 # API endpoints
│   │   └── admin/           # Admin API endpoints
│   ├── models/              # Data models
│   ├── client.py            # HTTP clients
│   ├── types.py             # Type definitions
│   └── errors.py            # Error handling
├── pyproject.toml           # Poetry configuration
├── README.md                # Usage documentation
├── example_usage.py         # Example code
├── test_sdk.py              # Automated tests
└── publish.sh               # Publishing script
```

## 🔧 Available Make Targets

| Target | Description |
|--------|-------------|
| `generate-sdk` | Generate MocOps SDK from OpenAPI spec |
| `test-sdk` | Run automated SDK tests |
| `sdk-example` | Run SDK usage examples |
| `publish-sdk` | Publish SDK to PyPI |
| `publish-sdk-test` | Publish SDK to test PyPI |

## 📖 Usage Examples

### Basic Usage
```python
from mocops_sdk.client import Client
from mocops_sdk.api.admin import health_check_admin_api_v1_health_get

client = Client(base_url="http://localhost:8080")

with client as client:
    health = health_check_admin_api_v1_health_get.sync(client=client)
    print(f"API Status: {health}")
```

### Async Usage
```python
import asyncio
from mocops_sdk.client import Client
from mocops_sdk.api.admin import health_check_admin_api_v1_health_get

async def main():
    client = Client(base_url="http://localhost:8080")
    async with client as client:
        health = await health_check_admin_api_v1_health_get.asyncio(client=client)
        print(f"API Status: {health}")

asyncio.run(main())
```

### Working with Actions
```python
from mocops_sdk.client import Client
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
    # List actions
    actions = list_actions_admin_api_v1_actions_get.sync(client=client)
    
    # Create action
    default_config = ActionCreateRequestDefaultConfig()
    default_config["url"] = "https://api.example.com/webhook"
    
    config_schema = ActionCreateRequestConfigSchema()
    config_schema["type"] = "object"
    
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
```

## 🔄 Regeneration Process

The SDK should be regenerated whenever the API changes:

1. **Update API** - Make changes to the MCP server API
2. **Start server** - `docker compose up mcp-server`
3. **Regenerate SDK** - `make generate-sdk`
4. **Test changes** - `make test-sdk`
5. **Update version** - Update version in `pyproject.toml`
6. **Publish** - `make publish-sdk`

## 📦 Publishing

### Prerequisites
- Poetry installed
- PyPI account and API token
- Test PyPI account (optional)

### Publishing Steps
```bash
# 1. Generate and test SDK
make generate-sdk
make test-sdk

# 2. Update version in mocops-sdk/pyproject.toml
# 3. Publish to test PyPI (optional)
make publish-sdk-test

# 4. Publish to PyPI
make publish-sdk
```

## 🛠️ Technical Details

### Generation Process
1. **OpenAPI Spec Extraction** - Pulls from running server
2. **Code Generation** - Uses `openapi-python-client`
3. **Package Structure** - Creates proper Poetry package
4. **Documentation** - Generates comprehensive README
5. **Testing** - Creates automated tests
6. **Publishing** - Sets up Poetry publishing

### Dependencies
- `openapi-python-client` - SDK generation
- `httpx` - HTTP client
- `attrs` - Data classes
- `python-dateutil` - Date handling
- `pytest` - Testing framework

## 🎯 Benefits

### For Developers
- **Always up-to-date** - Automatically synced with API
- **Type safety** - Full type hints and validation
- **Easy to use** - Simple, intuitive interface
- **Well documented** - Generated documentation

### For Maintenance
- **Zero manual work** - Fully automated
- **Consistent** - Same structure every time
- **Testable** - Automated validation
- **Publishable** - Ready for PyPI

## 🔮 Future Enhancements

- **CI/CD Integration** - Auto-publish on API changes
- **Version Management** - Semantic versioning
- **Multi-language** - Generate SDKs for other languages
- **Advanced Features** - Retry logic, rate limiting, etc.

## 📝 Notes

- The SDK is generated from the live OpenAPI spec
- Server must be running during generation
- Generated code should not be manually edited
- All customizations should be in the generation script
- Version bumping is manual (for now)

---

**Generated SDK Location**: `mocops-sdk/`  
**Main Script**: `scripts/generate-sdk.sh`  
**Make Targets**: `make help | grep sdk` 