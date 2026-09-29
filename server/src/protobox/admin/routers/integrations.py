"""Integrations router for managing workspace integrations."""

import json
from datetime import datetime, UTC
from typing import Any
import traceback

from loguru import logger
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer

from ..secrets.types import SecretType
from ..auth.dependencies import User, get_current_user, require_authentication
from ..integrations.registry import get_integration_registry
from ..models.secret import SecretCreateRequest, SecretUpdateRequest
from ..models.integration import (
    AuthType,
    IntegrationModel,
    IntegrationStatus,
    IntegrationType,
    IntegrationUIConfig,
)
from ..services.integration_service import IntegrationService
from ..services.secret_service import SecretService
from .workspace import get_workspace_id, workspace_router


# Create router
router = APIRouter()

# Security scheme
security = HTTPBearer(auto_error=False)

# Create integration service instance
from ..secrets.encryption import SecretEncryption
from ..services.action_service import ActionService

encryption = SecretEncryption()
secret_service = SecretService(encryption)
action_service = ActionService()
integration_service = IntegrationService(
    secret_service=secret_service, action_service=action_service
)


@router.get("/integrations/available", response_model=list[IntegrationUIConfig])
async def get_available_integrations(
    current_user: User = Depends(require_authentication),
) -> list[IntegrationUIConfig]:
    """Get list of available integrations."""
    try:
        return await integration_service.get_available_integrations()
    except Exception as e:
        logger.error(f"Failed to get available integrations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve available integrations",
        )


# Workspace-specific integration endpoints
workspace_integrations_router = APIRouter()


@workspace_integrations_router.get("", response_model=list[IntegrationModel])
async def get_workspace_integrations(
    workspace_id: str = Depends(get_workspace_id), current_user: User = Depends(get_current_user)
) -> list[IntegrationModel]:
    """Get all integrations for a workspace."""
    try:
        return await integration_service.get_workspace_integrations(workspace_id)
    except Exception as e:
        logger.error(f"Failed to get workspace integrations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workspace integrations",
        )


@workspace_integrations_router.post("/initialize")
async def initialize_workspace_integrations(
    workspace_id: str = Depends(get_workspace_id),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Initialize all missing integrations for a workspace.
    
    Creates database entries for any registered integrations that don't exist
    for the workspace. All new integrations will be in NOT_CONNECTED state.
    
    Returns:
        Summary of initialization including counts of existing and created integrations
    """
    try:
        # Get existing integrations before initialization
        existing_before = await integration_service.get_workspace_integrations(workspace_id)
        existing_count = len(existing_before)
        
        # Ensure all integrations exist
        all_integrations = await integration_service.ensure_all_integrations(workspace_id)
        total_count = len(all_integrations)
        created_count = total_count - existing_count
        
        return {
            "workspace_id": workspace_id,
            "existing_integrations": existing_count,
            "created_integrations": created_count,
            "total_integrations": total_count,
            "integrations": all_integrations
        }
    except Exception as e:
        logger.error(f"Failed to initialize integrations for workspace {workspace_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize workspace integrations",
        )


@workspace_integrations_router.get("/{integration_type}/settings")
async def get_integration_settings(
    integration_type: str,
    workspace_id: str = Depends(get_workspace_id),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get integration settings and schema.
    
    Returns:
        - schema: JSON schema for settings
        - current: Current settings values
        - defaults: Default settings values
    """
    try:
        # Validate integration type
        try:
            integration_type_enum = IntegrationType(integration_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid integration type: {integration_type}"
            )
        
        # Get integration from database
        logger.info(f"Getting integration for workspace {workspace_id}, type {integration_type_enum}")
        integration = await integration_service.get_workspace_integration(workspace_id, integration_type_enum)
        logger.info(f"Integration found: {integration is not None}")
        
        # Get integration instance from registry
        registry = get_integration_registry()
        integration_instance = registry.get(integration_type_enum)
        
        if not integration_instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Integration {integration_type} not found in registry"
            )
        
        # Get schema and defaults
        schema = integration_instance.get_settings_schema()
        defaults = integration_instance.get_default_settings()
        
        # Get current settings (merge with defaults)
        current = defaults.copy()
        if integration and integration.config:
            current.update(integration.config)
        
        return {
            "integration_type": integration_type,
            "schema": schema,
            "current": current,
            "defaults": defaults,
            "is_connected": integration.status == IntegrationStatus.CONNECTED if integration else False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get integration settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get integration settings"
        )


@workspace_integrations_router.put("/{integration_type}/settings")
async def update_integration_settings(
    integration_type: str,
    settings: dict[str, Any],
    workspace_id: str = Depends(get_workspace_id),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Update integration settings.
    
    Validates settings against schema before saving.
    """
    try:
        # Validate integration type
        try:
            integration_type_enum = IntegrationType(integration_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid integration type: {integration_type}"
            )
        
        # Get integration instance from registry
        registry = get_integration_registry()
        integration_instance = registry.get(integration_type_enum)
        
        if not integration_instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Integration {integration_type} not found in registry"
            )
        
        # Validate settings
        is_valid, error = integration_instance.validate_settings(settings)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid settings: {error}"
            )
        
        # Get or create integration
        integration = await integration_service.get_workspace_integration(workspace_id, integration_type_enum)
        
        if not integration:
            # Create integration if it doesn't exist
            integration = await integration_service.create_integration(
                workspace_id=workspace_id,
                integration_type=integration_type_enum,
                auth_type=integration_instance.auth_type,
                config=settings
            )
        else:
            # Update existing integration settings
            success = await integration_service.update_integration(
                workspace_id=workspace_id,
                integration_type=integration_type_enum,
                config=settings
            )
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update settings"
                )
        
        return {
            "message": "Settings updated successfully",
            "settings": settings
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update integration settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update integration settings"
        )


@workspace_integrations_router.post("/{integration_type}/validate")
async def validate_integration_settings(
    integration_type: str,
    settings: dict[str, Any],
    workspace_id: str = Depends(get_workspace_id),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Validate integration settings without saving.
    
    Tests if settings are valid and optionally tests connection.
    """
    try:
        # Validate integration type
        try:
            integration_type_enum = IntegrationType(integration_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid integration type: {integration_type}"
            )
        
        # Get integration instance from registry
        registry = get_integration_registry()
        integration_instance = registry.get(integration_type_enum)
        
        if not integration_instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Integration {integration_type} not found in registry"
            )
        
        # Validate settings
        is_valid, error = integration_instance.validate_settings(settings)
        
        result = {
            "valid": is_valid,
            "error": error,
            "integration_type": integration_type
        }
        
        # If settings are valid and integration is connected, test connection
        if is_valid:
            integration = await integration_service.get_workspace_integration(workspace_id, integration_type_enum)
            if integration and integration.status == IntegrationStatus.CONNECTED:
                # Get credentials from secrets
                credentials = {}
                if integration.oauth_secret_id:
                    secret = await secret_service.get_secret(integration.oauth_secret_id, workspace_id)
                    if secret:
                        credentials = json.loads(secret_service.decrypt_value(secret.value))
                elif integration.api_key_secret_id:
                    secret = await secret_service.get_secret(integration.api_key_secret_id, workspace_id)
                    if secret:
                        credentials = {"api_key": secret_service.decrypt_value(secret.value)}
                
                # Test with settings and credentials
                health = await integration_instance.test_with_settings(settings, credentials)
                result["connection_test"] = {
                    "healthy": health.is_healthy,
                    "error": health.error_message,
                    "details": health.details
                }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate integration settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate integration settings"
        )


@workspace_integrations_router.get("/{integration_type}/data")
async def get_integration_data(
    integration_type: str,
    workspace_id: str = Depends(get_workspace_id),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get integration-specific data (e.g., calendar list for Google Calendar)."""
    try:
        # Validate integration type
        try:
            integration_type_enum = IntegrationType(integration_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid integration type: {integration_type}",
            )
        
        # Get the integration
        integration = await integration_service.get_workspace_integration(
            workspace_id, integration_type_enum
        )
        
        if not integration or integration.status != IntegrationStatus.CONNECTED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Integration {integration_type} not connected",
            )
        
        # Get integration-specific data
        data = await integration_service.get_integration_data(
            workspace_id, integration_type_enum
        )
        
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get integration data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve integration data",
        )


@workspace_integrations_router.post("/{integration_type}/connect")
async def connect_integration(
    integration_type: str,
    workspace_id: str = Depends(get_workspace_id),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Start the connection process for an integration."""
    try:
        # Validate integration type
        try:
            integration_type_enum = IntegrationType(integration_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid integration type: {integration_type}",
            )

        # Check if integration already exists
        existing = await integration_service.get_workspace_integration(
            workspace_id, integration_type_enum
        )

        if existing and existing.status == IntegrationStatus.CONNECTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Integration already connected"
            )

        # Start connection process
        return await integration_service.start_connection(
            workspace_id=workspace_id,
            integration_type=integration_type_enum,
            user_id=current_user.id,
        )


    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to connect integration {integration_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to connect integration",
        )


@workspace_integrations_router.post("/{integration_type}/credentials")
async def save_integration_credentials(
    integration_type: str,
    credentials: dict[str, Any],
    workspace_id: str = Depends(get_workspace_id),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Save API key credentials for an integration."""
    try:
        # Validate integration type
        try:
            integration_type_enum = IntegrationType(integration_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid integration type: {integration_type}",
            )

        # Get the integration instance
        from ..integrations import get_integration_registry
        registry = get_integration_registry()
        integration_instance = registry.get(integration_type_enum)
        
        if not integration_instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Integration {integration_type} not found",
            )
        
        # Verify it's an API key integration
        if not hasattr(integration_instance, 'api_key_name'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Integration {integration_type} does not use API key authentication",
            )
        
        # Get required fields from integration setup instructions
        setup_instructions = integration_instance.get_setup_instructions()
        required_fields = [field for field in setup_instructions["fields"] if field["required"]]
        
        # Validate all required fields are provided
        for field in required_fields:
            if not credentials.get(field["name"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{field['label']} is required",
                )
        
        # Test the connection with the provided credentials
        health = await integration_instance.test_connection(credentials)
        
        if not health.is_healthy:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid credentials: {health.error_message}",
            )
        
        # Save credentials as multiple secrets (one per field)
        secret_ids = []
        
        for field in setup_instructions["fields"]:
            field_name = field["name"]
            field_value = credentials.get(field_name)
            secret_name = f"{integration_type}_{field_name}"
            
            # Check if secret already exists for this field
            existing_secret = await secret_service.get_secret_by_name(workspace_id=workspace_id, name=secret_name)
        
            if existing_secret:
                # Update existing secret
                update_request = SecretUpdateRequest(
                    secret_value=field_value,
                    description=f"{field['label']} for {integration_type}"
                )
                logger.warning(f"Updating existing secret {secret_name} for {integration_type} in workspace {workspace_id}")
                success = await secret_service.update_secret(
                    secret_id=existing_secret.id,
                    request=update_request,
                    user_id=current_user.id,
                )
                if success:
                    secret_ids.append(existing_secret.id)
                    logger.info(f"Updated existing secret {secret_name} for {integration_type} in workspace {workspace_id}")
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to update secret {secret_name}"
                    )
            else:
                # Create new secret
                create_request = SecretCreateRequest(
                    workspace_id=workspace_id,
                    name=secret_name,
                    description=f"{field['label']} for {integration_type}",
                    secret_type=SecretType.CUSTOM,
                    secret_value=field_value,
                    tags=[integration_type, "credential", field_name, "auto-refresh"]
                )
                logger.warning(f"Creating new secret {secret_name} for {integration_type} in workspace {workspace_id}")
                secret_id = await secret_service.create_secret(
                    request=create_request,
                    user_id=current_user.id,
                )
                secret_ids.append(secret_id)
                logger.info(f"Created new secret {secret_name} for {integration_type} in workspace {workspace_id}")
        
        # Update integration status
        integration = await integration_service.get_workspace_integration(
            workspace_id, integration_type_enum
        )
        
        if not integration:
            # Create integration if it doesn't exist
            integration = await integration_service.create_integration(
                workspace_id=workspace_id,
                integration_type=integration_type_enum,
                auth_type=AuthType.API_KEY,
            )
        
        # Update integration to connected status
        # For now, we'll store the first secret ID in api_key_secret_id for backward compatibility
        # In the future, we might want to add a field to store all secret IDs
        primary_secret_id = secret_ids[0] if secret_ids else None
        success = await integration_service.update_integration(
            workspace_id=workspace_id,
            integration_type=integration_type_enum,
            status=IntegrationStatus.CONNECTED,
            api_key_secret_id=primary_secret_id,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update integration status"
            )
        
        return {
            "message": f"{integration_instance.display_name} connected successfully",
            "integration_type": integration_type,
            "status": "connected",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save credentials for {integration_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save credentials",
        )


@workspace_integrations_router.get("/{integration_type}/tools")
async def get_integration_tools(
    integration_type: str,
    workspace_id: str = Depends(get_workspace_id),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get available tools/actions for an integration with their current status."""
    try:
        # Validate integration type
        try:
            integration_type_enum = IntegrationType(integration_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid integration type: {integration_type}",
            )

        # Check if integration exists and is connected
        integration = await integration_service.get_workspace_integration(
            workspace_id, integration_type_enum
        )

        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found"
            )

        # Get available tools from templates
        from ..services.template_manager import TemplateManager
        template_manager = TemplateManager()
        await template_manager.initialize()
        
        # Get all templates that require this integration
        templates = await template_manager.get_all_templates(
            connected_integrations=[integration_type_enum]
        )
        
        # Get current actions for this workspace
        current_actions = await integration_service.action_service.list_actions(
            workspace_id=workspace_id
        )
        
        # Create a mapping of template IDs to current actions
        action_map = {}
        integration_name_lower = integration_type.lower().replace("_", " ")
        
        for action in current_actions:
            # Check if action is related to this integration by name or tags
            if (integration_name_lower in action.name.lower() or 
                any(integration_type.lower() in tag.lower() for tag in action.tags)):
                # Try to match by template pattern
                for template in templates:
                    template_name = template.id.replace("_", " ").title()
                    if template_name in action.name or template.id in str(action.tags):
                        action_map[template.id] = {
                            "action_id": action.id_str,
                            "enabled": True,
                            "name": action.name
                        }
                        break
        
        # Build response with all available tools
        tools = []
        for template in templates:
            tool_enabled = template.id in action_map
            tool_info = {
                "template_id": template.id,
                "name": template.name,
                "description": template.description,
                "category": template.category,
                "enabled": tool_enabled,
            }
            
            if tool_enabled:
                tool_info.update(action_map[template.id])
            
            tools.append(tool_info)
        
        return {
            "integration_type": integration_type,
            "integration_status": integration.status.value if integration.status else None,
            "available_tools": tools
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get integration tools: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get integration tools",
        )


@workspace_integrations_router.post("/{integration_type}/tools/{tool_id}/enable")
async def enable_integration_tool(
    integration_type: str,
    tool_id: str,
    workspace_id: str = Depends(get_workspace_id),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Enable a specific tool/action for an integration."""
    try:
        # Validate integration type
        try:
            integration_type_enum = IntegrationType(integration_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid integration type: {integration_type}",
            )

        # Check if integration exists and is connected
        integration = await integration_service.get_workspace_integration(
            workspace_id, integration_type_enum
        )

        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found"
            )
            
        if integration.status != IntegrationStatus.CONNECTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Integration must be connected to enable tools",
            )

        # Get the specific template
        from ..services.template_manager import TemplateManager
        template_manager = TemplateManager()
        await template_manager.initialize()
        
        template = await template_manager.get_template(tool_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool template {tool_id} not found",
            )
        
        # Check if template requires this integration
        if integration_type not in template.required_integrations:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tool {tool_id} is not compatible with {integration_type}",
            )
        
        # Create action from template
        from ..models.action import ActionCreateRequest, ActionType
        action_request = ActionCreateRequest(
            workspace_id=workspace_id,
            name=template.id.replace("_", " ").title(),
            type=ActionType.REST,
            description=template.description,
            default_config=template.default_config or {},
            config_schema=template.config_schema or {},
            tags=template.tags + [f"integration:{integration_type}", f"template:{template.id}"],
            version=getattr(template, 'version', '1.0.0'),
        )
        
        # Create the action
        logger.info(f"Creating action from template {template.name} for {integration_type}")
        action_id = await integration_service.action_service.create_action(
            request=action_request,
            user_id=current_user.id
        )
        
        return {
            "message": f"Tool {template.name} enabled successfully",
            "tool_id": tool_id,
            "action_id": str(action_id) if action_id else None,
            "enabled": True
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Failed to enable tool {tool_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable tool: {str(e)}",
        )


@workspace_integrations_router.post("/{integration_type}/tools/{tool_id}/disable")
async def disable_integration_tool(
    integration_type: str,
    tool_id: str,
    workspace_id: str = Depends(get_workspace_id),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Disable a specific tool/action for an integration."""
    try:
        # Validate integration type
        try:
            integration_type_enum = IntegrationType(integration_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid integration type: {integration_type}",
            )

        # Check if integration exists
        integration = await integration_service.get_workspace_integration(
            workspace_id, integration_type_enum
        )

        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found"
            )

        # Find the action to disable
        current_actions = await integration_service.action_service.list_actions(
            workspace_id=workspace_id
        )
        
        action_to_disable = None
        for action in current_actions:
            # Check if this action corresponds to the tool
            if (f"template:{tool_id}" in action.tags or 
                tool_id.replace("_", " ").title() in action.name):
                action_to_disable = action
                break
        
        if not action_to_disable:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool {tool_id} is not currently enabled",
            )
        
        # Delete the action
        success = await integration_service.action_service.delete_action(action_to_disable.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete action for tool {tool_id}",
            )
        
        return {
            "message": f"Tool {tool_id} disabled successfully",
            "tool_id": tool_id,
            "action_id": action_to_disable.id_str,
            "enabled": False
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disable tool {tool_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable tool: {str(e)}",
        )


@workspace_integrations_router.post("/{integration_type}/set-default-calendar")
async def set_default_calendar(
    integration_type: str,
    request: dict[str, Any],
    workspace_id: str = Depends(get_workspace_id),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Set the default calendar for Google Calendar integration."""
    try:
        # Validate integration type
        if integration_type != "google_calendar":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This endpoint is only for Google Calendar integration",
            )
        
        integration_type_enum = IntegrationType.GOOGLE_CALENDAR
        
        # Get the calendar_id from request
        calendar_id = request.get("calendar_id")
        if not calendar_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="calendar_id is required",
            )
        
        # Get the integration
        integration = await integration_service.get_workspace_integration(
            workspace_id, integration_type_enum
        )
        
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Google Calendar integration not found",
            )
        
        if integration.status != IntegrationStatus.CONNECTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google Calendar is not connected",
            )
        
        # Update the integration config with the new default calendar
        config = integration.config or {}
        config["default_calendar_id"] = calendar_id
        
        # Update the integration
        success = await integration_service.update_integration(
            workspace_id=workspace_id,
            integration_type=integration_type_enum,
            config=config,
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update default calendar",
            )
        
        return {
            "message": "Default calendar updated successfully",
            "calendar_id": calendar_id,
            "config": config,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting default calendar: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set default calendar: {str(e)}",
        )


@workspace_integrations_router.post("/{integration_type}/reset")
async def reset_integration_actions(
    integration_type: str,
    workspace_id: str = Depends(get_workspace_id),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Reset integration actions to defaults."""
    try:
        # Validate integration type
        try:
            integration_type_enum = IntegrationType(integration_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid integration type: {integration_type}",
            )

        # Check if integration exists
        integration = await integration_service.get_workspace_integration(
            workspace_id, integration_type_enum
        )

        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found"
            )

        # Reset actions
        result = await integration_service.reset_integration_actions(
            workspace_id=workspace_id, integration_type=integration_type_enum
        )

        return {
            "deleted_actions": result.get("deleted_actions", 0),
            "created_actions": result.get("created_actions", 0),
            "message": "Integration actions reset successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset integration {integration_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to reset integration"
        )


@workspace_integrations_router.post("/{integration_type}/test")
async def test_integration(
    integration_type: str,
    workspace_id: str = Depends(get_workspace_id),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Test an integration connection."""
    try:
        # Validate integration type
        try:
            integration_type_enum = IntegrationType(integration_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid integration type: {integration_type}",
            )
        
        # Get the integration
        integration = await integration_service.get_workspace_integration(
            workspace_id, integration_type_enum
        )
        
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Integration {integration_type} not found",
            )
        
        if integration.status != IntegrationStatus.CONNECTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Integration {integration_type} is not connected",
            )
        
        # Test the integration
        health = await integration_service.test_integration(
            workspace_id, integration_type_enum
        )
        
        return {
            "success": health.is_healthy,
            "message": health.error_message if not health.is_healthy else "Connection successful",
            "details": health.details
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test integration {integration_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test integration",
        )


@workspace_integrations_router.post("/{integration_type}/disconnect")
async def disconnect_integration(
    integration_type: str,
    workspace_id: str = Depends(get_workspace_id),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Disconnect an integration."""
    try:
        # Validate integration type
        try:
            integration_type_enum = IntegrationType(integration_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid integration type: {integration_type}",
            )

        # Check if integration exists
        integration = await integration_service.get_workspace_integration(
            workspace_id, integration_type_enum
        )

        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found"
            )

        # Disconnect
        await integration_service.disconnect_integration(
            workspace_id=workspace_id,
            integration_type=integration_type_enum,
            user_id=current_user.id,
        )

        return {"message": "Integration disconnected successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disconnect integration {integration_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disconnect integration",
        )


# Register workspace routes under the workspace router
workspace_router.include_router(
    workspace_integrations_router, prefix="/integrations", tags=["Integrations"]
)
