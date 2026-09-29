"""Secret type definitions and metadata."""

import re
from enum import Enum
from typing import Any


class SecretType(str, Enum):
    """Secret types supported by the system."""

    API_KEY = "API_KEY"
    DATABASE_URL = "DATABASE_URL"
    OAUTH_TOKEN = "OAUTH_TOKEN"
    BASIC_AUTH = "BASIC_AUTH"
    CUSTOM = "CUSTOM"


# Secret type metadata and validation patterns
SECRET_TYPES: dict[str, dict[str, Any]] = {
    SecretType.API_KEY: {
        "description": "Bearer tokens, API keys",
        "validation_pattern": r"^[A-Za-z0-9_\-\.]+$",
        "example": "sk-1234567890abcdef",
        "metadata_schema": {
            "type": "object",
            "properties": {
                "prefix": {"type": "string", "description": "API key prefix (e.g., 'sk-', 'pk-')"},
                "service": {"type": "string", "description": "Service this key is for"},
            },
        },
    },
    SecretType.DATABASE_URL: {
        "description": "Database connection strings",
        "validation_pattern": r"^(postgresql|mysql|sqlite|mongodb):\/\/.*",
        "example": "postgresql://user:pass@host:5432/db",
        "metadata_schema": {
            "type": "object",
            "properties": {
                "database_type": {
                    "type": "string",
                    "enum": ["postgresql", "mysql", "sqlite", "mongodb"],
                },
                "host": {"type": "string"},
                "port": {"type": "integer"},
                "database_name": {"type": "string"},
            },
        },
    },
    SecretType.OAUTH_TOKEN: {
        "description": "OAuth 2.0 access tokens",
        "validation_pattern": r"^[A-Za-z0-9_\-\.]+$",
        "example": "ya29.1234567890abcdef",
        "metadata_schema": {
            "type": "object",
            "properties": {
                "scopes": {"type": "array", "items": {"type": "string"}},
                "expires_at": {"type": "string", "format": "date-time"},
                "refresh_token": {"type": "string"},
                "token_type": {"type": "string", "default": "Bearer"},
            },
        },
    },
    SecretType.BASIC_AUTH: {
        "description": "Username:password pairs (base64 encoded)",
        "validation_pattern": r"^[A-Za-z0-9+/]={0,2}$",
        "example": "dXNlcjpwYXNzd29yZA==",
        "metadata_schema": {
            "type": "object",
            "properties": {
                "username": {"type": "string"},
                "realm": {"type": "string", "description": "Authentication realm"},
            },
        },
    },
    SecretType.CUSTOM: {
        "description": "User-defined secret format",
        "validation_pattern": None,  # No default validation for custom types
        "example": "custom_secret_value",
        "metadata_schema": {
            "type": "object",
            "properties": {
                "format": {"type": "string", "description": "Description of the secret format"},
                "validation_pattern": {
                    "type": "string",
                    "description": "Custom regex pattern for validation",
                },
            },
        },
    },
}


def get_secret_type_info(secret_type: SecretType) -> dict[str, Any]:
    """Get metadata for a specific secret type."""
    return SECRET_TYPES.get(secret_type, {})


def validate_secret_format(
    secret_type: SecretType, value: str, custom_pattern: str | None = None
) -> bool:
    """Validate secret value against its type format."""
    type_info = get_secret_type_info(secret_type)

    if secret_type == SecretType.CUSTOM and custom_pattern:
        pattern = custom_pattern
    else:
        pattern = type_info.get("validation_pattern")

    if not pattern:
        return True  # No validation pattern defined

    try:
        return bool(re.match(pattern, value))
    except re.error:
        return False
