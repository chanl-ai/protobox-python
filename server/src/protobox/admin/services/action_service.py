"""Action service for managing actions."""

from typing import Any

from ..constants import SystemUsers
from ..database.repositories.action_repository import ActionRepository
from .base_service import BaseService
from ..models.action import (
    ActionCreateRequest,
    ActionModel,
    ActionStatus,
    ActionType,
    ActionUpdateRequest,
)
from enum import Enum
import mcp.types as types


class AdminToolName(str, Enum):
    """Names of available admin tools."""
    CREATE_ACTION = "admin_create_action"
    LIST_ACTIONS = "admin_list_actions"
    GET_WORKSPACE_INFO = "admin_get_workspace_info"
    SUGGEST_ACTION_TEMPLATE = "admin_suggest_action_template"
    GET_PROTOBOX_TIPS = "admin_get_protobox_tips"


class AdminToolManager:
    """Manages administrative tools for the MCP server."""
    
    def __init__(self, action_service: 'ActionService'):
        """Initialize the manager with required services."""
        self.action_service = action_service
    
    @staticmethod
    async def get_tools(workspace_id: str) -> list[ActionModel]:
        """Fetch admin tools for a workspace."""
        from datetime import datetime, timezone
        
        admin_actions = [
            ActionModel(
                workspace_id=workspace_id,
                name=AdminToolName.CREATE_ACTION,
                type=ActionType.ADMIN,
                description="Create a new action in the workspace",
                config_schema={
                    "inputVariables": [
                        {
                            "name": "name",
                            "type": "string",
                            "description": "Name of the action (e.g., 'get-weather', 'send-email')",
                            "required": True
                        },
                        {
                            "name": "action_type",
                            "type": "string",
                            "description": "Type of action (REST, GraphQL, etc.)",
                            "required": True
                        },
                        {
                            "name": "description",
                            "type": "string",
                            "description": "Description of what the action does",
                            "required": True
                        },
                        {
                            "name": "url",
                            "type": "string",
                            "description": "The API endpoint URL",
                            "required": True
                        },
                        {
                            "name": "method",
                            "type": "string",
                            "description": "HTTP method (GET, POST, PUT, DELETE)",
                            "required": False
                        },
                        {
                            "name": "headers",
                            "type": "object",
                            "description": "Optional headers for the request",
                            "required": False
                        }
                    ]
                },
                default_config={},
                created_by=SystemUsers.SYSTEM,
                updated_by=SystemUsers.SYSTEM,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            ActionModel(
                workspace_id=workspace_id,
                name=AdminToolName.LIST_ACTIONS,
                type=ActionType.ADMIN,
                description="List actions in the workspace",
                config_schema={
                    "inputVariables": [
                        {
                            "name": "action_type",
                            "type": "string",
                            "description": "Optional filter by action type (REST, GraphQL, etc.)",
                            "required": False
                        },
                        {
                            "name": "limit",
                            "type": "integer",
                            "description": "Maximum number of actions to return",
                            "required": False
                        }
                    ]
                },
                default_config={"limit": 20},
                created_by=SystemUsers.SYSTEM,
                updated_by=SystemUsers.SYSTEM,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            ActionModel(
                workspace_id=workspace_id,
                name=AdminToolName.GET_WORKSPACE_INFO,
                type=ActionType.ADMIN,
                description="Get information about the current workspace",
                config_schema={
                    "inputVariables": []
                },
                default_config={},
                created_by=SystemUsers.SYSTEM,
                updated_by=SystemUsers.SYSTEM,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            ActionModel(
                workspace_id=workspace_id,
                name=AdminToolName.SUGGEST_ACTION_TEMPLATE,
                type=ActionType.ADMIN,
                description="Suggest an action template based on the use case",
                config_schema={
                    "inputVariables": [
                        {
                            "name": "use_case",
                            "type": "string",
                            "description": "Description of what the user wants to do (e.g., 'send email', 'get weather', 'create task')",
                            "required": True
                        }
                    ]
                },
                default_config={},
                created_by=SystemUsers.SYSTEM,
                updated_by=SystemUsers.SYSTEM,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            ActionModel(
                workspace_id=workspace_id,
                name=AdminToolName.GET_PROTOBOX_TIPS,
                type=ActionType.ADMIN,
                description="Get ProtoBox-specific tips and best practices",
                config_schema={
                    "inputVariables": [
                        {
                            "name": "topic",
                            "type": "string",
                            "description": "Topic to get tips for (general, actions, security, testing, mcp)",
                            "required": False
                        }
                    ]
                },
                default_config={"topic": "general"},
                created_by=SystemUsers.SYSTEM,
                updated_by=SystemUsers.SYSTEM,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        ]
        return admin_actions
    
    async def execute_admin_action(
        self,
        action: ActionModel,
        arguments: dict[str, Any],
        workspace_id: str,
        user_id: str = "mcp_user"
    ) -> list[types.Content]:
        """Execute an admin action using the appropriate handler."""
        try:
            from loguru import logger
            logger.info(f"Executing admin action: {action.name}")
            
            if action.name == AdminToolName.CREATE_ACTION.value:
                return await self._handle_create_action(arguments, workspace_id, user_id)
            elif action.name == AdminToolName.LIST_ACTIONS.value:
                return await self._handle_list_actions(arguments, workspace_id)
            elif action.name == AdminToolName.GET_WORKSPACE_INFO.value:
                return await self._handle_get_workspace_info(workspace_id)
            elif action.name == AdminToolName.SUGGEST_ACTION_TEMPLATE.value:
                return await self._handle_suggest_action_template(arguments)
            elif action.name == AdminToolName.GET_PROTOBOX_TIPS.value:
                return await self._handle_get_protobox_tips(arguments)
            else:
                raise ValueError(f"Unknown admin action: {action.name}")
                
        except Exception as e:
            from loguru import logger
            logger.error(f"Error executing admin action {action.name}: {e}")
            return [types.TextContent(type="text", text=f"❌ Admin action execution failed: {str(e)}")]
    
    async def _handle_create_action(
        self,
        arguments: dict[str, Any],
        workspace_id: str,
        user_id: str
    ) -> list[types.Content]:
        """Handle create_action admin tool."""
        try:
            # Extract arguments
            name = arguments.get("name")
            action_type_str = arguments.get("action_type")
            description = arguments.get("description")
            url = arguments.get("url")
            method = arguments.get("method", "GET")
            headers = arguments.get("headers", {})
            
            if not all([name, action_type_str, description, url]):
                return [types.TextContent(type="text", text="❌ Missing required fields: name, action_type, description, url")]
            
            # Validate action type
            try:
                action_type = ActionType(action_type_str)
            except ValueError:
                return [types.TextContent(type="text", text=f"❌ Invalid action type: {action_type_str}")]
            
            # Create action request
            action_request = ActionCreateRequest(
                workspace_id=workspace_id,
                name=name,
                type=action_type,
                description=description,
                default_config={
                    "url": url,
                    "method": method,
                    "headers": headers
                },
                config_schema={
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                tags=[]
            )
            
            # Use action service to create
            action_id = await self.action_service.create_action(action_request, user_id)
            
            return [types.TextContent(type="text", text=f"✅ Successfully created action '{name}' with ID: {action_id}")]
            
        except Exception as e:
            from loguru import logger
            logger.error(f"Error creating action: {e}")
            return [types.TextContent(type="text", text=f"❌ Failed to create action: {str(e)}")]
    
    async def _handle_list_actions(
        self,
        arguments: dict[str, Any],
        workspace_id: str
    ) -> list[types.Content]:
        """Handle list_actions admin tool."""
        try:
            action_type_str = arguments.get("action_type")
            limit = arguments.get("limit", 20)
            
            # Get actions using repository directly to avoid duplication with admin tools
            from ..database.repositories.action_repository import ActionRepository
            action_repo = ActionRepository()
            actions = await action_repo.get_actions_by_workspace(
                workspace_id=workspace_id,
                limit=limit
            )
            
            if not actions:
                return [types.TextContent(type="text", text="No actions found in this workspace")]
            
            # Format results
            content_parts = []
            for action in actions[:limit]:
                status = getattr(action, 'status', 'active')
                created_at = getattr(action, 'created_at', None)
                created_str = created_at.isoformat() if created_at else "Unknown"
                
                action_info = f"**{action.name}** ({action.type.value})\n"
                action_info += f"Description: {action.description}\n"
                action_info += f"Status: {status}\n"
                action_info += f"Created: {created_str}\n"
                
                content_parts.append(action_info)
            
            content_text = "\n\n---\n\n".join(content_parts)
            return [types.TextContent(type="text", text=content_text)]
            
        except Exception as e:
            from loguru import logger
            logger.error(f"Error listing actions: {e}")
            return [types.TextContent(type="text", text=f"❌ Failed to list actions: {str(e)}")]
    
    async def _handle_get_workspace_info(self, workspace_id: str) -> list[types.Content]:
        """Handle get_workspace_info admin tool."""
        try:
            from ..database.connection import get_database_connection
            from bson import ObjectId
            
            db_connection = get_database_connection()
            database = db_connection.database
            
            # Get workspace info
            workspaces_collection = database["workspaces"]
            actions_collection = database["actions"]
            
            workspace = await workspaces_collection.find_one({"_id": ObjectId(workspace_id)})
            if not workspace:
                return [types.TextContent(type="text", text="❌ Workspace not found")]
            
            # Get action count
            action_count = await actions_collection.count_documents({"workspace_id": workspace_id})
            
            # Format workspace info
            workspace_info = f"**Workspace: {workspace.get('name', 'Unnamed Workspace')}**\n"
            workspace_info += f"ID: {workspace_id}\n"
            workspace_info += f"Description: {workspace.get('description', 'No description')}\n"
            workspace_info += f"Created: {workspace.get('created_at', 'Unknown')}\n"
            workspace_info += f"Total Actions: {action_count}\n"
            
            return [types.TextContent(type="text", text=workspace_info)]
            
        except Exception as e:
            from loguru import logger
            logger.error(f"Error getting workspace info: {e}")
            return [types.TextContent(type="text", text=f"❌ Failed to get workspace info: {str(e)}")]
    
    async def _handle_suggest_action_template(self, arguments: dict[str, Any]) -> list[types.Content]:
        """Handle suggest_action_template admin tool."""
        try:
            use_case = arguments.get("use_case", "")
            if not use_case:
                return [types.TextContent(type="text", text="❌ Use case description is required")]
            
            # Common action templates
            templates = {
                "email": {
                    "name": "send-email",
                    "type": "REST",
                    "description": "Send an email notification",
                    "method": "POST",
                    "url": "https://api.sendgrid.com/v3/mail/send",
                    "headers": {
                        "Authorization": "Bearer {{SENDGRID_API_KEY}}",
                        "Content-Type": "application/json"
                    },
                    "example_body": {
                        "personalizations": [{"to": [{"email": "{{recipient_email}}"}]}],
                        "from": {"email": "{{sender_email}}"},
                        "subject": "{{subject}}",
                        "content": [{"type": "text/plain", "value": "{{message}}"}]
                    }
                },
                "weather": {
                    "name": "get-weather",
                    "type": "REST",
                    "description": "Get current weather for a location",
                    "method": "GET",
                    "url": "https://api.openweathermap.org/data/2.5/weather?q={{city}}&appid={{API_KEY}}",
                    "headers": {},
                    "variables": ["city", "API_KEY"]
                },
                "task": {
                    "name": "create-task",
                    "type": "REST",
                    "description": "Create a new task in project management tool",
                    "method": "POST",
                    "url": "https://api.trello.com/1/cards",
                    "headers": {
                        "Accept": "application/json"
                    },
                    "example_body": {
                        "name": "{{task_name}}",
                        "desc": "{{task_description}}",
                        "idList": "{{list_id}}",
                        "key": "{{API_KEY}}",
                        "token": "{{API_TOKEN}}"
                    }
                },
                "slack": {
                    "name": "send-slack-message",
                    "type": "REST",
                    "description": "Send a message to Slack channel",
                    "method": "POST",
                    "url": "https://slack.com/api/chat.postMessage",
                    "headers": {
                        "Authorization": "Bearer {{SLACK_BOT_TOKEN}}",
                        "Content-Type": "application/json"
                    },
                    "example_body": {
                        "channel": "{{channel_id}}",
                        "text": "{{message}}"
                    }
                }
            }
            
            # Find matching template
            use_case_lower = use_case.lower()
            template = None
            
            for key, t in templates.items():
                if key in use_case_lower:
                    template = t
                    break
            
            if not template:
                # Default REST template
                template = {
                    "name": "custom-action",
                    "type": "REST",
                    "description": f"Custom action for: {use_case}",
                    "method": "GET",
                    "url": "https://api.example.com/endpoint",
                    "headers": {
                        "Authorization": "Bearer {{API_KEY}}"
                    },
                    "instructions": "This is a generic template. Please customize the URL, method, headers, and add any required variables."
                }
            
            # Format template response
            import json
            template_text = f"**Action Template for: {use_case}**\n\n"
            template_text += json.dumps(template, indent=2)
            
            return [types.TextContent(type="text", text=template_text)]
            
        except Exception as e:
            from loguru import logger
            logger.error(f"Error suggesting action template: {e}")
            return [types.TextContent(type="text", text=f"❌ Failed to suggest template: {str(e)}")]
    
    async def _handle_get_protobox_tips(self, arguments: dict[str, Any]) -> list[types.Content]:
        """Handle get_protobox_tips admin tool."""
        try:
            topic = arguments.get("topic", "general")
            
            tips = {
                "general": [
                    "Use descriptive names for actions (e.g., 'send-customer-email' instead of 'email')",
                    "Test your actions thoroughly before using them in production",
                    "Store sensitive data like API keys as secrets, not in action configurations",
                    "Use variables in your actions to make them reusable",
                    "Document your actions clearly so others can understand their purpose"
                ],
                "actions": [
                    "REST actions are the most common - start there for most APIs",
                    "Use {{variable_name}} syntax to create dynamic parameters",
                    "Headers often need authentication - use secrets for API keys",
                    "Test actions with sample data before connecting to AI assistants",
                    "Group related actions with consistent naming conventions"
                ],
                "security": [
                    "Never hardcode API keys or passwords in action configurations",
                    "Use ProtoBox secrets to store sensitive credentials",
                    "Limit action permissions to what's necessary",
                    "Regularly rotate API keys and update secrets",
                    "Use HTTPS endpoints whenever possible"
                ],
                "testing": [
                    "Use the Test button to verify actions work correctly",
                    "Start with simple GET requests before complex POST operations",
                    "Check response formats to ensure AI can parse them",
                    "Test error cases to ensure graceful handling",
                    "Use mock APIs for initial testing when possible"
                ],
                "mcp": [
                    "MCP allows AI assistants to discover and use your actions",
                    "Each workspace has its own MCP server endpoint",
                    "Actions are automatically exposed through MCP",
                    "Test MCP integration with the playground chat",
                    "Monitor MCP usage in execution logs"
                ]
            }
            
            selected_tips = tips.get(topic, tips["general"])
            
            # Format tips response
            tips_text = f"**ProtoBox Tips: {topic.title()}**\n"
            for i, tip in enumerate(selected_tips, 1):
                tips_text += f"{i}. {tip}\n"
            
            tips_text += f"\nAvailable topics: {', '.join(tips.keys())}"
            
            return [types.TextContent(type="text", text=tips_text)]
            
        except Exception as e:
            from loguru import logger
            logger.error(f"Error getting ProtoBox tips: {e}")
            return [types.TextContent(type="text", text=f"❌ Failed to get tips: {str(e)}")]


class ActionService(BaseService):
    """Service for managing actions."""

    def __init__(self):
        """Initialize the service.""" 
        super().__init__(ActionRepository())

    async def create_action(self, request: ActionCreateRequest, user_id: str) -> str:
        """Create a new action.

        Args:
            request: The action creation request
            user_id: ID of the user creating the action

        Returns:
            The ID of the created action

        Raises:
            DuplicateKeyError: If action name already exists in workspace
            ValueError: If action configuration is invalid
        """
        # Validate action configuration based on type
        self._validate_action_configuration(request.type, request.default_config)

        # Prepare action data and add audit fields using BaseService
        action_data = {
            "workspace_id": request.workspace_id,
            "name": request.name,
            "description": request.description,
            "type": request.type,
            "default_config": request.default_config,
            "config_schema": request.config_schema,
            "tags": request.tags,
            "status": ActionStatus.ACTIVE,
        }
        
        # Add audit fields using BaseService mixin
        action_data_with_audit = self.add_create_audit_fields(action_data, user_id)
        
        # Create action model and save
        action = ActionModel(**action_data_with_audit)
        return await self.repository.create_action(action)

    async def get_action_by_id(self, action_id: str) -> ActionModel | None:
        """Get an action by its ID.

        Args:
            action_id: The action ID

        Returns:
            The action model or None if not found
        """
        return await self.repository.get_action_by_id(action_id)

    async def list_actions(
        self,
        workspace_id: str,
        action_type: ActionType | None = None,
        status: ActionStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ActionModel]:
        """List actions for a workspace.

        Args:
            workspace_id: The workspace ID
            action_type: Optional action type filter
            status: Optional status filter
            skip: Number of actions to skip
            limit: Maximum number of actions to return

        Returns:
            List of action models
        """
        # TODO: Add role filtering
        admin_actions = await AdminToolManager.get_tools(workspace_id)
        workspace_actions = await self.repository.get_actions_by_workspace(
            workspace_id=workspace_id,
            action_type=action_type,
            status=status,
            skip=skip,
            limit=limit,
        )
        return admin_actions + workspace_actions

    async def update_action(
        self, action_id: str, request: ActionUpdateRequest, user_id: str
    ) -> bool:
        """Update an action.

        Args:
            action_id: The action ID
            request: The update request
            user_id: ID of the user updating the action

        Returns:
            True if updated successfully, False if not found
        """
        # Get existing action to validate type-specific configuration
        existing_action = await self.repository.get_action_by_id(action_id)
        if not existing_action:
            return False

        # Prepare updates
        updates = {}

        if request.name is not None:
            updates["name"] = request.name
        if request.description is not None:
            updates["description"] = request.description
        if request.tags is not None:
            updates["tags"] = request.tags
        if request.status is not None:
            updates["status"] = request.status.value

        # Handle configuration updates
        if request.configuration is not None:
            # Validate new configuration
            self._validate_action_configuration(existing_action.action_type, request.configuration)
            updates["configuration"] = request.configuration

        # Add audit fields using BaseService mixin
        if updates:  # Only add audit fields if there are actual updates
            updates_with_audit = self.add_update_audit_fields(updates, user_id)
            return await self.repository.update_action(action_id, updates_with_audit)
        
        return True  # No updates were needed

    async def delete_action(self, action_id: str) -> bool:
        """Delete an action.

        Args:
            action_id: The action ID

        Returns:
            True if deleted successfully, False if not found
        """
        return await self.repository.delete_action(action_id)

    async def get_action_by_name(self, workspace_id: str, name: str) -> ActionModel | None:
        """Get an action by workspace and name.

        Args:
            workspace_id: The workspace ID
            name: The action name

        Returns:
            The action model or None if not found
        """
        return await self.repository.get_action_by_name(workspace_id, name)

    async def count_actions(
        self,
        workspace_id: str,
        action_type: ActionType | None = None,
        status: ActionStatus | None = None,
    ) -> int:
        """Count actions for a workspace.

        Args:
            workspace_id: The workspace ID
            action_type: Optional action type filter
            status: Optional status filter

        Returns:
            Number of matching actions
        """
        return await self.repository.count_actions_by_workspace(
            workspace_id=workspace_id, action_type=action_type, status=status
        )

    async def get_action_types_info(self) -> dict[str, Any]:
        """Get information about available action types.

        Returns:
            Dictionary with action type information
        """
        return {
            "types": [
                {
                    "value": action_type.value,
                    "name": action_type.name,
                    "description": self._get_action_type_description(action_type),
                    "required_config": self._get_required_configuration(action_type),
                    "optional_config": self._get_optional_configuration(action_type),
                }
                for action_type in ActionType
            ]
        }

    def _validate_action_configuration(
        self, action_type: ActionType, configuration: dict[str, Any]
    ) -> None:
        """Validate action configuration based on type.

        Args:
            action_type: The action type
            configuration: The configuration to validate

        Raises:
            ValueError: If configuration is invalid
        """
        if action_type == ActionType.REST:
            self._validate_rest_configuration(configuration)
        elif action_type == ActionType.O3:
            self._validate_o3_configuration(configuration)
        elif action_type == ActionType.DATABASE:
            self._validate_database_configuration(configuration)
        elif action_type == ActionType.CODE_RUN:
            self._validate_code_run_configuration(configuration)

    def _validate_rest_configuration(self, configuration: dict[str, Any]) -> None:
        """Validate REST action configuration.

        Args:
            configuration: The configuration to validate

        Raises:
            ValueError: If configuration is invalid
        """
        # Required fields
        required_fields = ["url", "method"]
        for field in required_fields:
            if field not in configuration:
                raise ValueError(f"REST action missing required field: {field}")

        # Validate HTTP method
        valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
        method = configuration["method"].upper()
        if method not in valid_methods:
            raise ValueError(f"Invalid HTTP method: {method}. Must be one of {valid_methods}")

        # Validate URL format
        url = configuration["url"]
        if not isinstance(url, str) or not url.strip():
            raise ValueError("URL must be a non-empty string")
        if not (url.startswith("http://") or url.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")

        # Validate optional fields
        if "headers" in configuration:
            headers = configuration["headers"]
            if not isinstance(headers, dict):
                raise ValueError("Headers must be a dictionary")

        if "timeout" in configuration:
            timeout = configuration["timeout"]
            if not isinstance(timeout, int | float) or timeout <= 0:
                raise ValueError("Timeout must be a positive number")

        if "retry_count" in configuration:
            retry_count = configuration["retry_count"]
            if not isinstance(retry_count, int) or retry_count < 0:
                raise ValueError("Retry count must be a non-negative integer")

    def _validate_o3_configuration(self, configuration: dict[str, Any]) -> None:
        """Validate O3 action configuration.

        Args:
            configuration: The configuration to validate

        Raises:
            ValueError: If configuration is invalid
        """
        # For now, just placeholder validation
        # TODO: Implement O3-specific validation when O3 actions are implemented
        pass

    def _validate_database_configuration(self, configuration: dict[str, Any]) -> None:
        """Validate database action configuration.

        Args:
            configuration: The configuration to validate

        Raises:
            ValueError: If configuration is invalid
        """
        # For now, just placeholder validation
        # TODO: Implement database-specific validation when database actions are implemented
        pass

    def _validate_code_run_configuration(self, configuration: dict[str, Any]) -> None:
        """Validate code run action configuration.

        Args:
            configuration: The configuration to validate

        Raises:
            ValueError: If configuration is invalid
        """
        from ..models.action import CodeRunConfig
        
        try:
            # Validate using Pydantic model
            config = CodeRunConfig.model_validate(configuration)
            
            if not config.worker_name:
                raise ValueError("Worker name is required for file-based execution")
            
            if not config.dispatch_namespace:
                raise ValueError("Dispatch namespace is required for file-based execution")
            
            # Validate timeout and memory limits
            if config.timeout < 1 or config.timeout > 300:
                raise ValueError("Timeout must be between 1 and 300 seconds")
            
            if config.memory_limit_mb < 1 or config.memory_limit_mb > 1024:
                raise ValueError("Memory limit must be between 1 and 1024 MB")
                    
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Invalid CODE_RUN configuration: {str(e)}")

    def _get_action_type_description(self, action_type: ActionType) -> str:
        """Get description for an action type.

        Args:
            action_type: The action type

        Returns:
            Description string
        """
        descriptions = {
            ActionType.REST: "HTTP REST API calls with configurable methods, headers, and authentication",
            ActionType.O3: "O3 reasoning model interactions for complex problem solving",
            ActionType.DATABASE: "Database operations including queries, updates, and schema modifications",
            ActionType.CODE_RUN: "Execute Python and JavaScript code in isolated environments",
            ActionType.KNOWLEDGE_BASE: "Search and retrieve information from workspace knowledge base",
            ActionType.ADMIN: "Administrative tools for workspace management",
        }
        return descriptions.get(action_type, f"Action type: {action_type.value}")

    def _get_required_configuration(self, action_type: ActionType) -> list[dict[str, Any]]:
        """Get required configuration fields for an action type.

        Args:
            action_type: The action type

        Returns:
            List of required configuration field definitions
        """
        if action_type == ActionType.REST:
            return [
                {"name": "url", "type": "string", "description": "HTTP URL endpoint"},
                {
                    "name": "method",
                    "type": "string",
                    "description": "HTTP method (GET, POST, PUT, DELETE, etc.)",
                },
            ]
        elif action_type == ActionType.CODE_RUN:
            return [
                {
                    "name": "execution_type",
                    "type": "string",
                    "description": "How code is provided (file-based via Cloudflare Workers for Platforms)",
                },
                {
                    "name": "language",
                    "type": "string",
                    "description": "Programming language (python, javascript)",
                },
                {
                    "name": "worker_name",
                    "type": "string",
                    "description": "Cloudflare worker name for dispatch",
                },
                {
                    "name": "dispatch_namespace",
                    "type": "string",
                    "description": "Dispatch namespace name",
                },
            ]

        # For other types, return empty for now
        return []

    def _get_optional_configuration(self, action_type: ActionType) -> list[dict[str, Any]]:
        """Get optional configuration fields for an action type.

        Args:
            action_type: The action type

        Returns:
            List of optional configuration field definitions
        """
        if action_type == ActionType.REST:
            return [
                {"name": "headers", "type": "object", "description": "HTTP headers to include"},
                {"name": "body", "type": "string", "description": "Request body data"},
                {"name": "timeout", "type": "number", "description": "Request timeout in seconds"},
                {
                    "name": "retry_count",
                    "type": "integer",
                    "description": "Number of retry attempts",
                },
                {
                    "name": "follow_redirects",
                    "type": "boolean",
                    "description": "Whether to follow redirects",
                },
                {
                    "name": "verify_ssl",
                    "type": "boolean",
                    "description": "Whether to verify SSL certificates",
                },
            ]
        elif action_type == ActionType.CODE_RUN:
            return [
                {"name": "entry_point", "type": "string", "description": "Entry point file/function name"},
                {"name": "timeout", "type": "integer", "description": "Execution timeout in seconds"},
                {"name": "memory_limit_mb", "type": "integer", "description": "Memory limit in MB"},
                {"name": "dependencies", "type": "array", "description": "Required packages/libraries"},
                {"name": "allowed_imports", "type": "array", "description": "Allowed import modules"},
                {"name": "allow_network", "type": "boolean", "description": "Allow network requests"},
                {"name": "allow_file_ops", "type": "boolean", "description": "Allow file operations"},
            ]

        # For other types, return empty for now
        return []
