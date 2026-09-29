"""Simple unit tests for ChatService - properly structured for pytest."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest
from bson import ObjectId

from protobox.admin.models.chat import (
    ThreadCreateRequest,
    ThreadModel,
    ThreadStatus,
)
from protobox.admin.services.chat_service import ChatService


@pytest.fixture
def mock_db():
    """Create a mock database with collections."""
    mock_db = Mock()
    mock_threads_collection = AsyncMock()
    mock_messages_collection = AsyncMock()

    # Mock the database to return specific collections
    mock_database = Mock()
    mock_database.chat_threads = mock_threads_collection
    mock_database.chat_messages = mock_messages_collection
    mock_db.database = mock_database

    return mock_db, mock_threads_collection, mock_messages_collection


@pytest.fixture
def chat_service(mock_db):
    """Create a chat service with mocked database."""
    db, _, _ = mock_db
    return ChatService(db)


@pytest.mark.asyncio
async def test_create_thread(chat_service, mock_db):
    """Test creating a new chat thread."""
    _, threads_collection, _ = mock_db
    workspace_id = "test_workspace"
    user_id = "test_user"

    # Mock no existing thread
    inserted_id = ObjectId()

    # Mock insert result
    mock_result = Mock()
    mock_result.inserted_id = inserted_id
    threads_collection.insert_one = AsyncMock(return_value=mock_result)

    # Mock the two find_one calls:
    # 1. First call checks for existing thread (returns None)
    # 2. Second call gets the created thread
    created_thread_data = {
        "_id": inserted_id,
        "workspace_id": workspace_id,
        "name": "Test Thread",
        "description": "Test Description",
        "status": ThreadStatus.ACTIVE.value,
        "created_by": user_id,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    threads_collection.find_one = AsyncMock(side_effect=[None, created_thread_data])

    # Create request
    thread_request = ThreadCreateRequest(
        workspace_id=workspace_id, name="Test Thread", description="Test Description"
    )

    # Call service
    result = await chat_service.create_thread(thread_request, user_id)

    # Verify result
    assert isinstance(result, ThreadModel)
    assert result.name == "Test Thread"
    assert result.workspace_id == workspace_id
    assert result.created_by == user_id

    # Verify database calls
    assert (
        threads_collection.find_one.call_count == 2
    )  # Once for duplicate check, once after insert
    threads_collection.insert_one.assert_called_once()


@pytest.mark.asyncio
async def test_create_thread_duplicate_name(chat_service, mock_db):
    """Test creating a thread with duplicate name fails."""
    _, threads_collection, _ = mock_db
    workspace_id = "test_workspace"
    user_id = "test_user"

    # Mock existing thread with same name
    threads_collection.find_one = AsyncMock(
        return_value={"_id": ObjectId(), "name": "Test Thread", "workspace_id": workspace_id}
    )

    # Create request
    thread_request = ThreadCreateRequest(
        workspace_id=workspace_id, name="Test Thread", description="Test Description"
    )

    # Call service - should raise ValueError
    with pytest.raises(ValueError) as exc_info:
        await chat_service.create_thread(thread_request, user_id)

    assert "already exists" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_thread(chat_service, mock_db):
    """Test getting a thread by ID."""
    _, threads_collection, _ = mock_db
    thread_id = str(ObjectId())
    workspace_id = "test_workspace"

    # Mock find result
    mock_doc = {
        "_id": ObjectId(thread_id),
        "workspace_id": workspace_id,
        "name": "Test Thread",
        "status": ThreadStatus.ACTIVE.value,
        "created_by": "test_user",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    threads_collection.find_one = AsyncMock(return_value=mock_doc)

    # Call service
    result = await chat_service.get_thread(thread_id, workspace_id)

    # Verify result
    assert isinstance(result, ThreadModel)
    assert result.id == thread_id
    assert result.name == "Test Thread"

    # Verify database call
    threads_collection.find_one.assert_called_once()


@pytest.mark.asyncio
async def test_get_thread_not_found(chat_service, mock_db):
    """Test getting a non-existent thread returns None."""
    _, threads_collection, _ = mock_db
    thread_id = str(ObjectId())
    workspace_id = "test_workspace"

    # Mock no result
    threads_collection.find_one = AsyncMock(return_value=None)

    # Call service
    result = await chat_service.get_thread(thread_id, workspace_id)

    # Verify result
    assert result is None
