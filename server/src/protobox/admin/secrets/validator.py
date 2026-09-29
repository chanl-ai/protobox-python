"""Secret validation logic."""

import base64
from typing import Any
from urllib.parse import urlparse

from .types import SecretType, get_secret_type_info, validate_secret_format


class SecretValidator:
    """Validator for secrets and their metadata."""

    @staticmethod
    def validate_secret_value(
        secret_type: SecretType, value: str, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Validate a secret value against its type requirements.

        Args:
            secret_type: Type of the secret
            value: Secret value to validate
            metadata: Optional metadata for validation context

        Returns:
            Dictionary with validation results
        """
        result = {"valid": True, "errors": [], "warnings": [], "suggestions": []}

        if not value or len(value.strip()) == 0:
            result["valid"] = False
            result["errors"].append("Secret value cannot be empty")
            return result

        # Type-specific validation
        if secret_type == SecretType.API_KEY:
            result = SecretValidator._validate_api_key(value, metadata or {}, result)
        elif secret_type == SecretType.DATABASE_URL:
            result = SecretValidator._validate_database_url(value, metadata or {}, result)
        elif secret_type == SecretType.OAUTH_TOKEN:
            result = SecretValidator._validate_oauth_token(value, metadata or {}, result)
        elif secret_type == SecretType.BASIC_AUTH:
            result = SecretValidator._validate_basic_auth(value, metadata or {}, result)
        elif secret_type == SecretType.CUSTOM:
            result = SecretValidator._validate_custom(value, metadata or {}, result)

        # General format validation
        custom_pattern = metadata.get("validation_pattern") if metadata else None
        if not validate_secret_format(secret_type, value, custom_pattern):
            result["valid"] = False
            result["errors"].append(
                f"Secret value does not match expected format for {secret_type}"
            )

        return result

    @staticmethod
    def _validate_api_key(
        value: str, metadata: dict[str, Any], result: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate API key format."""
        # Check for common API key patterns
        if len(value) < 8:
            result["warnings"].append("API key seems unusually short")

        # Check for common prefixes
        common_prefixes = ["sk-", "pk-", "rk-", "ak-", "api_", "key_"]
        has_prefix = any(value.startswith(prefix) for prefix in common_prefixes)

        if not has_prefix:
            result["suggestions"].append("Consider using a standard API key prefix")

        # Check if it contains only valid characters
        if not value.replace("-", "").replace("_", "").replace(".", "").isalnum():
            result["errors"].append("API key contains invalid characters")
            result["valid"] = False

        return result

    @staticmethod
    def _validate_database_url(
        value: str, metadata: dict[str, Any], result: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate database URL format."""
        try:
            parsed = urlparse(value)

            # Check required components
            if not parsed.scheme:
                result["errors"].append("Database URL missing scheme (e.g., postgresql://)")
                result["valid"] = False
            elif parsed.scheme not in ["postgresql", "mysql", "sqlite", "mongodb"]:
                result["warnings"].append(f"Uncommon database scheme: {parsed.scheme}")

            if not parsed.hostname and parsed.scheme != "sqlite":
                result["errors"].append("Database URL missing hostname")
                result["valid"] = False

            if not parsed.path or parsed.path == "/":
                result["warnings"].append("Database URL missing database name")

            # Security checks
            if parsed.password and len(parsed.password) < 8:
                result["warnings"].append("Database password seems weak")

            if parsed.hostname in ["localhost", "127.0.0.1"] and "prod" in value.lower():
                result["warnings"].append("Localhost database in production context")

        except Exception as e:
            result["errors"].append(f"Invalid URL format: {str(e)}")
            result["valid"] = False

        return result

    @staticmethod
    def _validate_oauth_token(
        value: str, metadata: dict[str, Any], result: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate OAuth token format."""
        # Check token length
        if len(value) < 16:
            result["warnings"].append("OAuth token seems unusually short")

        # Check for common OAuth token patterns
        oauth_prefixes = ["ya29.", "EAA", "gho_", "ghp_"]
        has_oauth_prefix = any(value.startswith(prefix) for prefix in oauth_prefixes)

        if has_oauth_prefix:
            result["suggestions"].append("Token appears to follow known OAuth format")

        # Check expiration if provided in metadata
        expires_at = metadata.get("expires_at")
        if expires_at:
            # Could add datetime validation here
            result["suggestions"].append("Remember to refresh token before expiration")

        return result

    @staticmethod
    def _validate_basic_auth(
        value: str, metadata: dict[str, Any], result: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate Basic Auth format (base64 encoded username:password)."""
        try:
            # Attempt to decode base64
            decoded = base64.b64decode(value).decode("utf-8")

            # Check for username:password format
            if ":" not in decoded:
                result["errors"].append("Basic auth should be base64 encoded 'username:password'")
                result["valid"] = False
            else:
                username, password = decoded.split(":", 1)

                if len(username) == 0:
                    result["errors"].append("Username cannot be empty")
                    result["valid"] = False

                if len(password) < 8:
                    result["warnings"].append("Password seems weak (less than 8 characters)")

        except Exception:
            result["errors"].append("Invalid base64 encoding for Basic Auth")
            result["valid"] = False

        return result

    @staticmethod
    def _validate_custom(
        value: str, metadata: dict[str, Any], result: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate custom secret format."""
        # For custom types, rely on metadata for validation
        format_desc = metadata.get("format")
        if not format_desc:
            result["suggestions"].append("Consider adding format description for custom secret")

        validation_pattern = metadata.get("validation_pattern")
        if validation_pattern:
            result["suggestions"].append("Custom validation pattern will be applied")

        return result

    @staticmethod
    def validate_metadata(secret_type: SecretType, metadata: dict[str, Any]) -> dict[str, Any]:
        """Validate secret metadata against type schema.

        Args:
            secret_type: Type of the secret
            metadata: Metadata to validate

        Returns:
            Dictionary with validation results
        """
        result = {"valid": True, "errors": [], "warnings": []}

        type_info = get_secret_type_info(secret_type)
        metadata_schema = type_info.get("metadata_schema", {})

        # Basic validation - could be enhanced with jsonschema
        if metadata_schema.get("type") == "object":
            properties = metadata_schema.get("properties", {})

            for key, _value in metadata.items():
                if key not in properties:
                    result["warnings"].append(f"Unexpected metadata field: {key}")

        return result
