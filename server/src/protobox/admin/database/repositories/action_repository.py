"""Action repository for MongoDB operations."""

from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.errors import DuplicateKeyError

from ...models.action import ActionModel, ActionStatus, ActionType
from ..connection import get_database_connection


class ActionRepository:
    """Repository for action database operations."""

    def __init__(self):
        """Initialize the repository."""
        self.collection_name = "actions"

    def get_collection(self) -> AsyncIOMotorCollection:
        """Get the actions collection."""
        db_connection = get_database_connection()
        return db_connection.database[self.collection_name]

    async def create_action(self, action: ActionModel) -> str:
        """Create a new action in the database.

        Args:
            action: The action model to create

        Returns:
            The ID of the created action

        Raises:
            DuplicateKeyError: If action with same name exists in workspace
        """
        collection = self.get_collection()

        # Check for duplicate name in workspace
        existing = await collection.find_one(
            {"workspace_id": action.workspace_id, "name": action.name}
        )
        if existing:
            raise DuplicateKeyError("Action with this name already exists in workspace")

        action_data = action.model_dump_for_db()
        result = await collection.insert_one(action_data)
        return str(result.inserted_id)

    async def get_action_by_id(self, action_id: str) -> ActionModel | None:
        """Get an action by its ID.

        Args:
            action_id: The action ID

        Returns:
            The action model or None if not found
        """
        collection = self.get_collection()

        try:
            object_id = ObjectId(action_id)
        except Exception:
            return None

        action_data = await collection.find_one({"_id": object_id})
        if not action_data:
            return None

        return ActionModel.from_mongo(action_data)

    async def get_actions_by_workspace(
        self,
        workspace_id: str,
        action_type: ActionType | None = None,
        status: ActionStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ActionModel]:
        """Get actions for a workspace with optional filtering.

        Args:
            workspace_id: The workspace ID
            action_type: Optional action type filter
            status: Optional status filter
            skip: Number of documents to skip
            limit: Maximum number of documents to return

        Returns:
            List of action models
        """
        collection = self.get_collection()

        # Build filter query
        filter_query = {"workspace_id": workspace_id}
        if action_type:
            filter_query["type"] = action_type.value
        if status:
            filter_query["status"] = status.value

        # Execute query
        cursor = collection.find(filter_query).skip(skip).limit(limit)
        actions = []

        async for action_data in cursor:
            actions.append(ActionModel.from_mongo(action_data))

        return actions

    async def update_action(self, action_id: str, updates: dict[str, Any]) -> bool:
        """Update an action.

        Args:
            action_id: The action ID
            updates: Dictionary of field updates

        Returns:
            True if action was updated, False if not found
        """
        collection = self.get_collection()

        try:
            object_id = ObjectId(action_id)
        except Exception:
            return False

        # Add updated_at timestamp
        from datetime import datetime

        updates["updated_at"] = datetime.utcnow()

        result = await collection.update_one({"_id": object_id}, {"$set": updates})

        return result.modified_count > 0

    async def delete_action(self, action_id: str) -> bool:
        """Delete an action.

        Args:
            action_id: The action ID

        Returns:
            True if action was deleted, False if not found
        """
        collection = self.get_collection()

        try:
            object_id = ObjectId(action_id)
        except Exception:
            return False

        result = await collection.delete_one({"_id": object_id})
        return result.deleted_count > 0

    async def count_actions_by_workspace(
        self,
        workspace_id: str,
        action_type: ActionType | None = None,
        status: ActionStatus | None = None,
    ) -> int:
        """Count actions for a workspace with optional filtering.

        Args:
            workspace_id: The workspace ID
            action_type: Optional action type filter
            status: Optional status filter

        Returns:
            Number of matching actions
        """
        collection = self.get_collection()

        # Build filter query
        filter_query = {"workspace_id": workspace_id}
        if action_type:
            filter_query["type"] = action_type.value
        if status:
            filter_query["status"] = status.value

        return await collection.count_documents(filter_query)

    async def get_action_by_name(self, workspace_id: str, name: str) -> ActionModel | None:
        """Get an action by workspace and name.

        Args:
            workspace_id: The workspace ID
            name: The action name

        Returns:
            The action model or None if not found
        """
        collection = self.get_collection()

        action_data = await collection.find_one({"workspace_id": workspace_id, "name": name})

        if not action_data:
            return None

        return ActionModel.from_mongo(action_data)

    async def ensure_indexes(self) -> None:
        """Ensure required database indexes exist."""
        collection = self.get_collection()

        # Create indexes for performance
        await collection.create_index(
            [("workspace_id", 1), ("name", 1)], unique=True, name="workspace_name_unique"
        )

        await collection.create_index("workspace_id", name="workspace_id_idx")
        await collection.create_index("action_type", name="action_type_idx")
        await collection.create_index("status", name="status_idx")
        await collection.create_index("created_at", name="created_at_idx")
        await collection.create_index("updated_at", name="updated_at_idx")
