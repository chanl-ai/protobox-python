"""OAuth2 integrations management system."""

from loguru import logger

from .base import BaseOAuth2Provider, OAuth2Config
from .google_calendar import GoogleCalendarIntegration
from .registry import IntegrationRegistry, get_integration_registry

# Import Google integrations
from .gmail_integration import GmailIntegration
from .google_drive_integration import GoogleDriveIntegration
from .google_sheets_integration import GoogleSheetsIntegration
from .google_docs_integration import GoogleDocsIntegration
from .google_analytics_integration import GoogleAnalyticsIntegration
from .google_ads_integration import GoogleAdsIntegration

# Import other integrations
from .slack_integration import SlackIntegration
from .openai_integration import OpenAIIntegration
from .stripe_integration import StripeIntegration
from .github_integration import GitHubIntegration
from .twilio_integration import TwilioIntegration
from .sendgrid_integration import SendGridIntegration
from .notion_integration import NotionIntegration
from .resend_integration import ResendIntegration
from .anthropic_integration import AnthropicIntegration
from .airtable_integration import AirtableIntegration
from .hubspot_integration import HubspotIntegration


def initialize_integrations():
    """Initialize and register all available integrations."""
    logger.info("Starting integration initialization...")
    registry = get_integration_registry()
    
    # Clear any existing registrations
    registry.clear()
    logger.info("Cleared existing registrations")
    
    # Register all integrations
    integrations_to_register = [
        # Google Services
        GoogleCalendarIntegration,
        GmailIntegration,
        GoogleDriveIntegration,
        GoogleSheetsIntegration,
        GoogleDocsIntegration,
        GoogleAnalyticsIntegration,
        GoogleAdsIntegration,
        # Other Services
        SlackIntegration,
        OpenAIIntegration,
        StripeIntegration,
        GitHubIntegration,
        TwilioIntegration,
        SendGridIntegration,
        NotionIntegration,
        ResendIntegration,
        AnthropicIntegration,
        AirtableIntegration,
        HubspotIntegration,
    ]
    
    for integration_class in integrations_to_register:
        try:
            registry.register(integration_class)
            logger.info(f"Registered {integration_class.__name__}")
        except Exception as e:
            logger.error(f"Failed to register {integration_class.__name__}: {e}")
    
    logger.info(f"Initialized {len(registry.list_all())} integrations")
    return registry


__all__ = [
    "BaseOAuth2Provider",
    "OAuth2Config",
    "IntegrationRegistry",
    "get_integration_registry",
    "GoogleCalendarIntegration",
    "GmailIntegration",
    "SlackIntegration",
    "OpenAIIntegration",
    "StripeIntegration",
    "GitHubIntegration",
    "TwilioIntegration",
    "SendGridIntegration",
    "NotionIntegration",
    "HubspotIntegration",
    "initialize_integrations",
]