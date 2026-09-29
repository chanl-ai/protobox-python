"""Prompt service for managing MCP prompts."""

import re
from datetime import UTC, datetime
from typing import Any

from ..constants import SystemUsers
from ..database.repositories.prompt_repository import PromptRepository
from ..models.mcp_prompt import (
    MCPPromptCreateRequest,
    MCPPromptExecuteResponse,
    MCPPromptExtendRequest,
    MCPPromptModel,
    MCPPromptResolvedResponse,
    MCPPromptUpdateRequest,
    PromptArgument,
    PromptMessage,
    PromptVersionModel,
)
from .base_service import BaseService


class PromptValidationError(Exception):
    """Raised when prompt validation fails."""
    pass


class PromptService(BaseService):
    """Service for managing MCP prompts."""

    def __init__(self):
        """Initialize the prompt service."""
        super().__init__()
        self.repository = PromptRepository()

    async def create_prompt(
        self,
        workspace_id: str,
        prompt_data: MCPPromptCreateRequest,
        user_id: str
    ) -> MCPPromptModel:
        """Create a new prompt.

        Args:
            workspace_id: The workspace ID
            prompt_data: The prompt creation data
            user_id: The user creating the prompt

        Returns:
            The created prompt model

        Raises:
            PromptValidationError: If prompt validation fails
            DuplicateKeyError: If prompt name already exists
        """
        # Validate inheritance if applicable
        if prompt_data.extends:
            await self._validate_inheritance(workspace_id, prompt_data.extends)

        # Validate prompt template (after resolving inheritance)
        if prompt_data.extends:
            resolved = await self.resolve_inheritance(prompt_data.model_dump())
            self._validate_prompt_template(resolved["messages"], resolved["arguments"])
        else:
            self._validate_prompt_template(prompt_data.messages, prompt_data.arguments)

        # Prepare data with audit fields
        prompt_dict = prompt_data.model_dump(exclude_none=True)
        prompt_dict["workspace_id"] = workspace_id

        audit_data = self.add_create_audit_fields(prompt_dict, user_id)

        # Create the prompt model
        prompt = MCPPromptModel(**audit_data)

        # Save to database
        prompt_id = await self.repository.create_prompt(prompt)
        prompt.id = prompt_id

        return prompt

    async def get_prompt(self, workspace_id: str, prompt_name: str) -> MCPPromptModel | None:
        """Get a prompt by name.

        Args:
            workspace_id: The workspace ID
            prompt_name: The prompt name

        Returns:
            The prompt model or None if not found
        """
        return await self.repository.get_prompt_by_name(workspace_id, prompt_name)

    async def get_prompt_by_id(self, prompt_id: str) -> MCPPromptModel | None:
        """Get a prompt by ID.

        Args:
            prompt_id: The prompt ID

        Returns:
            The prompt model or None if not found
        """
        return await self.repository.get_prompt_by_id(prompt_id)

    async def list_prompts(
        self,
        workspace_id: str,
        category: str | None = None,
        tags: list[str] | None = None,
        is_active: bool | None = None,
        is_system: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[MCPPromptModel]:
        """List prompts for a workspace.

        Args:
            workspace_id: The workspace ID
            category: Optional category filter
            tags: Optional tags filter
            is_active: Optional active status filter
            is_system: Optional system status filter
            skip: Number of prompts to skip
            limit: Maximum number of prompts to return

        Returns:
            List of prompt models
        """
        return await self.repository.get_prompts_by_workspace(
            workspace_id=workspace_id,
            category=category,
            tags=tags,
            is_active=is_active,
            is_system=is_system,
            skip=skip,
            limit=limit
        )

    async def update_prompt(
        self,
        workspace_id: str,
        prompt_name: str,
        updates: MCPPromptUpdateRequest,
        user_id: str
    ) -> MCPPromptModel | None:
        """Update a prompt.

        Args:
            workspace_id: The workspace ID
            prompt_name: The prompt name
            updates: The updates to apply
            user_id: The user updating the prompt

        Returns:
            The updated prompt model or None if not found

        Raises:
            PromptValidationError: If validation fails
        """
        # Get existing prompt
        existing_prompt = await self.get_prompt(workspace_id, prompt_name)
        if not existing_prompt:
            return None

        # Validate updates if messages or arguments are being changed
        update_data = updates.model_dump(exclude_none=True)

        if "messages" in update_data or "arguments" in update_data:
            # Get the final messages and arguments after updates
            final_messages = update_data.get("messages", existing_prompt.messages)
            final_arguments = update_data.get("arguments", existing_prompt.arguments)

            self._validate_prompt_template(final_messages, final_arguments)

        # Add audit fields
        audit_updates = self.add_update_audit_fields(update_data, user_id)

        # Update in database
        return await self.repository.update_prompt(existing_prompt.id_str, audit_updates)

    async def delete_prompt(self, workspace_id: str, prompt_name: str) -> bool:
        """Delete a prompt.

        Args:
            workspace_id: The workspace ID
            prompt_name: The prompt name

        Returns:
            True if deleted, False if not found
        """
        # Get existing prompt to verify workspace
        existing_prompt = await self.get_prompt(workspace_id, prompt_name)
        if not existing_prompt:
            return False

        return await self.repository.delete_prompt(existing_prompt.id_str)

    async def update_prompt_by_id(
        self,
        prompt_id: str,
        updates: MCPPromptUpdateRequest,
        user_id: str
    ) -> MCPPromptModel | None:
        """Update a prompt by ID.

        Args:
            prompt_id: The prompt ID
            updates: The updates to apply
            user_id: The user updating the prompt

        Returns:
            The updated prompt model or None if not found

        Raises:
            PromptValidationError: If validation fails
        """
        # Get existing prompt
        existing_prompt = await self.get_prompt_by_id(prompt_id)
        if not existing_prompt:
            return None

        # Validate updates if messages or arguments are being changed
        update_data = updates.model_dump(exclude_none=True)

        if "messages" in update_data or "arguments" in update_data:
            # Get the final messages and arguments after updates
            final_messages = update_data.get("messages", existing_prompt.messages)
            final_arguments = update_data.get("arguments", existing_prompt.arguments)

            # Convert dict messages to PromptMessage objects if needed
            if final_messages and isinstance(final_messages[0], dict):
                final_messages = [PromptMessage(**msg) for msg in final_messages]

            # Convert dict arguments to PromptArgument objects if needed
            if final_arguments and isinstance(final_arguments[0], dict):
                final_arguments = [PromptArgument(**arg) for arg in final_arguments]

            self._validate_prompt_template(final_messages, final_arguments)

        # Check if significant changes are being made
        has_significant_changes = any(
            field in update_data
            for field in ["messages", "arguments", "name", "description"]
        )

        if has_significant_changes:
            # Save current state as a version before updating
            await self.save_version_snapshot(prompt_id, "Before update")

            # Increment version number
            update_data["version"] = existing_prompt.version + 1

        # Add audit fields
        audit_updates = self.add_update_audit_fields(update_data, user_id)

        # Update in database
        updated_prompt = await self.repository.update_prompt(prompt_id, audit_updates)

        if has_significant_changes and updated_prompt:
            # Save the new state as a version
            change_summary = []
            if "name" in update_data:
                change_summary.append("Updated name")
            if "description" in update_data:
                change_summary.append("Updated description")
            if "messages" in update_data:
                change_summary.append("Updated messages")
            if "arguments" in update_data:
                change_summary.append("Updated arguments")

            await self.save_version_snapshot(
                prompt_id,
                ", ".join(change_summary) if change_summary else "Updated prompt"
            )

        return updated_prompt

    async def delete_prompt_by_id(self, prompt_id: str) -> bool:
        """Delete a prompt by ID.

        Args:
            prompt_id: The prompt ID

        Returns:
            True if deleted, False if not found
        """
        return await self.repository.delete_prompt(prompt_id)

    async def execute_prompt_by_id(
        self,
        prompt_id: str,
        arguments: dict[str, Any]
    ) -> MCPPromptExecuteResponse:
        """Execute/render a prompt by ID with provided arguments.

        Args:
            prompt_id: The prompt ID
            arguments: Arguments to substitute in template

        Returns:
            The execution response with rendered messages

        Raises:
            PromptValidationError: If prompt not found or validation fails
        """
        start_time = datetime.now(UTC)

        # Get the prompt
        prompt = await self.get_prompt_by_id(prompt_id)
        if not prompt:
            raise PromptValidationError(f"Prompt with ID '{prompt_id}' not found")

        if not prompt.is_active:
            raise PromptValidationError(f"Prompt with ID '{prompt_id}' is not active")

        # Resolve inheritance if applicable
        if prompt.extends:
            resolved = await self.resolve_inheritance(prompt.model_dump())
            resolved_messages = [
                PromptMessage(**msg) if isinstance(msg, dict) else msg
                for msg in resolved["messages"]
            ]
            resolved_arguments = [
                PromptArgument(**arg) if isinstance(arg, dict) else arg
                for arg in resolved["arguments"]
            ]
            # Merge workspace variables with provided arguments
            merged_arguments = {**resolved.get("variables", {}), **arguments}
        else:
            resolved_messages = prompt.messages
            resolved_arguments = prompt.arguments
            merged_arguments = arguments

        # Validate arguments against resolved template
        validation_result = self._validate_arguments_against_list(resolved_arguments, merged_arguments)

        if not validation_result["valid"]:
            raise PromptValidationError(f"Argument validation failed: {validation_result}")

        # Render messages with merged arguments
        rendered_messages = []
        for message in resolved_messages:
            rendered_content = self.render_template(message.content, merged_arguments)
            rendered_messages.append({
                "role": message.role,
                "content": rendered_content
            })

        # Track usage (using prompt name for consistency)
        await self.track_usage(prompt.workspace_id, prompt.name)

        execution_time = (datetime.now(UTC) - start_time).total_seconds() * 1000

        return MCPPromptExecuteResponse(
            rendered_messages=rendered_messages,
            argument_validation=validation_result,
            execution_time_ms=int(execution_time)
        )

    async def execute_prompt(
        self,
        workspace_id: str,
        prompt_name: str,
        arguments: dict[str, Any]
    ) -> MCPPromptExecuteResponse:
        """Execute/render a prompt with provided arguments.

        Args:
            workspace_id: The workspace ID
            prompt_name: The prompt name
            arguments: Arguments to substitute in template

        Returns:
            The execution response with rendered messages

        Raises:
            PromptValidationError: If prompt not found or validation fails
        """
        start_time = datetime.now(UTC)

        # Get the prompt
        prompt = await self.get_prompt(workspace_id, prompt_name)
        if not prompt:
            raise PromptValidationError(f"Prompt '{prompt_name}' not found")

        if not prompt.is_active:
            raise PromptValidationError(f"Prompt '{prompt_name}' is not active")

        # Validate arguments
        validation_result = self.validate_arguments(prompt, arguments)

        if not validation_result["valid"]:
            raise PromptValidationError(f"Argument validation failed: {validation_result}")

        # Render messages
        rendered_messages = []
        for message in prompt.messages:
            rendered_content = self.render_template(message.content, arguments)
            rendered_messages.append({
                "role": message.role,
                "content": rendered_content
            })

        # Track usage
        await self.track_usage(workspace_id, prompt_name)

        execution_time = (datetime.now(UTC) - start_time).total_seconds() * 1000

        return MCPPromptExecuteResponse(
            rendered_messages=rendered_messages,
            argument_validation=validation_result,
            execution_time_ms=int(execution_time)
        )

    def validate_arguments(self, prompt: MCPPromptModel, provided_args: dict[str, Any]) -> dict[str, Any]:
        """Validate provided arguments against prompt requirements.

        Args:
            prompt: The prompt model
            provided_args: Arguments provided by user

        Returns:
            Validation result dictionary
        """
        result = {
            "valid": True,
            "missing_required": [],
            "invalid_types": [],
            "warnings": []
        }

        # Check required arguments
        for arg in prompt.arguments:
            if arg.required and arg.name not in provided_args:
                result["missing_required"].append(arg.name)
                result["valid"] = False

        # Type validation (basic)
        for arg in prompt.arguments:
            if arg.name in provided_args:
                value = provided_args[arg.name]
                if not self._validate_argument_type(value, arg.type):
                    result["invalid_types"].append({
                        "argument": arg.name,
                        "expected": arg.type,
                        "provided": type(value).__name__
                    })
                    result["valid"] = False

        # Check for unused arguments
        expected_args = {arg.name for arg in prompt.arguments}
        provided_arg_names = set(provided_args.keys())
        unused_args = provided_arg_names - expected_args

        if unused_args:
            result["warnings"].append(f"Unused arguments: {list(unused_args)}")

        return result

    def _validate_arguments_against_list(self, argument_definitions: list[PromptArgument], provided_args: dict[str, Any]) -> dict[str, Any]:
        """Validate provided arguments against a list of argument definitions.

        Args:
            argument_definitions: List of argument definitions
            provided_args: Arguments provided by user

        Returns:
            Validation result dictionary
        """
        result = {
            "valid": True,
            "missing_required": [],
            "invalid_types": [],
            "warnings": []
        }

        # Check required arguments
        for arg in argument_definitions:
            if arg.required and arg.name not in provided_args:
                result["missing_required"].append(arg.name)
                result["valid"] = False

        # Type validation (basic)
        for arg in argument_definitions:
            if arg.name in provided_args:
                value = provided_args[arg.name]
                if not self._validate_argument_type(value, arg.type):
                    result["invalid_types"].append({
                        "argument": arg.name,
                        "expected": arg.type,
                        "provided": type(value).__name__
                    })
                    result["valid"] = False

        # Check for unused arguments
        expected_args = {arg.name for arg in argument_definitions}
        provided_arg_names = set(provided_args.keys())
        unused_args = provided_arg_names - expected_args

        if unused_args:
            result["warnings"].append(f"Unused arguments: {list(unused_args)}")

        return result

    def render_template(self, template: str, arguments: dict[str, Any]) -> str:
        """Render a template string with provided arguments.

        Args:
            template: Template string with {{variable}} placeholders
            arguments: Arguments to substitute

        Returns:
            Rendered string
        """
        # Find all variables in template
        variables = re.findall(r'\{\{(\w+)\}\}', template)

        rendered = template
        for var in variables:
            if var in arguments:
                # Convert value to string
                value = str(arguments[var])
                # Replace all occurrences of {{var}}
                rendered = rendered.replace(f'{{{{{var}}}}}', value)
            # If variable not provided, leave placeholder as-is

        return rendered

    async def track_usage(self, workspace_id: str, prompt_name: str) -> None:
        """Track usage of a prompt.

        Args:
            workspace_id: The workspace ID
            prompt_name: The prompt name
        """
        prompt = await self.get_prompt(workspace_id, prompt_name)
        if prompt:
            await self.repository.increment_usage_count(prompt.id_str)

    async def get_usage_stats(self, workspace_id: str, days: int = 30) -> dict[str, Any]:
        """Get usage statistics for prompts in a workspace.

        Args:
            workspace_id: The workspace ID
            days: Number of days to look back

        Returns:
            Usage statistics
        """
        return await self.repository.get_usage_stats(workspace_id, days)

    async def count_prompts(
        self,
        workspace_id: str,
        category: str | None = None,
        tags: list[str] | None = None,
        is_active: bool | None = None,
        is_system: bool | None = None,
    ) -> int:
        """Count prompts for a workspace.

        Args:
            workspace_id: The workspace ID
            category: Optional category filter
            tags: Optional tags filter
            is_active: Optional active status filter
            is_system: Optional system status filter

        Returns:
            Number of matching prompts
        """
        return await self.repository.count_prompts_by_workspace(
            workspace_id=workspace_id,
            category=category,
            tags=tags,
            is_active=is_active,
            is_system=is_system
        )

    async def list_templates(self, workspace_id: str) -> list[MCPPromptModel]:
        """List all templates in a workspace.

        Args:
            workspace_id: The workspace ID

        Returns:
            List of template prompt models
        """
        return await self.repository.get_templates_by_workspace(workspace_id)

    async def create_prompt_from_template(
        self,
        workspace_id: str,
        template_id: str,
        extend_data: MCPPromptExtendRequest,
        user_id: str
    ) -> MCPPromptModel:
        """Create a new prompt extending from a template.

        Args:
            workspace_id: The workspace ID
            template_id: The ID of the template to extend
            extend_data: The extension data
            user_id: The user creating the prompt

        Returns:
            The created prompt model

        Raises:
            PromptValidationError: If validation fails
        """
        # Get the template
        template = await self.get_prompt_by_id(template_id)
        if not template:
            raise PromptValidationError(f"Template with ID '{template_id}' not found")

        if not template.is_template:
            raise PromptValidationError(f"Prompt '{template.name}' is not marked as a template")

        if template.workspace_id != workspace_id:
            raise PromptValidationError("Template must be in the same workspace")

        # Validate inheritance depth
        inheritance_chain = await self._get_inheritance_chain(template_id)
        if len(inheritance_chain) >= 5:  # Max depth of 5
            raise PromptValidationError("Maximum inheritance depth exceeded (5 levels)")

        # Create the new prompt
        prompt_data = MCPPromptCreateRequest(
            workspace_id=workspace_id,
            name=extend_data.name,
            description=extend_data.description,
            messages=template.messages,  # Start with template messages
            arguments=template.arguments,  # Start with template arguments
            extends=template_id,
            override_messages=extend_data.override_messages,
            override_arguments=extend_data.override_arguments,
            workspace_variables=extend_data.workspace_variables,
            category=extend_data.category,
            tags=extend_data.tags,
            is_active=extend_data.is_active
        )

        # Validate the resolved prompt
        resolved = await self.resolve_inheritance(prompt_data.model_dump())
        self._validate_prompt_template(resolved["messages"], resolved["arguments"])

        return await self.create_prompt(workspace_id, prompt_data, user_id)

    async def resolve_inheritance(self, prompt_data: dict) -> dict:
        """Resolve inheritance for a prompt, merging with parent templates.

        Args:
            prompt_data: The prompt data dictionary

        Returns:
            Dictionary with resolved messages, arguments, and variables

        Raises:
            PromptValidationError: If circular dependency detected or template not found
        """
        if not prompt_data.get("extends"):
            # No inheritance, return as-is
            return {
                "messages": prompt_data.get("messages", []),
                "arguments": prompt_data.get("arguments", []),
                "variables": prompt_data.get("workspace_variables", {}),
                "inheritance_chain": [],
                "resolution_depth": 0
            }

        # Build inheritance chain and detect circular dependencies
        inheritance_chain = await self._get_inheritance_chain(prompt_data["extends"])

        # Resolve from root parent down to current prompt
        resolved_messages = []
        resolved_arguments = []
        resolved_variables = {}

        # Start with the root template and work down
        for template_id in reversed(inheritance_chain):
            template = await self.get_prompt_by_id(template_id)
            if not template:
                raise PromptValidationError(f"Template '{template_id}' not found in inheritance chain")

            # Merge messages
            if template.messages:
                resolved_messages = self._merge_messages(resolved_messages, template.messages)

            # Merge arguments
            if template.arguments:
                resolved_arguments = self._merge_arguments(resolved_arguments, template.arguments)

            # Merge variables
            if template.workspace_variables:
                resolved_variables.update(template.workspace_variables)

        # Apply current prompt's overrides
        if prompt_data.get("override_messages"):
            resolved_messages = self._merge_messages(resolved_messages, prompt_data["override_messages"])
        elif prompt_data.get("messages"):
            resolved_messages = prompt_data["messages"]

        if prompt_data.get("override_arguments"):
            resolved_arguments = self._merge_arguments(resolved_arguments, prompt_data["override_arguments"])
        elif prompt_data.get("arguments"):
            resolved_arguments = prompt_data["arguments"]

        if prompt_data.get("workspace_variables"):
            resolved_variables.update(prompt_data["workspace_variables"])

        return {
            "messages": resolved_messages,
            "arguments": resolved_arguments,
            "variables": resolved_variables,
            "inheritance_chain": inheritance_chain,
            "resolution_depth": len(inheritance_chain)
        }

    async def get_resolved_prompt(self, prompt_id: str) -> MCPPromptResolvedResponse:
        """Get a fully resolved prompt with inheritance applied.

        Args:
            prompt_id: The prompt ID

        Returns:
            Resolved prompt response

        Raises:
            PromptValidationError: If prompt not found
        """
        prompt = await self.get_prompt_by_id(prompt_id)
        if not prompt:
            raise PromptValidationError(f"Prompt with ID '{prompt_id}' not found")

        resolved = await self.resolve_inheritance(prompt.model_dump())

        # Convert to PromptMessage and PromptArgument objects
        resolved_messages = [
            PromptMessage(**msg) if isinstance(msg, dict) else msg
            for msg in resolved["messages"]
        ]
        resolved_arguments = [
            PromptArgument(**arg) if isinstance(arg, dict) else arg
            for arg in resolved["arguments"]
        ]

        return MCPPromptResolvedResponse(
            prompt=prompt,
            resolved_messages=resolved_messages,
            resolved_arguments=resolved_arguments,
            resolved_variables=resolved["variables"],
            inheritance_chain=resolved["inheritance_chain"],
            resolution_depth=resolved["resolution_depth"]
        )

    async def _get_inheritance_chain(self, template_id: str, visited: set | None = None) -> list[str]:
        """Get the inheritance chain for a template, detecting circular dependencies.

        Args:
            template_id: The template ID to start from
            visited: Set of visited template IDs for circular dependency detection

        Returns:
            List of template IDs in inheritance order (parent to child)

        Raises:
            PromptValidationError: If circular dependency detected
        """
        if visited is None:
            visited = set()

        if template_id in visited:
            raise PromptValidationError(f"Circular dependency detected in template inheritance: {template_id}")

        visited.add(template_id)

        template = await self.get_prompt_by_id(template_id)
        if not template:
            raise PromptValidationError(f"Template '{template_id}' not found")

        if not template.extends:
            # This is the root template
            return [template_id]

        # Recursively get parent chain
        parent_chain = await self._get_inheritance_chain(template.extends, visited.copy())
        return parent_chain + [template_id]

    def _merge_messages(self, base_messages: list, override_messages: list) -> list:
        """Merge message lists, with overrides taking precedence by role.

        Args:
            base_messages: Base messages list
            override_messages: Override messages list

        Returns:
            Merged messages list
        """
        # Convert to dict by role for easier merging
        result = {}

        # Add base messages
        for msg in base_messages:
            if isinstance(msg, dict):
                result[msg["role"]] = msg
            else:
                result[msg.role] = {"role": msg.role, "content": msg.content}

        # Override with new messages
        for msg in override_messages:
            if isinstance(msg, dict):
                result[msg["role"]] = msg
            else:
                result[msg.role] = {"role": msg.role, "content": msg.content}

        # Convert back to list, preserving system, user, assistant order
        ordered_roles = ["system", "user", "assistant"]
        ordered_messages = []

        for role in ordered_roles:
            if role in result:
                ordered_messages.append(result[role])

        # Add any other roles that weren't in the standard order
        for role, msg in result.items():
            if role not in ordered_roles:
                ordered_messages.append(msg)

        return ordered_messages

    def _merge_arguments(self, base_arguments: list, override_arguments: list) -> list:
        """Merge argument lists, with overrides taking precedence by name.

        Args:
            base_arguments: Base arguments list
            override_arguments: Override arguments list

        Returns:
            Merged arguments list
        """
        # Convert to dict by name for easier merging
        result = {}

        # Add base arguments
        for arg in base_arguments:
            if isinstance(arg, dict):
                result[arg["name"]] = arg
            else:
                result[arg.name] = arg.model_dump()

        # Override with new arguments
        for arg in override_arguments:
            if isinstance(arg, dict):
                result[arg["name"]] = arg
            else:
                result[arg.name] = arg.model_dump()

        # Convert back to list, preserving original order where possible
        return list(result.values())

    async def _validate_inheritance(self, workspace_id: str, parent_id: str) -> None:
        """Validate inheritance rules.

        Args:
            workspace_id: The workspace ID
            parent_id: The parent template ID to extend from

        Raises:
            PromptValidationError: If inheritance validation fails
        """
        # Check if parent exists
        parent = await self.get_prompt_by_id(parent_id)
        if not parent:
            raise PromptValidationError(f"Parent template '{parent_id}' not found")

        # Check if parent is in same workspace
        if parent.workspace_id != workspace_id:
            raise PromptValidationError("Templates can only extend templates in the same workspace")

        # Check if parent is marked as template
        if not parent.is_template:
            raise PromptValidationError(f"Cannot extend from '{parent.name}' - it is not marked as a template")

        # Check inheritance depth
        try:
            inheritance_chain = await self._get_inheritance_chain(parent_id)
            if len(inheritance_chain) >= 5:  # Max depth of 5
                raise PromptValidationError("Maximum inheritance depth exceeded (5 levels)")
        except PromptValidationError as e:
            # Re-raise circular dependency or other inheritance errors
            raise e

    def _validate_prompt_template(self, messages: list[PromptMessage], arguments: list[PromptArgument]) -> None:
        """Validate prompt template consistency.

        Args:
            messages: List of prompt messages
            arguments: List of prompt arguments

        Raises:
            PromptValidationError: If validation fails
        """
        if not messages:
            raise PromptValidationError("Prompt must have at least one message")

        # Extract all variables from all messages
        all_variables = set()
        for message in messages:
            variables = re.findall(r'\{\{(\w+)\}\}', message.content)
            all_variables.update(variables)

        # Check that all variables have corresponding arguments
        argument_names = {arg.name for arg in arguments}

        missing_args = all_variables - argument_names
        if missing_args:
            raise PromptValidationError(
                f"Template variables without corresponding arguments: {list(missing_args)}"
            )

        # Check for unused arguments (warning, not error)
        unused_args = argument_names - all_variables
        if unused_args:
            # This is just a warning, not a validation error
            pass

    def _validate_argument_type(self, value: Any, expected_type: str) -> bool:
        """Validate argument type.

        Args:
            value: The value to validate
            expected_type: Expected type string

        Returns:
            True if valid, False otherwise
        """
        type_mapping = {
            "string": str,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict
        }

        expected_python_type = type_mapping.get(expected_type)
        if not expected_python_type:
            return True  # Unknown type, assume valid

        return isinstance(value, expected_python_type)

    async def create_default_system_prompts(self, workspace_id: str) -> list[MCPPromptModel]:
        """Create default system prompts for a new workspace.

        Args:
            workspace_id: The workspace ID

        Returns:
            List of created system prompts
        """
        system_prompts = [
            {
                "name": "code_review",
                "description": "Review code for quality, security, and best practices",
                "category": "development",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a senior software engineer reviewing {{language}} code. Focus on code quality, security vulnerabilities, performance issues, and adherence to best practices. Provide specific, actionable feedback."
                    },
                    {
                        "role": "user",
                        "content": "Please review this {{language}} code and provide feedback:\n\n{{code}}"
                    }
                ],
                "arguments": [
                    {
                        "name": "language",
                        "description": "Programming language (e.g., Python, JavaScript, Go)",
                        "type": "string",
                        "required": True
                    },
                    {
                        "name": "code",
                        "description": "Code to review",
                        "type": "string",
                        "required": True
                    }
                ],
                "tags": ["code", "review", "quality", "security"]
            },
            {
                "name": "api_documentation",
                "description": "Generate comprehensive API documentation from code",
                "category": "documentation",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a technical writer specializing in API documentation. Generate clear, comprehensive documentation for the {{api_type}} API endpoint provided. Include description, parameters, request/response examples, error codes, and usage notes."
                    },
                    {
                        "role": "user",
                        "content": "Generate API documentation for this {{api_type}} endpoint:\n\n{{code}}"
                    }
                ],
                "arguments": [
                    {
                        "name": "api_type",
                        "description": "Type of API (REST, GraphQL, gRPC, etc.)",
                        "type": "string",
                        "required": True
                    },
                    {
                        "name": "code",
                        "description": "API endpoint code or schema",
                        "type": "string",
                        "required": True
                    }
                ],
                "tags": ["api", "documentation", "technical-writing"]
            },
            {
                "name": "test_generation",
                "description": "Generate unit tests for functions and classes",
                "category": "testing",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a QA engineer specializing in test automation. Generate comprehensive unit tests for the provided {{language}} code. Include positive test cases, negative test cases, edge cases, and proper assertions using the {{test_framework}} framework."
                    },
                    {
                        "role": "user",
                        "content": "Generate unit tests for this {{language}} code:\n\n{{code}}"
                    }
                ],
                "arguments": [
                    {
                        "name": "language",
                        "description": "Programming language",
                        "type": "string",
                        "required": True
                    },
                    {
                        "name": "code",
                        "description": "Code to test",
                        "type": "string",
                        "required": True
                    },
                    {
                        "name": "test_framework",
                        "description": "Testing framework to use",
                        "type": "string",
                        "required": False,
                        "default": "pytest"
                    }
                ],
                "tags": ["testing", "unit-tests", "qa", "automation"]
            },
            {
                "name": "bug_analysis",
                "description": "Analyze bugs and suggest fixes",
                "category": "debugging",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a debugging expert. Analyze the provided error/bug information and suggest potential causes and fixes. Consider the {{context}} and provide step-by-step troubleshooting guidance."
                    },
                    {
                        "role": "user",
                        "content": "Analyze this bug and suggest fixes:\n\nError: {{error}}\n\nCode: {{code}}\n\nContext: {{context}}"
                    }
                ],
                "arguments": [
                    {
                        "name": "error",
                        "description": "Error message or bug description",
                        "type": "string",
                        "required": True
                    },
                    {
                        "name": "code",
                        "description": "Relevant code snippet",
                        "type": "string",
                        "required": True
                    },
                    {
                        "name": "context",
                        "description": "Additional context (environment, steps to reproduce, etc.)",
                        "type": "string",
                        "required": False,
                        "default": "No additional context provided"
                    }
                ],
                "tags": ["debugging", "troubleshooting", "error-analysis"]
            },
            {
                "name": "data_query",
                "description": "Convert natural language to database queries",
                "category": "data",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a database expert. Convert the natural language query into a {{query_type}} query for the provided schema. Ensure the query is efficient, secure, and follows best practices."
                    },
                    {
                        "role": "user",
                        "content": "Schema:\n{{schema}}\n\nConvert this natural language query to {{query_type}}:\n{{natural_query}}"
                    }
                ],
                "arguments": [
                    {
                        "name": "natural_query",
                        "description": "Natural language description of desired query",
                        "type": "string",
                        "required": True
                    },
                    {
                        "name": "schema",
                        "description": "Database schema or table structure",
                        "type": "string",
                        "required": True
                    },
                    {
                        "name": "query_type",
                        "description": "Type of query (SQL, MongoDB, GraphQL, etc.)",
                        "type": "string",
                        "required": False,
                        "default": "SQL"
                    }
                ],
                "tags": ["database", "sql", "query", "data-analysis"]
            },
            {
                "name": "content_summary",
                "description": "Summarize documents and content from knowledge base",
                "category": "analysis",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a content analyst. Create a {{summary_type}} summary of the provided content. Focus on key points, main ideas, and actionable insights."
                    },
                    {
                        "role": "user",
                        "content": "Create a {{summary_type}} summary of this content:\n\n{{content}}"
                    }
                ],
                "arguments": [
                    {
                        "name": "content",
                        "description": "Content to summarize",
                        "type": "string",
                        "required": True
                    },
                    {
                        "name": "summary_type",
                        "description": "Type of summary (brief, detailed, bullet-points, executive)",
                        "type": "string",
                        "required": False,
                        "default": "brief"
                    }
                ],
                "tags": ["summary", "analysis", "content", "knowledge-base"]
            },
            {
                "name": "translation",
                "description": "Translate content between languages",
                "category": "localization",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a professional translator. Translate the provided text from {{source_language}} to {{target_language}}. Maintain the original meaning, tone, and context while ensuring natural fluency in the target language."
                    },
                    {
                        "role": "user",
                        "content": "Translate this text from {{source_language}} to {{target_language}}:\n\n{{text}}"
                    }
                ],
                "arguments": [
                    {
                        "name": "text",
                        "description": "Text to translate",
                        "type": "string",
                        "required": True
                    },
                    {
                        "name": "source_language",
                        "description": "Source language",
                        "type": "string",
                        "required": True
                    },
                    {
                        "name": "target_language",
                        "description": "Target language",
                        "type": "string",
                        "required": True
                    }
                ],
                "tags": ["translation", "localization", "language"]
            },
            {
                "name": "refactoring",
                "description": "Suggest code refactoring improvements",
                "category": "development",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a software architecture expert. Analyze the provided {{language}} code and suggest refactoring improvements. Focus on {{focus_areas}}. Provide specific recommendations with code examples."
                    },
                    {
                        "role": "user",
                        "content": "Suggest refactoring improvements for this {{language}} code:\n\n{{code}}"
                    }
                ],
                "arguments": [
                    {
                        "name": "code",
                        "description": "Code to refactor",
                        "type": "string",
                        "required": True
                    },
                    {
                        "name": "language",
                        "description": "Programming language",
                        "type": "string",
                        "required": True
                    },
                    {
                        "name": "focus_areas",
                        "description": "Areas to focus on (performance, readability, maintainability, etc.)",
                        "type": "string",
                        "required": False,
                        "default": "readability, maintainability, performance"
                    }
                ],
                "tags": ["refactoring", "code-quality", "architecture", "improvement"]
            }
        ]

        created_prompts = []
        for prompt_data in system_prompts:
            try:
                # Convert to proper models
                messages = [PromptMessage(**msg) for msg in prompt_data["messages"]]
                arguments = [PromptArgument(**arg) for arg in prompt_data["arguments"]]

                prompt_request = MCPPromptCreateRequest(
                    workspace_id=workspace_id,
                    name=prompt_data["name"],
                    description=prompt_data["description"],
                    category=prompt_data["category"],
                    messages=messages,
                    arguments=arguments,
                    tags=prompt_data["tags"],
                    is_active=True
                )

                prompt = await self.create_prompt(
                    workspace_id=workspace_id,
                    prompt_data=prompt_request,
                    user_id=SystemUsers.SYSTEM
                )

                # Mark as system prompt
                await self.repository.update_prompt(
                    prompt.id_str,
                    {"is_system": True}
                )

                created_prompts.append(prompt)

            except Exception as e:
                # Log error but continue with other prompts
                print(f"Failed to create system prompt '{prompt_data['name']}': {e}")
                continue

        return created_prompts

    # Version History Methods

    async def save_version_snapshot(self, prompt_id: str, change_summary: str = "") -> PromptVersionModel:
        """Save a snapshot of the current prompt as a new version.
        
        Args:
            prompt_id: The prompt ID
            change_summary: Optional summary of changes
            
        Returns:
            The created version model
        """
        from ..database.connection import get_database_connection
        from ..models.mcp_prompt import PromptVersionModel

        # Get current prompt
        prompt = await self.get_prompt_by_id(prompt_id)
        if not prompt:
            raise PromptValidationError(f"Prompt with ID '{prompt_id}' not found")

        # Create version snapshot
        version_data = {
            "prompt_id": prompt_id,
            "version": prompt.version,
            "name": prompt.name,
            "description": prompt.description,
            "messages": [msg.model_dump() if hasattr(msg, 'model_dump') else msg for msg in prompt.messages],
            "arguments": [arg.model_dump() if hasattr(arg, 'model_dump') else arg for arg in prompt.arguments],
            "category": prompt.category,
            "tags": prompt.tags,
            "change_summary": change_summary or f"Version {prompt.version}",
            "created_by": prompt.updated_by or prompt.created_by,
            "created_at": datetime.utcnow()
        }

        # Save to prompt_versions collection
        db_connection = get_database_connection()
        versions_collection = db_connection.database["prompt_versions"]
        result = await versions_collection.insert_one(version_data)
        version_data["_id"] = result.inserted_id

        return PromptVersionModel(**version_data)

    async def get_prompt_versions(self, prompt_id: str) -> list[PromptVersionModel]:
        """Get all versions of a prompt.
        
        Args:
            prompt_id: The prompt ID
            
        Returns:
            List of version models ordered by version number descending
        """
        from ..database.connection import get_database_connection
        from ..models.mcp_prompt import PromptVersionModel

        db_connection = get_database_connection()
        versions_collection = db_connection.database["prompt_versions"]
        cursor = versions_collection.find(
            {"prompt_id": prompt_id}
        ).sort("version", -1)

        versions = []
        async for doc in cursor:
            versions.append(PromptVersionModel(**doc))

        return versions

    async def get_prompt_version(self, prompt_id: str, version: int) -> PromptVersionModel | None:
        """Get a specific version of a prompt.
        
        Args:
            prompt_id: The prompt ID
            version: The version number
            
        Returns:
            The version model or None if not found
        """
        from ..database.connection import get_database_connection
        from ..models.mcp_prompt import PromptVersionModel

        db_connection = get_database_connection()
        versions_collection = db_connection.database["prompt_versions"]
        doc = await versions_collection.find_one({
            "prompt_id": prompt_id,
            "version": version
        })

        return PromptVersionModel(**doc) if doc else None

    async def restore_prompt_version(self, prompt_id: str, version: int, user_id: str) -> MCPPromptModel:
        """Restore a prompt to a previous version.
        
        Args:
            prompt_id: The prompt ID
            version: The version number to restore
            user_id: The user performing the restore
            
        Returns:
            The updated prompt model
        """
        # Get the version to restore
        version_data = await self.get_prompt_version(prompt_id, version)
        if not version_data:
            raise PromptValidationError(f"Version {version} not found for prompt {prompt_id}")

        # Get current prompt
        current_prompt = await self.get_prompt_by_id(prompt_id)
        if not current_prompt:
            raise PromptValidationError(f"Prompt with ID '{prompt_id}' not found")

        # Save current state as a version before restoring
        await self.save_version_snapshot(
            prompt_id,
            f"Before restoring to version {version}"
        )

        # Increment version number
        new_version = current_prompt.version + 1

        # Restore the prompt with the version data
        update_data = {
            "name": version_data.name,
            "description": version_data.description,
            "messages": [msg.model_dump() if hasattr(msg, 'model_dump') else msg for msg in version_data.messages],
            "arguments": [arg.model_dump() if hasattr(arg, 'model_dump') else arg for arg in version_data.arguments],
            "category": version_data.category,
            "tags": version_data.tags,
            "version": new_version,
            "updated_by": user_id,
            "updated_at": datetime.utcnow()
        }

        # Update the prompt
        updated_prompt = await self.repository.update_prompt(prompt_id, update_data)

        # Save the restored state as a new version
        await self.save_version_snapshot(
            prompt_id,
            f"Restored from version {version}"
        )

        return updated_prompt
