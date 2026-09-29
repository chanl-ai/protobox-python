"""Chat router with thread and message management endpoints."""

import json
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from loguru import logger

from ..auth.dependencies import require_authentication
from ..auth.models import User
from ..dependencies import (
    AssistantServiceDep,
    ChatServiceDep,
)
from ..models.chat import (
    MessageCreateRequest,
    MessageRole,
    ThreadCreateRequest,
    ThreadStatus,
    ThreadUpdateRequest,
)

router = APIRouter(prefix="/workspaces/{workspace_id}/chat", tags=["Chat"])


# Thread Management Endpoints


@router.get("/threads", response_model=dict[str, Any])
async def list_threads(
    workspace_id: str,
    chat_service: ChatServiceDep,
    status_filter: ThreadStatus | None = Query(None, description="Filter by thread status"),
    search_query: str | None = Query(None, description="Search threads by name or description"),
    limit: int = Query(50, ge=1, le=100, description="Number of threads to return"),
    skip: int = Query(0, ge=0, description="Number of threads to skip"),
    current_user: User = Depends(require_authentication),
) -> dict[str, Any]:
    """List chat threads with filtering and pagination."""
    try:
        logger.info(f"Listing threads for workspace {workspace_id}, user {current_user.id}")

        threads, total_count = await chat_service.list_threads(
            workspace_id=workspace_id,
            user_id=current_user.id,
            status_filter=status_filter,
            search_query=search_query,
            limit=limit,
            skip=skip,
        )

        # Convert threads to dict format
        thread_dicts = []
        for thread in threads:
            thread_dict = thread.model_dump(mode="json")
            thread_dicts.append(thread_dict)

        # Calculate pagination info
        has_more = skip + len(threads) < total_count

        return {
            "threads": thread_dicts,
            "pagination": {
                "total": total_count,
                "skip": skip,
                "limit": limit,
                "has_more": has_more,
            },
        }

    except Exception as e:
        logger.error(f"Failed to list threads: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list threads"
        )


@router.post("/threads", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_thread(
    workspace_id: str,
    thread_request_data: dict[str, Any],
    chat_service: ChatServiceDep,
    current_user: User = Depends(require_authentication),
) -> dict[str, Any]:
    """Create a new chat thread."""
    try:
        logger.info(f"Creating thread in workspace {workspace_id}: {thread_request_data}")

        # Add workspace_id to request data
        thread_request_data["workspace_id"] = workspace_id

        # Validate the request
        thread_request = ThreadCreateRequest(**thread_request_data)

        thread = await chat_service.create_thread(thread_request, current_user.id)

        logger.info(f"Created thread {thread.id} in workspace {workspace_id}")
        return thread.model_dump(mode="json")

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create thread: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create thread"
        )


@router.get("/threads/{thread_id}", response_model=dict[str, Any])
async def get_thread(
    workspace_id: str,
    thread_id: str,
    chat_service: ChatServiceDep,
    current_user: User = Depends(require_authentication),
) -> dict[str, Any]:
    """Get a chat thread by ID."""
    try:
        thread = await chat_service.get_thread(thread_id, workspace_id)

        if not thread:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

        return thread.model_dump(mode="json")

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get thread {thread_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get thread"
        )


@router.put("/threads/{thread_id}", response_model=dict[str, Any])
async def update_thread(
    workspace_id: str,
    thread_id: str,
    thread_update: ThreadUpdateRequest,
    chat_service: ChatServiceDep,
    current_user: User = Depends(require_authentication),
) -> dict[str, Any]:
    """Update a chat thread."""
    try:
        updated_thread = await chat_service.update_thread(
            thread_id, workspace_id, thread_update, current_user.id
        )

        if not updated_thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found or access denied"
            )

        logger.info(f"Updated thread {thread_id} in workspace {workspace_id}")
        return updated_thread.model_dump(mode="json")

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update thread {thread_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update thread"
        )


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread(
    workspace_id: str,
    thread_id: str,
    chat_service: ChatServiceDep,
    current_user: User = Depends(require_authentication),
) -> None:
    """Delete a chat thread (soft delete)."""
    try:
        success = await chat_service.delete_thread(thread_id, workspace_id, current_user.id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found or access denied"
            )

        logger.info(f"Deleted thread {thread_id} from workspace {workspace_id}")

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete thread {thread_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete thread"
        )


# Message Management Endpoints


@router.get("/threads/{thread_id}/messages", response_model=dict[str, Any])
async def get_thread_messages(
    workspace_id: str,
    thread_id: str,
    chat_service: ChatServiceDep,
    limit: int = Query(50, ge=1, le=100, description="Number of messages to return"),
    skip: int = Query(0, ge=0, description="Number of messages to skip"),
    role_filter: MessageRole | None = Query(None, description="Filter by message role"),
    current_user: User = Depends(require_authentication),
) -> dict[str, Any]:
    """Get messages for a thread with pagination."""
    try:
        messages, total_count = await chat_service.get_thread_messages(
            thread_id=thread_id,
            workspace_id=workspace_id,
            user_id=current_user.id,
            limit=limit,
            skip=skip,
            role_filter=role_filter,
        )

        # Convert messages to dict format
        message_dicts = []
        for message in messages:
            message_dict = message.model_dump(mode="json")
            message_dicts.append(message_dict)

        # Calculate pagination info
        has_more = skip + len(messages) < total_count

        return {
            "messages": message_dicts,
            "pagination": {
                "total": total_count,
                "skip": skip,
                "limit": limit,
                "has_more": has_more,
            },
        }

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get thread messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get thread messages",
        )


@router.post(
    "/threads/{thread_id}/messages",
    response_model=dict[str, Any],
    status_code=status.HTTP_201_CREATED,
)
async def create_message(
    workspace_id: str,
    thread_id: str,
    chat_service: ChatServiceDep,
    message_request_data: dict[str, Any] = Body(...),
    current_user: User = Depends(require_authentication),
) -> dict[str, Any]:
    """Create a new message in a thread."""
    try:
        # Add workspace_id and thread_id to request data
        message_request_data["workspace_id"] = workspace_id
        message_request_data["thread_id"] = thread_id

        # Validate the request
        message_request = MessageCreateRequest(**message_request_data)

        message = await chat_service.create_message(message_request, current_user.id)

        logger.info(f"Created message {message.id} in thread {thread_id}")
        return message.model_dump(mode="json")

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create message"
        )


# Search and Analytics Endpoints


@router.get("/search/messages", response_model=dict[str, Any])
async def search_messages(
    workspace_id: str,
    chat_service: ChatServiceDep,
    search_query: str = Query(..., description="Search query"),
    thread_id: str | None = Query(None, description="Search within specific thread"),
    limit: int = Query(50, ge=1, le=100, description="Number of messages to return"),
    skip: int = Query(0, ge=0, description="Number of messages to skip"),
    current_user: User = Depends(require_authentication),
) -> dict[str, Any]:
    """Search messages across threads or within a specific thread."""
    try:
        messages, total_count = await chat_service.search_messages(
            workspace_id=workspace_id,
            user_id=current_user.id,
            search_query=search_query,
            thread_id=thread_id,
            limit=limit,
            skip=skip,
        )

        # Convert messages to dict format
        message_dicts = []
        for message in messages:
            message_dict = message.model_dump(mode="json")
            message_dicts.append(message_dict)

        # Calculate pagination info
        has_more = skip + len(messages) < total_count

        return {
            "messages": message_dicts,
            "pagination": {
                "total": total_count,
                "skip": skip,
                "limit": limit,
                "has_more": has_more,
            },
            "search": {"query": search_query, "thread_id": thread_id},
        }

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to search messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to search messages"
        )


@router.get("/summary", response_model=dict[str, Any])
async def get_chat_summary(
    workspace_id: str,
    chat_service: ChatServiceDep,
    current_user: User = Depends(require_authentication),
) -> dict[str, Any]:
    """Get chat usage summary for the workspace."""
    try:
        summary = await chat_service.get_chat_summary(workspace_id, current_user.id)
        return summary.model_dump(mode="json")

    except Exception as e:
        logger.error(f"Failed to get chat summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get chat summary"
        )


# Thread Sharing Endpoints


@router.post("/threads/{thread_id}/share", response_model=dict[str, Any])
async def share_thread(
    workspace_id: str,
    thread_id: str,
    share_request: dict[str, list[str]],
    chat_service: ChatServiceDep,
    current_user: User = Depends(require_authentication),
) -> dict[str, Any]:
    """Share a thread with other users."""
    try:
        shared_with_user_ids = share_request.get("user_ids", [])

        if not shared_with_user_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="user_ids list is required"
            )

        success = await chat_service.share_thread(
            thread_id, workspace_id, current_user.id, shared_with_user_ids
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found or access denied"
            )

        logger.info(f"Shared thread {thread_id} with users {shared_with_user_ids}")
        return {"success": True, "thread_id": thread_id, "shared_with": shared_with_user_ids}

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to share thread {thread_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to share thread"
        )


# MCP-Enabled Chat Endpoints


@router.post("/threads/{thread_id}/chat", response_model=None)
async def chat_with_assistant(
    workspace_id: str,
    thread_id: str,
    chat_service: ChatServiceDep,
    assistant_service: AssistantServiceDep,
    message_request_data: dict[str, Any] = Body(...),
    stream: bool = Query(default=True, description="Stream response via SSE (true) or return complete response (false)"),
    current_user: User = Depends(require_authentication),
):
    """Send a message and get AI response using assistant service.
    
    Args:
        stream: If True (default), streams response via SSE. If False, waits for complete response and returns JSON.
    """

    logger.info(f"Chat request received - workspace: {workspace_id}, thread: {thread_id}, user: {current_user.id}, stream: {stream}")
    logger.debug(f"Message data: {message_request_data}")

    # If not streaming, collect full response and return as JSON
    if not stream:
        return await chat_with_assistant_sync(
            workspace_id=workspace_id,
            thread_id=thread_id,
            message_request_data=message_request_data,
            current_user=current_user,
            chat_service=chat_service,
            assistant_service=assistant_service
        )

    async def generate_response():
        try:
            logger.info("Starting chat response generation")

            # Validate thread exists and user has access
            logger.debug(f"Validating thread {thread_id} in workspace {workspace_id}")
            thread = await chat_service.get_thread(thread_id, workspace_id)
            if not thread:
                logger.error(f"Thread {thread_id} not found in workspace {workspace_id}")
                yield f"data: {json.dumps({'type': 'error', 'data': {'error': 'Thread not found'}})}\n\n"
                return

            logger.info(f"Thread validated: {thread.name}")

            # Create user message
            user_message_data = {
                "workspace_id": workspace_id,
                "thread_id": thread_id,
                "role": MessageRole.USER.value,
                "content": message_request_data.get("content", ""),
            }

            logger.debug(f"Creating user message: {user_message_data}")
            user_message_request = MessageCreateRequest(**user_message_data)
            # Pass user_id string, not the full User object
            user_message = await chat_service.create_message(
                user_message_request, current_user.id
            )
            logger.info(f"User message created with ID: {user_message.id}")

            # Yield user message
            yield f"data: {json.dumps({'type': 'user_message', 'data': user_message.model_dump(mode='json')})}\n\n"

            # Get or create assistant
            # Check if assistant_id is provided in the request or thread context
            assistant_id = message_request_data.get("assistant_id") or thread.context_data.get(
                "assistant_id"
            )

            if assistant_id:
                logger.info(f"Using existing assistant: {assistant_id}")
                assistant = await assistant_service.get_assistant(workspace_id, assistant_id)
                if not assistant:
                    logger.error(f"Assistant {assistant_id} not found in workspace {workspace_id}")
                    yield f"data: {json.dumps({'type': 'error', 'data': {'error': 'Assistant not found'}})}\n\n"
                    return
            else:
                logger.info("Creating new assistant for this thread")
                # Create a new assistant for this thread
                from ..models.assistant import AssistantCreateRequest

                assistant_request = AssistantCreateRequest(
                    name=thread.context_data.get("assistant_name", "ProtoBox Assistant"),
                    instructions=thread.system_instructions
                    or "You are a helpful assistant. Answer questions accurately and concisely.",
                    model=thread.context_data.get("assistant_model", "gpt-4-turbo-preview"),
                    enable_mcp_tools=True,
                    metadata={"chat_thread_id": thread_id},
                )

                logger.debug(f"Assistant creation request: {assistant_request}")
                assistant = await assistant_service.create_assistant(
                    workspace_id, current_user.id, assistant_request
                )
                logger.info(f"New assistant created with ID: {assistant.id}")

                # Update thread with assistant ID
                thread.context_data["assistant_id"] = assistant.id
                from ..models.chat import ThreadUpdateRequest

                thread_update = ThreadUpdateRequest(context_data=thread.context_data)
                await chat_service.update_thread(
                    thread_id, workspace_id, thread_update, current_user.id
                )
                logger.debug(f"Thread updated with assistant ID: {assistant.id}")

            # Get or create assistant thread
            from ..models.assistant import (
                ThreadCreateRequest as AssistantThreadCreateRequest,
            )

            # Check if we already have an assistant thread for this chat
            assistant_thread_id = thread.context_data.get("assistant_thread_id")
            assistant_thread = None

            if assistant_thread_id:
                logger.info(f"Reusing existing assistant thread: {assistant_thread_id}")
                # Retrieve the existing assistant thread
                assistant_thread = await assistant_service.get_thread(workspace_id, assistant_thread_id)
                if not assistant_thread:
                    logger.warning(f"Assistant thread {assistant_thread_id} not found, creating new one")
                    assistant_thread_id = None

            if not assistant_thread_id or not assistant_thread:
                # Create new assistant thread only if we don't have one
                assistant_thread_request = AssistantThreadCreateRequest(
                    title=f"Chat: {thread.name}", metadata={"chat_thread_id": thread_id}
                )

                logger.debug(f"Creating new assistant thread: {assistant_thread_request}")
                assistant_thread = await assistant_service.create_thread(
                    workspace_id, assistant.id, current_user.id, assistant_thread_request
                )
                logger.info(f"Assistant thread created with ID: {assistant_thread.id}")

                # Store the assistant thread ID in the chat thread context
                thread.context_data["assistant_thread_id"] = assistant_thread.id
                from ..models.chat import ThreadUpdateRequest

                thread_update = ThreadUpdateRequest(context_data=thread.context_data)
                await chat_service.update_thread(
                    thread_id, workspace_id, thread_update, current_user.id
                )
                logger.debug(f"Thread updated with assistant thread ID: {assistant_thread.id}")

            # Send message to assistant
            from ..models.assistant import (
                MessageCreateRequest as AssistantMessageCreateRequest,
            )

            assistant_message_request = AssistantMessageCreateRequest(
                content=user_message.content, metadata={"chat_thread_id": thread_id}
            )

            # Stream the assistant response
            logger.info(f"Starting message streaming with assistant thread: {assistant_thread.id}")
            logger.debug(f"Calling send_message with thread_id={assistant_thread.id}")

            async for event in assistant_service.send_message(
                workspace_id, assistant_thread.id, assistant_message_request
            ):
                logger.debug(f"Received event from assistant service: {event['type']}")

                if event["type"] == "message" and event["data"].get("role") == "assistant":
                    # Store assistant response in chat
                    assistant_response_data = {
                        "workspace_id": workspace_id,
                        "thread_id": thread_id,
                        "role": MessageRole.ASSISTANT.value,
                        "content": event["data"]["content"],
                    }

                    # Add tool call information if present
                    if event["data"].get("tool_calls"):
                        assistant_response_data["tool_calls"] = event["data"]["tool_calls"]
                        logger.debug(f"Tool calls present in response: {event['data']['tool_calls']}")

                    logger.debug(f"Creating assistant message: {assistant_response_data}")
                    assistant_response_request = MessageCreateRequest(**assistant_response_data)
                    assistant_message = await chat_service.create_message(
                        assistant_response_request, current_user.id
                    )
                    logger.info(f"Assistant message stored with ID: {assistant_message.id}")

                    # Yield assistant message
                    yield f"data: {json.dumps({'type': 'assistant_message', 'data': assistant_message.model_dump(mode='json')})}\n\n"

                elif event["type"] == "status":
                    # Yield status updates
                    logger.debug(f"Status update: {event['data']}")
                    yield f"data: {json.dumps({'type': 'status', 'data': event['data']})}\n\n"

                elif event["type"] == "error":
                    # Yield error information
                    logger.error(f"Error from assistant service: {event['data']}")
                    yield f"data: {json.dumps({'type': 'error', 'data': event['data']})}\n\n"

            # Final completion message
            logger.info("Chat response generation completed successfully")
            yield f"data: {json.dumps({'type': 'complete', 'data': {'status': 'completed'}})}\n\n"

        except Exception as e:
            logger.error(f"Chat with assistant failed: {e}")
            import traceback

            logger.error(traceback.format_exc())
            yield f"data: {json.dumps({'type': 'error', 'data': {'error': str(e)}})}\n\n"

    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )


async def chat_with_assistant_sync(
    workspace_id: str,
    thread_id: str,
    message_request_data: dict[str, Any],
    current_user: User,
    chat_service: ChatServiceDep,
    assistant_service: AssistantServiceDep,
) -> dict:
    """Send a message and get complete AI response (non-streaming)."""

    logger.info(f"Sync chat request - workspace: {workspace_id}, thread: {thread_id}")

    try:
        # Validate thread exists
        thread = await chat_service.get_thread(thread_id, workspace_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        # Create user message
        user_message_data = {
            "workspace_id": workspace_id,
            "thread_id": thread_id,
            "role": MessageRole.USER.value,
            "content": message_request_data.get("content", ""),
        }

        user_message_request = MessageCreateRequest(**user_message_data)
        user_message = await chat_service.create_message(
            user_message_request, current_user.id
        )
        logger.info(f"User message created: {user_message.id}")

        # Get or determine assistant
        assistant_id = message_request_data.get("assistant_id") or thread.context_data.get("assistant_id")

        if assistant_id:
            assistant = await assistant_service.get_assistant(workspace_id, assistant_id)
            if not assistant:
                raise HTTPException(status_code=404, detail="Assistant not found")
        else:
            # Create a new assistant
            from ..models.assistant import AssistantCreateRequest

            assistant_request = AssistantCreateRequest(
                name=thread.context_data.get("assistant_name", "ProtoBox Assistant"),
                instructions=thread.system_instructions or "You are a helpful assistant.",
                model=thread.context_data.get("assistant_model", "gpt-4-turbo-preview"),
                enable_mcp_tools=True,
                metadata={"chat_thread_id": thread_id},
            )

            assistant = await assistant_service.create_assistant(
                workspace_id, current_user.id, assistant_request
            )

            # Update thread with assistant ID
            thread.context_data["assistant_id"] = assistant.id
            from ..models.chat import ThreadUpdateRequest
            thread_update = ThreadUpdateRequest(context_data=thread.context_data)
            await chat_service.update_thread(
                thread_id, workspace_id, thread_update, current_user.id
            )

        # Get or create assistant thread
        assistant_thread_id = thread.context_data.get("assistant_thread_id")
        assistant_thread = None

        if assistant_thread_id:
            assistant_thread = await assistant_service.get_thread(workspace_id, assistant_thread_id)

        if not assistant_thread:
            from ..models.assistant import ThreadCreateRequest as AssistantThreadCreateRequest
            assistant_thread_request = AssistantThreadCreateRequest(
                title=f"Chat: {thread.name}",
                metadata={"chat_thread_id": thread_id}
            )
            assistant_thread = await assistant_service.create_thread(
                workspace_id, assistant.id, current_user.id, assistant_thread_request
            )

            # Store assistant thread ID
            thread.context_data["assistant_thread_id"] = assistant_thread.id
            from ..models.chat import ThreadUpdateRequest
            thread_update = ThreadUpdateRequest(context_data=thread.context_data)
            await chat_service.update_thread(
                thread_id, workspace_id, thread_update, current_user.id
            )

        # Send message and collect full response
        from ..models.assistant import MessageCreateRequest as AssistantMessageCreateRequest
        assistant_message_request = AssistantMessageCreateRequest(
            content=user_message.content,
            metadata={"chat_thread_id": thread_id}
        )

        assistant_content = ""
        tool_calls = []

        # Collect the complete response
        async for event in assistant_service.send_message(
            workspace_id, assistant_thread.id, assistant_message_request
        ):
            if event["type"] == "message" and event["data"].get("role") == "assistant":
                assistant_content = event["data"]["content"]
                if event["data"].get("tool_calls"):
                    tool_calls = event["data"]["tool_calls"]
            elif event["type"] == "error":
                raise HTTPException(
                    status_code=500,
                    detail=event["data"].get("error", "Assistant error")
                )

        # Create assistant message in chat history
        assistant_response_data = {
            "workspace_id": workspace_id,
            "thread_id": thread_id,
            "role": MessageRole.ASSISTANT.value,
            "content": assistant_content,
        }

        if tool_calls:
            assistant_response_data["tool_calls"] = tool_calls

        assistant_response_request = MessageCreateRequest(**assistant_response_data)
        assistant_message = await chat_service.create_message(
            assistant_response_request, current_user.id
        )

        logger.info(f"Sync chat completed - assistant message: {assistant_message.id}")

        # Return complete response
        return {
            "user_message": user_message.model_dump(mode="json"),
            "assistant_message": assistant_message.model_dump(mode="json"),
            "thread_id": thread_id,
            "assistant_id": assistant.id,
            "tool_calls": tool_calls if tool_calls else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sync chat failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
