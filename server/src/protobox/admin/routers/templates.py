"""API endpoints for action template management.

ARCHITECTURAL NOTE: Templates are intentionally GLOBAL resources, not workspace-scoped.
This is by design because:
1. Templates are reusable across all workspaces
2. They provide standard action patterns for common integrations  
3. They serve as a catalog of available integrations
4. Workspace isolation would prevent sharing of common templates

The workspace_id parameter in some endpoints is used only for checking template
availability/compatibility within a specific workspace context, but the templates
themselves remain global resources accessible to all users.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth.dependencies import get_current_user
from ..models.action_template import ActionTemplateModel, TemplateCategory, TemplateStatus
from ..models.integration import IntegrationType
from ..models.user import UserModel
from ..services.template_manager import get_template_manager

logger = logging.getLogger(__name__)

# NOTE: Templates router is intentionally NOT workspace-scoped (/templates, not /workspaces/{id}/templates)
# Templates are global resources shared across all workspaces for reusability
router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("/", response_model=list[ActionTemplateModel])
async def list_templates(
    category: Optional[TemplateCategory] = Query(None, description="Filter by category"),
    status: Optional[TemplateStatus] = Query(None, description="Filter by status"),
    integration: Optional[IntegrationType] = Query(None, description="Filter by integration"),
    available_only: bool = Query(False, description="Only show available templates"),
    workspace_id: Optional[str] = Query(None, description="Workspace ID for availability check"),
    current_user: UserModel = Depends(get_current_user)
) -> list[ActionTemplateModel]:
    """
    List all action templates with optional filtering.
    
    Args:
        category: Filter by template category
        status: Filter by template status
        integration: Filter by integration type
        available_only: Only show templates that can be used now
        workspace_id: Check availability for specific workspace
    """
    template_manager = get_template_manager()
    
    # If checking availability, get connected integrations
    connected_integrations = None
    if available_only and workspace_id:
        # TODO: Get connected integrations for workspace
        # For now, return empty list
        connected_integrations = []
    
    # Get templates
    templates = await template_manager.get_all_templates(
        category=category,
        status=status,
        connected_integrations=connected_integrations if available_only else None
    )
    
    # Filter by specific integration if requested
    if integration:
        filtered = []
        for template in templates:
            for req in template.integrations:
                if req.integration_type == integration:
                    filtered.append(template)
                    break
        templates = filtered
    
    return templates


@router.get("/statistics")
async def get_template_statistics(
    current_user: UserModel = Depends(get_current_user)
) -> dict:
    """Get statistics about available templates."""
    template_manager = get_template_manager()
    return await template_manager.get_template_statistics()


@router.get("/{template_id}", response_model=ActionTemplateModel)
async def get_template(
    template_id: str,
    current_user: UserModel = Depends(get_current_user)
) -> ActionTemplateModel:
    """Get a specific template by ID."""
    template_manager = get_template_manager()
    
    template = await template_manager.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return template


@router.get("/{template_id}/requirements")
async def check_template_requirements(
    template_id: str,
    workspace_id: str = Query(..., description="Workspace ID"),
    current_user: UserModel = Depends(get_current_user)
) -> dict:
    """
    Check if a template's requirements are met for a workspace.
    
    Returns:
        Dictionary with availability status and missing integrations
    """
    template_manager = get_template_manager()
    
    template = await template_manager.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # TODO: Get connected integrations for workspace
    connected_integrations = []
    
    missing = template.get_missing_integrations(connected_integrations)
    
    return {
        "template_id": template_id,
        "template_name": template.name,
        "is_available": len(missing) == 0,
        "required_integrations": template.get_required_integrations(),
        "optional_integrations": template.get_optional_integrations(),
        "missing_integrations": missing,
        "connected_integrations": connected_integrations
    }


@router.post("/{template_id}/create-action")
async def create_action_from_template(
    template_id: str,
    workspace_id: str = Query(..., description="Workspace ID"),
    name: Optional[str] = Query(None, description="Custom name for the action"),
    config: Optional[dict] = None,
    current_user: UserModel = Depends(get_current_user)
) -> dict:
    """
    Create an action from a template.
    
    Args:
        template_id: Template to use
        workspace_id: Workspace to create action in
        name: Custom name for the action (uses template name if not provided)
        config: Configuration overrides
    """
    template_manager = get_template_manager()
    
    template = await template_manager.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # TODO: Check if template requirements are met
    # TODO: Create action using ActionService
    
    action_config = template.to_action_config(config)
    if name:
        action_config["name"] = name
    
    return {
        "message": "Action creation from template not yet implemented",
        "template_id": template_id,
        "action_config": action_config
    }


@router.get("/by-integration/{integration_type}")
async def get_templates_by_integration(
    integration_type: IntegrationType,
    required_only: bool = Query(False, description="Only show templates that require this integration"),
    current_user: UserModel = Depends(get_current_user)
) -> list[ActionTemplateModel]:
    """Get all templates that use a specific integration."""
    template_manager = get_template_manager()
    
    templates = await template_manager.get_templates_by_integration(
        integration_type,
        required_only=required_only
    )
    
    return templates


@router.get("/missing/by-workspace/{workspace_id}")
async def get_missing_templates(
    workspace_id: str,
    current_user: UserModel = Depends(get_current_user)
) -> list[dict]:
    """
    Get templates that are missing integrations for a workspace.
    
    Returns templates sorted by how close they are to being usable
    (fewer missing integrations = closer to usable).
    """
    template_manager = get_template_manager()
    
    # TODO: Get connected integrations for workspace
    connected_integrations = []
    
    missing_templates = await template_manager.get_missing_templates(connected_integrations)
    
    result = []
    for template, missing in missing_templates:
        result.append({
            "template": template,
            "missing_integrations": missing,
            "missing_count": len(missing),
            "availability_percentage": (
                (len(template.get_required_integrations()) - len(missing)) / 
                len(template.get_required_integrations()) * 100
                if template.get_required_integrations() else 100
            )
        })
    
    return result


@router.post("/custom")
async def create_custom_template(
    template: ActionTemplateModel,
    workspace_id: str = Query(..., description="Workspace ID"),
    current_user: UserModel = Depends(get_current_user)
) -> dict:
    """Create a custom template for a workspace."""
    template_manager = get_template_manager()
    
    # Ensure template has a unique ID
    if not template.id:
        template.id = f"custom_{workspace_id}_{template.name.lower().replace(' ', '_')}"
    
    template_id = await template_manager.save_custom_template(template, workspace_id)
    
    return {
        "message": "Custom template created",
        "template_id": template_id
    }


@router.delete("/custom/{template_id}")
async def delete_custom_template(
    template_id: str,
    workspace_id: str = Query(..., description="Workspace ID"),
    current_user: UserModel = Depends(get_current_user)
) -> dict:
    """Delete a custom template."""
    template_manager = get_template_manager()
    
    success = await template_manager.delete_custom_template(template_id, workspace_id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Template not found or not owned by workspace"
        )
    
    return {
        "message": "Custom template deleted",
        "template_id": template_id
    }