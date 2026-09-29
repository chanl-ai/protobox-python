"""Repository for workspace team member operations."""

from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from ...models.team_member import MemberRole, WorkspaceMember


class TeamMemberRepository:
    """Repository for workspace team member operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.workspace_members

    async def initialize(self) -> None:
        """Initialize collection with proper indexes."""
        # Composite index for workspace and user queries
        await self.collection.create_index([
            ("workspace_id", ASCENDING),
            ("user_id", ASCENDING)
        ], unique=True)

        # Index for workspace queries
        await self.collection.create_index([("workspace_id", ASCENDING)])

        # Index for user queries across workspaces
        await self.collection.create_index([("user_id", ASCENDING)])

        # Index for email queries
        await self.collection.create_index([("email", ASCENDING)])

        # Index for role queries
        await self.collection.create_index([("role", ASCENDING)])

        # Index for activity tracking
        await self.collection.create_index([("last_active", DESCENDING)])

    async def create_member(self, member: WorkspaceMember) -> WorkspaceMember:
        """Create a new workspace member."""
        member_data = member.model_dump_for_db()
        result = await self.collection.insert_one(member_data)
        member.id = str(result.inserted_id)
        return member

    async def get_member_by_workspace_and_user(
        self, workspace_id: ObjectId, user_id: str
    ) -> WorkspaceMember | None:
        """Get a member by workspace ID and user ID."""
        member_data = await self.collection.find_one({
            "workspace_id": workspace_id,
            "user_id": user_id
        })

        if member_data:
            return WorkspaceMember.from_mongo(member_data)
        return None

    async def get_members_by_workspace(
        self, workspace_id: ObjectId, skip: int = 0, limit: int = 100
    ) -> list[WorkspaceMember]:
        """Get all members of a workspace."""
        cursor = self.collection.find(
            {"workspace_id": workspace_id}
        ).skip(skip).limit(limit).sort("joined_at", ASCENDING)

        members = []
        async for member_data in cursor:
            members.append(WorkspaceMember.from_mongo(member_data))

        return members

    async def count_members_by_workspace(self, workspace_id: ObjectId) -> int:
        """Count total members in a workspace."""
        return await self.collection.count_documents({"workspace_id": workspace_id})

    async def get_member_by_id(self, member_id: str) -> WorkspaceMember | None:
        """Get a member by their ID."""
        if not ObjectId.is_valid(member_id):
            return None

        member_data = await self.collection.find_one({"_id": ObjectId(member_id)})

        if member_data:
            return WorkspaceMember.from_mongo(member_data)
        return None

    async def update_member_role(
        self, workspace_id: ObjectId, user_id: str, role: MemberRole, updated_by: str
    ) -> WorkspaceMember | None:
        """Update a member's role."""
        # Create new permissions for the role
        permissions = WorkspaceMember._get_permissions_for_role(role)

        result = await self.collection.find_one_and_update(
            {
                "workspace_id": workspace_id,
                "user_id": user_id
            },
            {
                "$set": {
                    "role": role.value,
                    "permissions": permissions.model_dump(),
                    "updated_by": updated_by,
                    "updated_at": datetime.utcnow()
                }
            },
            return_document=True
        )

        if result:
            return WorkspaceMember.from_mongo(result)
        return None

    async def remove_member(
        self, workspace_id: ObjectId, user_id: str
    ) -> bool:
        """Remove a member from workspace."""
        result = await self.collection.delete_one({
            "workspace_id": workspace_id,
            "user_id": user_id
        })

        return result.deleted_count > 0

    async def update_last_active(
        self, workspace_id: ObjectId, user_id: str, timestamp: datetime | None = None
    ) -> bool:
        """Update member's last active timestamp."""
        if timestamp is None:
            timestamp = datetime.utcnow()

        result = await self.collection.update_one(
            {
                "workspace_id": workspace_id,
                "user_id": user_id
            },
            {
                "$set": {
                    "last_active": timestamp
                }
            }
        )

        return result.modified_count > 0

    async def get_workspaces_by_user(self, user_id: str) -> list[WorkspaceMember]:
        """Get all workspaces where user is a member."""
        cursor = self.collection.find({"user_id": user_id})

        memberships = []
        async for member_data in cursor:
            memberships.append(WorkspaceMember.from_mongo(member_data))

        return memberships

    async def count_members_by_role(
        self, workspace_id: ObjectId, role: MemberRole
    ) -> int:
        """Count members by role in a workspace."""
        return await self.collection.count_documents({
            "workspace_id": workspace_id,
            "role": role.value
        })

    async def get_workspace_owners(self, workspace_id: ObjectId) -> list[WorkspaceMember]:
        """Get all owners of a workspace."""
        cursor = self.collection.find({
            "workspace_id": workspace_id,
            "role": MemberRole.OWNER.value
        })

        owners = []
        async for member_data in cursor:
            owners.append(WorkspaceMember.from_mongo(member_data))

        return owners

    async def has_permission(
        self, workspace_id: ObjectId, user_id: str, permission: str
    ) -> bool:
        """Check if user has specific permission in workspace."""
        member_data = await self.collection.find_one({
            "workspace_id": workspace_id,
            "user_id": user_id,
            f"permissions.{permission}": True
        })

        return member_data is not None

    async def member_exists(self, workspace_id: ObjectId, user_id: str) -> bool:
        """Check if user is a member of workspace."""
        count = await self.collection.count_documents({
            "workspace_id": workspace_id,
            "user_id": user_id
        })

        return count > 0

    async def get_member_by_email(
        self, workspace_id: ObjectId, email: str
    ) -> WorkspaceMember | None:
        """Get member by email in a workspace."""
        member_data = await self.collection.find_one({
            "workspace_id": workspace_id,
            "email": email.lower()
        })

        if member_data:
            return WorkspaceMember.from_mongo(member_data)
        return None
