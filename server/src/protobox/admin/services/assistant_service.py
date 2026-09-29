"""Assistant service for OpenAI integration and MCP tool testing."""

import os
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import openai
import yaml
from agents.mcp import MCPServerSse
from bson import ObjectId
from loguru import logger

from agents import Agent, Runner

from ..auth.mcp_auth import MCPAuthService
from ..config import settings
from ..database.connection import get_database_connection
from ..models.assistant import (
    AssistantCreateRequest,
    AssistantModel,
    AssistantUpdateRequest,
    MessageCreateRequest,
    MessageModel,
    MessageRole,
    ThreadCreateRequest,
    ThreadModel,
)
from ..services.action_service import ActionService
from ..services.secret_service import SecretService

# from ...tools.discovery import discover_tools  # TODO: Implement when available


class AssistantService:
    """Service for managing OpenAI assistants and conversations."""

    def __init__(self, action_service: ActionService, secret_service: SecretService):
        self.action_service = action_service
        self.secret_service = secret_service
        self.assistants_collection = "assistants"
        self.threads_collection = "assistant_threads"
        self.messages_collection = "assistant_messages"
        self.client = None
        self.db = get_database_connection()
        self.mcp_base_url = os.getenv("MCP_BASE_URL", "http://localhost:8090")

        # Use MCP endpoint at root level
        self.mcp_url_template = f"{self.mcp_base_url}/mcp" + "/{workspace_id}/sse"
        self.mcp_name = "ProtoBox MCP Server"
        logger.info(f"Agent configured for MCP integration with URL: {self.mcp_url_template}")
        self.agents_cache = {}  # Cache for OpenAI Agents

    async def _get_openai_client(self, workspace_id: str) -> openai.AsyncOpenAI:
        """Get OpenAI client with API key from secrets."""
        if self.client:
            return self.client

        # Try to get OpenAI API key from workspace secrets
        try:
            api_key_secret = await self.secret_service.get_secret_by_name(
                workspace_id, "openai_api_key"
            )
            if api_key_secret:
                api_key = await self.secret_service.decrypt_secret_value(
                    api_key_secret.id, "system"
                )
            else:
                # Fall back to environment variable
                import os

                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OpenAI API key not found in secrets or environment")
        except Exception as e:
            logger.error(f"Error getting OpenAI API key: {e}")
            raise

        self.client = openai.AsyncOpenAI(api_key=api_key)
        return self.client

    def _get_collection(self, collection_name: str):
        """Get a database collection."""
        db_connection = get_database_connection()
        return db_connection.database[collection_name]

    def _get_mcp_server_url(self, workspace_id: str) -> str:
        """Get the MCP server URL for this workspace."""
        # Get the base URL from environment or use localhost
        base_url = os.getenv("MCP_BASE_URL", "http://localhost:8090")
        return f"{base_url}/mcp/{workspace_id}/sse"

    async def _get_or_create_agent(
        self, workspace_id: str, assistant: AssistantModel
    ):
        """Get or create an OpenAI Agent with MCP integration."""

        # Check if MCP is enabled for this assistant
        mcp_enabled_value = assistant.metadata.get("mcp_enabled", "true")
        mcp_enabled = mcp_enabled_value in ["true", "True", True]
        logger.debug(f"MCP enabled check: {assistant.metadata} -> {mcp_enabled}")
        if not mcp_enabled:
            logger.debug("MCP not enabled for assistant")
            return None

        # Check cache first
        cache_key = f"{workspace_id}:{assistant.id}"
        if cache_key in self.agents_cache:
            return self.agents_cache[cache_key]

        try:
            # Get API key
            api_key = await self._get_api_key(workspace_id)
            os.environ["OPENAI_API_KEY"] = api_key

            # Create agent - MCP server will be connected during message sending
            agent = Agent(
                name=assistant.name, instructions=assistant.instructions, model=assistant.model
            )

            # Cache the agent
            self.agents_cache[cache_key] = agent

            return agent

        except Exception as e:
            logger.error(f"Failed to create MCP-enabled agent: {e}")
            return None

    def _load_default_assistant_config(self) -> dict[str, Any]:
        """Load default assistant configuration from YAML file."""
        try:
            config_path = Path(__file__).parent.parent / "config" / "default_assistant.yaml"
            if config_path.exists():
                with open(config_path) as f:
                    config = yaml.safe_load(f)
                logger.info("Loaded default assistant configuration from file")
                return config
            logger.warning("Default assistant config file not found, using hardcoded defaults")
            return {
                "name": "ProtoBox Assistant",
                "model": "gpt-4o",
                "is_default": True,
                "instructions": "You are a helpful ProtoBox assistant.",
                "metadata": {"mcp_enabled": "true"},
            }
        except Exception as e:
            logger.error(f"Error loading default assistant config: {e}")
            return {
                "name": "ProtoBox Assistant",
                "model": "gpt-4o",
                "is_default": True,
                "instructions": "You are a helpful ProtoBox assistant.",
                "metadata": {"mcp_enabled": "true"},
            }

    async def _get_api_key(self, workspace_id: str) -> str:
        """Get OpenAI API key from secrets or environment."""
        try:
            api_key_secret = await self.secret_service.get_secret_by_name(
                workspace_id, "openai_api_key"
            )
            if api_key_secret:
                api_key = await self.secret_service.decrypt_secret_value(
                    api_key_secret.id, "system"
                )
                return api_key
            # Fall back to environment variable
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key not found in secrets or environment")
            return api_key
        except Exception as e:
            logger.error(f"Error getting OpenAI API key: {e}")
            raise

    async def _get_or_create_internal_mcp_token(self, workspace_id: str) -> str:
        """Get or create an internal MCP token for workspace MCP servers."""
        try:
            # Check if we already have an internal MCP token for this workspace
            mcp_tokens_collection = self.db.database["mcp_tokens"]
            existing_token = await mcp_tokens_collection.find_one({
                "workspace_id": workspace_id,
                "name": "internal-assistant-mcp",
                "status": "active"
            })

            if existing_token:
                # Check if token is still valid (not expired)
                expires_at = existing_token.get("expires_at")
                if expires_at is None or expires_at > datetime.now():
                    logger.info(f"Using existing internal MCP token for workspace {workspace_id}")
                    # We can't return the actual token since it's hashed, but we know it exists
                    # For now, we'll create a new one each time to ensure we have the plain token
                    pass

            # Create a new internal MCP token
            logger.info(f"Creating new internal MCP token for workspace {workspace_id}")
            token_data = await MCPAuthService.create_mcp_token(
                db=self.db.database,
                workspace_id=workspace_id,
                user_id="system",  # System-generated token for internal use
                name="internal-assistant-mcp",
                description="Auto-generated token for assistant internal MCP access",
                expires_in_days=30,  # 30 day expiry for internal tokens
                scopes=["read:actions", "execute:actions", "read:secrets", "read:knowledge_base"]
            )

            logger.info(f"Created internal MCP token for workspace {workspace_id}")
            return token_data["token"]

        except Exception as e:
            logger.error(f"Error getting or creating internal MCP token: {e}")
            raise ValueError(f"Failed to create internal MCP token: {e}")

    async def get_or_create_default_assistant(
        self, workspace_id: str, user_id: str
    ) -> AssistantModel:
        """Get or create the default assistant for a workspace."""
        try:
            # Get collection properly
            collection = self._get_collection(self.assistants_collection)

            # Check if default assistant already exists
            existing_default = await collection.find_one(
                {"workspace_id": workspace_id, "is_default": True}
            )

            if existing_default:
                # Convert to model
                existing_default["id"] = str(existing_default.pop("_id"))
                return AssistantModel(**existing_default)

            # Load default configuration
            config = self._load_default_assistant_config()

            # Create new default assistant
            request = AssistantCreateRequest(
                name=config["name"], instructions=config["instructions"], model=config["model"]
            )

            # Create the assistant
            return await self.create_assistant(workspace_id, user_id, request, is_default=True)

        except Exception as e:
            logger.error(f"Error getting or creating default assistant: {e}")
            raise

    async def create_assistant(
        self,
        workspace_id: str,
        user_id: str,
        request: AssistantCreateRequest,
        is_default: bool = False,
    ) -> AssistantModel:
        """Create a new assistant."""
        try:
            # Check if MCP tools should be enabled
            enable_mcp = request.enable_mcp_tools if hasattr(request, "enable_mcp_tools") else True

            if enable_mcp:
                # Use Agents SDK (without MCP for now due to module conflicts)
                api_key = await self._get_api_key(workspace_id)
                os.environ["OPENAI_API_KEY"] = api_key

                # Get MCP server configurations
                try:
                    # Get or create internal MCP token for workspace
                    internal_mcp_token = await self._get_or_create_internal_mcp_token(workspace_id)

                    # Get MCP server configurations
                    mcp_base_url = os.getenv("MCP_BASE_URL", "http://localhost:8090")

                    # 1. User MCP server for workspace-specific actions
                    user_mcp_url = f"{mcp_base_url}/mcp/{workspace_id}/sse"

                    # 2. Internal MCP server for ProtoBox management
                    internal_mcp_url = f"{mcp_base_url}/internal-mcp/sse"

                    # Create MCP server configurations
                    from agents.mcp import MCPServerSseParams

                    # User MCP server params - uses the internal token for authentication
                    user_mcp_params = MCPServerSseParams()
                    user_mcp_params["url"] = user_mcp_url
                    user_mcp_params["headers"] = {
                        "Authorization": f"Bearer {internal_mcp_token}"
                    }

                    # Internal MCP server params - uses the internal token for authentication
                    internal_mcp_params = MCPServerSseParams()
                    internal_mcp_params["url"] = f"{internal_mcp_url}?workspace_id={workspace_id}"
                    internal_mcp_params["headers"] = {
                        "Authorization": f"Bearer {internal_mcp_token}",
                        "X-Workspace-Id": workspace_id
                    }

                    # Create MCP servers (currently commented out due to integration complexity)
                    # TODO: Enable MCP servers when integration is stable
                    # from agents.mcp import MCPServerSse
                    # user_mcp_server = MCPServerSse(params=user_mcp_params, name="ProtoBox User MCP")
                    # internal_mcp_server = MCPServerSse(params=internal_mcp_params, name="ProtoBox Internal MCP")
                    # mcp_servers = [user_mcp_server]
                    # if is_default:
                    #     mcp_servers.append(internal_mcp_server)
                    #     logger.info("Adding internal MCP tools to default assistant")

                    agent = Agent(
                        name=request.name,
                        instructions=request.instructions,
                        model=request.model,
                        # mcp_servers=mcp_servers,  # Commented out until integration is stable
                    )
                    logger.info(
                        f"Created agent with MCP configuration prepared for workspace {workspace_id}"
                    )

                except Exception as e:
                    logger.error(f"Failed to configure MCP integration: {e}")
                    # Fallback to agent without MCP
                    agent = Agent(
                        name=request.name, instructions=request.instructions, model=request.model
                    )
                    logger.warning("MCP integration not available, using basic agent")

                # Store agent in cache for later use
                cache_key = f"{workspace_id}:agent_{request.name}"
                self.agents_cache[cache_key] = agent

                # Create assistant via regular OpenAI API
                # The agent will be used later when sending messages
                client = await self._get_openai_client(workspace_id)
                
                # Convert metadata values to strings (OpenAI API requirement)
                metadata = {k: str(v) for k, v in request.metadata.items()}
                metadata["mcp_enabled"] = "true"
                
                assistant = await client.beta.assistants.create(
                    name=request.name,
                    instructions=request.instructions,
                    model=request.model,
                    tools=[],  # Tools managed by Agents SDK
                    metadata=metadata,
                )

                assistant_id = assistant.id
                tools = []  # Tools discovered via MCP

            else:
                # Use regular OpenAI client
                client = await self._get_openai_client(workspace_id)

                # Prepare tools
                tools = []

                # Convert metadata values to strings (OpenAI API requirement)
                metadata = {k: str(v) for k, v in request.metadata.items()}
                
                # Create OpenAI assistant
                assistant = await client.beta.assistants.create(
                    name=request.name,
                    instructions=request.instructions,
                    model=request.model,
                    tools=tools,
                    metadata=metadata,
                )

                assistant_id = assistant.id

            # Create database record
            assistant_model = AssistantModel(
                workspace_id=workspace_id,
                assistant_id=assistant_id,
                name=request.name,
                description=request.description,
                instructions=request.instructions,
                model=request.model,
                is_default=is_default,
                tools=tools,
                metadata={**metadata, "mcp_enabled": str(enable_mcp)},
                created_by=user_id,
            )

            collection = self._get_collection(self.assistants_collection)
            result = await collection.insert_one(assistant_model.model_dump_for_db())
            assistant_model.id = str(result.inserted_id)

            logger.info(
                f"Created assistant {assistant_id} for workspace {workspace_id} (MCP: {enable_mcp})"
            )
            return assistant_model

        except Exception as e:
            import traceback

            logger.error(f"Error creating assistant: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    async def get_assistant(self, workspace_id: str, assistant_id: str) -> AssistantModel | None:
        """Get an assistant by ID."""
        try:
            collection = self._get_collection(self.assistants_collection)
            doc = await collection.find_one(
                {"_id": ObjectId(assistant_id), "workspace_id": workspace_id}
            )

            if doc:
                doc["id"] = str(doc.pop("_id"))
                return AssistantModel(**doc)
            return None

        except Exception as e:
            logger.error(f"Error getting assistant: {e}")
            raise

    async def list_assistants(self, workspace_id: str) -> list[AssistantModel]:
        """List all assistants in a workspace."""
        try:
            collection = self._get_collection(self.assistants_collection)
            cursor = collection.find({"workspace_id": workspace_id})

            assistants = []
            async for doc in cursor:
                doc["id"] = str(doc.pop("_id"))
                assistants.append(AssistantModel(**doc))

            return assistants

        except Exception as e:
            logger.error(f"Error listing assistants: {e}")
            raise

    async def update_assistant(
        self, workspace_id: str, assistant_id: str, request: AssistantUpdateRequest
    ) -> AssistantModel:
        """Update an assistant."""
        try:
            # Get existing assistant
            assistant = await self.get_assistant(workspace_id, assistant_id)
            if not assistant:
                raise ValueError(f"Assistant {assistant_id} not found")

            client = await self._get_openai_client(workspace_id)

            # Update OpenAI assistant
            update_params = {}
            if request.name is not None:
                update_params["name"] = request.name
            if request.instructions is not None:
                update_params["instructions"] = request.instructions
            if request.model is not None:
                update_params["model"] = request.model
            if request.metadata is not None:
                update_params["metadata"] = request.metadata

            if update_params:
                await client.beta.assistants.update(assistant.assistant_id, **update_params)

            # Update database record
            update_data = {"updated_at": datetime.now(UTC)}

            if request.name is not None:
                update_data["name"] = request.name
            if request.description is not None:
                update_data["description"] = request.description
            if request.instructions is not None:
                update_data["instructions"] = request.instructions
            if request.model is not None:
                update_data["model"] = request.model
            if request.status is not None:
                update_data["status"] = request.status
            if request.metadata is not None:
                update_data["metadata"] = request.metadata

            collection = self._get_collection(self.assistants_collection)
            await collection.update_one({"_id": ObjectId(assistant_id)}, {"$set": update_data})

            return await self.get_assistant(workspace_id, assistant_id)

        except Exception as e:
            logger.error(f"Error updating assistant: {e}")
            raise

    async def delete_assistant(self, workspace_id: str, assistant_id: str) -> bool:
        """Delete an assistant."""
        try:
            # Get assistant
            assistant = await self.get_assistant(workspace_id, assistant_id)
            if not assistant:
                return False

            client = await self._get_openai_client(workspace_id)

            # Delete from OpenAI
            await client.beta.assistants.delete(assistant.assistant_id)

            # Delete from database
            collection = self._get_collection(self.assistants_collection)
            result = await collection.delete_one(
                {"_id": ObjectId(assistant_id), "workspace_id": workspace_id}
            )

            return result.deleted_count > 0

        except Exception as e:
            logger.error(f"Error deleting assistant: {e}")
            raise

    async def create_thread(
        self, workspace_id: str, assistant_id: str, user_id: str, request: ThreadCreateRequest
    ) -> ThreadModel:
        """Create a new conversation thread."""
        try:
            # Verify assistant exists
            assistant = await self.get_assistant(workspace_id, assistant_id)
            if not assistant:
                raise ValueError(f"Assistant {assistant_id} not found")

            client = await self._get_openai_client(workspace_id)

            # Create OpenAI thread
            thread = await client.beta.threads.create(metadata=request.metadata)

            # Create database record
            thread_model = ThreadModel(
                workspace_id=workspace_id,
                assistant_id=assistant_id,
                thread_id=thread.id,
                title=request.title,
                metadata=request.metadata,
                created_by=user_id,
            )

            collection = self._get_collection(self.threads_collection)
            result = await collection.insert_one(thread_model.model_dump_for_db())
            thread_model.id = str(result.inserted_id)

            logger.info(f"Created thread {thread.id} for assistant {assistant_id}")
            return thread_model

        except Exception as e:
            logger.error(f"Error creating thread: {e}")
            raise

    async def get_thread(self, workspace_id: str, thread_id: str) -> ThreadModel | None:
        """Get a thread by ID."""
        try:
            logger.debug(f"Getting thread {thread_id} in workspace {workspace_id}")
            collection = self._get_collection(self.threads_collection)
            thread_doc = await collection.find_one(
                {"_id": ObjectId(thread_id), "workspace_id": workspace_id}
            )
            
            if not thread_doc:
                logger.warning(f"Thread {thread_id} not found in workspace {workspace_id}")
                return None
            
            logger.debug(f"Found thread: {thread_doc.get('title', 'Unknown')}")
            # Convert ObjectId to string for the id field
            thread_doc['id'] = str(thread_doc['_id'])
            return ThreadModel(**thread_doc)
        
        except Exception as e:
            logger.error(f"Error getting thread {thread_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    async def send_message(
        self, workspace_id: str, thread_id: str, request: MessageCreateRequest
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Send a message and stream the response."""
        try:
            # Get thread
            collection = self._get_collection(self.threads_collection)
            thread_doc = await collection.find_one(
                {"_id": ObjectId(thread_id), "workspace_id": workspace_id}
            )

            if not thread_doc:
                raise ValueError(f"Thread {thread_id} not found")

            logger.info(f"Thread doc: {thread_doc}")

            # Get assistant
            assistant = await self.get_assistant(workspace_id, thread_doc["assistant_id"])
            logger.debug(f"Got assistant: {assistant.id if assistant else 'None'}")
            if not assistant:
                raise ValueError("Assistant not found")

            # Try to use OpenAI Agents SDK with MCP if available
            logger.info(f"Using OpenAI Agents SDK for assistant {assistant.id}")
            agent = await self._get_or_create_agent(workspace_id, assistant)
            if agent:
                logger.info("Agent created successfully, sending message with MCP tools")
                async for event in self._send_message_with_agents_sdk(
                    agent, workspace_id, thread_id, request
                ):
                    yield event
                return
            else:
                logger.debug("Could not create or get agent")

            # Fall back to direct OpenAI API
            async for event in self._send_message_with_openai_api(
                workspace_id, thread_id, assistant, request
            ):
                yield event

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            yield {"type": "error", "data": {"error": str(e)}}
            raise

    async def _send_message_with_agents_sdk(
        self, agent: Agent, workspace_id: str, thread_id: str, request: MessageCreateRequest
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Send a message using OpenAI Agents SDK with MCP."""
        try:
            # Store user message
            user_message = MessageModel(
                thread_id=thread_id,
                role=MessageRole.USER,
                content=request.content,
                metadata=request.metadata,
            )

            messages_collection = self._get_collection(self.messages_collection)
            await messages_collection.insert_one(user_message.model_dump_for_db())

            # Yield user message
            yield {"type": "message", "data": user_message.model_dump(mode="json")}

            # Retrieve conversation history for context
            history_messages = []
            try:
                # Get previous messages from this thread (limit to last 20 for context window)
                cursor = messages_collection.find(
                    {"thread_id": thread_id}
                ).sort("created_at", 1).limit(20)
                
                async for msg_doc in cursor:
                    # Convert to message format for Runner
                    history_messages.append({
                        "role": msg_doc.get("role", "user"),
                        "content": msg_doc.get("content", "")
                    })
                
                logger.info(f"Retrieved {len(history_messages)} messages from conversation history")
            except Exception as e:
                logger.warning(f"Failed to retrieve conversation history: {e}")
                # Continue without history if retrieval fails
                history_messages = []

            # Add the current message to the history
            history_messages.append({
                "role": "user",
                "content": request.content
            })

            internal_mcp_token = await self._get_or_create_internal_mcp_token(workspace_id)
            mcp_url = self.mcp_url_template.format(workspace_id=workspace_id)
            logger.info(f"Creating MCP server with URL: {self.mcp_url_template}")

            try:
                async with MCPServerSse(
                    name=self.mcp_name,
                    params={
                        "url": mcp_url,
                        "headers": {
                            "Authorization": f"Bearer {internal_mcp_token}",
                        },
                    },
                    client_session_timeout_seconds=settings.mcp_client_session_timeout_seconds,
                ) as mcp_server:
                    # Create a new agent instance with MCP server for this conversation
                    mcp_agent = Agent(
                        name=agent.name,
                        instructions=agent.instructions,
                        model=agent.model,
                        mcp_servers=[mcp_server],
                    )

                    logger.info(
                        f"Running agent with MCP tools and {len(history_messages)} messages in history"
                    )
                    # Pass the full conversation history to Runner
                    result = await Runner.run(
                        starting_agent=mcp_agent, 
                        input=history_messages if len(history_messages) > 1 else request.content
                    )
            except Exception as e:
                logger.error(f"MCP connection failed: {e}")
                logger.warning("Falling back to non-MCP execution")
                # Fall back to running without MCP
                result = await Runner.run(
                    starting_agent=agent, 
                    input=history_messages if len(history_messages) > 1 else request.content
                )

            logger.info(
                f"Agent result: {result.final_output[:100] if result.final_output else 'No output'}"
            )

            # Store assistant response
            assistant_message = MessageModel(
                thread_id=thread_id,
                role=MessageRole.ASSISTANT,
                content=result.final_output or "",
                metadata={},
            )

            await messages_collection.insert_one(assistant_message.model_dump_for_db())

            # Yield assistant message
            yield {"type": "message", "data": assistant_message.model_dump(mode="json")}

            # Yield completion status
            yield {"type": "status", "data": {"status": "completed"}}

        except Exception as e:
            logger.error(f"Error in Agents SDK message handling: {e}")
            yield {"type": "error", "data": {"error": str(e)}}
            raise

    async def _send_message_with_openai_api(
        self,
        workspace_id: str,
        thread_id: str,
        assistant: AssistantModel,
        request: MessageCreateRequest,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Send a message using direct OpenAI API (fallback)."""
        try:
            # Get thread document
            collection = self._get_collection(self.threads_collection)
            thread_doc = await collection.find_one(
                {"_id": ObjectId(thread_id), "workspace_id": workspace_id}
            )

            if not thread_doc:
                raise ValueError(f"Thread {thread_id} not found")

            client = await self._get_openai_client(workspace_id)

            # Create user message
            message = await client.beta.threads.messages.create(
                thread_id=thread_doc["thread_id"],
                role="user",
                content=request.content,
                metadata=request.metadata,
            )

            # Store user message
            user_message = MessageModel(
                thread_id=thread_id,
                message_id=message.id,
                role=MessageRole.USER,
                content=request.content,
                metadata=request.metadata,
            )

            messages_collection = self._get_collection(self.messages_collection)
            await messages_collection.insert_one(user_message.model_dump_for_db())

            # Yield user message
            yield {"type": "message", "data": user_message.model_dump(mode="json")}

            # Create and poll run
            run = await client.beta.threads.runs.create(
                thread_id=thread_doc["thread_id"], assistant_id=assistant.assistant_id
            )

            # Poll run status and handle tool calls
            while True:
                run = await client.beta.threads.runs.retrieve(
                    thread_id=thread_doc["thread_id"], run_id=run.id
                )

                # Yield status update
                yield {"type": "status", "data": {"run_id": run.id, "status": run.status}}

                if run.status == "completed":
                    break
                elif run.status == "requires_action":
                    # Note: Tool execution is handled via MCP when using Agents SDK
                    # This fallback method doesn't support tools
                    yield {
                        "type": "error",
                        "data": {
                            "error": "Tool execution requires OpenAI Agents SDK with MCP integration"
                        },
                    }
                    break

                elif run.status in ["failed", "cancelled", "expired"]:
                    raise Exception(f"Run failed with status: {run.status}")

                # Wait before polling again
                import asyncio

                await asyncio.sleep(1)

            # Get assistant messages
            messages = await client.beta.threads.messages.list(
                thread_id=thread_doc["thread_id"], order="desc", limit=1
            )

            if messages.data:
                assistant_message = messages.data[0]

                # Store assistant message
                message_model = MessageModel(
                    thread_id=thread_id,
                    message_id=assistant_message.id,
                    role=MessageRole.ASSISTANT,
                    content=assistant_message.content[0].text.value,
                    metadata={},
                )

                await messages_collection.insert_one(message_model.model_dump_for_db())

                # Yield assistant message
                yield {"type": "message", "data": message_model.model_dump(mode="json")}

            # Update thread last message time
            await collection.update_one(
                {"_id": ObjectId(thread_id)},
                {"$set": {"last_message_at": datetime.now(UTC)}},
            )

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            yield {"type": "error", "data": {"error": str(e)}}
