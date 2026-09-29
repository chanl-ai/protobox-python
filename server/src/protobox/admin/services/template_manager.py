"""Template manager service for centralized action template management."""

import json
import glob
from pathlib import Path
from typing import Optional

from loguru import logger

from ..database.connection import get_database_connection
from ..models.action_template import ActionTemplateModel, TemplateCategory, TemplateStatus
from ..models.integration import IntegrationType


class TemplateManager:
    """Manages action templates from database and JSON sources."""
    
    def __init__(self):
        self.collection_name = "action_templates"
        self._templates_cache: dict[str, ActionTemplateModel] = {}
        self._initialized = False
    
    def _get_collection(self):
        """Get the action templates collection."""
        db_connection = get_database_connection()
        return db_connection.database[self.collection_name]
    
    async def initialize(self) -> None:
        """Initialize template manager and load templates."""
        if self._initialized:
            return
        
        # First, load templates from JSON file
        await self._load_json_templates()
        
        # Then, load any custom templates from database
        await self._load_database_templates()
        
        self._initialized = True
        logger.info(f"Initialized template manager with {len(self._templates_cache)} templates")
    
    async def _load_json_templates(self) -> None:
        """Load templates from JSON file."""
        template_dir = Path(__file__).parent.parent.parent.parent.parent / "data" / "action_templates"
        if not template_dir.exists():
            raise FileNotFoundError(f"Action templates directory not found at {template_dir.as_posix()}")
        template_files = glob.glob(str(template_dir / "*.json"))
        logger.info(f"Loading {len(template_files)} action template files from {template_dir.as_posix()}")
        for template_file in template_files:
            await self._load_json_template(Path(template_file))
    
    async def _load_json_template(self, json_path: Path) -> None:
        if not json_path.exists():
            logger.warning(f"Action templates JSON not found at {json_path}")
            return
        
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
            
            for template_data in data.get("templates", []):
                try:
                    # Map JSON fields to model fields
                    if "id" in template_data:
                        template_data["template_id"] = template_data["id"]
                    
                    # Extract capability from first integration if not present
                    if "capability" not in template_data and "integrations" in template_data:
                        # Use a default capability based on category
                        category = template_data.get("category", "")
                        if "scheduling" in category:
                            template_data["capability"] = "CREATE_EVENT"
                        elif "communication" in category:
                            template_data["capability"] = "SEND_MESSAGE"
                        elif "file" in category or "storage" in category:
                            template_data["capability"] = "UPLOAD_FILE"
                        else:
                            template_data["capability"] = "EXECUTE_ACTION"
                    
                    # Convert integration requirements to simple lists
                    if "integrations" in template_data:
                        required_integrations = []
                        optional_integrations = []
                        for integration in template_data["integrations"]:
                            if integration.get("required", False):
                                required_integrations.append(integration["integration_type"])
                            else:
                                optional_integrations.append(integration["integration_type"])
                        template_data["required_integrations"] = required_integrations
                        template_data["optional_integrations"] = optional_integrations
                    
                    # Clean up fields that don't exist in model
                    template_data.pop("integrations", None)
                    template_data.pop("action_type", None)
                    template_data.pop("examples", None)
                    template_data.pop("popularity_score", None)
                    
                    # Convert string enums to proper enum values  
                    if "category" in template_data:
                        try:
                            template_data["category"] = TemplateCategory(template_data["category"])
                        except ValueError:
                            # If category doesn't match enum, use CUSTOM
                            template_data["category"] = TemplateCategory.CUSTOM
                    if "status" in template_data:
                        try:
                            template_data["status"] = TemplateStatus(template_data["status"])
                        except ValueError:
                            template_data["status"] = TemplateStatus.ACTIVE
                    
                    template = ActionTemplateModel(**template_data)
                    self._templates_cache[template.template_id] = template
                    
                except Exception as e:
                    logger.error(f"Failed to load template {template_data.get('id')}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to load templates from JSON: {e}")
    
    async def _load_database_templates(self) -> None:
        """Load custom templates from database."""
        try:
            collection = self._get_collection()
            
            # Find all active custom templates
            cursor = collection.find({"status": {"$ne": "deleted"}})
            
            async for doc in cursor:
                try:
                    # Remove MongoDB fields
                    doc.pop("_id", None)
                    
                    # Convert to model
                    template = ActionTemplateModel(**doc)
                    
                    # Custom templates override JSON templates
                    self._templates_cache[template.id] = template
                    
                except Exception as e:
                    logger.error(f"Failed to load template from database: {e}")
        
        except Exception as e:
            logger.error(f"Failed to load database templates: {e}")
    
    async def get_all_templates(
        self,
        category: Optional[TemplateCategory] = None,
        status: Optional[TemplateStatus] = None,
        connected_integrations: Optional[list[IntegrationType]] = None
    ) -> list[ActionTemplateModel]:
        """
        Get all templates with optional filtering.
        
        Args:
            category: Filter by category
            status: Filter by status
            connected_integrations: Filter to only available templates
        """
        if not self._initialized:
            await self.initialize()
        
        templates = list(self._templates_cache.values())
        
        # Apply filters
        if category:
            templates = [t for t in templates if t.category == category]
        
        if status:
            templates = [t for t in templates if t.status == status]
        else:
            # By default, exclude deprecated and coming_soon
            templates = [
                t for t in templates 
                if t.status in [TemplateStatus.ACTIVE, TemplateStatus.BETA]
            ]
        
        if connected_integrations is not None:
            templates = [
                t for t in templates 
                if t.is_available(connected_integrations)
            ]
        
        # Sort by popularity
        templates.sort(key=lambda x: x.popularity_score, reverse=True)
        
        return templates
    
    async def get_template(self, template_id: str) -> Optional[ActionTemplateModel]:
        """Get a specific template by ID."""
        if not self._initialized:
            await self.initialize()
        
        return self._templates_cache.get(template_id)
    
    async def get_templates_by_integration(
        self,
        integration_type: IntegrationType,
        required_only: bool = False
    ) -> list[ActionTemplateModel]:
        """Get all templates that use a specific integration."""
        if not self._initialized:
            await self.initialize()
        
        templates = []
        for template in self._templates_cache.values():
            for req in template.integrations:
                if req.integration_type == integration_type:
                    if not required_only or req.required:
                        templates.append(template)
                        break
        
        return templates
    
    async def get_available_templates(
        self,
        connected_integrations: list[IntegrationType]
    ) -> list[ActionTemplateModel]:
        """Get templates that can be used with current integrations."""
        return await self.get_all_templates(connected_integrations=connected_integrations)
    
    async def get_missing_templates(
        self,
        connected_integrations: list[IntegrationType]
    ) -> list[tuple[ActionTemplateModel, list[IntegrationType]]]:
        """
        Get templates that are missing integrations.
        
        Returns:
            List of (template, missing_integrations) tuples
        """
        if not self._initialized:
            await self.initialize()
        
        missing_templates = []
        
        for template in self._templates_cache.values():
            if template.status not in [TemplateStatus.ACTIVE, TemplateStatus.BETA]:
                continue
            
            missing = template.get_missing_integrations(connected_integrations)
            if missing:
                missing_templates.append((template, missing))
        
        # Sort by number of missing integrations (fewer missing = closer to usable)
        missing_templates.sort(key=lambda x: len(x[1]))
        
        return missing_templates
    
    async def save_custom_template(
        self,
        template: ActionTemplateModel,
        workspace_id: str
    ) -> str:
        """
        Save a custom template to the database.
        
        Args:
            template: The template to save
            workspace_id: Workspace that owns this template
            
        Returns:
            The template ID
        """
        collection = self._get_collection()
        
        doc = template.dict()
        doc["workspace_id"] = workspace_id
        doc["is_custom"] = True
        
        # Convert enums to strings for storage
        doc["category"] = doc["category"].value if isinstance(doc["category"], TemplateCategory) else doc["category"]
        doc["status"] = doc["status"].value if isinstance(doc["status"], TemplateStatus) else doc["status"]
        
        for integration in doc.get("integrations", []):
            if isinstance(integration["integration_type"], IntegrationType):
                integration["integration_type"] = integration["integration_type"].value
        
        # Upsert the template
        result = await collection.replace_one(
            {"id": template.id, "workspace_id": workspace_id},
            doc,
            upsert=True
        )
        
        # Update cache
        self._templates_cache[template.id] = template
        
        logger.info(f"Saved custom template {template.id} for workspace {workspace_id}")
        return template.id
    
    async def delete_custom_template(
        self,
        template_id: str,
        workspace_id: str
    ) -> bool:
        """
        Delete a custom template.
        
        Args:
            template_id: Template to delete
            workspace_id: Workspace that owns the template
            
        Returns:
            True if deleted, False if not found or not owned by workspace
        """
        collection = self._get_collection()
        
        result = await collection.update_one(
            {"id": template_id, "workspace_id": workspace_id},
            {"$set": {"status": "deleted"}}
        )
        
        if result.modified_count > 0:
            # Remove from cache
            self._templates_cache.pop(template_id, None)
            logger.info(f"Deleted custom template {template_id}")
            return True
        
        return False
    
    async def get_template_statistics(self) -> dict:
        """Get statistics about templates."""
        if not self._initialized:
            await self.initialize()
        
        templates = list(self._templates_cache.values())
        
        stats = {
            "total": len(templates),
            "by_category": {},
            "by_status": {},
            "by_integration": {},
            "no_integration_required": 0,
            "avg_popularity": 0
        }
        
        # Count by category
        for category in TemplateCategory:
            count = len([t for t in templates if t.category == category])
            if count > 0:
                stats["by_category"][category.value] = count
        
        # Count by status
        for status in TemplateStatus:
            count = len([t for t in templates if t.status == status])
            if count > 0:
                stats["by_status"][status.value] = count
        
        # Count by integration
        integration_counts = {}
        for template in templates:
            if not template.integrations:
                stats["no_integration_required"] += 1
            
            for req in template.integrations:
                integration = req.integration_type.value
                if integration not in integration_counts:
                    integration_counts[integration] = 0
                integration_counts[integration] += 1
        
        stats["by_integration"] = integration_counts
        
        # Calculate average popularity
        if templates:
            total_popularity = sum(t.popularity_score for t in templates)
            stats["avg_popularity"] = total_popularity / len(templates)
        
        return stats


# Global template manager instance
_template_manager: Optional[TemplateManager] = None


def get_template_manager() -> TemplateManager:
    """Get the global template manager instance."""
    global _template_manager
    if _template_manager is None:
        _template_manager = TemplateManager()
    return _template_manager