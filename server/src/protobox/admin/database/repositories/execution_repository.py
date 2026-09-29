"""Execution repository for MongoDB operations."""

from datetime import datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from ...models.execution import ExecutionModel, ExecutionStatus, ExecutionSummary
from ..connection import get_database_connection


class ExecutionRepository:
    """Repository for execution database operations."""

    def __init__(self):
        """Initialize the repository."""
        self.collection_name = "executions"

    async def get_collection(self) -> AsyncIOMotorCollection:
        """Get the executions collection."""
        db_connection = get_database_connection()
        return db_connection.database[self.collection_name]

    async def create_execution(self, execution: ExecutionModel) -> str:
        """Create a new execution.

        Args:
            execution: The execution model to create

        Returns:
            The ID of the created execution
        """
        try:
            db = get_database_connection()
            collection = db.database.executions

            # Prepare data for insertion
            execution_data = execution.model_dump()
            execution_data["created_at"] = datetime.utcnow()

            # Insert execution
            result = await collection.insert_one(execution_data)
            return str(result.inserted_id)

        except Exception as e:
            raise RuntimeError(f"Failed to create execution: {e}")

    async def get_execution_by_id(self, execution_id: str) -> ExecutionModel | None:
        """Get an execution by its ID.

        Args:
            execution_id: The execution ID

        Returns:
            The execution model or None if not found
        """
        try:
            from bson.errors import InvalidId

            # Validate ObjectId format
            try:
                object_id = ObjectId(execution_id)
            except InvalidId:
                return None

            db = get_database_connection()
            collection = db.database.executions

            execution_data = await collection.find_one({"_id": object_id})
            if not execution_data:
                return None

            # Convert ObjectId to string
            execution_data["id"] = str(execution_data.pop("_id"))

            return ExecutionModel(**execution_data)

        except Exception:
            return None

    async def get_executions_by_workspace(
        self,
        workspace_id: str,
        action_id: str | None = None,
        status: ExecutionStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ExecutionModel]:
        """Get executions for a workspace.

        Args:
            workspace_id: The workspace ID
            action_id: Optional action ID filter
            status: Optional status filter
            skip: Number of executions to skip
            limit: Maximum number of executions to return

        Returns:
            List of execution models
        """
        try:
            db = get_database_connection()
            collection = db.database.executions

            # Build filter query
            filter_query = {"workspace_id": workspace_id}
            if action_id:
                filter_query["action_id"] = action_id
            if status:
                filter_query["status"] = status.value

            # Execute query with pagination
            cursor = collection.find(filter_query).skip(skip).limit(limit).sort("created_at", -1)
            executions_data = await cursor.to_list(length=limit)

            # Convert to models
            executions = []
            for data in executions_data:
                data["id"] = str(data.pop("_id"))
                executions.append(ExecutionModel(**data))

            return executions

        except Exception:
            return []

    async def get_executions_with_names(
        self,
        workspace_id: str,
        action_id: str | None = None,
        status: ExecutionStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get executions for a workspace with action and user names via aggregation.

        Args:
            workspace_id: The workspace ID
            action_id: Optional action ID filter
            status: Optional status filter
            skip: Number of executions to skip
            limit: Maximum number of executions to return

        Returns:
            List of execution dictionaries with action_name and user_name fields
        """
        try:
            db = get_database_connection()
            collection = db.database.executions

            # Build match filter
            match_filter = {"workspace_id": workspace_id}
            if action_id:
                match_filter["action_id"] = action_id
            if status:
                match_filter["status"] = status.value

            print(f"DEBUG: Match filter: {match_filter}")

            # Start with a simple pipeline first
            basic_pipeline = [
                {"$match": match_filter},
                {"$sort": {"started_at": -1}},
                {"$skip": skip},
                {"$limit": limit},
            ]

            print("DEBUG: Testing basic pipeline...")
            basic_cursor = collection.aggregate(basic_pipeline)
            basic_results = await basic_cursor.to_list(length=limit)
            print(f"DEBUG: Basic pipeline returned {len(basic_results)} results")

            if not basic_results:
                print("DEBUG: No basic results, returning empty list")
                return []

            # Now try with action lookup - simplified approach
            pipeline = [
                {"$match": match_filter},
                {"$sort": {"started_at": -1}},
                {"$skip": skip},
                {"$limit": limit},
                # Simple lookup first - try string matching
                {
                    "$lookup": {
                        "from": "actions",
                        "let": {"action_id_str": "$action_id"},
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {"$eq": [{"$toString": "$_id"}, "$$action_id_str"]}
                                }
                            },
                            {"$project": {"name": 1}},
                        ],
                        "as": "action_info",
                    }
                },
                # Add computed fields with fallbacks
                {
                    "$addFields": {
                        "action_name": {
                            "$cond": {
                                "if": {"$gt": [{"$size": "$action_info"}, 0]},
                                "then": {"$arrayElemAt": ["$action_info.name", 0]},
                                "else": "$action_id",
                            }
                        },
                        "user_name": "$user_id",  # Simple fallback for now
                    }
                },
                # Clean up and format output
                {
                    "$project": {
                        "id": {"$toString": "$_id"},
                        "_id": 0,
                        "action_id": 1,
                        "action_name": 1,
                        "workspace_id": 1,
                        "user_id": 1,
                        "user_name": 1,
                        "status": 1,
                        "started_at": 1,
                        "completed_at": 1,
                        "execution_time_ms": 1,
                        "error_message": 1,
                        "output_data": 1,
                        "retry_count": 1,
                        "max_retries": {"$ifNull": ["$max_retries", 3]},
                    }
                },
            ]

            print("DEBUG: Executing full pipeline...")
            cursor = collection.aggregate(pipeline)
            results = await cursor.to_list(length=limit)
            print(f"DEBUG: Full pipeline returned {len(results)} results")

            # Add computed fields for each result
            for result in results:
                # Add can_retry logic (since it's a method in the model)
                result["can_retry"] = result.get("status") == "failed" and result.get(
                    "retry_count", 0
                ) < result.get("max_retries", 3)

            print(f"DEBUG: Final results count: {len(results)}")
            if results:
                print(f"DEBUG: Sample result keys: {list(results[0].keys())}")

            return results

        except Exception as e:
            # Log the error but don't expose it
            import traceback

            print(f"Error in get_executions_with_names: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            print(f"Pipeline: {pipeline}")
            return []

    async def update_execution(self, execution_id: str, updates: dict[str, Any]) -> bool:
        """Update an execution.

        Args:
            execution_id: The execution ID
            updates: Dictionary of fields to update

        Returns:
            True if updated successfully, False otherwise
        """
        try:
            from bson import ObjectId
            from bson.errors import InvalidId

            # Validate ObjectId format
            try:
                object_id = ObjectId(execution_id)
            except InvalidId:
                return False

            db = get_database_connection()
            collection = db.database.executions

            # Add updated timestamp
            updates["updated_at"] = datetime.utcnow()

            # Update execution
            result = await collection.update_one({"_id": object_id}, {"$set": updates})

            return result.matched_count > 0

        except Exception:
            return False

    async def delete_execution(self, execution_id: str) -> bool:
        """Delete an execution.

        Args:
            execution_id: The execution ID

        Returns:
            True if execution was deleted, False if not found
        """
        collection = await self.get_collection()

        try:
            object_id = ObjectId(execution_id)
        except Exception:
            return False

        result = await collection.delete_one({"_id": object_id})
        return result.deleted_count > 0

    async def get_executions_by_action(
        self,
        action_id: str,
        status: ExecutionStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ExecutionModel]:
        """Get executions for an action.

        Args:
            action_id: The action ID
            status: Optional status filter
            skip: Number of executions to skip
            limit: Maximum number of executions to return

        Returns:
            List of execution models
        """
        try:
            db = get_database_connection()
            collection = db.database.executions

            # Build filter query
            filter_query = {"action_id": action_id}
            if status:
                filter_query["status"] = status.value

            # Execute query with pagination
            cursor = collection.find(filter_query).skip(skip).limit(limit).sort("created_at", -1)
            executions_data = await cursor.to_list(length=limit)

            # Convert to models
            executions = []
            for data in executions_data:
                data["id"] = str(data.pop("_id"))
                executions.append(ExecutionModel(**data))

            return executions

        except Exception:
            return []

    async def get_pending_executions(self, limit: int = 100) -> list[ExecutionModel]:
        """Get pending executions that need to be processed.

        Args:
            limit: Maximum number of executions to return

        Returns:
            List of pending execution models
        """
        collection = await self.get_collection()

        cursor = (
            collection.find({"status": ExecutionStatus.PENDING.value})
            .sort("started_at", 1)
            .limit(limit)
        )
        executions = []

        async for execution_data in cursor:
            execution_data["_id"] = str(execution_data["_id"])
            executions.append(ExecutionModel(**execution_data))

        return executions

    async def get_execution_summary(
        self, workspace_id: str, action_id: str | None = None
    ) -> ExecutionSummary:
        """Get execution summary statistics.

        Args:
            workspace_id: The workspace ID
            action_id: Optional action ID filter

        Returns:
            Execution summary statistics
        """
        try:
            db = get_database_connection()
            collection = db.database.executions

            # Build match query
            match_query = {"workspace_id": workspace_id}
            if action_id:
                match_query["action_id"] = action_id

            # Aggregation pipeline
            pipeline = [
                {"$match": match_query},
                {
                    "$group": {
                        "_id": None,
                        "total_executions": {"$sum": 1},
                        "status_counts": {"$push": "$status"},
                        "avg_execution_time": {"$avg": "$execution_time_ms"},
                        "completed_count": {
                            "$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}
                        },
                    }
                },
            ]

            # Execute aggregation
            result = await collection.aggregate(pipeline).to_list(1)

            if not result:
                return ExecutionSummary(
                    total_executions=0, by_status={}, avg_execution_time_ms=0.0, success_rate=0.0
                )

            data = result[0]

            # Count statuses
            status_counts = {}
            for status in data.get("status_counts", []):
                status_counts[status] = status_counts.get(status, 0) + 1

            # Calculate success rate
            total = data.get("total_executions", 0)
            completed = data.get("completed_count", 0)
            success_rate = completed / total if total > 0 else 0.0

            return ExecutionSummary(
                total_executions=total,
                by_status=status_counts,
                avg_execution_time_ms=data.get("avg_execution_time", 0.0) or 0.0,
                success_rate=success_rate,
            )

        except Exception:
            return ExecutionSummary(
                total_executions=0, by_status={}, avg_execution_time_ms=0.0, success_rate=0.0
            )

    async def count_executions_by_workspace(
        self,
        workspace_id: str,
        action_id: str | None = None,
        status: ExecutionStatus | None = None,
    ) -> int:
        """Count executions for a workspace with optional filtering.

        Args:
            workspace_id: The workspace ID
            action_id: Optional action ID filter
            status: Optional status filter

        Returns:
            Number of matching executions
        """
        collection = await self.get_collection()

        # Build filter query
        filter_query = {"workspace_id": workspace_id}
        if action_id:
            filter_query["action_id"] = action_id
        if status:
            filter_query["status"] = status.value

        return await collection.count_documents(filter_query)

    async def cleanup_old_executions(self, days_old: int = 30) -> int:
        """Clean up old completed/failed executions.

        Args:
            days_old: Age in days for executions to be considered old

        Returns:
            Number of deleted executions
        """
        collection = await self.get_collection()

        from datetime import datetime, timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        result = await collection.delete_many(
            {
                "status": {"$in": [ExecutionStatus.COMPLETED.value, ExecutionStatus.FAILED.value]},
                "completed_at": {"$lt": cutoff_date},
            }
        )

        return result.deleted_count

    async def ensure_indexes(self) -> None:
        """Ensure required database indexes exist."""
        collection = await self.get_collection()

        # Create indexes for performance
        await collection.create_index("workspace_id", name="workspace_id_idx")
        await collection.create_index("action_id", name="action_id_idx")
        await collection.create_index("user_id", name="user_id_idx")
        await collection.create_index("status", name="status_idx")
        await collection.create_index("started_at", name="started_at_idx")
        await collection.create_index("completed_at", name="completed_at_idx")

        # Compound indexes for common queries
        await collection.create_index(
            [("workspace_id", 1), ("action_id", 1), ("started_at", -1)],
            name="workspace_action_time_idx",
        )

        await collection.create_index([("status", 1), ("started_at", 1)], name="status_time_idx")

        # Index for cleanup operations
        await collection.create_index(
            [("status", 1), ("completed_at", 1)], name="status_completed_idx"
        )
