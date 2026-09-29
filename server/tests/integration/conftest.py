"""Integration test configuration with environment setup."""
import os
import sys
import subprocess
from pathlib import Path

# Add project src/ directory to Python import path for protobox package
ROOT = Path(__file__).parent.parent.parent.absolute()
SRC_DIR = ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

def setup_test_environment():
    """Load the repository's .env if present, then fill any gaps with test defaults."""
    env_file = Path(__file__).resolve().parents[3] / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                if value and key not in os.environ:
                    os.environ[key] = value

    # Fallback: Set minimum required environment variables for tests
    print("🔧 Setting up test environment with defaults...")
    
    test_env_defaults = {
        # Core MCP configuration
        "MCP_SECRET_KEY": "test-secret-key-for-integration-tests-0123456789",
        "JWT_SECRET": "test-jwt-secret-for-integration-tests-0123456789",
        "ENVIRONMENT": "test",
        # Removed deprecated AUTH_MODE - now always uses Firebase authentication
        "AUTH_TEST_MODE": "true",  # Enable test mode for Firebase auth
        
        # Database configuration
        "MONGODB_URL": "mongodb://localhost:27847/mcp_server_test?directConnection=true",
        "DATABASE_NAME": "mcp_server_test",
        "SKIP_INDEX_CREATION": "true",
        
        # API Keys (optional for tests)
        "OPENAI_API_KEY": "test-openai-key-not-real",
        "INTERNAL_API_KEY": "test-internal-api-key",
        
        # Storage configuration (use local fallback for tests)
        "TIGRIS_ACCESS_KEY": "",
        "TIGRIS_SECRET_KEY": "",
        "TIGRIS_ENDPOINT": "",
        "TIGRIS_BUCKET_NAME": "test-bucket",
        
        # Test-specific configuration
        "TEST_WORKSPACE_ID": "507f1f77bcf86cd799439011",
        "TEST_API_BASE_URL": "/admin/api/v1",
        "TEST_TIMEOUT": "60",
        "TEST_WEBSITE_URL": "https://docs.python.org/3/tutorial/introduction.html",
        
        # Disable some features in tests
        "MCP_VALIDATION_MIDDLEWARE": "false",
        "SENTRY_DSN": "",
    }
    
    # Set defaults only if not already set
    for key, value in test_env_defaults.items():
        if key not in os.environ:
            os.environ[key] = value
    
    print("✅ Test environment configured")

# Run environment setup when this module is imported
setup_test_environment()

# Print environment info for debugging
if os.getenv("PYTEST_VERBOSE", "false").lower() == "true":
    print(f"🧪 Integration Test Environment Status:")
    print(f"   MCP_SECRET_KEY: {'✅ Set' if os.getenv('MCP_SECRET_KEY') else '❌ Missing'}")
    print(f"   MONGODB_URL: {os.getenv('MONGODB_URL', 'Not set')}")
    print(f"   AUTH_TEST_MODE: {os.getenv('AUTH_TEST_MODE', 'Not set')}")
    print(f"   ENVIRONMENT: {os.getenv('ENVIRONMENT', 'Not set')}")
