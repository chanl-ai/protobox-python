"""
Configuration Settings for MCP Server

Provides Pydantic models for server configuration with support for:
- Environment variable substitution
- YAML/JSON file loading
- Validation and type checking
- Default values
"""

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, validator


class ServerConfig(BaseModel):
    """Server configuration"""

    name: str = Field(default="mcp-server", description="Server name")
    version: str = Field(default="1.0.0", description="Server version")
    description: str | None = Field(default=None, description="Server description")


class TransportConfig(BaseModel):
    """Transport configuration"""

    type: Literal["stdio", "http", "websocket"] = Field(
        default="stdio", description="Transport type"
    )
    host: str = Field(default="localhost", description="Host to bind to")
    port: int = Field(default=8080, description="Port to bind to")
    path: str = Field(default="/mcp", description="HTTP path for MCP endpoint")


class AuthConfig(BaseModel):
    """Authentication configuration"""

    environment: str = Field(
        default="production", description="Environment (development, staging, production)"
    )
    # Removed auth_test_mode - use Firebase emulator for development testing
    firebase_project_id: str | None = Field(default=None, description="Firebase project ID")
    firebase_service_account_key: str | None = Field(
        default=None, description="Firebase service account JSON"
    )
    firebase_service_account_path: str | None = Field(
        default=None, description="Firebase service account file path"
    )
    use_firebase_emulator: bool = Field(default=False, description="Use Firebase emulator")
    firebase_emulator_host: str = Field(
        default="localhost:9099", description="Firebase emulator host"
    )
    jwt_secret: str | None = Field(default=None, description="JWT signing secret")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=60, description="Access token expiration in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=30, description="Refresh token expiration in days"
    )


class AdminConfig(BaseModel):
    """Admin API configuration"""

    enabled: bool = Field(default=False, description="Enable admin API")
    mongodb_url: str = Field(
        default="mongodb://localhost:27017/mcp_admin", description="MongoDB connection URL"
    )
    secret_key: str = Field(default="", description="Master key for secret encryption")
    prefix: str = Field(default="/admin/api/v1", description="API prefix path")
    host: str | None = Field(
        default=None, description="Admin API host (inherits from transport if not set)"
    )
    port: int | None = Field(
        default=None, description="Admin API port (inherits from transport if not set)"
    )

    # Client-Side Isolation Architecture feature flag
    use_client_side_isolation: bool = Field(
        default=False,
        description="Use Next.js client for user/workspace/billing data instead of direct MongoDB",
    )
    nextjs_internal_api_url: str = Field(
        default="http://localhost:3001", description="Next.js internal API base URL"
    )
    nextjs_internal_api_key: str | None = Field(
        default=None, description="API key for Next.js internal API authentication"
    )

    @validator("secret_key")
    def validate_secret_key(cls, v):
        """Validate secret key is provided when admin is enabled"""
        if not v:
            return v  # Let it be empty for now, will be validated later if enabled
        if len(v) < 16:
            raise ValueError("Secret key must be at least 16 characters long")
        return v


class ToolConfig(BaseModel):
    """Tool configuration"""

    name: str = Field(description="Tool name")
    type: str = Field(description="Tool type (builtin.echo, builtin.rest_api, etc.)")
    enabled: bool = Field(default=True, description="Whether tool is enabled")
    config: dict[str, Any] = Field(default_factory=dict, description="Tool-specific configuration")


class LoggingConfig(BaseModel):
    """Logging configuration"""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", description="Log level"
    )
    format: Literal["text", "json", "structured"] = Field(
        default="structured", description="Log format"
    )
    file: str | None = Field(default=None, description="Log file path")


class ContextConfig(BaseModel):
    """Context management configuration"""

    storage: Literal["memory", "redis", "file"] = Field(
        default="memory", description="Context storage type"
    )
    ttl: int = Field(default=3600, description="Context TTL in seconds")
    redis_url: str | None = Field(default=None, description="Redis URL for context storage")
    file_path: str | None = Field(default=None, description="File path for context storage")


class Config(BaseModel):
    """Main configuration model"""

    server: ServerConfig = Field(default_factory=ServerConfig)
    transport: TransportConfig = Field(default_factory=TransportConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    admin: AdminConfig = Field(default_factory=AdminConfig)
    tools: list[ToolConfig] = Field(default_factory=list)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    context: ContextConfig = Field(default_factory=ContextConfig)

    @validator("admin")
    def validate_admin_config(cls, v, values):
        """Validate admin configuration"""
        if v.enabled:
            if not v.secret_key:
                raise ValueError("secret_key is required when admin API is enabled")
            if len(v.secret_key) < 16:
                raise ValueError(
                    "Secret key must be at least 16 characters long when admin API is enabled"
                )
        return v

    @validator("*", pre=True)
    def substitute_env_vars(cls, v):
        """Substitute environment variables in string values"""
        if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
            env_var = v[2:-1]
            return os.getenv(env_var, v)
        return v

    @classmethod
    def from_file(cls, config_path: str | Path) -> "Config":
        """Load configuration from YAML or JSON file"""
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path) as f:
            if config_path.suffix.lower() in [".yaml", ".yml"]:
                data = yaml.safe_load(f)
            elif config_path.suffix.lower() == ".json":
                data = json.load(f)
            else:
                raise ValueError(f"Unsupported configuration file format: {config_path.suffix}")

        return cls(**data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create configuration from dictionary"""
        return cls(**data)

    @classmethod
    def from_env(cls, prefix: str = "MCP_") -> "Config":
        """Create configuration from environment variables"""
        config_data = {}

        # Server config
        server_config = {}
        if os.getenv(f"{prefix}SERVER_NAME"):
            server_config["name"] = os.getenv(f"{prefix}SERVER_NAME")
        if os.getenv(f"{prefix}SERVER_VERSION"):
            server_config["version"] = os.getenv(f"{prefix}SERVER_VERSION")
        if server_config:
            config_data["server"] = server_config

        # Transport config
        transport_config = {}
        if os.getenv(f"{prefix}TRANSPORT_TYPE"):
            transport_config["type"] = os.getenv(f"{prefix}TRANSPORT_TYPE")
        if os.getenv(f"{prefix}TRANSPORT_HOST"):
            transport_config["host"] = os.getenv(f"{prefix}TRANSPORT_HOST")
        if os.getenv(f"{prefix}TRANSPORT_PORT"):
            transport_config["port"] = int(os.getenv(f"{prefix}TRANSPORT_PORT"))
        if transport_config:
            config_data["transport"] = transport_config

        # Auth config
        auth_config = {}
        if os.getenv("ENVIRONMENT"):
            auth_config["environment"] = os.getenv("ENVIRONMENT")
        if os.getenv("AUTH_TEST_MODE"):
            auth_config["auth_test_mode"] = os.getenv("AUTH_TEST_MODE").lower() in [
                "true",
                "1",
                "yes",
            ]
        if os.getenv("FIREBASE_PROJECT_ID"):
            auth_config["firebase_project_id"] = os.getenv("FIREBASE_PROJECT_ID")
        if os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY"):
            auth_config["firebase_service_account_key"] = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")
        if os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH"):
            auth_config["firebase_service_account_path"] = os.getenv(
                "FIREBASE_SERVICE_ACCOUNT_PATH"
            )
        if os.getenv("USE_FIREBASE_EMULATOR"):
            auth_config["use_firebase_emulator"] = os.getenv("USE_FIREBASE_EMULATOR").lower() in [
                "true",
                "1",
                "yes",
            ]
        if os.getenv("FIREBASE_AUTH_EMULATOR_HOST"):
            auth_config["firebase_emulator_host"] = os.getenv("FIREBASE_AUTH_EMULATOR_HOST")
        if os.getenv("JWT_SECRET"):
            auth_config["jwt_secret"] = os.getenv("JWT_SECRET")
        if os.getenv("JWT_ALGORITHM"):
            auth_config["jwt_algorithm"] = os.getenv("JWT_ALGORITHM")
        if os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"):
            auth_config["access_token_expire_minutes"] = int(
                os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
            )
        if os.getenv("REFRESH_TOKEN_EXPIRE_DAYS"):
            auth_config["refresh_token_expire_days"] = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS"))
        if auth_config:
            config_data["auth"] = auth_config

        # Admin config
        admin_config = {}
        if os.getenv(f"{prefix}ADMIN_ENABLED"):
            admin_config["enabled"] = os.getenv(f"{prefix}ADMIN_ENABLED").lower() in [
                "true",
                "1",
                "yes",
            ]
        # MONGODB_URL is what the rest of the app (admin/config.py) reads; accept it here too
        # so one variable configures both.
        mongodb_url = os.getenv(f"{prefix}MONGODB_URL") or os.getenv("MONGODB_URL")
        if mongodb_url:
            admin_config["mongodb_url"] = mongodb_url
        if os.getenv(f"{prefix}SECRET_KEY"):
            admin_config["secret_key"] = os.getenv(f"{prefix}SECRET_KEY")
        if os.getenv(f"{prefix}ADMIN_PREFIX"):
            admin_config["prefix"] = os.getenv(f"{prefix}ADMIN_PREFIX")
        if os.getenv(f"{prefix}ADMIN_HOST"):
            admin_config["host"] = os.getenv(f"{prefix}ADMIN_HOST")
        if os.getenv(f"{prefix}ADMIN_PORT"):
            admin_config["port"] = int(os.getenv(f"{prefix}ADMIN_PORT"))

        # Client-Side Isolation Architecture settings
        if os.getenv(f"{prefix}ADMIN_USE_CLIENT_SIDE_ISOLATION"):
            admin_config["use_client_side_isolation"] = os.getenv(
                f"{prefix}ADMIN_USE_CLIENT_SIDE_ISOLATION"
            ).lower() in ["true", "1", "yes"]
        if os.getenv(f"{prefix}ADMIN_NEXTJS_INTERNAL_API_URL"):
            admin_config["nextjs_internal_api_url"] = os.getenv(
                f"{prefix}ADMIN_NEXTJS_INTERNAL_API_URL"
            )
        if os.getenv(f"{prefix}ADMIN_NEXTJS_INTERNAL_API_KEY"):
            admin_config["nextjs_internal_api_key"] = os.getenv(
                f"{prefix}ADMIN_NEXTJS_INTERNAL_API_KEY"
            )

        if admin_config:
            config_data["admin"] = admin_config

        # Logging config
        logging_config = {}
        if os.getenv(f"{prefix}LOG_LEVEL"):
            logging_config["level"] = os.getenv(f"{prefix}LOG_LEVEL")
        if os.getenv(f"{prefix}LOG_FORMAT"):
            logging_config["format"] = os.getenv(f"{prefix}LOG_FORMAT")
        if os.getenv(f"{prefix}LOG_FILE"):
            logging_config["file"] = os.getenv(f"{prefix}LOG_FILE")
        if logging_config:
            config_data["logging"] = logging_config

        # Default tools if admin is enabled
        if admin_config.get("enabled"):
            config_data["tools"] = [
                {"name": "echo", "type": "builtin.echo", "enabled": True},
                {"name": "search", "type": "builtin.search", "enabled": True},
                {"name": "fetch", "type": "builtin.fetch", "enabled": True},
                {"name": "calculator", "type": "builtin.calculator", "enabled": True},
            ]

        return cls(**config_data)

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary"""
        return self.dict()

    def to_yaml(self, file_path: str | Path | None = None) -> str:
        """Export configuration to YAML format"""
        yaml_str = yaml.dump(self.dict(), default_flow_style=False, indent=2)

        if file_path:
            with open(file_path, "w") as f:
                f.write(yaml_str)

        return yaml_str

    def to_json(self, file_path: str | Path | None = None, indent: int = 2) -> str:
        """Export configuration to JSON format"""
        json_str = json.dumps(self.dict(), indent=indent)

        if file_path:
            with open(file_path, "w") as f:
                f.write(json_str)

        return json_str


# Default configurations for common use cases
DEFAULT_STDIO_CONFIG = Config(
    server=ServerConfig(name="mcp-stdio-server"),
    transport=TransportConfig(type="stdio"),
    tools=[ToolConfig(name="echo", type="builtin.echo")],
)

DEFAULT_HTTP_CONFIG = Config(
    server=ServerConfig(name="mcp-http-server"),
    transport=TransportConfig(type="http", host="0.0.0.0", port=8080),
    tools=[
        ToolConfig(name="echo", type="builtin.echo"),
        ToolConfig(
            name="httpbin_test",
            type="builtin.rest_api",
            config={"url": "https://httpbin.org/{endpoint}", "method": "GET", "timeout": 30},
        ),
    ],
)

DEFAULT_WEBSOCKET_CONFIG = Config(
    server=ServerConfig(name="mcp-websocket-server"),
    transport=TransportConfig(type="websocket", host="0.0.0.0", port=8081),
    tools=[ToolConfig(name="echo", type="builtin.echo")],
)

# New default config with admin API enabled
DEFAULT_HTTP_WITH_ADMIN_CONFIG = Config(
    server=ServerConfig(name="mcp-server-with-admin"),
    transport=TransportConfig(type="http", host="0.0.0.0", port=8080),
    admin=AdminConfig(
        enabled=True,
        mongodb_url="mongodb://localhost:27017/mcp_admin",
        secret_key="${MCP_SECRET_KEY}",
        prefix="/admin/api/v1",
    ),
    tools=[
        ToolConfig(name="echo", type="builtin.echo"),
        ToolConfig(
            name="httpbin_test",
            type="builtin.rest_api",
            config={"url": "https://httpbin.org/{endpoint}", "method": "GET", "timeout": 30},
        ),
    ],
)

# New remote MCP server configuration for Phase 1X
DEFAULT_REMOTE_MCP_CONFIG = Config(
    server=ServerConfig(name="voiceman-remote-mcp-server"),
    transport=TransportConfig(type="http", host="0.0.0.0", port=8080),
    tools=[
        # ChatGPT-compatible tools for Deep Research
        ToolConfig(
            name="search",
            type="builtin.search",
            description="Search for information across various sources",
        ),
        ToolConfig(
            name="fetch",
            type="builtin.fetch",
            description="Fetch detailed content from a specific source",
        ),
        ToolConfig(
            name="calculator",
            type="builtin.calculator",
            description="Perform mathematical calculations",
        ),
        # Classic MCP tools
        ToolConfig(name="echo", type="builtin.echo"),
        ToolConfig(
            name="httpbin_test",
            type="builtin.rest_api",
            config={"url": "https://httpbin.org/{endpoint}", "method": "GET", "timeout": 30},
        ),
    ],
)


# Global settings instance
_settings: Config | None = None


@lru_cache
def get_settings() -> Config:
    """Get the global settings instance, loading from environment if not already loaded."""
    return Config.from_env()


def set_settings(config: Config) -> None:
    """Set the global settings instance (useful for testing)."""
    global _settings
    _settings = config
