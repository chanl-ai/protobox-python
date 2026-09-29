"""Authentication configuration - now always uses Firebase authentication."""


from pydantic import BaseModel

from ..config import settings


class AuthConfig(BaseModel):
    """Authentication configuration - now always uses Firebase authentication."""

    # Simplified - no test modes, always use Firebase (emulator for development)
    environment: str = "production"

    @classmethod
    def from_settings(cls) -> "AuthConfig":
        """Create config from settings."""
        return cls(
            environment=settings.environment,
        )

    def override(self, **kwargs) -> "AuthConfig":
        """Create a new config with overridden values."""
        data = self.model_dump()
        data.update(kwargs)
        return AuthConfig(**data)


# Global config instance
_auth_config: AuthConfig | None = None


def get_auth_config() -> AuthConfig:
    """Get the current auth configuration."""
    global _auth_config
    if _auth_config is None:
        _auth_config = AuthConfig.from_settings()
    return _auth_config


def set_auth_config(config: AuthConfig) -> None:
    """Set the auth configuration (for testing or runtime override)."""
    global _auth_config
    _auth_config = config


# Removed deprecated override_auth_mode() - now always uses Firebase authentication


def reset_auth_config() -> None:
    """Reset auth config to environment defaults."""
    global _auth_config
    _auth_config = None
