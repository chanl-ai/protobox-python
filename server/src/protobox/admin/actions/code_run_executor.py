"""CODE_RUN action executor using Pyodide in Cloudflare Workers."""

import asyncio
import json
import os
import time
from typing import Any

import aiohttp
from loguru import logger

from ..models.action import ActionModel, ActionType, CodeRunConfig
from ..models.execution import ExecutionModel, ExecutionStatus
from .base import BaseActionExecutor


class CodeRunActionExecutor(BaseActionExecutor):
    """Executor for CODE_RUN actions using Pyodide in Cloudflare Workers."""

    def get_supported_action_types(self) -> list[str]:
        """Get the list of action types supported by this executor."""
        return [ActionType.CODE_RUN.value]

    def get_configuration_schema(self) -> dict[str, Any]:
        """Get the JSON schema for CODE_RUN action configuration."""
        return {
            "type": "object",
            "properties": {
                "execution_type": {
                    "type": "string",
                    "enum": ["file"],
                    "default": "file",
                    "description": "How code is provided (file-based via Cloudflare Workers for Platforms)",
                },
                "language": {
                    "type": "string",
                    "enum": ["python", "javascript"],
                    "default": "python",
                    "description": "Programming language",
                },
                "worker_name": {
                    "type": "string",
                    "description": "Cloudflare worker name for dispatch",
                },
                "dispatch_namespace": {
                    "type": "string",
                    "description": "Dispatch namespace name",
                },
                "entry_point": {
                    "type": "string",
                    "default": "main",
                    "description": "Entry point file/function name",
                },
                "timeout": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 300,
                    "default": 30,
                    "description": "Execution timeout in seconds",
                },
                "memory_limit_mb": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1024,
                    "default": 128,
                    "description": "Memory limit in megabytes",
                },
                "dependencies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                    "description": "Required packages/libraries",
                },
                "allowed_imports": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["json", "math", "datetime", "re", "time", "random"],
                    "description": "Allowed import modules",
                },
                "allow_network": {
                    "type": "boolean",
                    "default": False,
                    "description": "Allow network requests",
                },
                "allow_file_ops": {
                    "type": "boolean",
                    "default": False,
                    "description": "Allow file operations",
                },
            },
            "required": ["worker_name", "dispatch_namespace"],
        }

    async def execute(
        self, action: ActionModel, execution: ExecutionModel
    ) -> tuple[dict[str, Any], str | None]:
        """Execute a CODE_RUN action using Cloudflare Workers for Platforms dispatcher.

        Args:
            action: The action to execute
            execution: The execution context

        Returns:
            Tuple of (output_data, error_message)
        """
        start_time = time.time()

        try:
            # Parse configuration
            config = CodeRunConfig.model_validate(action.default_config)
            
            logger.info(f"Executing CODE_RUN action: {action.name} with worker {config.worker_name}")

            # Validate required fields
            if not config.worker_name:
                return {
                    "error": "No worker name provided for execution",
                    "execution_time_ms": 0,
                }, "No worker name provided for execution"
            
            if not config.dispatch_namespace:
                return {
                    "error": "No dispatch namespace provided for execution",
                    "execution_time_ms": 0,
                }, "No dispatch namespace provided for execution"

            # Prepare dispatcher request
            dispatcher_payload = {
                "worker_name": config.worker_name,
                "input_data": execution.input_data,
            }

            # Execute via dispatcher
            success, result = await self._execute_via_dispatcher(dispatcher_payload)

            execution_time_ms = int((time.time() - start_time) * 1000)
            result["execution_time_ms"] = execution_time_ms

            # Check for errors
            error_message = None
            if not success:
                error_message = result.get("error", "Unknown execution error")

            return success, result, error_message

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Error executing CODE_RUN action {action.name}: {e}")

            return {
                "error": str(e),
                "error_type": type(e).__name__,
                "success": False,
                "execution_time_ms": execution_time_ms,
            }, str(e)

    async def _execute_via_dispatcher(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute code via the Cloudflare Workers for Platforms dispatcher.

        Args:
            payload: The execution payload with worker name and dispatch info

        Returns:
            Execution result from dispatcher
        """
        dispatcher_url = os.getenv("CLOUDFLARE_DISPATCHER_URL")
        if not dispatcher_url:
            raise ValueError("CLOUDFLARE_DISPATCHER_URL is not set")
        worker_token = os.getenv("CODE_EXECUTOR_WORKER_TOKEN")
        if not worker_token:
            raise ValueError("CODE_EXECUTOR_WORKER_TOKEN is not set")
        
        logger.debug(f"Executing code via dispatcher: {dispatcher_url} for worker {payload.get('worker_name')}")
        
        success = False
        result = None
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    dispatcher_url,
                    json=payload,
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {worker_token}"},
                    timeout=aiohttp.ClientTimeout(total=payload.get("timeout", 30) + 10)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        result = {
                            "error": f"Dispatcher error {response.status}: {error_text}",
                            "dispatcher_error": True
                        }
                    
                    try:
                        result = await response.json()
                        success = True
                    except json.JSONDecodeError as e:
                        result = {
                            "error": f"Failed to parse dispatcher response: {str(e)}",
                            "dispatcher_error": True
                        }
                        
            except asyncio.TimeoutError:
                result = {
                    "error": "Dispatcher request timed out",
                    "timeout": True
                }
            except Exception as e:
                result = {
                    "error": f"Dispatcher request failed: {str(e)}",
                    "dispatcher_error": True
                }

        return success, result

    async def validate_action(self, action: ActionModel) -> tuple[bool, str | None]:
        """Validate a CODE_RUN action configuration.

        Args:
            action: The action to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Validate using Pydantic model
            config = CodeRunConfig.model_validate(action.default_config)

            if not config.worker_name:
                return False, "Worker name is required for file-based execution"
            
            if not config.dispatch_namespace:
                return False, "Dispatch namespace is required for file-based execution"

            # Validate timeout and memory limits
            if config.timeout < 1 or config.timeout > 300:
                return False, "Timeout must be between 1 and 300 seconds"
            
            if config.memory_limit_mb < 1 or config.memory_limit_mb > 1024:
                return False, "Memory limit must be between 1 and 1024 MB"

            return True, None

        except Exception as e:
            return False, f"Validation error: {str(e)}"

    async def test_action(self, action: ActionModel, test_input: dict[str, Any]) -> dict[str, Any]:
        """Test a CODE_RUN action with sample input.

        Args:
            action: The action to test
            test_input: Test input data

        Returns:
            Test result dictionary
        """
        # Create a mock execution for testing
        mock_execution = ExecutionModel(
            action_id=str(action.id) if action.id else "test",
            workspace_id=action.workspace_id,
            user_id=action.created_by,
            input_data=test_input,
            status=ExecutionStatus.PENDING,
        )

        # Execute the action
        success, output_data, error_message = await self.execute(action, mock_execution)

        return {
            "success": success,
            "output_data": output_data,
            "error_message": error_message,
            "test_input": test_input,
        }