"""Service for managing action templates and their integration dependencies."""

import logging
from typing import Optional

from ..database.connection import get_database_connection
from ..integrations.base_classes import ActionTemplate, IntegrationCapability
from ..models.action import ActionCreateRequest, ActionModel, ActionType
from ..models.action_template import ActionTemplateModel
from ..models.integration import IntegrationType

logger = logging.getLogger(__name__)


class ActionTemplateService:
    """Service for managing action templates."""
    
    def __init__(self):
        self.collection_name = "action_templates"
        # Cache for frequently accessed templates
        self._template_cache: dict[str, ActionTemplateModel] = {}
        self._cache_loaded = False
    
    def _get_collection(self):
        """Get the action templates collection."""
        db_connection = get_database_connection()
        return db_connection.database[self.collection_name]
    
    async def _load_cache(self):
        """Load templates from database into cache."""
        if self._cache_loaded:
            return
        
        collection = self._get_collection()
        cursor = collection.find({"is_active": True})
        
        async for doc in cursor:
            template = ActionTemplateModel(**doc)
            self._template_cache[template.template_id] = template
        
        self._cache_loaded = True
        logger.info(f"Loaded {len(self._template_cache)} templates into cache")
    
    def _convert_to_action_template(self, model: ActionTemplateModel) -> ActionTemplate:
        """Convert database model to ActionTemplate for backward compatibility."""
        return ActionTemplate(
            id=model.template_id,
            name=model.name,
            description=model.description,
            category=model.category,
            capability=IntegrationCapability(model.capability) if model.capability else IntegrationCapability.CREATE_EVENT,
            required_integrations=[
                IntegrationType(i) for i in model.required_integrations
            ],
            optional_integrations=[
                IntegrationType(i) for i in model.optional_integrations
            ],
            config_schema=model.config_schema,
            default_config=model.default_config,
            integration_config=model.integration_config
        )
    
    async def get_all_templates(self) -> list[ActionTemplate]:
        """Get all available action templates."""
        await self._load_cache()
        return [self._convert_to_action_template(t) for t in self._template_cache.values()]
    
    async def get_template_by_id(self, template_id: str) -> Optional[ActionTemplate]:
        """Get a specific action template by ID."""
        await self._load_cache()
        model = self._template_cache.get(template_id)
        return self._convert_to_action_template(model) if model else None
    
    async def get_templates_by_category(self, category: str) -> list[ActionTemplate]:
        """Get action templates by category."""
        await self._load_cache()
        templates = [t for t in self._template_cache.values() if t.category == category]
        return [self._convert_to_action_template(t) for t in templates]
    
    async def get_templates_by_capability(
        self,
        capability: IntegrationCapability
    ) -> list[ActionTemplate]:
        """Get action templates by capability."""
        await self._load_cache()
        templates = [t for t in self._template_cache.values() if t.capability == capability.value]
        return [self._convert_to_action_template(t) for t in templates]
    
    async def get_templates_for_integration(
        self,
        integration_type: IntegrationType
    ) -> list[ActionTemplate]:
        """Get all templates that can use a specific integration."""
        await self._load_cache()
        templates = []
        integration_str = integration_type.value
        for template in self._template_cache.values():
            if (integration_str in template.required_integrations or 
                integration_str in template.optional_integrations):
                templates.append(self._convert_to_action_template(template))
        return templates
    
    async def get_available_templates(
        self,
        connected_integrations: list[IntegrationType]
    ) -> list[ActionTemplate]:
        """Get templates that can be used with current integrations."""
        await self._load_cache()
        available = []
        connected_strs = [i.value for i in connected_integrations]
        for template in self._template_cache.values():
            # Check if all required integrations are connected
            if all(req in connected_strs for req in template.required_integrations):
                available.append(self._convert_to_action_template(template))
        return available
    
    async def check_template_dependencies(
        self,
        template_id: str,
        connected_integrations: list[IntegrationType]
    ) -> dict:
        """Check if a template's dependencies are met."""
        await self._load_cache()
        template = self._template_cache.get(template_id)
        if not template:
            return {
                "template_found": False,
                "error": "Template not found"
            }
        
        connected_strs = [i.value for i in connected_integrations]
        required_types = [IntegrationType(i) for i in template.required_integrations]
        optional_types = [IntegrationType(i) for i in template.optional_integrations]
        
        missing_required = [r for r in required_types if r.value not in connected_strs]
        missing_optional = [o for o in optional_types if o.value not in connected_strs]
        
        return {
            "template_found": True,
            "is_available": len(missing_required) == 0,
            "required_integrations": {
                "needed": required_types,
                "connected": [i for i in required_types if i.value in connected_strs],
                "missing": missing_required
            },
            "optional_integrations": {
                "available": optional_types,
                "connected": [i for i in optional_types if i.value in connected_strs],
                "missing": missing_optional
            }
        }
    
    async def create_action_from_template(
        self,
        workspace_id: str,
        user_id: str,
        template_id: str,
        name: str,
        config_overrides: Optional[dict] = None
    ) -> ActionModel:
        """Create an action from a template."""
        await self._load_cache()
        template = self._template_cache.get(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        # Merge default config with overrides
        config = template.default_config.copy()
        if config_overrides:
            config.update(config_overrides)
        
        # Create action request
        action_request = ActionCreateRequest(
            workspace_id=workspace_id,
            name=name,
            type=ActionType.REST,  # Most templates use REST
            description=f"{template.description} (from template: {template.name})",
            tags=["template", template.category, template_id],
            default_config=config,
            config_schema={
                "template_id": template_id,
                "capability": template.capability,
                "integration_config": template.integration_config
            }
        )
        
        # Create action through action service
        from .action_service import ActionService
        action_service = ActionService()
        action_id = await action_service.create_action(action_request, user_id)
        action = await action_service.get_action_by_id(action_id)
        
        logger.info(f"Created action {name} from template {template_id}")
        return action
    
    async def add_custom_template(
        self,
        template: ActionTemplate,
        workspace_id: Optional[str] = None
    ) -> str:
        """Add a custom action template."""
        # For workspace-specific templates, prefix the ID
        template_id = f"{workspace_id}_{template.id}" if workspace_id else template.id
        
        # Convert to database model
        model = ActionTemplateModel(
            template_id=template_id,
            name=template.name,
            description=template.description,
            category=template.category,
            capability=template.capability.value,
            required_integrations=[i.value for i in template.required_integrations],
            optional_integrations=[i.value for i in template.optional_integrations],
            config_schema=template.config_schema,
            default_config=template.default_config,
            integration_config=template.integration_config,
            tags=["custom", "workspace" if workspace_id else "global"]
        )
        
        # Save to database
        collection = self._get_collection()
        await collection.update_one(
            {"template_id": template_id},
            {"$set": model.model_dump_for_db()},
            upsert=True
        )
        
        # Update cache
        self._template_cache[template_id] = model
        
        logger.info(f"Added custom template {template_id}")
        return template_id
    
    async def refresh_cache(self):
        """Force refresh the template cache from database."""
        self._template_cache.clear()
        self._cache_loaded = False
        await self._load_cache()