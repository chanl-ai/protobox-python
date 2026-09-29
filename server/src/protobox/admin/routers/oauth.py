"""OAuth callback handler for integrations."""

import json
import uuid
from datetime import UTC, datetime, timedelta

from loguru import logger
from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from ..auth.oauth2_handler import OAuth2Handler
from ..config import settings
from ..models.integration import IntegrationType, OAuth2TokenData
from ..secrets.encryption import SecretEncryption
from ..services.action_service import ActionService
from ..services.integration_service import IntegrationService
from ..services.secret_service import SecretService


router = APIRouter(tags=["OAuth"])

# Initialize services
encryption = SecretEncryption()
secret_service = SecretService(encryption)
action_service = ActionService()
integration_service = IntegrationService(
    secret_service=secret_service, action_service=action_service
)
oauth_handler = OAuth2Handler()


def generate_oauth_success_html(integration_type: str) -> str:
    """Generate HTML page for successful OAuth callback."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Integration Connected</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
                background-color: #f7fafc;
            }}
            .container {{
                text-align: center;
                padding: 2rem;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                max-width: 400px;
            }}
            .success-icon {{
                color: #22c55e;
                font-size: 3rem;
                margin-bottom: 1rem;
            }}
            h1 {{
                color: #1f2937;
                font-size: 1.5rem;
                margin-bottom: 0.5rem;
            }}
            p {{
                color: #6b7280;
                margin-bottom: 1.5rem;
            }}
            .close-text {{
                color: #9ca3af;
                font-size: 0.875rem;
            }}
        </style>
        <script>
            // Send success message to parent window
            if (window.opener) {{
                window.opener.postMessage({{
                    type: 'OAUTH_SUCCESS',
                    integration: '{integration_type}'
                }}, window.location.origin);
            }}

            // Auto-close after 3 seconds
            setTimeout(() => {{
                window.close();
            }}, 3000);
        </script>
    </head>
    <body>
        <div class="container">
            <div class="success-icon">✓</div>
            <h1>Successfully Connected!</h1>
            <p>{integration_type.replace('_', ' ').title()} has been connected to your workspace.</p>
            <p class="close-text">This window will close automatically...</p>
        </div>
    </body>
    </html>
    """


def generate_oauth_error_html(error: str, description: str = "") -> str:
    """Generate HTML page for OAuth error."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Integration Error</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
                background-color: #f7fafc;
            }}
            .container {{
                text-align: center;
                padding: 2rem;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                max-width: 400px;
            }}
            .error-icon {{
                color: #ef4444;
                font-size: 3rem;
                margin-bottom: 1rem;
            }}
            h1 {{
                color: #1f2937;
                font-size: 1.5rem;
                margin-bottom: 0.5rem;
            }}
            p {{
                color: #6b7280;
                margin-bottom: 1.5rem;
            }}
            .error-details {{
                background: #fef2f2;
                border: 1px solid #fecaca;
                border-radius: 4px;
                padding: 0.75rem;
                color: #991b1b;
                font-size: 0.875rem;
                margin-bottom: 1rem;
            }}
            .close-text {{
                color: #9ca3af;
                font-size: 0.875rem;
            }}
        </style>
        <script>
            // Send error message to parent window
            if (window.opener) {{
                window.opener.postMessage({{
                    type: 'OAUTH_ERROR',
                    error: '{error}',
                    description: '{description}'
                }}, window.location.origin);
            }}

            // Auto-close after 5 seconds
            setTimeout(() => {{
                window.close();
            }}, 5000);
        </script>
    </head>
    <body>
        <div class="container">
            <div class="error-icon">✗</div>
            <h1>Connection Failed</h1>
            <p>We couldn't connect the integration.</p>
            <div class="error-details">
                {error}: {description or 'Please try again'}
            </div>
            <p class="close-text">This window will close automatically...</p>
        </div>
    </body>
    </html>
    """


# IMPORTANT: This callback route is mounted under /integrations prefix in router.py
# Final URL: /admin/api/v1/integrations/oauth/callback/{integration_provider}
# This MUST match Google Cloud Console redirect URI configuration
@router.get("/oauth/callback/{integration_provider}")
async def handle_oauth_callback(
    integration_provider: str,
    request: Request,
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    error_description: str | None = Query(None),
) -> HTMLResponse:
    """Handle OAuth callback from external services."""
    logger.info(f"OAuth callback for {integration_provider} with code: {code} and state: {state}")
    try:
        # Handle error from OAuth provider
        if error:
            logger.error(f"OAuth error for {integration_provider}: {error} - {error_description}")
            return HTMLResponse(
                content=generate_oauth_error_html(error, error_description or ""), status_code=200
            )

        # Validate required parameters
        if not code or not state:
            logger.error(f"Missing required OAuth parameters for {integration_provider}")
            return HTMLResponse(
                content=generate_oauth_error_html(
                    "invalid_request", "Missing authorization code or state"
                ),
                status_code=200,
            )

        # Extract data from state
        try:
            # Try OAuth handler's state format first
            try:
                state_info = oauth_handler.parse_state_parameter(state)
                workspace_id = state_info["workspace_id"]
                user_id = state_info["user_id"]
                integration_type = state_info["integration_type"]
            except:
                # Fallback to JSON format (for backwards compatibility)
                state_data = json.loads(state)
                workspace_id = state_data.get("workspace_id")
                user_id = state_data.get("user_id")
                integration_type = state_data.get("integration_type")

            if not workspace_id or not user_id or not integration_type:
                raise ValueError("Missing workspace_id, user_id or integration_type in state")
        except Exception as e:
            logger.error(f"Invalid state parameter: {e}")
            return HTMLResponse(
                content=generate_oauth_error_html("invalid_state", "Invalid authorization state"),
                status_code=200,
            )

        # Validate integration type
        try:
            integration_type_enum = IntegrationType(integration_type)
            logger.info(f"Integration type: {integration_type}")
        except ValueError:
            logger.error(f"Invalid integration type: {integration_type}")
            return HTMLResponse(
                content=generate_oauth_error_html(
                    "invalid_integration", f"Unknown integration type: {integration_type}"
                ),
                status_code=200,
            )

        # Handle demo mode
        if settings.google_client_id == "demo-client-id" or not settings.google_client_id:
            logger.info(f"Demo mode: Simulating OAuth success for {integration_type}")

            # Create demo OAuth data
            oauth_data = OAuth2TokenData(
                access_token=f"demo_access_token_{uuid.uuid4().hex[:16]}",
                refresh_token=f"demo_refresh_token_{uuid.uuid4().hex[:16]}",
                token_type="Bearer",
                expires_at=datetime.now(UTC) + timedelta(hours=1),
                scope="https://www.googleapis.com/auth/calendar",
            )

            # Update integration with demo tokens
            await integration_service.complete_oauth_connection(
                workspace_id=workspace_id,
                integration_type=integration_type_enum,
                oauth_data=oauth_data,
            )

            return HTMLResponse(
                content=generate_oauth_success_html(integration_type), status_code=200
            )

        # Exchange authorization code for tokens using OAuth handler
        try:
            token_data = await oauth_handler.exchange_code_for_tokens(
                integration_type=integration_type_enum, authorization_code=code
            )
        except Exception as e:
            logger.error(f"Token exchange failed: {e}")
            token_data = None

        if not token_data:
            logger.error(f"Failed to exchange code for tokens for {integration_type}")
            return HTMLResponse(
                content=generate_oauth_error_html(
                    "token_exchange_failed", "Failed to exchange authorization code"
                ),
                status_code=200,
            )

        # Update integration with tokens
        await integration_service.complete_oauth_connection(
            workspace_id=workspace_id, integration_type=integration_type_enum, oauth_data=token_data
        )

        logger.info(f"Successfully connected {integration_type} for workspace {workspace_id}")

        return HTMLResponse(content=generate_oauth_success_html(integration_type), status_code=200)

    except Exception as e:
        logger.error(f"Unexpected error in OAuth callback for {integration_type}: {e}")
        return HTMLResponse(
            content=generate_oauth_error_html("server_error", "An unexpected error occurred"),
            status_code=200,
        )
