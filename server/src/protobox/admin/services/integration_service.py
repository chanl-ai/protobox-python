"""Integration service for managing workspace integrations."""

import traceback
from typing import Any, Optional

from loguru import logger
from fastapi import HTTPException

from ..database import get_database_connection
from ..models.secret import SecretCreateRequest, SecretUpdateRequest
from ..models.integration import (
    AuthType,
    IntegrationModel,
    IntegrationStatus,
    IntegrationType,
    IntegrationUIConfig,
    OAuth2TokenData,
)
from ..secrets.types import SecretType
from ..integrations.base_classes import IntegrationHealth
from ..integrations.registry import get_integration_registry
from ..secrets.encryption import SecretEncryption
from .action_service import ActionService
from .secret_service import SecretService


class IntegrationService:
    """Service for managing integrations."""

    def __init__(
        self, secret_service: SecretService, action_service: ActionService
    ) -> None:
        self.secret_service = secret_service
        self.action_service = action_service
        self.collection_name = "integrations"

    def _get_collection(self):
        """Get the integrations collection."""
        db_connection = get_database_connection()
        return db_connection.database[self.collection_name]

    async def get_available_integrations(self) -> list[IntegrationUIConfig]:
        """Get list of available integrations with their UI configurations."""
        from ..integrations import get_integration_registry, initialize_integrations
        
        # Initialize integrations if not already done
        initialize_integrations()
        
        # Get all registered integrations from the registry
        registry = get_integration_registry()
        all_integrations = []
        
        # Add integrations from registry using list_instances() which returns actual instances
        for integration in registry.list_instances():
            # Determine auth type based on the integration's base class
            auth_type = AuthType.OAUTH2
            if hasattr(integration, 'api_key_name'):
                auth_type = AuthType.API_KEY
            
            # Get category from integration or default
            category = getattr(integration, 'category', 'other')
            
            ui_config = IntegrationUIConfig(
                integration_type=integration.integration_type,
                display_name=integration.display_name,
                description=integration.description,
                category=category,
                auth_type=auth_type,
                available_actions=[],
            )
            all_integrations.append(ui_config)
        
        return all_integrations

    async def get_workspace_integrations(self, workspace_id: str) -> list[IntegrationModel]:
        """Get all integrations for a workspace."""

        try:
            collection = self._get_collection()
            cursor = collection.find({"workspace_id": workspace_id})
            integrations = []

            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                integration = IntegrationModel(**doc)
                integrations.append(integration)

            return integrations
        except Exception as e:
            logger.error(f"Error getting workspace integrations: {e}")
            return []

    async def get_workspace_integration(
        self, workspace_id: str, integration_type: IntegrationType
    ) -> Optional[IntegrationModel]:
        """Get a specific integration for a workspace."""
        try:
            collection = self._get_collection()
            doc = await collection.find_one(
                {
                    "workspace_id": workspace_id,
                    "integration_type": integration_type.value,
                }
            )

            if doc:
                doc["_id"] = str(doc["_id"])
                return IntegrationModel(**doc)

            return None
        except Exception as e:
            logger.error(f"Error getting integration: {e}")
            return None

    async def create_integration(
        self,
        workspace_id: str,
        integration_type: IntegrationType,
        auth_type: AuthType,
        config: dict[str, Any] | None = None,
    ) -> IntegrationModel:
        """Create a new integration."""
        try:
            integration = IntegrationModel(
                workspace_id=workspace_id,
                integration_type=integration_type,
                auth_type=auth_type,
                status=IntegrationStatus.NOT_CONNECTED,
                config=config or {},
            )

            collection = self._get_collection()
            result = await collection.insert_one(integration.model_dump_for_db())
            integration.id = str(result.inserted_id)

            return integration
        except Exception as e:
            logger.error(f"Error creating integration: {e}")
            raise
    
    async def ensure_all_integrations(self, workspace_id: str) -> list[IntegrationModel]:
        """Ensure all registered integrations exist for a workspace.
        
        Creates missing integration entries (in NOT_CONNECTED state) for any
        registered integrations that don't exist for the workspace.
        
        Returns:
            List of all integrations for the workspace (existing + newly created)
        """
        try:
            # Get all registered integration types
            registry = get_integration_registry()
            registered_types = registry.list_all()
            
            # Get existing integrations for workspace
            existing_integrations = await self.get_workspace_integrations(workspace_id)
            existing_types = {i.integration_type for i in existing_integrations}
            
            # Create missing integrations
            created_integrations = []
            for int_type in registered_types:
                if int_type not in existing_types:
                    # Get the integration instance to determine auth type
                    integration_instance = registry.get(int_type)
                    if integration_instance:
                        auth_type = integration_instance.auth_type
                        logger.info(f"Creating missing integration {int_type} for workspace {workspace_id}")
                        new_integration = await self.create_integration(
                            workspace_id=workspace_id,
                            integration_type=int_type,
                            auth_type=auth_type,
                            config={}
                        )
                        created_integrations.append(new_integration)
            
            if created_integrations:
                logger.info(f"Created {len(created_integrations)} missing integrations for workspace {workspace_id}")
            
            # Return all integrations
            return existing_integrations + created_integrations
            
        except Exception as e:
            logger.error(f"Error ensuring integrations for workspace {workspace_id}: {e}")
            raise

    async def update_integration(
        self,
        workspace_id: str,
        integration_type: IntegrationType,
        status: IntegrationStatus | None = None,
        config: dict[str, Any] | None = None,
        oauth_data: OAuth2TokenData | None = None,
        oauth_secret_id: str | None = None,
        api_key_secret_id: str | None = None,
        error_message: str | None = None,
    ) -> bool:
        """Update an integration."""
        try:
            update_data: dict[str, Any] = {}

            if status is not None:
                update_data["status"] = status.value

            if config is not None:
                update_data["config"] = config

            if oauth_data is not None:
                update_data["oauth_data"] = oauth_data.model_dump()
            
            if oauth_secret_id is not None:
                update_data["oauth_secret_id"] = oauth_secret_id

            if api_key_secret_id is not None:
                update_data["api_key_secret_id"] = api_key_secret_id

            if error_message is not None:
                update_data["error_message"] = error_message

            if not update_data:
                return True

            collection = self._get_collection()
            result = await collection.update_one(
                {
                    "workspace_id": workspace_id,
                    "integration_type": integration_type.value,
                },
                {"$set": update_data},
            )

            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating integration: {e}")
            return False

    async def delete_integration(
        self, workspace_id: str, integration_type: IntegrationType
    ) -> bool:
        """Delete an integration."""
        try:
            collection = self._get_collection()
            result = await collection.delete_one(
                {
                    "workspace_id": workspace_id,
                    "integration_type": integration_type.value,
                }
            )

            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting integration: {e}")
            return False

    async def start_connection(
        self,
        workspace_id: str,
        integration_type: IntegrationType,
        user_id: str,
    ) -> dict[str, Any]:
        """Start the connection process for an integration."""
        logger.info(f"Starting connection process for {integration_type}")

        from ..auth.oauth2_handler import OAuth2Handler
        from ..integrations import get_integration_registry
        
        # Get the integration from registry to determine auth type
        registry = get_integration_registry()
        integration_instance = registry.get(integration_type)
        
        if not integration_instance:
            raise ValueError(f"Integration {integration_type} not found in registry")
        
        # Determine auth type based on integration
        auth_type = (
            AuthType.API_KEY
            if hasattr(integration_instance, 'api_key_name')
            else AuthType.OAUTH2
        )
        logger.info(f"Using auth type: {auth_type.value} for {integration_type.value}")

        # Create or update integration record
        existing = await self.get_workspace_integration(workspace_id, integration_type)

        if not existing:
            integration = await self.create_integration(
                workspace_id=workspace_id,
                integration_type=integration_type,
                auth_type=auth_type,
            )
        else:
            integration = existing

        # For OAuth2 integrations, generate authorization URL
        if auth_type == AuthType.OAUTH2:
            # Use the actual OAuth2Handler to generate proper URL
            oauth_handler = OAuth2Handler()
            try:
                authorization_url = oauth_handler.get_authorization_url(
                    integration_type=integration_type,
                    workspace_id=workspace_id,
                    user_id=user_id
                )
                return {
                    "type": "oauth2",
                    "authorization_url": authorization_url,
                }
            except Exception as e:
                logger.error(f"Failed to generate OAuth URL: {e}")
                raise HTTPException(status_code=400, detail=f"Failed to generate OAuth URL: {e}")
        else:
            # For API key integrations
            setup_instructions = integration_instance.get_setup_instructions()
            
            return {
                "type": "api_key",
                "display_name": integration_instance.display_name,
                "instructions": setup_instructions.get("steps", []),
                "fields": setup_instructions.get("fields", []),
                "message": f"Enter your credentials for {integration_instance.display_name}",
            }

    async def disconnect_integration(
        self, workspace_id: str, integration_type: IntegrationType, user_id: str,
    ) -> bool:
        """Disconnect an integration."""
        try:
            # Delete associated actions
            all_actions = await self.action_service.list_actions(
                workspace_id=workspace_id
            )
            
            deleted_count = 0
            integration_name = integration_type.value.lower()
            for action in all_actions:
                # Check if action is related to this integration
                if integration_name in action.name.lower() or integration_name.replace("_", " ") in action.name.lower():
                    success = await self.action_service.delete_action(action.id)
                    if success:
                        deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} actions for {integration_type}")
            
            # Update status to not connected
            success = await self.update_integration(
                workspace_id=workspace_id,
                integration_type=integration_type,
                status=IntegrationStatus.NOT_CONNECTED,
                oauth_data=None,
                oauth_secret_id=None,
                api_key_secret_id=None,
            )

            # Delete associated OAuth secret if it exists
            try:                
                encryption = SecretEncryption()
                secret_service = SecretService(encryption)
                
                # Find and delete the OAuth secret for this integration
                secret_name = f"{integration_type.value}_oauth_token"
                existing_secrets = await secret_service.list_secrets(workspace_id=workspace_id)
                for secret in existing_secrets:
                    if secret.name == secret_name:
                        await secret_service.delete_secret(secret.id, user_id=user_id)
                        logger.info(f"Deleted OAuth secret for {integration_type}")
                        break
            except Exception as e:
                traceback.print_exc()
                logger.error(f"Error cleaning up OAuth secret: {e}")
                # Continue even if secret cleanup fails

            return success
        except Exception as e:
            logger.error(f"Error disconnecting integration: {e}")
            return False

    async def get_integration_data(
        self, workspace_id: str, integration_type: IntegrationType
    ) -> dict[str, Any]:
        """Get integration-specific data (e.g., calendars for Google Calendar)."""
        # Get the integration
        integration = await self.get_workspace_integration(workspace_id, integration_type)
        
        if not integration or integration.status != IntegrationStatus.CONNECTED:
            return {"error": "Integration not connected"}
        
        # Get the integration instance from registry
        from ..integrations import get_integration_registry
        registry = get_integration_registry()
        integration_instance = registry.get(integration_type)
        if not integration_instance:
            return {"error": f"Integration {integration_type} not found"}
        
        # Handle Google Calendar specifically
        if integration_type == IntegrationType.GOOGLE_CALENDAR:
            try:
                # Get Google Calendar integration instance
                registry = get_integration_registry()
                google_integration = registry.get(IntegrationType.GOOGLE_CALENDAR)
                
                if not google_integration:
                    return {"error": "Google Calendar integration not found"}
                
                # Check if we have cached calendar data in integration config
                if integration.config and integration.config.get("calendars"):
                    # Return cached data with fresh timestamp
                    cached_data = integration.config.copy()
                    cached_data["last_fetched"] = "cached"
                    return cached_data
                
                # Fetch fresh calendar data using OAuth token
                if integration.oauth_data and integration.oauth_data.access_token:
                    # Check if token needs refresh
                    from datetime import datetime, timedelta
                    import dateutil.parser
                    
                    access_token = integration.oauth_data.access_token
                    
                    # Check if access token is expired
                    if hasattr(integration.oauth_data, 'expires_at') and integration.oauth_data.expires_at:
                        try:
                            # Handle both string and datetime objects
                            if isinstance(integration.oauth_data.expires_at, str):
                                expires_at = dateutil.parser.parse(integration.oauth_data.expires_at)
                            else:
                                expires_at = integration.oauth_data.expires_at
                            
                            now = datetime.utcnow().replace(tzinfo=expires_at.tzinfo) if expires_at.tzinfo else datetime.utcnow()
                            
                            if now >= expires_at:
                                logger.info("Google Calendar token expired, refreshing...")
                                # Token is expired, refresh it
                                if integration.oauth_data.refresh_token:
                                    try:
                                        refresh_result = await google_integration.refresh_token(
                                            integration.oauth_data.refresh_token
                                        )
                                        
                                        # Update integration with new tokens
                                        from ..models.integration import OAuth2TokenData
                                        new_oauth_data = OAuth2TokenData(
                                            access_token=refresh_result["access_token"],
                                            refresh_token=integration.oauth_data.refresh_token,  # Keep existing refresh token
                                            token_type=refresh_result.get("token_type", "Bearer"),
                                            expires_in=refresh_result.get("expires_in", 3600),
                                            expires_at=(datetime.utcnow() + timedelta(seconds=refresh_result.get("expires_in", 3600))).isoformat(),
                                            scope=integration.oauth_data.scope
                                        )
                                        
                                        await self.update_integration(
                                            workspace_id=workspace_id,
                                            integration_type=integration_type,
                                            oauth_data=new_oauth_data
                                        )
                                        
                                        access_token = refresh_result["access_token"]
                                        logger.info("Google Calendar token refreshed successfully")
                                        
                                    except Exception as e:
                                        logger.error(f"Failed to refresh Google Calendar token: {e}")
                                        return {"error": "Failed to refresh OAuth token. Please reconnect Google Calendar."}
                                else:
                                    return {"error": "No refresh token available. Please reconnect Google Calendar."}
                        except Exception as e:
                            logger.warning(f"Error parsing token expiry date: {e}")
                    
                    calendar_data = await google_integration.fetch_user_calendars(access_token)
                    
                    # Update integration config with fetched data
                    if not calendar_data.get("error"):
                        from datetime import datetime
                        calendar_data["last_fetched"] = datetime.utcnow().isoformat()
                        
                        # Update the integration config with fresh data
                        await self.update_integration(
                            workspace_id=workspace_id,
                            integration_type=integration_type,
                            config=calendar_data
                        )
                    
                    # Add common timezones for user selection
                    calendar_data["timezones"] = [
                        {"value": "America/New_York", "label": "Eastern Time (ET)"},
                        {"value": "America/Chicago", "label": "Central Time (CT)"},
                        {"value": "America/Denver", "label": "Mountain Time (MT)"},
                        {"value": "America/Los_Angeles", "label": "Pacific Time (PT)"},
                        {"value": "Europe/London", "label": "London (GMT)"},
                        {"value": "Europe/Paris", "label": "Paris (CET)"},
                        {"value": "Asia/Tokyo", "label": "Tokyo (JST)"},
                        {"value": "Asia/Shanghai", "label": "Shanghai (CST)"},
                        {"value": "Australia/Sydney", "label": "Sydney (AEDT)"},
                    ]
                    
                    return calendar_data
                else:
                    return {"error": "No valid OAuth token found for Google Calendar"}
                    
            except Exception as e:
                logger.error(f"Error fetching Google Calendar data: {e}")
                return {"error": f"Failed to fetch Google Calendar data: {str(e)}"}
        elif integration_type == IntegrationType.GMAIL:
            # Mock Gmail labels
            return {
                "labels": [
                    {"id": "INBOX", "name": "Inbox"},
                    {"id": "SENT", "name": "Sent"},
                    {"id": "DRAFT", "name": "Drafts"},
                    {"id": "IMPORTANT", "name": "Important"},
                    {"id": "STARRED", "name": "Starred"},
                    {"id": "TRASH", "name": "Trash"},
                    {"id": "SPAM", "name": "Spam"},
                ],
                "filters": [],
                "signatures": []
            }
        elif integration_type == IntegrationType.GITHUB:
            # Mock GitHub repositories
            return {
                "repositories": [
                    {"id": "repo1", "name": "my-project", "full_name": "user/my-project", "default_branch": "main"},
                    {"id": "repo2", "name": "another-project", "full_name": "user/another-project", "default_branch": "master"},
                    {"id": "repo3", "name": "team-project", "full_name": "org/team-project", "default_branch": "main"},
                ],
                "organizations": [
                    {"id": "org1", "login": "my-org", "name": "My Organization"},
                ]
            }
        else:
            return {}

    async def test_integration(
        self, workspace_id: str, integration_type: IntegrationType
    ) -> IntegrationHealth:
        """Test an integration connection."""
        integration = await self.get_workspace_integration(workspace_id, integration_type)

        if not integration:
            return IntegrationHealth(
                is_healthy=False,
                error_message="Integration not found",
                details={"error": "not_found"},
            )

        if integration.status != IntegrationStatus.CONNECTED:
            return IntegrationHealth(
                is_healthy=False,
                error_message="Integration not connected",
                details={"status": integration.status},
            )

        # Provider-specific health check
        # This is a placeholder - actual implementation will use provider-specific logic
        return IntegrationHealth(
            is_healthy=True,
            error_message=None,
            details={},
        )

    async def _create_integration_actions(
        self, workspace_id: str, integration_type: IntegrationType, oauth_secret_id: str | None = None
    ) -> list[str]:
        """Create default actions for an integration from templates."""
        created_action_ids = []
        
        try:
            from ..services.template_manager import TemplateManager
            from ..models.action import ActionCreateRequest, ActionType
            
            # Initialize template manager
            template_manager = TemplateManager()
            await template_manager.initialize()
            
            # Get templates that require this integration
            templates = await template_manager.get_all_templates(
                connected_integrations=[integration_type]
            )
            
            # Get the integration config to use the primary calendar ID
            integration = await self.get_workspace_integration(workspace_id, integration_type)
            default_calendar_id = "primary"  # Default fallback
            if integration and integration.config:
                default_calendar_id = integration.config.get("default_calendar_id", "primary")
            
            # Create actions from templates
            for template in templates:                
                if integration_type in template.required_integrations:
                    try:
                        # Get the default config and update calendar_id if it's a Google Calendar template
                        default_config = template.default_config or {}
                        if integration_type == IntegrationType.GOOGLE_CALENDAR and "calendar_id" in default_config:
                            default_config["calendar_id"] = default_calendar_id
                        
                        # Replace old token placeholders with secret references if OAuth secret ID is provided
                        if oauth_secret_id and default_config:
                            # Update authorization header to use secret reference
                            if "headers" in default_config and "Authorization" in default_config["headers"]:
                                # Replace old placeholder with secret reference
                                default_config["headers"]["Authorization"] = f"Bearer ${{secret:{integration_type.value}_oauth_token.access_token}}"
                        logger.info(f"Creating action from template {template.name} for {integration_type} in workspace {workspace_id}")
                        # Create action from template - use proper field mapping
                        action_request = ActionCreateRequest(
                            workspace_id=workspace_id,
                            name=template.id.replace("_", " ").title(),
                            type=ActionType.REST,
                            description=template.description,
                            default_config=default_config,
                            config_schema=template.config_schema or {},
                            tags=template.tags or [],
                            version=getattr(template, 'version', '1.0.0'),
                        )
                        
                        # Create the action (create_action takes request and user_id)
                        action_id = await self.action_service.create_action(
                            request=action_request,
                            user_id="system"  # System-created action
                        )
                        
                        if action_id:
                            created_action_ids.append(action_id)
                            logger.info(f"Created action {template.id} for {integration_type}")
                    except Exception as e:
                        logger.error(f"Failed to create action from template {template.id}: {e}\n{traceback.format_exc()}")
            
            logger.info(f"Created {len(created_action_ids)} actions for {integration_type}")
            
        except Exception as e:
            traceback.print_exc()
            logger.error(f"Error creating integration actions: {e}")
        
        return created_action_ids

    async def reset_integration_actions(
        self, workspace_id: str, integration_type: IntegrationType
    ) -> dict[str, Any]:
        """Reset integration actions to defaults."""
        try:
            # Get all actions for this workspace
            all_actions = await self.action_service.list_actions(
                workspace_id=workspace_id
            )
            
            deleted_count = 0
            # Filter and delete actions related to this integration
            integration_name = integration_type.value.lower()
            for action in all_actions:
                # Check if action is related to this integration
                if integration_name in action.name.lower() or integration_name.replace("_", " ") in action.name.lower():
                    success = await self.action_service.delete_action(action.id)
                    if success:
                        deleted_count += 1

            # Create default actions based on integration templates
            created_action_ids = await self._create_integration_actions(workspace_id, integration_type)

            return {
                "deleted_actions": deleted_count,
                "created_actions": len(created_action_ids),
            }
        except Exception as e:
            logger.error(f"Error resetting integration actions: {e}")
            raise

    async def complete_oauth_connection(
        self,
        workspace_id: str,
        integration_type: IntegrationType,
        oauth_data: OAuth2TokenData,
    ) -> bool:
        """Complete OAuth connection by storing tokens and updating status."""
        try:
            # Store OAuth tokens as an encrypted secret
            secret_name = f"{integration_type.value}_oauth_token"
            
            # Initialize secret service
            encryption = SecretEncryption()
            secret_service = SecretService(encryption)
            
            # Check if secret already exists for this integration
            existing_secret = await secret_service.get_secret_by_name(workspace_id=workspace_id, name=secret_name)
            oauth_secret_id = existing_secret.id if existing_secret else None
            
            # Prepare OAuth data as JSON string
            oauth_data_json = oauth_data.model_dump_json()
            
            if existing_secret:
                # Update existing secret
                update_request = SecretUpdateRequest(
                    secret_value=oauth_data_json,
                    description=f"OAuth tokens for {integration_type.value}"
                )
                success = await secret_service.update_secret(
                    secret_id=existing_secret.id,
                    request=update_request,
                    user_id="system"  # System update for OAuth
                )
                logger.info(f"Updated existing OAuth secret for {integration_type} in workspace {workspace_id}")
            else:
                # Create new secret
                create_request = SecretCreateRequest(
                    workspace_id=workspace_id,
                    name=secret_name,
                    description=f"OAuth tokens for {integration_type.value}",
                    secret_type=SecretType.OAUTH_TOKEN,
                    secret_value=oauth_data_json,
                    tags=[integration_type.value, "oauth", "auto-refresh"]
                )
                oauth_secret_id = await secret_service.create_secret(
                    request=create_request,
                    user_id="system"  # System creation for OAuth
                )
                logger.info(f"Created OAuth secret for {integration_type} in workspace {workspace_id}")
            
            # For Google Calendar, fetch user's calendars and set primary as default
            config = {}
            if integration_type == IntegrationType.GOOGLE_CALENDAR:
                from ..integrations import get_integration_registry
                registry = get_integration_registry()
                google_cal_integration = registry.get(IntegrationType.GOOGLE_CALENDAR)
                
                if google_cal_integration and oauth_data.access_token:
                    # Fetch user's calendars
                    calendar_data = await google_cal_integration.fetch_user_calendars(oauth_data.access_token)
                    
                    if calendar_data and calendar_data.get("calendars"):
                        calendars = calendar_data["calendars"]
                        # Find primary calendar
                        primary_calendar_id = "primary"  # Default to "primary" identifier
                        for cal in calendars:
                            if cal.get("primary"):
                                primary_calendar_id = cal.get("id", "primary")
                                break
                        
                        # Set the primary calendar as the default in config
                        config = {
                            "default_calendar_id": primary_calendar_id,
                            "calendars": calendars,  # Store calendar list for reference
                            "timezone": calendar_data.get("timezone"),
                        }
                        logger.info(f"Set primary calendar {primary_calendar_id} as default for workspace {workspace_id}")
            
            # Update integration with secret reference and mark as connected
            success = await self.update_integration(
                workspace_id=workspace_id,
                integration_type=integration_type,
                status=IntegrationStatus.CONNECTED,
                oauth_secret_id=oauth_secret_id,  # Store reference to secret
                config=config,  # Pass the config with calendar settings
                error_message=None,
            )
            
            if success:
                logger.info(f"OAuth connection completed for {integration_type} in workspace {workspace_id}")
                
                # Create default actions for this integration with secret reference
                await self._create_integration_actions(
                    workspace_id=workspace_id, 
                    integration_type=integration_type,
                    oauth_secret_id=oauth_secret_id
                )
            else:
                logger.error(f"Failed to update integration {integration_type} with OAuth secret")
            
            return success
        except Exception as e:
            traceback.print_exc()
            logger.error(f"Error completing OAuth connection: {e}")
            await self.update_integration(
                workspace_id=workspace_id,
                integration_type=integration_type,
                status=IntegrationStatus.ERROR,
                error_message=str(e),
            )
            return False