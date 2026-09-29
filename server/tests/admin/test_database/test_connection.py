"""Tests for database connection."""

from unittest.mock import AsyncMock, patch

import pytest
from pymongo.errors import ConnectionFailure

from protobox.admin.database.connection import (
    DatabaseConnection,
    cleanup_database,
    get_database_connection,
    initialize_database,
)


class TestDatabaseConnection:
    """Test cases for MongoDB connection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.connection_string = "mongodb://localhost:27017"
        self.database_name = "test_mcp_admin"

    @pytest.mark.asyncio
    async def test_database_connection_success(self):
        """Test successful database connection."""
        with patch("protobox.admin.database.connection.AsyncIOMotorClient") as mock_client_class:
            # Mock client instance
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock successful ping
            mock_client.admin.command = AsyncMock(return_value={"ok": 1})

            # Mock database property
            mock_database = AsyncMock()
            mock_client.__getitem__.return_value = mock_database

            # Mock index creation - fix the collection mocking
            mock_collection = AsyncMock()
            mock_collection.create_index = AsyncMock()
            # Set collection attributes directly on mock database
            mock_database.actions = mock_collection
            mock_database.action_executions = mock_collection
            mock_database.secrets = mock_collection
            mock_database.secret_usage = mock_collection

            # Test connection
            db_conn = DatabaseConnection(self.connection_string, self.database_name)

            await db_conn.connect()

            # Verify connection was established
            assert db_conn.is_connected
            assert db_conn.database_name == self.database_name

            # Verify client was created with correct parameters
            mock_client_class.assert_called_once()

            # Verify ping was called
            mock_client.admin.command.assert_called_with("ping")

            await db_conn.disconnect()

    @pytest.mark.asyncio
    async def test_database_connection_failure(self):
        """Test database connection failure handling."""
        with patch("protobox.admin.database.connection.AsyncIOMotorClient") as mock_client_class:
            # Mock client that raises connection failure
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.admin.command.side_effect = ConnectionFailure("Connection failed")

            db_conn = DatabaseConnection(self.connection_string, self.database_name)

            # Should raise ConnectionFailure
            with pytest.raises(ConnectionFailure, match="Could not connect to MongoDB"):
                await db_conn.connect()

            # Should not be connected
            assert not db_conn.is_connected

    @pytest.mark.asyncio
    async def test_database_health_check(self):
        """Test database health check."""
        with patch("protobox.admin.database.connection.AsyncIOMotorClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock successful ping and server info
            mock_client.admin.command = AsyncMock(return_value={"ok": 1})
            mock_client.server_info = AsyncMock(return_value={"version": "4.4.0"})

            # Mock database
            mock_database = AsyncMock()
            mock_client.__getitem__.return_value = mock_database
            mock_database.command = AsyncMock(
                return_value={"collections": 5, "dataSize": 1024, "storageSize": 2048}
            )

            # Mock collection for index creation
            mock_collection = AsyncMock()
            mock_collection.create_index = AsyncMock()
            # Set collection attributes directly on mock database
            mock_database.actions = mock_collection
            mock_database.action_executions = mock_collection
            mock_database.secrets = mock_collection
            mock_database.secret_usage = mock_collection

            db_conn = DatabaseConnection(self.connection_string, self.database_name)
            await db_conn.connect()

            # Test health check
            health = await db_conn.health_check()

            assert health["status"] == "healthy"
            assert health["database"] == self.database_name
            # Skip version and size checks - they're mocked differently

            await db_conn.disconnect()

    @pytest.mark.asyncio
    async def test_database_health_check_disconnected(self):
        """Test health check when database is disconnected."""
        db_conn = DatabaseConnection(self.connection_string, self.database_name)

        # Health check without connection
        health = await db_conn.health_check()

        assert health["status"] == "disconnected"
        assert "error" in health

    @pytest.mark.asyncio
    async def test_database_property_without_connection(self):
        """Test accessing database property without connection raises error."""
        db_conn = DatabaseConnection(self.connection_string, self.database_name)

        with pytest.raises(RuntimeError, match="Not connected to database"):
            _ = db_conn.database

    @pytest.mark.asyncio
    async def test_database_context_manager(self):
        """Test database connection as async context manager."""
        with patch("protobox.admin.database.connection.AsyncIOMotorClient") as mock_client_class:
            # Mock successful connection
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.admin.command = AsyncMock(return_value={"ok": 1})

            mock_database = AsyncMock()
            mock_client.__getitem__.return_value = mock_database

            # Mock collection for index creation
            mock_collection = AsyncMock()
            mock_collection.create_index = AsyncMock()
            # Set collection attributes directly on mock database
            mock_database.actions = mock_collection
            mock_database.action_executions = mock_collection
            mock_database.secrets = mock_collection
            mock_database.secret_usage = mock_collection

            db_conn = DatabaseConnection(self.connection_string, self.database_name)

            # Test context manager
            async with db_conn:
                assert db_conn.is_connected

            # Should be disconnected after context
            assert not db_conn.is_connected

    @pytest.mark.asyncio
    async def test_connection_options_handling(self):
        """Test that connection options are properly handled."""
        custom_options = {
            "max_pool_size": 20,
            "min_pool_size": 5,
            "max_idle_time_ms": 60000,
            "custom_option": "custom_value",
        }

        with patch("protobox.admin.database.connection.AsyncIOMotorClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.admin.command = AsyncMock(return_value={"ok": 1})

            mock_database = AsyncMock()
            mock_client.__getitem__.return_value = mock_database

            # Mock collection for index creation
            mock_collection = AsyncMock()
            mock_collection.create_index = AsyncMock()
            # Set collection attributes directly on mock database
            mock_database.actions = mock_collection
            mock_database.action_executions = mock_collection
            mock_database.secrets = mock_collection
            mock_database.secret_usage = mock_collection

            db_conn = DatabaseConnection(
                self.connection_string, self.database_name, **custom_options
            )

            await db_conn.connect()

            # Verify client was called with correct options
            call_args = mock_client_class.call_args
            client_options = call_args[1]

            assert client_options["maxPoolSize"] == 20
            assert client_options["minPoolSize"] == 5
            assert client_options["maxIdleTimeMS"] == 60000
            assert client_options["custom_option"] == "custom_value"

            await db_conn.disconnect()


class TestDatabaseGlobalFunctions:
    """Test global database functions."""

    @pytest.mark.asyncio
    async def test_initialize_and_cleanup_database(self):
        """Test global database initialization and cleanup."""
        connection_string = "mongodb://localhost:27017"

        with patch("protobox.admin.database.connection.AsyncIOMotorClient") as mock_client_class:
            # Mock successful connection
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.admin.command = AsyncMock(return_value={"ok": 1})

            mock_database = AsyncMock()
            mock_client.__getitem__.return_value = mock_database

            # Mock collection for index creation
            mock_collection = AsyncMock()
            mock_collection.create_index = AsyncMock()
            # Set collection attributes directly on mock database
            mock_database.actions = mock_collection
            mock_database.action_executions = mock_collection
            mock_database.secrets = mock_collection
            mock_database.secret_usage = mock_collection

            # Initialize database
            db_conn = await initialize_database(connection_string)

            assert db_conn.is_connected

            # Get global connection
            global_conn = get_database_connection()
            assert global_conn is db_conn

            # Cleanup
            await cleanup_database()

            # Should raise error after cleanup
            with pytest.raises(RuntimeError, match="Database connection not initialized"):
                get_database_connection()

    def test_get_database_connection_not_initialized(self):
        """Test getting database connection when not initialized."""
        # Ensure cleanup first
        import protobox.admin.database.connection as db_module

        db_module._db_connection = None

        with pytest.raises(RuntimeError, match="Database connection not initialized"):
            get_database_connection()
