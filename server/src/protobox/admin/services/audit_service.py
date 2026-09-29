"""
Audit Service for tracking all admin API operations.

This service provides centralized audit logging for all CRUD operations
across the ProtoBox platform, ensuring compliance and security.
"""

import logging
from datetime import datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from ..models.audit_log import AuditAction, AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """Service for managing audit logs."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.audit_logs

    async def initialize(self):
        """Initialize audit log collection with indexes."""
        # Create indexes for efficient querying
        await self.collection.create_index([("timestamp", DESCENDING)])
        await self.collection.create_index([("user_id", ASCENDING)])
        await self.collection.create_index([("workspace_id", ASCENDING)])
        await self.collection.create_index([("resource_type", ASCENDING)])
        await self.collection.create_index([("action", ASCENDING)])

        # TTL index for automatic cleanup (e.g., 90 days)
        await self.collection.create_index(
            [("timestamp", ASCENDING)], expireAfterSeconds=90 * 24 * 60 * 60  # 90 days
        )

        logger.info("Audit log indexes created")

    async def log_action(
        self,
        user_id: str,
        workspace_id: str,
        action: AuditAction,
        resource_type: str,
        resource_id: str,
        user_email: str | None = None,
        changes: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Log an audit action."""
        audit_log = AuditLog(
            user_id=user_id,
            user_email=user_email,
            workspace_id=workspace_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
            metadata=metadata or {},
            timestamp=datetime.utcnow(),
        )

        # Don't include id field when inserting (MongoDB will generate it)
        audit_dict = audit_log.model_dump(by_alias=True, exclude={"id"})
        result = await self.collection.insert_one(audit_dict)
        audit_log.id = str(result.inserted_id)

        logger.info(
            f"Audit log created: {action} on {resource_type}:{resource_id} " f"by user {user_id}"
        )

        return audit_log

    async def get_logs(
        self,
        workspace_id: str | None = None,
        user_id: str | None = None,
        resource_type: str | None = None,
        action: AuditAction | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Get audit logs with filtering."""
        query = {}

        if workspace_id:
            query["workspace_id"] = workspace_id
        if user_id:
            query["user_id"] = user_id
        if resource_type:
            query["resource_type"] = resource_type
        if action:
            query["action"] = action.value

        if start_date or end_date:
            timestamp_query = {}
            if start_date:
                timestamp_query["$gte"] = start_date
            if end_date:
                timestamp_query["$lte"] = end_date
            query["timestamp"] = timestamp_query

        cursor = self.collection.find(query).sort("timestamp", DESCENDING).skip(offset).limit(limit)

        logs = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))

            # Handle legacy documents that may have different field names
            # Legacy documents may have 'event' instead of 'action'
            if "event" in doc and "action" not in doc:
                # Try to extract action from event string (e.g., "mcp_token.create" -> "CREATE")
                event = doc.pop("event", "")
                if "create" in event.lower():
                    doc["action"] = "CREATE"
                elif "update" in event.lower():
                    doc["action"] = "UPDATE"
                elif "delete" in event.lower():
                    doc["action"] = "DELETE"
                elif "read" in event.lower() or "get" in event.lower():
                    doc["action"] = "READ"
                elif "execute" in event.lower():
                    doc["action"] = "EXECUTE"
                else:
                    doc["action"] = "READ"  # Default action

                # Extract resource type from event if not present
                if "resource_type" not in doc:
                    if "mcp_token" in event:
                        doc["resource_type"] = "mcp_token"
                    elif "workspace" in event:
                        doc["resource_type"] = "workspace"
                    elif "action" in event:
                        doc["resource_type"] = "action"
                    else:
                        doc["resource_type"] = "unknown"

                # Use a default resource_id if not present
                if "resource_id" not in doc:
                    doc["resource_id"] = doc.get("target_id", "unknown")

            # Ensure required fields exist with defaults if missing
            if "action" not in doc:
                doc["action"] = "READ"
            if "resource_type" not in doc:
                doc["resource_type"] = "unknown"
            if "resource_id" not in doc:
                doc["resource_id"] = "unknown"

            try:
                logs.append(AuditLog(**doc))
            except Exception as e:
                logger.warning(f"Skipping invalid audit log entry: {e}")
                continue

        return logs

    async def get_log_by_id(self, log_id: str) -> AuditLog | None:
        """Get a specific audit log by ID."""
        doc = await self.collection.find_one({"_id": ObjectId(log_id)})
        if doc:
            doc["id"] = str(doc.pop("_id"))

            # Ensure required fields exist with defaults if missing
            if "action" not in doc:
                doc["action"] = "READ"
            if "resource_type" not in doc:
                doc["resource_type"] = "unknown"
            if "resource_id" not in doc:
                doc["resource_id"] = "unknown"

            try:
                return AuditLog(**doc)
            except Exception as e:
                logger.warning(f"Invalid audit log entry: {e}")
                return None
        return None

    async def get_resource_history(
        self, resource_type: str, resource_id: str, limit: int = 50
    ) -> list[AuditLog]:
        """Get audit history for a specific resource."""
        cursor = (
            self.collection.find({"resource_type": resource_type, "resource_id": resource_id})
            .sort("timestamp", DESCENDING)
            .limit(limit)
        )

        logs = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))

            # Ensure required fields exist with defaults if missing
            if "action" not in doc:
                doc["action"] = "READ"
            if "resource_type" not in doc:
                doc["resource_type"] = resource_type or "unknown"
            if "resource_id" not in doc:
                doc["resource_id"] = resource_id or "unknown"

            try:
                logs.append(AuditLog(**doc))
            except Exception as e:
                logger.warning(f"Skipping invalid audit log entry: {e}")
                continue

        return logs

    async def get_user_activity(
        self, user_id: str, workspace_id: str | None = None, limit: int = 100
    ) -> list[AuditLog]:
        """Get activity logs for a specific user."""
        query = {"user_id": user_id}
        if workspace_id:
            query["workspace_id"] = workspace_id

        cursor = self.collection.find(query).sort("timestamp", DESCENDING).limit(limit)

        logs = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))

            # Ensure required fields exist with defaults if missing
            if "action" not in doc:
                doc["action"] = "READ"
            if "resource_type" not in doc:
                doc["resource_type"] = "unknown"
            if "resource_id" not in doc:
                doc["resource_id"] = "unknown"

            try:
                logs.append(AuditLog(**doc))
            except Exception as e:
                logger.warning(f"Skipping invalid audit log entry: {e}")
                continue

        return logs

    async def get_statistics(
        self,
        workspace_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """Get audit log statistics for a workspace."""
        match_stage = {"workspace_id": workspace_id}

        if start_date or end_date:
            timestamp_query = {}
            if start_date:
                timestamp_query["$gte"] = start_date
            if end_date:
                timestamp_query["$lte"] = end_date
            match_stage["timestamp"] = timestamp_query

        pipeline = [
            {"$match": match_stage},
            {
                "$group": {
                    "_id": {"action": "$action", "resource_type": "$resource_type"},
                    "count": {"$sum": 1},
                }
            },
            {
                "$group": {
                    "_id": "$_id.resource_type",
                    "actions": {"$push": {"action": "$_id.action", "count": "$count"}},
                    "total": {"$sum": "$count"},
                }
            },
        ]

        cursor = self.collection.aggregate(pipeline)
        stats = {"by_resource": {}, "total_actions": 0}

        async for doc in cursor:
            resource_type = doc["_id"]
            stats["by_resource"][resource_type] = {
                "total": doc["total"],
                "actions": {item["action"]: item["count"] for item in doc["actions"]},
            }
            stats["total_actions"] += doc["total"]

        # Get unique users count
        user_count = await self.collection.distinct("user_id", match_stage)
        stats["unique_users"] = len(user_count)

        return stats
