"""Base action executor interface."""

from abc import ABC, abstractmethod
from typing import Any

from ..models.action import ActionModel
from ..models.execution import ExecutionModel
from ..services.secret_service import SecretService


class BaseActionExecutor(ABC):
    """Base class for action executors."""

    def __init__(self, secret_service: SecretService):
        """Initialize the executor.

        Args:
            secret_service: Service for accessing secrets
        """
        self.secret_service = secret_service

    @abstractmethod
    async def execute(
        self, action: ActionModel, execution: ExecutionModel
    ) -> tuple[dict[str, Any], str | None]:
        """Execute an action.

        Args:
            action: The action to execute
            execution: The execution context

        Returns:
            Tuple of (output_data, error_message)
        """
        pass

    @abstractmethod
    async def validate_action(self, action: ActionModel) -> tuple[bool, str | None]:
        """Validate an action configuration.

        Args:
            action: The action to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        pass

    @abstractmethod
    async def test_action(self, action: ActionModel, test_input: dict[str, Any]) -> dict[str, Any]:
        """Test an action with sample input.

        Args:
            action: The action to test
            test_input: Test input data

        Returns:
            Test result dictionary
        """
        pass

    def get_supported_action_types(self) -> list[str]:
        """Get the list of action types supported by this executor.

        Returns:
            List of supported action type strings
        """
        return []

    def get_configuration_schema(self) -> dict[str, Any]:
        """Get the JSON schema for action configuration.

        Returns:
            JSON schema dictionary
        """
        return {"type": "object", "properties": {}, "required": []}
