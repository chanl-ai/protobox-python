"""Configuration settings for admin API."""

import os

# Removed deprecated AuthMode - now always uses Firebase authentication


MIN_KEY_LENGTH = 32

# Values that have appeared in this codebase as defaults or examples.
KNOWN_PUBLIC_KEYS = {
    "development-jwt-secret",
    "development-secret-key-12345",
    "test-secret-key-do-not-use-in-production",
    "dev-jwt-secret-for-testing-only-not-production",
    "internal-api-secret-key-for-backend-access",
}


class Settings:
    """Admin API settings with centralized configuration management."""

    def __init__(self):
        # Environment
        self.environment = os.getenv("ENVIRONMENT", "development")

        # Authentication settings - now always Firebase
        self.auth_test_mode = os.getenv("AUTH_TEST_MODE", "false").lower() == "true"
        self.auth_allow_test_tokens = os.getenv("AUTH_ALLOW_TEST_TOKENS", "false").lower() == "true"

        # JWT settings
        self.jwt_secret = os.getenv("JWT_SECRET")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
        self.refresh_token_expire_days = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

        # Firebase settings
        self.firebase_project_id = os.getenv("FIREBASE_PROJECT_ID")
        self.firebase_service_account_key = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")
        self.firebase_service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")

        # Firebase emulator settings - only used if FIREBASE_AUTH_EMULATOR_HOST is set
        emulator_host = os.getenv("FIREBASE_AUTH_EMULATOR_HOST")
        if emulator_host:
            self.use_firebase_emulator = True
            self.firebase_auth_emulator_host = emulator_host
            # Set it for Firebase Admin SDK to detect
            os.environ["FIREBASE_AUTH_EMULATOR_HOST"] = emulator_host
        else:
            self.use_firebase_emulator = False
            self.firebase_auth_emulator_host = None

        # OAuth settings
        self.google_client_id = os.getenv("GOOGLE_CLIENT_ID", "demo-client-id")
        self.google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "demo-secret")

        # API URLs
        self.admin_api_base_url = os.getenv(
            "ADMIN_API_BASE_URL", "http://localhost:8090/admin/api/v1"
        )
        self.platform_api_url = os.getenv("PLATFORM_API_URL", "http://localhost:3000")
        self.nextjs_internal_api_url = os.getenv("NEXTJS_INTERNAL_API_URL", "http://localhost:3001")
        self.nextjs_url = os.getenv("NEXTJS_URL", "http://localhost:3001")
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3010")
        self.mcp_base_url = os.getenv("MCP_BASE_URL", "http://localhost:8090")
        self.mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8090")
        self.internal_mcp_base_url = os.getenv(
            "INTERNAL_MCP_BASE_URL", "http://localhost:8090/internal-mcp/sse"
        )

        # API Keys and Secrets
        self._secret_encryption_key = os.getenv("MCP_SECRET_KEY")
        self.internal_api_key = os.getenv("INTERNAL_API_KEY", "")
        self.internal_api_secret = os.getenv("INTERNAL_API_SECRET", "")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.admin_config_secret = os.getenv("ADMIN_CONFIG_SECRET")

        # Database settings
        self.mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        self.database_name = os.getenv("DATABASE_NAME", "mcp_server")
        self.skip_index_creation = os.getenv("SKIP_INDEX_CREATION", "false").lower() == "true"
        self.mcp_skip_index_creation = os.getenv("MCP_SKIP_INDEX_CREATION", "false").lower() == "true"
        self.mcp_client_session_timeout_seconds = int(os.getenv("MCP_CLIENT_SESSION_TIMEOUT_SECONDS", "10"))

        # Tigris/S3 Storage Configuration
        self.tigris_access_key = os.getenv("AWS_ACCESS_KEY_ID", "")
        self.tigris_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")
        self.tigris_endpoint = os.getenv("AWS_ENDPOINT_URL_S3", "")
        self.tigris_bucket_name = os.getenv("AWS_BUCKET_NAME", "protobox-dev")

        # AI/ML Processing Configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self.embedding_provider = os.getenv("EMBEDDING_PROVIDER", "openai")  # openai, huggingface
        self.huggingface_model = os.getenv("HUGGINGFACE_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

        # Processing Configuration
        self.page_retrieval_timeout = int(os.getenv("PAGE_RETRIEVAL_TIMEOUT", "10"))  # seconds
        self.kb_source_processing_timeout = int(os.getenv("KB_SOURCE_PROCESSING_TIMEOUT", "300"))  # seconds
        self.max_content_size = int(os.getenv("MAX_CONTENT_SIZE", "50")) * 1024 * 1024  # MB to bytes
        self.max_page_size = int(os.getenv("MAX_PAGE_SIZE", "10")) * 1024 * 1024  # MB to bytes

        # Chunking Configuration
        self.default_chunk_size = int(os.getenv("DEFAULT_CHUNK_SIZE", "512"))  # tokens
        self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "50"))  # tokens
        self.max_file_size = int(os.getenv("MAX_FILE_SIZE", str(10 * 1024 * 1024)))  # 10MB

        # Document Processor Service - Environment-based URL selection
        self.document_processor_url = self._get_document_processor_url()
        self.document_processor_api_key = os.getenv("DOCUMENT_PROCESSOR_API_KEY")

        # Cache settings
        self.cache_backend = os.getenv("CACHE_BACKEND", "memory").lower()
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6381")

        # CORS settings
        self.cors_allowed_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")

        # Vercel settings (for production)
        self.vercel_url = os.getenv("VERCEL_URL")
        self.vercel_preview_domain = os.getenv("VERCEL_PREVIEW_DOMAIN")

        # MCP settings
        self.mcp_base_path = os.getenv("MCP_BASE_PATH", "")
        self.mcp_validation_middleware = os.getenv("MCP_VALIDATION_MIDDLEWARE", "true").lower() in (
            "true",
            "1",
            "yes",
        )
        self.mcp_mount_path = os.getenv("MCP_MOUNT_PATH", "/mcp")
        self.mcp_mount_name = os.getenv("MCP_MOUNT_NAME", "multitenant-mcp")
        self.mcp_cache_size = int(os.getenv("MCP_CACHE_SIZE", "100"))
        self.internal_mcp_mount_path = os.getenv("INTERNAL_MCP_MOUNT_PATH", "/internal-mcp")
        self.internal_mcp_mount_name = os.getenv("INTERNAL_MCP_MOUNT_NAME", "internal-mcp")
        
        # MCP Native Implementation Settings
        self.mcp_enable_workspace_isolation = os.getenv("MCP_ENABLE_WORKSPACE_ISOLATION", "true").lower() == "true"
        self.mcp_cleanup_interval_minutes = int(os.getenv("MCP_CLEANUP_INTERVAL_MINUTES", "5"))
        self.mcp_redis_ttl_seconds = int(os.getenv("MCP_REDIS_TTL_SECONDS", "3600"))
        self.mcp_workspace_timeout_minutes = int(os.getenv("MCP_WORKSPACE_TIMEOUT_MINUTES", "30"))
        self.mcp_max_concurrent_workspaces = int(os.getenv("MCP_MAX_CONCURRENT_WORKSPACES", "100"))
        
        # Redis Settings for MCP Caching
        self.redis_password = os.getenv("REDIS_PASSWORD", "")
        self.redis_db = int(os.getenv("REDIS_DB", "0"))
        self.redis_max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", "10"))
        self.redis_connection_timeout = int(os.getenv("REDIS_CONNECTION_TIMEOUT", "5"))
        self.redis_socket_keepalive = os.getenv("REDIS_SOCKET_KEEPALIVE", "true").lower() == "true"

        # Test settings
        self.testing_user_id = os.getenv("TESTING_USER_ID", "dev_user")
        self.test_workspace_id = os.getenv("TEST_WORKSPACE_ID", "")

        # App version info
        self.app_version = os.getenv("APP_VERSION", "1.0.0")

        # Monitoring settings
        self.monitoring_api_key = os.getenv("MCP_MONITORING_API_KEY", "")
        self.commit_sha = os.getenv("COMMIT_SHA", "unknown")
        self.deployed_at = os.getenv("DEPLOYED_AT", "unknown")

        # Server settings
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8090"))
        self.workers = int(os.getenv("WORKERS", "1"))

    def validate_required_secrets(self) -> None:
        """Refuse to run with a missing, short or publicly known key.

        JWT_SECRET signs every login token and MCP_SECRET_KEY encrypts every stored
        secret. A value that appears in this repository lets anyone forge tokens or
        decrypt secrets, so the check applies in every environment.
        """
        problems = []
        for env_name, value in (("JWT_SECRET", self.jwt_secret), ("MCP_SECRET_KEY", self._secret_encryption_key)):
            if not value:
                problems.append(f"{env_name} is not set")
            elif value in KNOWN_PUBLIC_KEYS:
                problems.append(f"{env_name} uses a value published in this repository")
            elif len(value) < MIN_KEY_LENGTH:
                problems.append(f"{env_name} must be at least {MIN_KEY_LENGTH} characters")
        if problems:
            raise ValueError(
                "; ".join(problems)
                + ". Generate values with: python -c 'import secrets; print(secrets.token_urlsafe(48))'"
            )

    def get_secret_encryption_key(self) -> bytes:
        """Get the secret encryption key as bytes."""
        return self._secret_encryption_key.encode()

    # Removed deprecated get_auth_mode() - now always uses Firebase authentication

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment in ["development", "dev_test"]

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def has_monitoring_key(self) -> bool:
        """Check if monitoring API key is configured."""
        return bool(self.monitoring_api_key and len(self.monitoring_api_key) > 20)

    def _get_document_processor_url(self) -> str:
        """Get document processor URL based on environment and explicit override."""
        # Explicit override takes priority
        explicit_url = os.getenv("DOCUMENT_PROCESSOR_URL")
        if explicit_url:
            return explicit_url

        return "http://localhost:8092"
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean setting with fallback to default."""
        return os.getenv(key, str(default)).lower() in ("true", "1", "yes", "on")
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer setting with fallback to default."""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            return default
    
    def get_list(self, key: str, default: list = None) -> list:
        """Get comma-separated list setting with fallback to default."""
        value = os.getenv(key)
        if not value:
            return default or []
        return [item.strip() for item in value.split(",") if item.strip()]


# Global settings instance
settings = Settings()
