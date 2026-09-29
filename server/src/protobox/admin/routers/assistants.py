"""Assistant router for OpenAI integration and MCP tool testing."""

import json

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer
from loguru import logger

from ..auth.dependencies import User, require_authentication
from ..database.connection import get_database_connection
from ..models.assistant import (
    AssistantCreateRequest,
    AssistantResponse,
    AssistantUpdateRequest,
    MessageCreateRequest,
    MessageModel,
    ThreadCreateRequest,
    ThreadModel,
    ThreadResponse,
)
from ..services.action_service import ActionService
from ..services.assistant_service import AssistantService
from ..services.secret_service import SecretService

router = APIRouter(prefix="/workspaces/{workspace_id}/assistants", tags=["Assistants"])

# Security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user_id(
    workspace_id: str, current_user: User = Depends(require_authentication)
) -> str:
    """Get current user ID from auth system."""
    return current_user.id


def get_assistant_service():
    """Get assistant service instance."""
    # Initialize services directly for now
    # TODO: Replace with proper dependency injection
    from ..secrets.encryption import SecretEncryption

    action_service = ActionService()
    encryption = SecretEncryption()
    secret_service = SecretService(encryption)

    return AssistantService(action_service, secret_service)


@router.post("", response_model=AssistantResponse)
async def create_assistant(
    workspace_id: str,
    request: AssistantCreateRequest,
    current_user: str = Depends(get_current_user_id),
    assistant_service: AssistantService = Depends(get_assistant_service),
):
    """
    Create a new OpenAI assistant with MCP tool integration.

    This endpoint creates an OpenAI assistant that can execute ProtoBox actions
    through the MCP protocol. The assistant can be configured with custom
    instructions, model selection, and tool bindings.

    **Request Body:**
    ```json
    {
        "name": "MCP Assistant",
        "instructions": "You are a helpful assistant that can execute actions.",
        "model": "gpt-4",
        "tools": [
            {
                "type": "mcp_action",
                "action_id": "6883cc77f0dd6dbee6550be8"
            }
        ],
        "metadata": {
            "department": "support",
            "capabilities": ["customer-service", "data-processing"]
        }
    }
    ```

    **Tool Types:**
    - `mcp_action`: Binds a ProtoBox action as an MCP tool
    - `code_interpreter`: Enables OpenAI's code interpreter
    - `retrieval`: Enables document retrieval (requires file upload)

    **Response:**
    ```json
    {
        "id": "assistant-id",
        "workspace_id": "workspace-id",
        "name": "MCP Assistant",
        "openai_assistant_id": "asst_xxx",
        "instructions": "...",
        "model": "gpt-4",
        "tools": [...],
        "created_at": "2024-01-01T00:00:00Z"
    }
    ```

    **MCP Integration:**
    When `mcp_action` tools are configured, the assistant can execute
    ProtoBox actions through the MCP protocol. This enables seamless
    integration between OpenAI's assistant API and your custom actions.
    """
    try:
        # current_user is a string (user_id) from the router dependency
        return await assistant_service.create_assistant(
            workspace_id=workspace_id, user_id=current_user, request=request
        )
    except Exception as e:
        logger.error(f"Error creating assistant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=list[AssistantResponse])
async def list_assistants(
    workspace_id: str,
    current_user: str = Depends(get_current_user_id),
    assistant_service: AssistantService = Depends(get_assistant_service),
):
    """
    List all assistants in the workspace.

    Returns all OpenAI assistants created in this workspace, including their
    configuration, MCP tool bindings, and metadata.

    **Response Example:**
    ```json
    [
        {
            "id": "assistant-1",
            "workspace_id": "workspace-id",
            "name": "Customer Support Bot",
            "openai_assistant_id": "asst_xxx",
            "instructions": "Help customers with inquiries",
            "model": "gpt-4",
            "tools": [
                {
                    "type": "mcp_action",
                    "action_id": "action-id"
                }
            ],
            "created_at": "2024-01-01T00:00:00Z"
        }
    ]
    ```

    **Tool Information:**
    Each assistant's `tools` array shows the configured tools:
    - MCP actions are referenced by their ProtoBox action ID
    - Other OpenAI tools (code_interpreter, retrieval) are also listed
    """
    try:
        return await assistant_service.list_assistants(workspace_id)
    except Exception as e:
        logger.error(f"Error listing assistants: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/default", response_model=AssistantResponse)
async def get_or_create_default_assistant(
    workspace_id: str,
    current_user: str = Depends(get_current_user_id),
    assistant_service: AssistantService = Depends(get_assistant_service),
):
    """
    Get or create the default assistant for the workspace.

    This endpoint ensures there is always a default assistant available for the workspace.
    If no default assistant exists, it creates one using the configuration from
    default_assistant.yaml.
    """
    try:
        assistant = await assistant_service.get_or_create_default_assistant(
            workspace_id, current_user
        )
        return AssistantResponse(**assistant.model_dump())
    except Exception as e:
        logger.error(f"Error getting/creating default assistant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{assistant_id}", response_model=AssistantResponse)
async def get_assistant(
    workspace_id: str,
    assistant_id: str,
    current_user: str = Depends(get_current_user_id),
    assistant_service: AssistantService = Depends(get_assistant_service),
):
    """Get an assistant by ID."""
    try:
        assistant = await assistant_service.get_assistant(workspace_id, assistant_id)
        if not assistant:
            raise HTTPException(status_code=404, detail="Assistant not found")
        return assistant
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting assistant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{assistant_id}", response_model=AssistantResponse)
async def update_assistant(
    workspace_id: str,
    assistant_id: str,
    request: AssistantUpdateRequest,
    current_user: str = Depends(get_current_user_id),
    assistant_service: AssistantService = Depends(get_assistant_service),
):
    """Update an assistant."""
    try:
        return await assistant_service.update_assistant(
            workspace_id=workspace_id, assistant_id=assistant_id, request=request
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating assistant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{assistant_id}")
async def delete_assistant(
    workspace_id: str,
    assistant_id: str,
    current_user: str = Depends(get_current_user_id),
    assistant_service: AssistantService = Depends(get_assistant_service),
):
    """Delete an assistant."""
    try:
        success = await assistant_service.delete_assistant(workspace_id, assistant_id)
        if not success:
            raise HTTPException(status_code=404, detail="Assistant not found")
        return {"message": "Assistant deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting assistant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Thread endpoints
@router.post("/{assistant_id}/threads", response_model=ThreadResponse)
async def create_thread(
    workspace_id: str,
    assistant_id: str,
    request: ThreadCreateRequest,
    current_user: str = Depends(get_current_user_id),
    assistant_service: AssistantService = Depends(get_assistant_service),
):
    """
    Create a new conversation thread with an assistant.

    Threads represent individual conversations with an assistant. Each thread
    maintains its own conversation history and context.

    **Request Body:**
    ```json
    {
        "metadata": {
            "user_id": "user-123",
            "session_type": "support",
            "priority": "high"
        }
    }
    ```

    **Response:**
    ```json
    {
        "id": "thread-id",
        "assistant_id": "assistant-id",
        "openai_thread_id": "thread_xxx",
        "workspace_id": "workspace-id",
        "user_id": "user-id",
        "metadata": {...},
        "created_at": "2024-01-01T00:00:00Z"
    }
    ```

    **Thread Lifecycle:**
    - Threads persist conversation history
    - Can be resumed after interruption
    - Support metadata for categorization and routing
    - Automatically cleaned up after inactivity (configurable)
    """
    try:
        # current_user is a string (user_id) from the router dependency
        return await assistant_service.create_thread(
            workspace_id=workspace_id,
            assistant_id=assistant_id,
            user_id=current_user,
            request=request,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating thread: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{assistant_id}/threads", response_model=list[ThreadResponse])
async def list_threads(
    workspace_id: str,
    assistant_id: str,
    current_user: str = Depends(get_current_user_id),
    assistant_service: AssistantService = Depends(get_assistant_service),
):
    """List all threads for an assistant."""
    try:
        # Get collection directly
        db_connection = get_database_connection()
        collection = db_connection.database[assistant_service.threads_collection]

        cursor = collection.find({"workspace_id": workspace_id, "assistant_id": assistant_id}).sort(
            "created_at", -1
        )

        threads = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            threads.append(ThreadModel(**doc))

        return threads
    except Exception as e:
        logger.error(f"Error listing threads: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Message endpoints
@router.get("/threads/{thread_id}/messages", response_model=list[MessageModel])
async def get_messages(
    workspace_id: str,
    thread_id: str,
    limit: int = 50,
    current_user: str = Depends(get_current_user_id),
    assistant_service: AssistantService = Depends(get_assistant_service),
):
    """Get messages in a thread."""
    try:
        # Verify thread belongs to workspace
        db_connection = get_database_connection()
        threads_collection = db_connection.database[assistant_service.threads_collection]

        thread = await threads_collection.find_one(
            {"_id": ObjectId(thread_id), "workspace_id": workspace_id}
        )

        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        # Get messages
        messages_collection = db_connection.database[assistant_service.messages_collection]
        cursor = (
            messages_collection.find({"thread_id": thread_id}).sort("created_at", 1).limit(limit)
        )

        messages = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            messages.append(MessageModel(**doc))

        return messages
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoint for real-time chat
@router.websocket("/threads/{thread_id}/stream")
async def websocket_endpoint(
    workspace_id: str,
    thread_id: str,
    websocket: WebSocket,
    assistant_service: AssistantService = Depends(get_assistant_service),
):
    """
    WebSocket endpoint for real-time chat with assistant.

    Enables real-time, bidirectional communication with an OpenAI assistant.
    Supports streaming responses and MCP tool execution notifications.

    **WebSocket URL:**
    ```
    ws://localhost:8090/admin/api/v1/workspaces/{workspace_id}/assistants/threads/{thread_id}/stream
    ```

    **Client Message Format:**
    ```json
    {
        "content": "Please help me with...",
        "metadata": {
            "request_id": "req-123",
            "context": "customer-support"
        }
    }
    ```

    **Server Event Types:**

    1. **Message Event** (Assistant Response):
    ```json
    {
        "type": "message",
        "data": {
            "id": "msg-id",
            "role": "assistant",
            "content": "I can help you with that...",
            "created_at": "2024-01-01T00:00:00Z"
        }
    }
    ```

    2. **Tool Call Event** (MCP Action Execution):
    ```json
    {
        "type": "tool_call",
        "data": {
            "tool_name": "action-name",
            "tool_call_id": "call-id",
            "arguments": {...}
        }
    }
    ```

    3. **Tool Result Event**:
    ```json
    {
        "type": "tool_result",
        "data": {
            "tool_call_id": "call-id",
            "output": {...}
        }
    }
    ```

    4. **Error Event**:
    ```json
    {
        "type": "error",
        "data": {
            "error": "Error message",
            "code": "error_code"
        }
    }
    ```

    **Connection Flow:**
    1. Client connects to WebSocket endpoint
    2. Client sends message
    3. Server streams assistant response
    4. If MCP tools are called, tool events are sent
    5. Final message contains complete response

    **Error Handling:**
    - Connection errors close the WebSocket with error event
    - Message processing errors are sent as error events
    - WebSocket remains open for continued conversation
    """
    await websocket.accept()

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)

            # Create message request
            request = MessageCreateRequest(
                content=message_data["content"], metadata=message_data.get("metadata", {})
            )

            # Send message and stream response
            async for event in assistant_service.send_message(
                workspace_id=workspace_id, thread_id=thread_id, request=request
            ):
                await websocket.send_json(event)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for thread {thread_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({"type": "error", "data": {"error": str(e)}})
        await websocket.close()


# Streaming endpoint for chat
@router.post("/threads/{thread_id}/chat")
async def stream_chat(
    workspace_id: str,
    thread_id: str,
    request: MessageCreateRequest,
    current_user: str = Depends(get_current_user_id),
    assistant_service: AssistantService = Depends(get_assistant_service),
):
    """
    Stream chat responses with SSE (Server-Sent Events).

    This endpoint streams the assistant's response in real-time, including
    MCP tool calls and their results.
    """
    from fastapi.responses import StreamingResponse
    logger.info(f"Streaming chat for workspace {workspace_id} and thread {thread_id}")

    async def event_generator():
        try:
            async for event in assistant_service.send_message(
                workspace_id=workspace_id, thread_id=thread_id, request=request
            ):
                # Convert to SSE format
                event_data = json.dumps(event)
                yield f"data: {event_data}\n\n"
        except Exception as e:
            error_event = json.dumps({"type": "error", "data": {"error": str(e)}})
            yield f"data: {error_event}\n\n"
        finally:
            # Send done signal
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# REST endpoint for sending messages (alternative to WebSocket)
@router.post("/threads/{thread_id}/messages")
async def send_message(
    workspace_id: str,
    thread_id: str,
    request: MessageCreateRequest,
    current_user: str = Depends(get_current_user_id),
    assistant_service: AssistantService = Depends(get_assistant_service),
):
    """
    Send a message to a thread and get the complete response.

    This is a REST alternative to the WebSocket endpoint. It sends a message
    to the assistant and waits for the complete response, including any
    MCP tool executions.

    **Request Body:**
    ```json
    {
        "content": "Calculate the total for order #12345",
        "metadata": {
            "source": "api",
            "priority": "normal"
        }
    }
    ```

    **Response:**
    ```json
    {
        "message": {
            "id": "msg-id",
            "role": "assistant",
            "content": "The total for order #12345 is $150.00",
            "created_at": "2024-01-01T00:00:00Z"
        },
        "events": [
            {
                "type": "tool_call",
                "data": {
                    "tool_name": "get-order-total",
                    "tool_call_id": "call-123",
                    "arguments": {"order_id": "12345"}
                }
            },
            {
                "type": "tool_result",
                "data": {
                    "tool_call_id": "call-123",
                    "output": {"total": 150.00, "currency": "USD"}
                }
            },
            {
                "type": "message",
                "data": {...}
            }
        ]
    }
    ```

    **Events Array:**
    The `events` array contains all events that occurred during message
    processing, including:
    - Tool calls (MCP action executions)
    - Tool results
    - Intermediate messages
    - The final assistant response

    **Use Cases:**
    - Synchronous API integrations
    - Batch processing
    - Testing and debugging
    - Clients that don't support WebSockets
    """
    try:
        # Collect all events from the generator
        events = []
        async for event in assistant_service.send_message(
            workspace_id=workspace_id, thread_id=thread_id, request=request
        ):
            events.append(event)

        # Extract the final assistant message
        assistant_message = None
        for event in reversed(events):
            if event["type"] == "message" and event["data"]["role"] == "assistant":
                assistant_message = event["data"]
                break

        return {"message": assistant_message, "events": events}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail=str(e))
