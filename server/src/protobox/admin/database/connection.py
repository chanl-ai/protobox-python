"""MongoDB connection management with Motor async driver."""

from typing import Any

from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError


class DatabaseConnection:
    """MongoDB connection manager using Motor async driver."""

    def __init__(self, connection_string: str, database_name: str = "mcp_admin", **kwargs):
        """Initialize database connection.

        Args:
            connection_string: MongoDB connection string
            database_name: Name of the database to use
            **kwargs: Additional MongoDB client options
        """
        self.connection_string = connection_string
        self.database_name = database_name
        self.client_options = {
            "maxPoolSize": kwargs.get("max_pool_size", 10),
            "minPoolSize": kwargs.get("min_pool_size", 1),
            "maxIdleTimeMS": kwargs.get("max_idle_time_ms", 30000),
            "serverSelectionTimeoutMS": kwargs.get("server_selection_timeout_ms", 5000),
            "connectTimeoutMS": kwargs.get("connect_timeout_ms", 10000),
            "retryWrites": kwargs.get("retry_writes", True),
            **{
                k: v
                for k, v in kwargs.items()
                if k
                not in [
                    "max_pool_size",
                    "min_pool_size",
                    "max_idle_time_ms",
                    "server_selection_timeout_ms",
                    "connect_timeout_ms",
                    "retry_writes",
                ]
            },
        }

        self._client: AsyncIOMotorClient | None = None
        self._database: AsyncIOMotorDatabase | None = None
        self._is_connected = False

    async def connect(self) -> None:
        """Establish connection to MongoDB.

        Raises:
            ConnectionFailure: If connection cannot be established
        """
        try:
            logger.info(f"Connecting to MongoDB database: {self.database_name}")

            self._client = AsyncIOMotorClient(self.connection_string, **self.client_options)

            # Test the connection
            await self._client.admin.command("ping")

            self._database = self._client[self.database_name]
            self._is_connected = True

            logger.info("MongoDB connection established successfully")

            # Create indexes for better performance (can be disabled via environment variable)
            import os

            if os.getenv("MCP_SKIP_INDEX_CREATION", "false").lower() not in ("true", "1", "yes"):
                await self._create_indexes()
            else:
                logger.info("Index creation skipped (MCP_SKIP_INDEX_CREATION=true)")

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise ConnectionFailure(f"Could not connect to MongoDB: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during MongoDB connection: {e}")
            raise

    async def disconnect(self) -> None:
        """Close the database connection."""
        if self._client:
            logger.info("Closing MongoDB connection")
            self._client.close()
            self._client = None
            self._database = None
            self._is_connected = False

    async def health_check(self) -> dict[str, Any]:
        """Check database health and return status information.

        Returns:
            Dictionary with health status and metadata
        """
        if not self._is_connected or not self._client:
            return {"status": "disconnected", "error": "No active database connection"}

        try:
            # Simple ping to check connection
            await self._client.admin.command("ping")

            # Try a simple read operation instead of dbStats
            # Count documents in a collection (should work with read permissions)
            collections_count = 0
            try:
                collections = await self._database.list_collection_names()
                collections_count = len(collections)
            except Exception:
                # If we can't list collections, just skip it
                pass

            return {
                "status": "healthy",
                "database": self.database_name,
                "collections": collections_count,
                "connection": "active",
            }

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    @property
    def database(self) -> AsyncIOMotorDatabase:
        """Get the database instance.

        Returns:
            AsyncIOMotorDatabase instance

        Raises:
            RuntimeError: If not connected to database
        """
        if not self._is_connected or self._database is None:
            raise RuntimeError("Not connected to database. Call connect() first.")

        return self._database

    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._is_connected and self._client is not None

    async def _create_indexes(self) -> None:
        """Create database indexes for better performance.

        This method gracefully handles authentication and permission errors,
        as index creation is optional for basic functionality.
        """
        try:
            logger.debug("Attempting to create database indexes...")

            # Actions collection indexes
            actions_collection = self._database.actions
            await self._create_collection_indexes(
                actions_collection,
                "actions",
                [
                    "workspace_id",
                    "type",
                    "created_by",
                    "created_at",
                    # Compound unique index: same name allowed across workspaces
                    # but unique within a workspace
                    ([("workspace_id", 1), ("name", 1)], {"unique": True}),
                ],
            )

            # Action executions collection indexes
            executions_collection = self._database.action_executions
            await self._create_collection_indexes(
                executions_collection,
                "action_executions",
                ["action_id", "executed_at", "status", "user_id"],
            )

            # Secrets collection indexes
            secrets_collection = self._database.secrets
            await self._create_collection_indexes(
                secrets_collection,
                "secrets",
                [
                    "type",
                    "workspace_id",
                    "created_by",
                    ([("name", 1), ("workspace_id", 1)], {"unique": True}),
                ],
            )

            # Secret usage audit collection indexes
            secret_usage_collection = self._database.secret_usage
            await self._create_collection_indexes(
                secret_usage_collection,
                "secret_usage",
                ["secret_id", "action_id", "used_at", "workspace_id"],
            )

            # Knowledge base collections indexes
            knowledge_documents_collection = self._database.knowledge_documents
            await self._create_collection_indexes(
                knowledge_documents_collection,
                "knowledge_documents",
                [
                    "workspace_id",
                    "source_type",
                    "processing_status",
                    "created_at",
                    "author_id",
                    # Text search on title and description
                    ([("title", "text"), ("description", "text")], {"default_language": "english"}),
                ],
            )

            # Knowledge chunks collection indexes (for text search)
            knowledge_chunks_collection = self._database.knowledge_chunks
            await self._create_collection_indexes(
                knowledge_chunks_collection,
                "knowledge_chunks",
                [
                    "document_id",
                    "chunk_index",
                    "chunk_type",
                    "created_at",
                    # Text search on content - this is the critical one for search functionality
                    ([("content", "text")], {"default_language": "english"}),
                ],
            )

            # Create vector index for knowledge chunks (required for semantic search)
            try:
                knowledge_chunks_vector_collection = self._database.knowledge_chunks_vector
                await knowledge_chunks_vector_collection.create_index(
                    [("embedding", 1)],
                    name="vector_index",
                    vectorSearch={
                        "dimensions": 1536,  # OpenAI text-embedding-3-small dimensions
                        "similarity": "cosine"
                    }
                )
                logger.info("Vector index created successfully for semantic search")
            except Exception as vector_error:
                logger.warning(f"Failed to create vector index: {vector_error}")
                # Continue - semantic search will fall back to keyword search

            logger.info("Database indexes created successfully")

        except Exception as e:
            # Check for authentication/permission errors and handle gracefully
            error_msg = str(e).lower()
            if any(
                keyword in error_msg
                for keyword in ["authentication", "unauthorized", "not allowed", "permission"]
            ):
                logger.info(
                    "Index creation skipped due to insufficient permissions (this is normal for managed databases)"
                )
            else:
                logger.warning(f"Failed to create some indexes: {e}")

    async def _create_collection_indexes(
        self, collection, collection_name: str, indexes: list
    ) -> None:
        """Create indexes for a specific collection with error handling."""
        for index_spec in indexes:
            try:
                if isinstance(index_spec, tuple):
                    # Complex index with options
                    index_keys, options = index_spec
                    await collection.create_index(index_keys, **options)
                else:
                    # Simple index
                    await collection.create_index(index_spec)
            except Exception as e:
                error_msg = str(e).lower()
                if any(
                    keyword in error_msg
                    for keyword in ["authentication", "unauthorized", "not allowed", "permission"]
                ):
                    logger.debug(
                        f"Skipping index creation for {collection_name} due to permissions"
                    )
                    break  # Skip remaining indexes for this collection
                logger.warning(f"Failed to create index {index_spec} on {collection_name}: {e}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


# Global database connection instance
_db_connection: DatabaseConnection | None = None


def get_database_connection() -> DatabaseConnection:
    """Get the global database connection instance.

    Returns:
        DatabaseConnection instance

    Raises:
        RuntimeError: If database connection is not initialized
    """
    global _db_connection
    if _db_connection is None:
        raise RuntimeError(
            "Database connection not initialized. " "Call initialize_database() first."
        )
    return _db_connection


async def initialize_database(
    connection_string: str, database_name: str = "mcp_admin", **kwargs
) -> DatabaseConnection:
    """Initialize the global database connection.

    Args:
        connection_string: MongoDB connection string
        database_name: Name of the database to use
        **kwargs: Additional MongoDB client options

    Returns:
        DatabaseConnection instance
    """
    global _db_connection

    _db_connection = DatabaseConnection(
        connection_string=connection_string, database_name=database_name, **kwargs
    )

    await _db_connection.connect()
    return _db_connection


async def cleanup_database() -> None:
    """Cleanup the global database connection."""
    global _db_connection
    if _db_connection:
        await _db_connection.disconnect()
        _db_connection = None
