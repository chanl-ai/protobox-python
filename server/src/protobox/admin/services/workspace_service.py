"""Workspace service for managing workspaces."""
import logging
from datetime import datetime

from bson import ObjectId
from bson.errors import InvalidId

from ..database.connection import DatabaseConnection, get_database_connection
from ..models.workspace import Workspace, WorkspaceCreate, WorkspaceUpdate

logger = logging.getLogger(__name__)


class WorkspaceService:
    """Service for managing workspaces."""

    def __init__(self, db: DatabaseConnection | None = None):
        self.db = db or get_database_connection()
        self.collection_name = "workspaces"

    def _get_collection(self):
        """Get the workspaces collection."""
        return self.db.database[self.collection_name]

    async def create_workspace(self, workspace_data: WorkspaceCreate) -> Workspace:
        """Create a new workspace."""
        try:
            # Create workspace document
            workspace_dict = workspace_data.dict()
            workspace_dict["created_at"] = datetime.utcnow()
            workspace_dict["updated_at"] = datetime.utcnow()

            # Insert into database
            collection = self._get_collection()
            result = await collection.insert_one(workspace_dict)
            workspace_dict["_id"] = result.inserted_id

            return Workspace(**workspace_dict)
        except Exception as e:
            logger.error(f"Error creating workspace: {e}")
            raise

    async def get_workspace(self, workspace_id: str) -> Workspace | None:
        """Get a workspace by ID."""
        try:
            # Validate ObjectId
            try:
                obj_id = ObjectId(workspace_id)
            except InvalidId:
                logger.warning(f"Invalid workspace ID format: {workspace_id}")
                return None

            # Find workspace
            collection = self._get_collection()
            workspace_dict = await collection.find_one({"_id": obj_id})
            if not workspace_dict:
                return None

            return Workspace(**workspace_dict)
        except Exception as e:
            logger.error(f"Error getting workspace {workspace_id}: {e}")
            raise

    async def get_workspace_by_name(self, name: str) -> Workspace | None:
        """Get a workspace by name."""
        try:
            collection = self._get_collection()
            workspace_dict = await collection.find_one({"name": name})
            if not workspace_dict:
                return None

            return Workspace(**workspace_dict)
        except Exception as e:
            logger.error(f"Error getting workspace by name {name}: {e}")
            raise

    async def list_workspaces(self, owner_id: str | None = None) -> list[Workspace]:
        """List workspaces, optionally filtered by owner."""
        try:
            query = {}
            if owner_id:
                query["owner_id"] = owner_id

            collection = self._get_collection()
            cursor = collection.find(query)
            workspaces = []
            async for workspace_dict in cursor:
                workspaces.append(Workspace(**workspace_dict))

            return workspaces
        except Exception as e:
            logger.error(f"Error listing workspaces: {e}")
            raise

    async def update_workspace(
        self, workspace_id: str, update_data: WorkspaceUpdate
    ) -> Workspace | None:
        """Update a workspace."""
        try:
            # Validate ObjectId
            try:
                obj_id = ObjectId(workspace_id)
            except InvalidId:
                logger.warning(f"Invalid workspace ID format: {workspace_id}")
                return None

            # Prepare update document
            update_dict = update_data.dict(exclude_unset=True)
            if update_dict:
                update_dict["updated_at"] = datetime.utcnow()

                # Update workspace
                collection = self._get_collection()
                result = await collection.update_one({"_id": obj_id}, {"$set": update_dict})

                if result.modified_count == 0:
                    return None

            # Return updated workspace
            return await self.get_workspace(workspace_id)
        except Exception as e:
            logger.error(f"Error updating workspace {workspace_id}: {e}")
            raise

    async def delete_workspace(self, workspace_id: str) -> bool:
        """Delete a workspace."""
        try:
            # Validate ObjectId
            try:
                obj_id = ObjectId(workspace_id)
            except InvalidId:
                logger.warning(f"Invalid workspace ID format: {workspace_id}")
                return False

            # Delete workspace
            collection = self._get_collection()
            result = await collection.delete_one({"_id": obj_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting workspace {workspace_id}: {e}")
            raise

    async def add_member(self, workspace_id: str, user_id: str, role: str = "member") -> bool:
        """Add a member to a workspace."""
        try:
            # Validate ObjectId
            try:
                obj_id = ObjectId(workspace_id)
            except InvalidId:
                logger.warning(f"Invalid workspace ID format: {workspace_id}")
                return False

            # Add member
            collection = self._get_collection()
            result = await collection.update_one(
                {"_id": obj_id},
                {
                    "$addToSet": {
                        "members": {"user_id": user_id, "role": role, "added_at": datetime.utcnow()}
                    },
                    "$set": {"updated_at": datetime.utcnow()},
                },
            )

            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error adding member to workspace {workspace_id}: {e}")
            raise

    async def remove_member(self, workspace_id: str, user_id: str) -> bool:
        """Remove a member from a workspace."""
        try:
            # Validate ObjectId
            try:
                obj_id = ObjectId(workspace_id)
            except InvalidId:
                logger.warning(f"Invalid workspace ID format: {workspace_id}")
                return False

            # Remove member
            collection = self._get_collection()
            result = await collection.update_one(
                {"_id": obj_id},
                {
                    "$pull": {"members": {"user_id": user_id}},
                    "$set": {"updated_at": datetime.utcnow()},
                },
            )

            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error removing member from workspace {workspace_id}: {e}")
            raise

    async def is_member(self, workspace_id: str, user_id: str) -> bool:
        """Check if a user is a member of a workspace."""
        try:
            # Validate ObjectId
            try:
                obj_id = ObjectId(workspace_id)
            except InvalidId:
                logger.warning(f"Invalid workspace ID format: {workspace_id}")
                return False

            # Check membership
            collection = self._get_collection()
            workspace = await collection.find_one(
                {"_id": obj_id, "$or": [{"owner_id": user_id}, {"members.user_id": user_id}]}
            )

            return workspace is not None
        except Exception as e:
            logger.error(f"Error checking membership for workspace {workspace_id}: {e}")
            raise
