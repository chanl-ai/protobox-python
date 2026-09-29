"""Prompt repository for MongoDB operations."""

from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.errors import DuplicateKeyError

from ...models.mcp_prompt import MCPPromptModel
from ..connection import get_database_connection


class PromptRepository:
    """Repository for prompt database operations."""

    def __init__(self):
        """Initialize the repository."""
        self.collection_name = "mcp_prompts"

    def get_collection(self) -> AsyncIOMotorCollection:
        """Get the prompts collection."""
        db_connection = get_database_connection()
        return db_connection.database[self.collection_name]

    async def create_prompt(self, prompt: MCPPromptModel) -> str:
        """Create a new prompt in the database.

        Args:
            prompt: The prompt model to create

        Returns:
            The ID of the created prompt

        Raises:
            DuplicateKeyError: If prompt with same name exists in workspace
        """
        collection = self.get_collection()

        # Check for duplicate name in workspace
        existing = await collection.find_one(
            {"workspace_id": prompt.workspace_id, "name": prompt.name}
        )
        if existing:
            raise DuplicateKeyError("Prompt with this name already exists in workspace")

        prompt_data = prompt.model_dump_for_db()
        result = await collection.insert_one(prompt_data)
        return str(result.inserted_id)

    async def get_prompt_by_id(self, prompt_id: str) -> MCPPromptModel | None:
        """Get a prompt by its ID.

        Args:
            prompt_id: The prompt ID

        Returns:
            The prompt model or None if not found
        """
        collection = self.get_collection()

        try:
            object_id = ObjectId(prompt_id)
        except Exception:
            return None

        prompt_data = await collection.find_one({"_id": object_id})
        if not prompt_data:
            return None

        return MCPPromptModel.from_mongo(prompt_data)

    async def get_prompt_by_name(self, workspace_id: str, name: str) -> MCPPromptModel | None:
        """Get a prompt by name within a workspace.

        Args:
            workspace_id: The workspace ID
            name: The prompt name

        Returns:
            The prompt model or None if not found
        """
        collection = self.get_collection()

        prompt_data = await collection.find_one(
            {"workspace_id": workspace_id, "name": name}
        )
        if not prompt_data:
            return None

        return MCPPromptModel.from_mongo(prompt_data)

    async def get_prompts_by_workspace(
        self,
        workspace_id: str,
        category: str | None = None,
        tags: list[str] | None = None,
        is_active: bool | None = None,
        is_system: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[MCPPromptModel]:
        """Get prompts for a workspace with optional filtering.

        Args:
            workspace_id: The workspace ID
            category: Optional category filter
            tags: Optional tags filter (prompts must have all tags)
            is_active: Optional active status filter
            is_system: Optional system status filter
            skip: Number of prompts to skip
            limit: Maximum number of prompts to return

        Returns:
            List of prompt models
        """
        collection = self.get_collection()

        # Build filter
        query_filter = {"workspace_id": workspace_id}

        if category:
            query_filter["category"] = category

        if tags:
            query_filter["tags"] = {"$all": tags}

        if is_active is not None:
            query_filter["is_active"] = is_active

        if is_system is not None:
            query_filter["is_system"] = is_system

        cursor = collection.find(query_filter).skip(skip).limit(limit)
        prompt_docs = await cursor.to_list(length=limit)

        return [MCPPromptModel.from_mongo(doc) for doc in prompt_docs]

    async def get_templates_by_workspace(self, workspace_id: str) -> list[MCPPromptModel]:
        """Get all templates for a workspace.

        Args:
            workspace_id: The workspace ID

        Returns:
            List of template prompt models
        """
        collection = self.get_collection()

        query_filter = {
            "workspace_id": workspace_id,
            "is_template": True,
            "is_active": True
        }

        cursor = collection.find(query_filter).sort("name", 1)
        template_docs = await cursor.to_list(length=None)

        return [MCPPromptModel.from_mongo(doc) for doc in template_docs]

    async def update_prompt(self, prompt_id: str, updates: dict[str, Any]) -> MCPPromptModel | None:
        """Update a prompt.

        Args:
            prompt_id: The prompt ID
            updates: Dictionary of fields to update

        Returns:
            The updated prompt model or None if not found
        """
        collection = self.get_collection()

        try:
            object_id = ObjectId(prompt_id)
        except Exception:
            return None

        result = await collection.find_one_and_update(
            {"_id": object_id},
            {"$set": updates},
            return_document=True,
        )

        if not result:
            return None

        return MCPPromptModel.from_mongo(result)

    async def delete_prompt(self, prompt_id: str) -> bool:
        """Delete a prompt.

        Args:
            prompt_id: The prompt ID

        Returns:
            True if deleted, False if not found
        """
        collection = self.get_collection()

        try:
            object_id = ObjectId(prompt_id)
        except Exception:
            return False

        result = await collection.delete_one({"_id": object_id})
        return result.deleted_count > 0

    async def count_prompts_by_workspace(
        self,
        workspace_id: str,
        category: str | None = None,
        tags: list[str] | None = None,
        is_active: bool | None = None,
        is_system: bool | None = None,
    ) -> int:
        """Count prompts for a workspace with optional filtering.

        Args:
            workspace_id: The workspace ID
            category: Optional category filter
            tags: Optional tags filter
            is_active: Optional active status filter
            is_system: Optional system status filter

        Returns:
            Number of matching prompts
        """
        collection = self.get_collection()

        # Build filter (same as get_prompts_by_workspace)
        query_filter = {"workspace_id": workspace_id}

        if category:
            query_filter["category"] = category

        if tags:
            query_filter["tags"] = {"$all": tags}

        if is_active is not None:
            query_filter["is_active"] = is_active

        if is_system is not None:
            query_filter["is_system"] = is_system

        return await collection.count_documents(query_filter)

    async def increment_usage_count(self, prompt_id: str) -> bool:
        """Increment the usage count for a prompt.

        Args:
            prompt_id: The prompt ID

        Returns:
            True if updated, False if not found
        """
        collection = self.get_collection()

        try:
            object_id = ObjectId(prompt_id)
        except Exception:
            return False

        from datetime import UTC, datetime

        result = await collection.update_one(
            {"_id": object_id},
            {
                "$inc": {"usage_count": 1},
                "$set": {"last_used_at": datetime.now(UTC)}
            }
        )

        return result.modified_count > 0

    async def get_usage_stats(self, workspace_id: str, days: int = 30) -> dict[str, Any]:
        """Get usage statistics for prompts in a workspace.

        Args:
            workspace_id: The workspace ID
            days: Number of days to look back for usage stats

        Returns:
            Dictionary with usage statistics
        """
        collection = self.get_collection()

        from datetime import UTC, datetime, timedelta

        cutoff_date = datetime.now(UTC) - timedelta(days=days)

        # Aggregate pipeline for usage stats
        pipeline = [
            {"$match": {"workspace_id": workspace_id}},
            {
                "$group": {
                    "_id": None,
                    "total_prompts": {"$sum": 1},
                    "active_prompts": {
                        "$sum": {"$cond": [{"$eq": ["$is_active", True]}, 1, 0]}
                    },
                    "system_prompts": {
                        "$sum": {"$cond": [{"$eq": ["$is_system", True]}, 1, 0]}
                    },
                    "total_usage": {"$sum": "$usage_count"},
                    "recently_used": {
                        "$sum": {
                            "$cond": [
                                {"$gte": ["$last_used_at", cutoff_date]},
                                1,
                                0
                            ]
                        }
                    }
                }
            }
        ]

        result = await collection.aggregate(pipeline).to_list(1)

        if not result:
            return {
                "total_prompts": 0,
                "active_prompts": 0,
                "system_prompts": 0,
                "total_usage": 0,
                "recently_used": 0
            }

        return result[0]

    async def create_indexes(self):
        """Create database indexes for optimal performance."""
        collection = self.get_collection()

        # Compound index for workspace queries
        await collection.create_index([
            ("workspace_id", 1),
            ("name", 1)
        ], unique=True)

        # Index for filtering by category and active status
        await collection.create_index([
            ("workspace_id", 1),
            ("category", 1),
            ("is_active", 1)
        ])

        # Index for tag searches
        await collection.create_index([
            ("workspace_id", 1),
            ("tags", 1)
        ])

        # Index for usage tracking
        await collection.create_index([
            ("workspace_id", 1),
            ("last_used_at", -1)
        ])

        # Index for template queries
        await collection.create_index([
            ("workspace_id", 1),
            ("is_template", 1),
            ("is_active", 1)
        ])

        # Index for inheritance chain lookups
        await collection.create_index([
            ("extends", 1)
        ])
