#!/usr/bin/env python3
"""Import action templates from JSON files to MongoDB."""

import json
import sys
from pathlib import Path
from datetime import datetime, UTC
from typing import Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "server" / "src"))

from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
from protobox.admin.config import settings
from protobox.admin.models.action_template import ActionTemplateModel


class ActionTemplateImporter:
    """Import action templates from JSON files to database."""
    
    def __init__(self):
        self.client = AsyncIOMotorClient(settings.mongodb_url)
        # Extract database name from URL or use default
        database_name = settings.mongodb_url.split("/")[-1].split("?")[0] if "/" in settings.mongodb_url else "mcp_server"
        self.db = self.client[database_name]
        self.collection = self.db.action_templates
        
    async def clear_templates(self):
        """Clear existing templates from database."""
        result = await self.collection.delete_many({})
        print(f"Cleared {result.deleted_count} existing templates")
        
    async def import_file(self, file_path: Path) -> int:
        """Import templates from a single JSON file."""
        with open(file_path) as f:
            data = json.load(f)
            
        templates = data.get("templates", data if isinstance(data, list) else [])
        imported = 0
        
        for template_data in templates:
            # Convert old format to new model format
            template = ActionTemplateModel(
                template_id=template_data.get("id", template_data.get("template_id")),
                name=template_data["name"],
                description=template_data["description"],
                category=template_data["category"],
                capability=template_data.get("capability", template_data.get("category", "general")),
                required_integrations=self._extract_required_integrations(template_data),
                optional_integrations=template_data.get("optional_integrations", []),
                config_schema=template_data.get("config_schema", {}),
                default_config=template_data.get("default_config", {}),
                integration_config=template_data.get("integration_config", {}),
                tags=template_data.get("tags", []),
                is_active=template_data.get("status") == "active" if "status" in template_data else True,
                version=template_data.get("version", "1.0.0")
            )
            
            # Upsert to database
            await self.collection.update_one(
                {"template_id": template.template_id},
                {"$set": template.model_dump_for_db()},
                upsert=True
            )
            imported += 1
            
        print(f"Imported {imported} templates from {file_path.name}")
        return imported
    
    def _extract_required_integrations(self, template_data: dict) -> list[str]:
        """Extract required integrations from old format."""
        required = []
        
        # Check for integrations array (old format)
        if "integrations" in template_data:
            for integration in template_data["integrations"]:
                if integration.get("required", False):
                    required.append(integration["integration_type"])
        
        # Check for required_integrations (new format)
        if "required_integrations" in template_data:
            required.extend(template_data["required_integrations"])
            
        return list(set(required))  # Remove duplicates
    
    async def import_all(self):
        """Import all template files from the templates directory."""
        templates_dir = Path(__file__).parent.parent / "server" / "data" / "action_templates"
        
        # Also check for the old single file
        old_file = Path(__file__).parent.parent / "server" / "data" / "action_templates.json"
        
        total = 0
        
        # Import from old file if it exists
        if old_file.exists():
            print(f"Importing from legacy file: {old_file.name}")
            total += await self.import_file(old_file)
        
        # Import from category files
        if templates_dir.exists():
            for file_path in sorted(templates_dir.glob("*.json")):
                total += await self.import_file(file_path)
        
        print(f"\nTotal templates imported: {total}")
        
        # Create indexes
        await self.create_indexes()
        
    async def create_indexes(self):
        """Create database indexes for efficient queries."""
        await self.collection.create_index("template_id", unique=True)
        await self.collection.create_index("category")
        await self.collection.create_index("required_integrations")
        await self.collection.create_index("is_active")
        await self.collection.create_index([("category", 1), ("is_active", 1)])
        print("Created database indexes")
        
    async def close(self):
        """Close database connection."""
        self.client.close()


async def main():
    """Main import function."""
    importer = ActionTemplateImporter()
    
    try:
        # Option to clear existing templates
        if "--clear" in sys.argv:
            await importer.clear_templates()
        
        # Import all templates
        await importer.import_all()
        
    finally:
        await importer.close()


if __name__ == "__main__":
    asyncio.run(main())