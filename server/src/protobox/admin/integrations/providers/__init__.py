"""OAuth2 provider implementations."""

import os
from typing import TYPE_CHECKING

from ...config import settings
from ...models.integration import IntegrationType
from ..base import OAuth2Config

if TYPE_CHECKING:
    from .github import GitHubOAuth2Provider
    from .google import GoogleOAuth2Provider
    from .linkedin import LinkedInOAuth2Provider
    from .microsoft import MicrosoftOAuth2Provider
    from .salesforce import SalesforceOAuth2Provider
    from .slack import SlackOAuth2Provider


def get_provider_config(integration_type: IntegrationType) -> OAuth2Config | None:
    """Get OAuth2 configuration for a specific provider."""
    
    base_url = os.getenv("MCP_SERVER_URL", "http://localhost:8090")
    
    configs = {
        IntegrationType.GOOGLE_CALENDAR: OAuth2Config(
            client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            revoke_url="https://oauth2.googleapis.com/revoke",
            user_info_url="https://www.googleapis.com/oauth2/v2/userinfo",
            scopes=[
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/calendar.readonly",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
            ],
            redirect_uri=f"{base_url}/admin/api/v1/integrations/oauth/callback/google_calendar",
            supports_pkce=True,
            access_type="offline",
            prompt="consent",
        ),
        IntegrationType.SLACK: OAuth2Config(
            client_id=os.getenv("SLACK_CLIENT_ID", ""),
            client_secret=os.getenv("SLACK_CLIENT_SECRET", ""),
            authorize_url="https://slack.com/oauth/v2/authorize",
            token_url="https://slack.com/api/oauth.v2.access",
            revoke_url="https://slack.com/api/auth.revoke",
            user_info_url="https://slack.com/api/users.identity",
            scopes=[
                "channels:read",
                "channels:write",
                "chat:write",
                "files:read",
                "files:write",
                "users:read",
                "users:read.email",
            ],
            redirect_uri=f"{base_url}/admin/api/v1/integrations/oauth/callback/slack",
            supports_pkce=False,  # Slack doesn't support PKCE yet
        ),
    }
    
    # Add new integration types when enum is updated
    # IntegrationType.MICROSOFT_365: OAuth2Config(...),
    # IntegrationType.SALESFORCE: OAuth2Config(...),
    # IntegrationType.GITHUB: OAuth2Config(...),
    # IntegrationType.LINKEDIN: OAuth2Config(...),
    
    config = configs.get(integration_type)
    if config and config.client_id and config.client_secret:
        return config
    
    return None


# Lazy imports to avoid circular dependencies
__all__ = [
    "get_provider_config",
    "GoogleOAuth2Provider",
    "SlackOAuth2Provider",
    "MicrosoftOAuth2Provider",
    "SalesforceOAuth2Provider",
    "GitHubOAuth2Provider",
    "LinkedInOAuth2Provider",
]


def __getattr__(name):
    """Lazy import providers."""
    if name == "GoogleOAuth2Provider":
        from .google import GoogleOAuth2Provider
        return GoogleOAuth2Provider
    elif name == "SlackOAuth2Provider":
        from .slack import SlackOAuth2Provider
        return SlackOAuth2Provider
    elif name == "MicrosoftOAuth2Provider":
        from .microsoft import MicrosoftOAuth2Provider
        return MicrosoftOAuth2Provider
    elif name == "SalesforceOAuth2Provider":
        from .salesforce import SalesforceOAuth2Provider
        return SalesforceOAuth2Provider
    elif name == "GitHubOAuth2Provider":
        from .github import GitHubOAuth2Provider
        return GitHubOAuth2Provider
    elif name == "LinkedInOAuth2Provider":
        from .linkedin import LinkedInOAuth2Provider
        return LinkedInOAuth2Provider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")