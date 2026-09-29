"""Prompts management API endpoints."""


from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from pymongo.errors import DuplicateKeyError

from ..auth.dependencies import get_current_user_jwt
from ..auth.models import User
from ..models.mcp_prompt import (
    MCPPromptCreateRequest,
    MCPPromptExecuteRequest,
    MCPPromptExecuteResponse,
    MCPPromptExtendRequest,
    MCPPromptListResponse,
    MCPPromptModel,
    MCPPromptResolvedResponse,
    MCPPromptResponse,
    MCPPromptTemplateListResponse,
    MCPPromptUpdateRequest,
    PromptVersionListResponse,
    PromptVersionModel,
)
from ..services.prompt_service import PromptService, PromptValidationError

router = APIRouter(prefix="/workspaces/{workspace_id}/prompts", tags=["Prompts"])


@router.get("", response_model=MCPPromptListResponse)
async def list_prompts(
    workspace_id: str,
    category: str | None = Query(None, description="Filter by category"),
    tags: str | None = Query(None, description="Filter by tags (comma-separated)"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    is_system: bool | None = Query(None, description="Filter by system status"),
    skip: int = Query(0, ge=0, description="Number of prompts to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of prompts to return"),
    user: User = Depends(get_current_user_jwt),
):
    """List prompts for a workspace."""
    try:
        # Parse tags if provided
        tags_list = None
        if tags:
            tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

        prompt_service = PromptService()
        prompts = await prompt_service.list_prompts(
            workspace_id=workspace_id,
            category=category,
            tags=tags_list,
            is_active=is_active,
            is_system=is_system,
            skip=skip,
            limit=limit
        )

        total = await prompt_service.count_prompts(
            workspace_id=workspace_id,
            category=category,
            tags=tags_list,
            is_active=is_active,
            is_system=is_system
        )

        return MCPPromptListResponse(
            prompts=prompts,
            total=total,
            category_filter=category,
            tags_filter=tags_list
        )

    except Exception as e:
        logger.error(f"Error listing prompts for workspace {workspace_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list prompts")


@router.post("", response_model=MCPPromptModel)
async def create_prompt(
    workspace_id: str,
    prompt_data: MCPPromptCreateRequest,
    user: User = Depends(get_current_user_jwt),
):
    """Create a new prompt."""
    try:
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Ensure workspace_id is set in the request data
        prompt_data.workspace_id = workspace_id

        prompt_service = PromptService()
        prompt = await prompt_service.create_prompt(
            workspace_id=workspace_id,
            prompt_data=prompt_data,
            user_id=user.id
        )

        logger.info(f"Created prompt '{prompt.name}' in workspace {workspace_id}")
        return prompt

    except PromptValidationError as e:
        logger.warning(f"Prompt validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except DuplicateKeyError as e:
        logger.warning(f"Duplicate prompt name: {e}")
        raise HTTPException(status_code=409, detail="A prompt with this name already exists in the workspace")
    except Exception as e:
        logger.error(f"Error creating prompt: {e}")
        raise HTTPException(status_code=500, detail="Failed to create prompt")


@router.get("/{prompt_id}", response_model=MCPPromptResponse)
async def get_prompt(
    workspace_id: str,
    prompt_id: str,
    user: User = Depends(get_current_user_jwt),
):
    """Get a specific prompt by ID."""
    try:
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        prompt_service = PromptService()
        prompt = await prompt_service.get_prompt_by_id(prompt_id)

        if not prompt:
            raise HTTPException(status_code=404, detail="Prompt not found")

        # Get usage stats
        usage_stats = await prompt_service.get_usage_stats(workspace_id)

        return MCPPromptResponse(
            prompt=prompt,
            usage_stats=usage_stats
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prompt '{prompt_id}': {e}")
        raise HTTPException(status_code=500, detail="Failed to get prompt")


@router.put("/{prompt_id}", response_model=MCPPromptModel)
async def update_prompt(
    workspace_id: str,
    prompt_id: str,
    updates: MCPPromptUpdateRequest,
    user: User = Depends(get_current_user_jwt),
):
    """Update a prompt."""
    try:
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        prompt_service = PromptService()
        prompt = await prompt_service.update_prompt_by_id(
            prompt_id=prompt_id,
            updates=updates,
            user_id=user.id
        )

        if not prompt:
            raise HTTPException(status_code=404, detail="Prompt not found")

        logger.info(f"Updated prompt {prompt_id} in workspace {workspace_id}")
        return prompt

    except PromptValidationError as e:
        logger.warning(f"Prompt validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating prompt {prompt_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update prompt")


@router.delete("/{prompt_id}", status_code=204)
async def delete_prompt(
    workspace_id: str,
    prompt_id: str,
    user: User = Depends(get_current_user_jwt),
):
    """Delete a prompt."""
    try:
        prompt_service = PromptService()
        deleted = await prompt_service.delete_prompt_by_id(prompt_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Prompt not found")

        logger.info(f"Deleted prompt {prompt_id} from workspace {workspace_id}")
        # Return nothing for 204 No Content response
        return

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting prompt {prompt_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete prompt")


@router.post("/{prompt_id}/execute", response_model=MCPPromptExecuteResponse)
async def execute_prompt(
    workspace_id: str,
    prompt_id: str,
    request: MCPPromptExecuteRequest,
    user: User = Depends(get_current_user_jwt),
):
    """Execute/test a prompt with provided arguments."""
    try:
        prompt_service = PromptService()
        result = await prompt_service.execute_prompt_by_id(
            prompt_id=prompt_id,
            arguments=request.arguments
        )

        logger.info(f"Executed prompt {prompt_id} in workspace {workspace_id}")
        return result

    except PromptValidationError as e:
        logger.warning(f"Prompt execution error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error executing prompt {prompt_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to execute prompt")


@router.get("/templates", response_model=MCPPromptTemplateListResponse)
async def list_templates(
    workspace_id: str,
    user: User = Depends(get_current_user_jwt),
):
    """List all templates in workspace."""
    try:
        prompt_service = PromptService()
        templates = await prompt_service.list_templates(workspace_id)

        return MCPPromptTemplateListResponse(
            templates=templates,
            total=len(templates)
        )

    except Exception as e:
        logger.error(f"Error listing templates for workspace {workspace_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list templates")


@router.post("/{prompt_id}/extend", response_model=MCPPromptModel)
async def create_prompt_from_template(
    workspace_id: str,
    prompt_id: str,
    extend_data: MCPPromptExtendRequest,
    user: User = Depends(get_current_user_jwt),
):
    """Create new prompt extending from template."""
    try:
        prompt_service = PromptService()
        prompt = await prompt_service.create_prompt_from_template(
            workspace_id=workspace_id,
            template_id=prompt_id,
            extend_data=extend_data,
            user_id=user.id
        )

        logger.info(f"Created prompt '{prompt.name}' extending template {prompt_id} in workspace {workspace_id}")
        return prompt

    except PromptValidationError as e:
        logger.warning(f"Template extension validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except DuplicateKeyError as e:
        logger.warning(f"Duplicate prompt name when extending template: {e}")
        raise HTTPException(status_code=409, detail="A prompt with this name already exists in the workspace")
    except Exception as e:
        logger.error(f"Error creating prompt from template {prompt_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create prompt from template")


@router.get("/{prompt_id}/resolved", response_model=MCPPromptResolvedResponse)
async def get_resolved_prompt(
    workspace_id: str,
    prompt_id: str,
    user: User = Depends(get_current_user_jwt),
):
    """Get fully resolved prompt with inheritance."""
    try:
        prompt_service = PromptService()
        resolved_prompt = await prompt_service.get_resolved_prompt(prompt_id)

        logger.info(f"Retrieved resolved prompt {prompt_id} in workspace {workspace_id}")
        return resolved_prompt

    except PromptValidationError as e:
        logger.warning(f"Error resolving prompt inheritance: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting resolved prompt {prompt_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get resolved prompt")


@router.get("/templates/system")
async def get_system_templates(
    user: User = Depends(get_current_user_jwt),
):
    """Get available system prompt templates."""
    try:
        # Return metadata about system prompts that can be used as templates
        templates = [
            {
                "name": "code_review",
                "category": "development",
                "description": "Review code for quality, security, and best practices",
                "tags": ["code", "review", "quality", "security"],
                "arguments": ["language", "code"]
            },
            {
                "name": "api_documentation",
                "category": "documentation",
                "description": "Generate comprehensive API documentation from code",
                "tags": ["api", "documentation", "technical-writing"],
                "arguments": ["api_type", "code"]
            },
            {
                "name": "test_generation",
                "category": "testing",
                "description": "Generate unit tests for functions and classes",
                "tags": ["testing", "unit-tests", "qa", "automation"],
                "arguments": ["language", "code", "test_framework"]
            },
            {
                "name": "bug_analysis",
                "category": "debugging",
                "description": "Analyze bugs and suggest fixes",
                "tags": ["debugging", "troubleshooting", "error-analysis"],
                "arguments": ["error", "code", "context"]
            },
            {
                "name": "data_query",
                "category": "data",
                "description": "Convert natural language to database queries",
                "tags": ["database", "sql", "query", "data-analysis"],
                "arguments": ["natural_query", "schema", "query_type"]
            },
            {
                "name": "content_summary",
                "category": "analysis",
                "description": "Summarize documents and content from knowledge base",
                "tags": ["summary", "analysis", "content", "knowledge-base"],
                "arguments": ["content", "summary_type"]
            },
            {
                "name": "translation",
                "category": "localization",
                "description": "Translate content between languages",
                "tags": ["translation", "localization", "language"],
                "arguments": ["text", "source_language", "target_language"]
            },
            {
                "name": "refactoring",
                "category": "development",
                "description": "Suggest code refactoring improvements",
                "tags": ["refactoring", "code-quality", "architecture", "improvement"],
                "arguments": ["code", "language", "focus_areas"]
            }
        ]

        return {"templates": templates}

    except Exception as e:
        logger.error(f"Error getting system templates: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system templates")


@router.post("/seed-system-prompts")
async def seed_system_prompts(
    workspace_id: str,
    user: User = Depends(get_current_user_jwt),
):
    """Create default system prompts for the workspace."""
    try:
        prompt_service = PromptService()
        created_prompts = await prompt_service.create_default_system_prompts(workspace_id)

        logger.info(f"Created {len(created_prompts)} system prompts for workspace {workspace_id}")
        return {
            "message": f"Created {len(created_prompts)} system prompts",
            "prompts": [{"name": p.name, "category": p.category} for p in created_prompts]
        }

    except Exception as e:
        logger.error(f"Error seeding system prompts: {e}")
        raise HTTPException(status_code=500, detail="Failed to seed system prompts")


@router.get("/stats/usage")
async def get_prompt_usage_stats(
    workspace_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    user: User = Depends(get_current_user_jwt),
):
    """Get prompt usage statistics for the workspace."""
    try:
        prompt_service = PromptService()
        stats = await prompt_service.get_usage_stats(workspace_id, days)

        return {
            "workspace_id": workspace_id,
            "period_days": days,
            "stats": stats
        }

    except Exception as e:
        logger.error(f"Error getting prompt usage stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get usage stats")


# Version History Endpoints

@router.get(
    "/{prompt_id}/versions",
    response_model=PromptVersionListResponse,
    summary="Get prompt version history",
    description="Retrieve all versions of a prompt"
)
async def get_prompt_versions(
    workspace_id: str,
    prompt_id: str,
    user: User = Depends(get_current_user_jwt),
):
    """Get all versions of a prompt."""
    try:
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        prompt_service = PromptService()

        # Verify prompt exists and belongs to workspace
        prompt = await prompt_service.get_prompt_by_id(prompt_id)
        if not prompt:
            raise HTTPException(status_code=404, detail="Prompt not found")

        if prompt.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Prompt not found in this workspace")

        # Get versions
        versions = await prompt_service.get_prompt_versions(prompt_id)

        return PromptVersionListResponse(
            versions=versions,
            total=len(versions),
            current_version=prompt.version
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prompt versions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get prompt versions")


@router.get(
    "/{prompt_id}/versions/{version}",
    response_model=PromptVersionModel,
    summary="Get specific prompt version",
    description="Retrieve a specific version of a prompt"
)
async def get_prompt_version(
    workspace_id: str,
    prompt_id: str,
    version: int,
    user: User = Depends(get_current_user_jwt),
):
    """Get a specific version of a prompt."""
    try:
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        prompt_service = PromptService()

        # Verify prompt exists and belongs to workspace
        prompt = await prompt_service.get_prompt_by_id(prompt_id)
        if not prompt:
            raise HTTPException(status_code=404, detail="Prompt not found")

        if prompt.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Prompt not found in this workspace")

        # Get specific version
        version_data = await prompt_service.get_prompt_version(prompt_id, version)
        if not version_data:
            raise HTTPException(status_code=404, detail=f"Version {version} not found")

        return version_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prompt version: {e}")
        raise HTTPException(status_code=500, detail="Failed to get prompt version")


@router.post(
    "/{prompt_id}/restore/{version}",
    response_model=MCPPromptModel,
    summary="Restore prompt to previous version",
    description="Restore a prompt to a previous version, creating a new version in the process"
)
async def restore_prompt_version(
    workspace_id: str,
    prompt_id: str,
    version: int,
    user: User = Depends(get_current_user_jwt),
):
    """Restore a prompt to a previous version."""
    try:
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        prompt_service = PromptService()

        # Verify prompt exists and belongs to workspace
        prompt = await prompt_service.get_prompt_by_id(prompt_id)
        if not prompt:
            raise HTTPException(status_code=404, detail="Prompt not found")

        if prompt.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Prompt not found in this workspace")

        # Restore to the specified version
        restored_prompt = await prompt_service.restore_prompt_version(
            prompt_id,
            version,
            user.id
        )

        return restored_prompt

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring prompt version: {e}")
        raise HTTPException(status_code=500, detail="Failed to restore prompt version")
