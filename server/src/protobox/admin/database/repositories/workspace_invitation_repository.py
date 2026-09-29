"""Repository for workspace invitation operations."""

from datetime import datetime, timedelta

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from ...models.workspace_invitation import InvitationStatus, WorkspaceInvitation


class WorkspaceInvitationRepository:
    """Repository for workspace invitation operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.workspace_invitations

    async def initialize(self) -> None:
        """Initialize collection with proper indexes."""
        # Composite index to prevent duplicate invitations
        await self.collection.create_index([
            ("workspace_id", ASCENDING),
            ("email", ASCENDING),
            ("status", ASCENDING)
        ], unique=True, partialFilterExpression={"status": "pending"})

        # Index for workspace queries
        await self.collection.create_index([("workspace_id", ASCENDING)])

        # Index for email queries
        await self.collection.create_index([("email", ASCENDING)])

        # Index for token lookups
        await self.collection.create_index([("token", ASCENDING)], unique=True)

        # Index for status queries
        await self.collection.create_index([("status", ASCENDING)])

        # Index for expiry cleanup
        await self.collection.create_index([("expires_at", ASCENDING)])

        # Index for chronological queries
        await self.collection.create_index([("invited_at", DESCENDING)])

    async def create_invitation(self, invitation: WorkspaceInvitation) -> WorkspaceInvitation:
        """Create a new workspace invitation."""
        invitation_data = invitation.model_dump_for_db()
        result = await self.collection.insert_one(invitation_data)
        invitation.id = str(result.inserted_id)
        return invitation

    async def get_invitation_by_id(self, invitation_id: str) -> WorkspaceInvitation | None:
        """Get invitation by ID."""
        if not ObjectId.is_valid(invitation_id):
            return None

        invitation_data = await self.collection.find_one({"_id": ObjectId(invitation_id)})

        if invitation_data:
            return WorkspaceInvitation.from_mongo(invitation_data)
        return None

    async def get_invitation_by_token(self, token: str) -> WorkspaceInvitation | None:
        """Get invitation by token."""
        invitation_data = await self.collection.find_one({"token": token})

        if invitation_data:
            return WorkspaceInvitation.from_mongo(invitation_data)
        return None

    async def get_invitations_by_workspace(
        self, workspace_id: ObjectId, skip: int = 0, limit: int = 100
    ) -> list[WorkspaceInvitation]:
        """Get all invitations for a workspace."""
        cursor = self.collection.find(
            {"workspace_id": workspace_id}
        ).skip(skip).limit(limit).sort("invited_at", DESCENDING)

        invitations = []
        async for invitation_data in cursor:
            invitations.append(WorkspaceInvitation.from_mongo(invitation_data))

        return invitations

    async def get_pending_invitations_by_workspace(
        self, workspace_id: ObjectId
    ) -> list[WorkspaceInvitation]:
        """Get pending invitations for a workspace."""
        cursor = self.collection.find({
            "workspace_id": workspace_id,
            "status": InvitationStatus.PENDING.value
        })

        invitations = []
        async for invitation_data in cursor:
            invitations.append(WorkspaceInvitation.from_mongo(invitation_data))

        return invitations

    async def count_pending_invitations(self, workspace_id: ObjectId) -> int:
        """Count pending invitations for a workspace."""
        return await self.collection.count_documents({
            "workspace_id": workspace_id,
            "status": InvitationStatus.PENDING.value
        })

    async def get_invitation_by_workspace_and_email(
        self, workspace_id: ObjectId, email: str, status: InvitationStatus | None = None
    ) -> WorkspaceInvitation | None:
        """Get invitation by workspace and email."""
        query = {
            "workspace_id": workspace_id,
            "email": email.lower()
        }

        if status:
            query["status"] = status.value

        invitation_data = await self.collection.find_one(query)

        if invitation_data:
            return WorkspaceInvitation.from_mongo(invitation_data)
        return None

    async def update_invitation_status(
        self, invitation_id: str, status: InvitationStatus, accepted_at: datetime | None = None
    ) -> WorkspaceInvitation | None:
        """Update invitation status."""
        if not ObjectId.is_valid(invitation_id):
            return None

        update_data = {
            "status": status.value,
            "updated_at": datetime.utcnow()
        }

        if accepted_at:
            update_data["accepted_at"] = accepted_at

        result = await self.collection.find_one_and_update(
            {"_id": ObjectId(invitation_id)},
            {"$set": update_data},
            return_document=True
        )

        if result:
            return WorkspaceInvitation.from_mongo(result)
        return None

    async def delete_invitation(self, invitation_id: str) -> bool:
        """Delete an invitation."""
        if not ObjectId.is_valid(invitation_id):
            return False

        result = await self.collection.delete_one({"_id": ObjectId(invitation_id)})
        return result.deleted_count > 0

    async def cancel_invitation(self, invitation_id: str) -> WorkspaceInvitation | None:
        """Cancel a pending invitation."""
        return await self.update_invitation_status(invitation_id, InvitationStatus.CANCELLED)

    async def mark_expired_invitations(self) -> int:
        """Mark expired invitations as expired."""
        result = await self.collection.update_many(
            {
                "status": InvitationStatus.PENDING.value,
                "expires_at": {"$lt": datetime.utcnow()}
            },
            {
                "$set": {
                    "status": InvitationStatus.EXPIRED.value,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return result.modified_count

    async def cleanup_old_invitations(self, days_old: int = 30) -> int:
        """Clean up old expired/cancelled invitations."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        result = await self.collection.delete_many({
            "status": {"$in": [InvitationStatus.EXPIRED.value, InvitationStatus.CANCELLED.value]},
            "invited_at": {"$lt": cutoff_date}
        })

        return result.deleted_count

    async def get_invitations_by_email(self, email: str) -> list[WorkspaceInvitation]:
        """Get all invitations for an email address."""
        cursor = self.collection.find({"email": email.lower()})

        invitations = []
        async for invitation_data in cursor:
            invitations.append(WorkspaceInvitation.from_mongo(invitation_data))

        return invitations

    async def has_pending_invitation(self, workspace_id: ObjectId, email: str) -> bool:
        """Check if there's a pending invitation for email in workspace."""
        count = await self.collection.count_documents({
            "workspace_id": workspace_id,
            "email": email.lower(),
            "status": InvitationStatus.PENDING.value
        })

        return count > 0

    async def get_invitations_by_inviter(
        self, invited_by: str, workspace_id: ObjectId | None = None
    ) -> list[WorkspaceInvitation]:
        """Get invitations sent by a specific user."""
        query = {"invited_by": invited_by}

        if workspace_id:
            query["workspace_id"] = workspace_id

        cursor = self.collection.find(query).sort("invited_at", DESCENDING)

        invitations = []
        async for invitation_data in cursor:
            invitations.append(WorkspaceInvitation.from_mongo(invitation_data))

        return invitations
