"""Chat service for managing chat threads and messages."""

from datetime import datetime

from bson import ObjectId
from bson.errors import InvalidId
from loguru import logger

from ..database.connection import DatabaseConnection, get_database_connection
from ..models.chat import (
    ChatSummary,
    MessageCreateRequest,
    MessageModel,
    MessageRole,
    ThreadCreateRequest,
    ThreadModel,
    ThreadStatus,
    ThreadUpdateRequest,
)


class ChatService:
    """Service for managing chat threads and messages."""

    def __init__(self, db_connection: DatabaseConnection | None = None):
        """Initialize the chat service."""
        self.db = db_connection or get_database_connection()
        self.threads_collection = self.db.database.chat_threads
        self.messages_collection = self.db.database.chat_messages

    async def create_thread(self, request: ThreadCreateRequest, user_id: str) -> ThreadModel:
        """Create a new chat thread."""
        try:
            # No longer checking for duplicate thread names - threads can have duplicate names
            # This allows multiple threads with the same name for different purposes

            # Create thread model
            thread_data = request.model_dump()
            thread_data["created_by"] = user_id
            thread = ThreadModel(**thread_data)

            # Insert into database
            thread_dict = thread.model_dump_for_db()
            result = await self.threads_collection.insert_one(thread_dict)

            # Get the fresh thread from database to ensure proper ObjectId handling
            created_thread_data = await self.threads_collection.find_one(
                {"_id": result.inserted_id}
            )
            created_thread = ThreadModel.from_mongo(created_thread_data)

            logger.info(
                f"Created chat thread {result.inserted_id} in workspace {request.workspace_id}"
            )
            return created_thread

        except Exception as e:
            logger.error(f"Failed to create chat thread: {e}")
            raise

    async def get_thread(self, thread_id: str, workspace_id: str) -> ThreadModel | None:
        """Get a chat thread by ID."""
        try:
            # Validate ObjectId format
            try:
                object_id = ObjectId(thread_id)
            except InvalidId:
                raise ValueError("Invalid thread ID format")

            thread_data = await self.threads_collection.find_one(
                {
                    "_id": object_id,
                    "workspace_id": workspace_id,
                    "status": {"$ne": ThreadStatus.DELETED.value},
                }
            )

            if not thread_data:
                return None

            return ThreadModel.from_mongo(thread_data)

        except Exception as e:
            logger.error(f"Failed to get chat thread {thread_id}: {e}")
            raise

    async def list_threads(
        self,
        workspace_id: str,
        user_id: str,
        status_filter: ThreadStatus | None = None,
        search_query: str | None = None,
        limit: int = 50,
        skip: int = 0,
    ) -> tuple[list[ThreadModel], int]:
        """List chat threads with filtering and pagination."""
        try:
            # Build query
            query = {
                "workspace_id": workspace_id,
                "status": {"$ne": ThreadStatus.DELETED.value},
                "$or": [{"created_by": user_id}, {"shared_with": user_id}, {"is_public": True}],
            }

            if status_filter:
                query["status"] = status_filter.value

            if search_query:
                query["$or"] = [
                    {"name": {"$regex": search_query, "$options": "i"}},
                    {"description": {"$regex": search_query, "$options": "i"}},
                ]

            # Get total count
            total_count = await self.threads_collection.count_documents(query)

            # Get threads with pagination
            cursor = (
                self.threads_collection.find(query).sort("updated_at", -1).skip(skip).limit(limit)
            )

            threads = []
            async for thread_data in cursor:
                threads.append(ThreadModel.from_mongo(thread_data))

            return threads, total_count

        except Exception as e:
            logger.error(f"Failed to list chat threads: {e}")
            raise

    async def update_thread(
        self, thread_id: str, workspace_id: str, request: ThreadUpdateRequest, user_id: str
    ) -> ThreadModel | None:
        """Update a chat thread."""
        try:
            # Validate ObjectId format
            try:
                object_id = ObjectId(thread_id)
            except InvalidId:
                raise ValueError("Invalid thread ID format")

            # Check thread exists and user has access
            existing_thread = await self.threads_collection.find_one(
                {
                    "_id": object_id,
                    "workspace_id": workspace_id,
                    "status": {"$ne": ThreadStatus.DELETED.value},
                    "$or": [{"created_by": user_id}, {"shared_with": user_id}],
                }
            )

            if not existing_thread:
                return None

            # Build update data
            update_data = {}
            if request.name is not None:
                # Check for name conflicts
                if request.name != existing_thread["name"]:
                    name_conflict = await self.threads_collection.find_one(
                        {
                            "name": request.name,
                            "workspace_id": workspace_id,
                            "status": {"$ne": ThreadStatus.DELETED.value},
                            "_id": {"$ne": object_id},
                        }
                    )
                    if name_conflict:
                        raise ValueError(f"Thread with name '{request.name}' already exists")
                update_data["name"] = request.name

            if request.description is not None:
                update_data["description"] = request.description
            if request.system_instructions is not None:
                update_data["system_instructions"] = request.system_instructions
            if request.context_data is not None:
                update_data["context_data"] = request.context_data
            if request.status is not None:
                update_data["status"] = request.status.value
            if request.is_public is not None:
                update_data["is_public"] = request.is_public

            update_data["updated_at"] = datetime.utcnow()

            # Update thread
            result = await self.threads_collection.update_one(
                {"_id": object_id, "workspace_id": workspace_id}, {"$set": update_data}
            )

            if result.matched_count == 0:
                return None

            # Return updated thread
            updated_thread_data = await self.threads_collection.find_one({"_id": object_id})
            return ThreadModel.from_mongo(updated_thread_data)

        except Exception as e:
            logger.error(f"Failed to update chat thread {thread_id}: {e}")
            raise

    async def delete_thread(self, thread_id: str, workspace_id: str, user_id: str) -> bool:
        """Delete a chat thread (soft delete)."""
        try:
            # Validate ObjectId format
            try:
                object_id = ObjectId(thread_id)
            except InvalidId:
                raise ValueError("Invalid thread ID format")

            # Update thread status to deleted
            result = await self.threads_collection.update_one(
                {
                    "_id": object_id,
                    "workspace_id": workspace_id,
                    "created_by": user_id,  # Only creator can delete
                },
                {"$set": {"status": ThreadStatus.DELETED.value, "updated_at": datetime.utcnow()}},
            )

            return result.matched_count > 0

        except Exception as e:
            logger.error(f"Failed to delete chat thread {thread_id}: {e}")
            raise

    async def create_message(self, request: MessageCreateRequest, user_id: str) -> MessageModel:
        """Create a new message in a thread."""
        try:
            # Verify thread exists and user has access
            thread = await self.get_thread(request.thread_id, request.workspace_id)
            if not thread:
                raise ValueError("Thread not found or access denied")

            # Create message model
            message_data = request.model_dump()
            message_data["user_id"] = user_id
            message = MessageModel(**message_data)

            # Insert message
            message_dict = message.model_dump_for_db()
            result = await self.messages_collection.insert_one(message_dict)

            # Update thread statistics
            await self.threads_collection.update_one(
                {"_id": ObjectId(request.thread_id)},
                {
                    "$inc": {"message_count": 1},
                    "$set": {"last_message_at": datetime.utcnow(), "updated_at": datetime.utcnow()},
                },
            )

            # Get the fresh message from database to ensure proper ObjectId handling
            created_message_data = await self.messages_collection.find_one(
                {"_id": result.inserted_id}
            )
            created_message = MessageModel.from_mongo(created_message_data)

            logger.info(f"Created message {result.inserted_id} in thread {request.thread_id}")
            return created_message

        except Exception as e:
            logger.error(f"Failed to create message: {e}")
            raise

    async def get_thread_messages(
        self,
        thread_id: str,
        workspace_id: str,
        user_id: str,
        limit: int = 50,
        skip: int = 0,
        role_filter: MessageRole | None = None,
    ) -> tuple[list[MessageModel], int]:
        """Get messages for a thread with pagination."""
        try:
            # Verify thread access
            thread = await self.get_thread(thread_id, workspace_id)
            if not thread:
                raise ValueError("Thread not found or access denied")

            # Build query
            query = {"thread_id": thread_id, "workspace_id": workspace_id}

            if role_filter:
                query["role"] = role_filter.value

            # Get total count
            total_count = await self.messages_collection.count_documents(query)

            # Get messages with pagination (oldest first for chat display)
            cursor = (
                self.messages_collection.find(query).sort("created_at", 1).skip(skip).limit(limit)
            )

            messages = []
            async for message_data in cursor:
                messages.append(MessageModel.from_mongo(message_data))

            return messages, total_count

        except Exception as e:
            logger.error(f"Failed to get thread messages: {e}")
            raise

    async def search_messages(
        self,
        workspace_id: str,
        user_id: str,
        search_query: str,
        thread_id: str | None = None,
        limit: int = 50,
        skip: int = 0,
    ) -> tuple[list[MessageModel], int]:
        """Search messages across threads or within a specific thread."""
        try:
            # Build base query
            query = {
                "workspace_id": workspace_id,
                "content": {"$regex": search_query, "$options": "i"},
            }

            # Filter by thread if specified
            if thread_id:
                # Verify thread access
                thread = await self.get_thread(thread_id, workspace_id)
                if not thread:
                    raise ValueError("Thread not found or access denied")
                query["thread_id"] = thread_id
            else:
                # Get accessible thread IDs
                accessible_threads = await self.threads_collection.find(
                    {
                        "workspace_id": workspace_id,
                        "status": {"$ne": ThreadStatus.DELETED.value},
                        "$or": [
                            {"created_by": user_id},
                            {"shared_with": user_id},
                            {"is_public": True},
                        ],
                    },
                    {"_id": 1},
                ).to_list(None)

                thread_ids = [str(thread["_id"]) for thread in accessible_threads]
                query["thread_id"] = {"$in": thread_ids}

            # Get total count
            total_count = await self.messages_collection.count_documents(query)

            # Get messages with pagination (most recent first for search results)
            cursor = (
                self.messages_collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
            )

            messages = []
            async for message_data in cursor:
                messages.append(MessageModel.from_mongo(message_data))

            return messages, total_count

        except Exception as e:
            logger.error(f"Failed to search messages: {e}")
            raise

    async def get_chat_summary(self, workspace_id: str, user_id: str) -> ChatSummary:
        """Get chat usage summary for a workspace."""
        try:
            # Get accessible thread IDs
            accessible_threads = await self.threads_collection.find(
                {
                    "workspace_id": workspace_id,
                    "status": {"$ne": ThreadStatus.DELETED.value},
                    "$or": [{"created_by": user_id}, {"shared_with": user_id}, {"is_public": True}],
                },
                {"_id": 1},
            ).to_list(None)

            thread_ids = [str(thread["_id"]) for thread in accessible_threads]

            # Count threads
            total_threads = len(accessible_threads)
            active_threads = await self.threads_collection.count_documents(
                {
                    "workspace_id": workspace_id,
                    "status": ThreadStatus.ACTIVE.value,
                    "$or": [{"created_by": user_id}, {"shared_with": user_id}, {"is_public": True}],
                }
            )

            # Get message statistics
            message_stats_pipeline = [
                {"$match": {"workspace_id": workspace_id, "thread_id": {"$in": thread_ids}}},
                {
                    "$group": {
                        "_id": None,
                        "total_messages": {"$sum": 1},
                        "by_role": {"$push": "$role"},
                        "tool_calls_count": {
                            "$sum": {
                                "$cond": [
                                    {"$ne": ["$tool_calls", None]},
                                    {"$size": {"$ifNull": ["$tool_calls", []]}},
                                    0,
                                ]
                            }
                        },
                    }
                },
            ]

            stats_result = await self.messages_collection.aggregate(message_stats_pipeline).to_list(
                1
            )

            if stats_result:
                stats = stats_result[0]

                # Count messages by role
                role_counts = {}
                for role in stats["by_role"]:
                    role_counts[role] = role_counts.get(role, 0) + 1

                return ChatSummary(
                    total_threads=total_threads,
                    active_threads=active_threads,
                    total_messages=stats["total_messages"],
                    by_role=role_counts,
                    tool_calls_count=stats["tool_calls_count"],
                )
            return ChatSummary(
                total_threads=total_threads,
                active_threads=active_threads,
                total_messages=0,
                by_role={},
                tool_calls_count=0,
            )

        except Exception as e:
            logger.error(f"Failed to get chat summary: {e}")
            raise

    async def share_thread(
        self, thread_id: str, workspace_id: str, owner_user_id: str, shared_with_user_ids: list[str]
    ) -> bool:
        """Share a thread with other users."""
        try:
            # Validate ObjectId format
            try:
                object_id = ObjectId(thread_id)
            except InvalidId:
                raise ValueError("Invalid thread ID format")

            # Update thread sharing
            result = await self.threads_collection.update_one(
                {
                    "_id": object_id,
                    "workspace_id": workspace_id,
                    "created_by": owner_user_id,  # Only owner can share
                },
                {"$set": {"shared_with": shared_with_user_ids, "updated_at": datetime.utcnow()}},
            )

            return result.matched_count > 0

        except Exception as e:
            logger.error(f"Failed to share thread {thread_id}: {e}")
            raise
