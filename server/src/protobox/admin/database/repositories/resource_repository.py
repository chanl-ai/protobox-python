"""Resource repository for MongoDB operations."""

from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.errors import DuplicateKeyError

from ...models.mcp_resource import MCPResourceModel, ResourceType
from ..connection import get_database_connection


class ResourceRepository:
    """Repository for resource database operations."""

    def __init__(self):
        """Initialize the repository."""
        self.collection_name = "mcp_resources"

    def get_collection(self) -> AsyncIOMotorCollection:
        """Get the resources collection."""
        db_connection = get_database_connection()
        return db_connection.database[self.collection_name]

    async def create_resource(self, resource: MCPResourceModel) -> str:
        """Create a new resource in the database.

        Args:
            resource: The resource model to create

        Returns:
            The ID of the created resource

        Raises:
            DuplicateKeyError: If resource with same URI exists in workspace
        """
        collection = self.get_collection()

        # Check for duplicate URI in workspace
        existing = await collection.find_one(
            {"workspace_id": resource.workspace_id, "uri": resource.uri}
        )
        if existing:
            raise DuplicateKeyError("Resource with this URI already exists in workspace")

        resource_data = resource.model_dump_for_db()
        result = await collection.insert_one(resource_data)
        return str(result.inserted_id)

    async def get_resource_by_id(self, resource_id: str) -> MCPResourceModel | None:
        """Get a resource by its ID.

        Args:
            resource_id: The resource ID

        Returns:
            The resource model or None if not found
        """
        collection = self.get_collection()

        try:
            object_id = ObjectId(resource_id)
        except Exception:
            return None

        resource_data = await collection.find_one({"_id": object_id})
        if not resource_data:
            return None

        return MCPResourceModel.from_mongo(resource_data)

    async def get_resource_by_uri(self, workspace_id: str, uri: str) -> MCPResourceModel | None:
        """Get a resource by URI within a workspace.

        Args:
            workspace_id: The workspace ID
            uri: The resource URI

        Returns:
            The resource model or None if not found
        """
        collection = self.get_collection()

        resource_data = await collection.find_one(
            {"workspace_id": workspace_id, "uri": uri}
        )
        if not resource_data:
            return None

        return MCPResourceModel.from_mongo(resource_data)

    async def get_resources_by_workspace(
        self,
        workspace_id: str,
        resource_type: ResourceType | None = None,
        uri_pattern: str | None = None,
        is_active: bool | None = None,
        is_template: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[MCPResourceModel]:
        """Get resources for a workspace with optional filtering.

        Args:
            workspace_id: The workspace ID
            resource_type: Optional resource type filter
            uri_pattern: Optional URI pattern filter (regex)
            is_active: Optional active status filter
            is_template: Optional template status filter
            skip: Number of resources to skip
            limit: Maximum number of resources to return

        Returns:
            List of resource models
        """
        collection = self.get_collection()

        # Build filter
        query_filter = {"workspace_id": workspace_id}

        if resource_type:
            query_filter["resource_type"] = resource_type

        if uri_pattern:
            query_filter["uri"] = {"$regex": uri_pattern, "$options": "i"}

        if is_active is not None:
            query_filter["is_active"] = is_active

        if is_template is not None:
            query_filter["is_template"] = is_template

        cursor = collection.find(query_filter).skip(skip).limit(limit)
        resource_docs = await cursor.to_list(length=limit)

        return [MCPResourceModel.from_mongo(doc) for doc in resource_docs]

    async def update_resource(self, resource_id: str, updates: dict[str, Any]) -> MCPResourceModel | None:
        """Update a resource.

        Args:
            resource_id: The resource ID
            updates: Dictionary of fields to update

        Returns:
            The updated resource model or None if not found
        """
        collection = self.get_collection()

        try:
            object_id = ObjectId(resource_id)
        except Exception:
            return None

        result = await collection.find_one_and_update(
            {"_id": object_id},
            {"$set": updates},
            return_document=True,
        )

        if not result:
            return None

        return MCPResourceModel.from_mongo(result)

    async def delete_resource(self, resource_id: str) -> bool:
        """Delete a resource.

        Args:
            resource_id: The resource ID

        Returns:
            True if deleted, False if not found
        """
        collection = self.get_collection()

        try:
            object_id = ObjectId(resource_id)
        except Exception:
            return False

        result = await collection.delete_one({"_id": object_id})
        return result.deleted_count > 0

    async def delete_resource_by_uri(self, workspace_id: str, uri: str) -> bool:
        """Delete a resource by URI.

        Args:
            workspace_id: The workspace ID
            uri: The resource URI

        Returns:
            True if deleted, False if not found
        """
        collection = self.get_collection()

        result = await collection.delete_one({
            "workspace_id": workspace_id,
            "uri": uri
        })
        return result.deleted_count > 0

    async def count_resources_by_workspace(
        self,
        workspace_id: str,
        resource_type: ResourceType | None = None,
        uri_pattern: str | None = None,
        is_active: bool | None = None,
        is_template: bool | None = None,
    ) -> int:
        """Count resources for a workspace with optional filtering.

        Args:
            workspace_id: The workspace ID
            resource_type: Optional resource type filter
            uri_pattern: Optional URI pattern filter
            is_active: Optional active status filter
            is_template: Optional template status filter

        Returns:
            Number of matching resources
        """
        collection = self.get_collection()

        # Build filter (same as get_resources_by_workspace)
        query_filter = {"workspace_id": workspace_id}

        if resource_type:
            query_filter["resource_type"] = resource_type

        if uri_pattern:
            query_filter["uri"] = {"$regex": uri_pattern, "$options": "i"}

        if is_active is not None:
            query_filter["is_active"] = is_active

        if is_template is not None:
            query_filter["is_template"] = is_template

        return await collection.count_documents(query_filter)

    async def increment_access_count(self, resource_id: str) -> bool:
        """Increment the access count for a resource.

        Args:
            resource_id: The resource ID

        Returns:
            True if updated, False if not found
        """
        collection = self.get_collection()

        try:
            object_id = ObjectId(resource_id)
        except Exception:
            return False

        from datetime import UTC, datetime

        result = await collection.update_one(
            {"_id": object_id},
            {
                "$inc": {"access_count": 1},
                "$set": {"last_accessed_at": datetime.now(UTC)}
            }
        )

        return result.modified_count > 0

    async def get_resources_by_source(
        self,
        workspace_id: str,
        source_type: str,
        source_id: str
    ) -> list[MCPResourceModel]:
        """Get resources by their source.

        Args:
            workspace_id: The workspace ID
            source_type: The source type
            source_id: The source ID

        Returns:
            List of matching resources
        """
        collection = self.get_collection()

        cursor = collection.find({
            "workspace_id": workspace_id,
            "source.type": source_type,
            "source.id": source_id
        })

        resource_docs = await cursor.to_list(length=None)
        return [MCPResourceModel.from_mongo(doc) for doc in resource_docs]

    async def bulk_delete_by_source(
        self,
        workspace_id: str,
        source_type: str,
        source_ids: list[str]
    ) -> int:
        """Bulk delete resources by source IDs.

        Args:
            workspace_id: The workspace ID
            source_type: The source type
            source_ids: List of source IDs to delete

        Returns:
            Number of deleted resources
        """
        collection = self.get_collection()

        result = await collection.delete_many({
            "workspace_id": workspace_id,
            "source.type": source_type,
            "source.id": {"$in": source_ids}
        })

        return result.deleted_count

    async def get_usage_stats(self, workspace_id: str, days: int = 30) -> dict[str, Any]:
        """Get usage statistics for resources in a workspace.

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
                    "total_resources": {"$sum": 1},
                    "active_resources": {
                        "$sum": {"$cond": [{"$eq": ["$is_active", True]}, 1, 0]}
                    },
                    "template_resources": {
                        "$sum": {"$cond": [{"$eq": ["$is_template", True]}, 1, 0]}
                    },
                    "total_accesses": {"$sum": "$access_count"},
                    "total_size": {"$sum": "$size"},
                    "recently_accessed": {
                        "$sum": {
                            "$cond": [
                                {"$gte": ["$last_accessed_at", cutoff_date]},
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
                "total_resources": 0,
                "active_resources": 0,
                "template_resources": 0,
                "total_accesses": 0,
                "total_size": 0,
                "recently_accessed": 0
            }

        return result[0]

    async def get_resource_type_counts(self, workspace_id: str) -> dict[str, int]:
        """Get count of resources by type.

        Args:
            workspace_id: The workspace ID

        Returns:
            Dictionary mapping resource types to counts
        """
        collection = self.get_collection()

        pipeline = [
            {"$match": {"workspace_id": workspace_id}},
            {
                "$group": {
                    "_id": "$resource_type",
                    "count": {"$sum": 1}
                }
            }
        ]

        result = await collection.aggregate(pipeline).to_list(None)
        return {item["_id"]: item["count"] for item in result}

    async def get_mime_type_counts(self, workspace_id: str) -> dict[str, int]:
        """Get count of resources by MIME type.

        Args:
            workspace_id: The workspace ID

        Returns:
            Dictionary mapping MIME types to counts
        """
        collection = self.get_collection()

        pipeline = [
            {"$match": {"workspace_id": workspace_id}},
            {
                "$group": {
                    "_id": "$mime_type",
                    "count": {"$sum": 1}
                }
            }
        ]

        result = await collection.aggregate(pipeline).to_list(None)
        return {item["_id"]: item["count"] for item in result}

    async def get_most_accessed_resources(
        self,
        workspace_id: str,
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get most frequently accessed resources.

        Args:
            workspace_id: The workspace ID
            limit: Maximum number of resources to return

        Returns:
            List of resource access data
        """
        collection = self.get_collection()

        pipeline = [
            {"$match": {"workspace_id": workspace_id, "access_count": {"$gt": 0}}},
            {
                "$project": {
                    "uri": 1,
                    "name": 1,
                    "access_count": 1,
                    "last_accessed_at": 1,
                    "resource_type": 1
                }
            },
            {"$sort": {"access_count": -1}},
            {"$limit": limit}
        ]

        return await collection.aggregate(pipeline).to_list(limit)

    async def create_indexes(self):
        """Create database indexes for optimal performance."""
        collection = self.get_collection()

        # Compound index for workspace + URI uniqueness
        await collection.create_index([
            ("workspace_id", 1),
            ("uri", 1)
        ], unique=True)

        # Index for filtering by resource type and active status
        await collection.create_index([
            ("workspace_id", 1),
            ("resource_type", 1),
            ("is_active", 1)
        ])

        # Index for source lookups
        await collection.create_index([
            ("workspace_id", 1),
            ("source.type", 1),
            ("source.id", 1)
        ])

        # Index for access tracking
        await collection.create_index([
            ("workspace_id", 1),
            ("last_accessed_at", -1)
        ])

        # Text index for URI searches
        await collection.create_index([
            ("workspace_id", 1),
            ("uri", "text"),
            ("name", "text"),
            ("description", "text")
        ])
