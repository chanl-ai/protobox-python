"""
Admin API Client for MCP Server Management

Provides a clean interface for managing MCP server resources:
- Actions (create, list, update, delete)
- Secrets (create, list, update, delete)
- Executions (create, list, get status)
- Health monitoring
"""

import builtins
from typing import Any

import aiohttp

from .types import (
    ActionConfig,
    ActionResponse,
    ExecutionConfig,
    ExecutionResponse,
    HealthResponse,
    SecretConfig,
)


class AdminAPIError(Exception):
    """Exception raised for Admin API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_data: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class ActionsClient:
    """Client for managing MCP actions."""

    def __init__(self, base_url: str, session: aiohttp.ClientSession):
        self.base_url = base_url
        self.session = session

    async def create(self, action: ActionConfig) -> ActionResponse:
        """Create a new action."""
        async with self.session.post(f"{self.base_url}/actions", json=action.to_dict()) as response:
            if response.status != 201:
                try:
                    error_data = await response.json()
                    error_msg = error_data.get("detail", f"HTTP {response.status}")
                except:
                    error_msg = f"HTTP {response.status}"
                raise AdminAPIError(
                    f"Failed to create action: {error_msg}",
                    response.status,
                    error_data if "error_data" in locals() else None,
                )
            data = await response.json()
            return ActionResponse.from_dict(data)

    async def list(self, workspace_id: str | None = None) -> list[ActionResponse]:
        """List all actions."""
        params = {}
        if workspace_id:
            params["workspace_id"] = workspace_id

        async with self.session.get(f"{self.base_url}/actions", params=params) as response:
            if response.status != 200:
                raise AdminAPIError(
                    f"Failed to list actions: {response.status}",
                    response.status,
                    await response.json(),
                )
            data = await response.json()
            return [ActionResponse.from_dict(item) for item in data]

    async def get(self, action_id: str) -> ActionResponse:
        """Get a specific action."""
        async with self.session.get(f"{self.base_url}/actions/{action_id}") as response:
            if response.status != 200:
                raise AdminAPIError(
                    f"Failed to get action: {response.status}",
                    response.status,
                    await response.json(),
                )
            data = await response.json()
            return ActionResponse.from_dict(data)

    async def update(self, action_id: str, action: ActionConfig) -> ActionResponse:
        """Update an existing action."""
        async with self.session.put(
            f"{self.base_url}/actions/{action_id}", json=action.to_dict()
        ) as response:
            if response.status != 200:
                raise AdminAPIError(
                    f"Failed to update action: {response.status}",
                    response.status,
                    await response.json(),
                )
            data = await response.json()
            return ActionResponse.from_dict(data)

    async def delete(self, action_id: str) -> bool:
        """Delete an action."""
        async with self.session.delete(f"{self.base_url}/actions/{action_id}") as response:
            if response.status not in (200, 204):
                raise AdminAPIError(
                    f"Failed to delete action: {response.status}",
                    response.status,
                    await response.json(),
                )
            return True

    async def get_types(self) -> builtins.list[dict[str, Any]]:
        """Get available action types."""
        async with self.session.get(f"{self.base_url}/actions/types") as response:
            if response.status != 200:
                raise AdminAPIError(
                    f"Failed to get action types: {response.status}",
                    response.status,
                    await response.json(),
                )
            return await response.json()


class SecretsClient:
    """Client for managing MCP secrets."""

    def __init__(self, base_url: str, session: aiohttp.ClientSession):
        self.base_url = base_url
        self.session = session

    async def create(self, secret: SecretConfig) -> dict[str, Any]:
        """Create a new secret."""
        async with self.session.post(f"{self.base_url}/secrets", json=secret.to_dict()) as response:
            if response.status != 201:
                raise AdminAPIError(
                    f"Failed to create secret: {response.status}",
                    response.status,
                    await response.json(),
                )
            return await response.json()

    async def list(self, workspace_id: str | None = None) -> list[dict[str, Any]]:
        """List all secrets (without values)."""
        params = {}
        if workspace_id:
            params["workspace_id"] = workspace_id

        async with self.session.get(f"{self.base_url}/secrets", params=params) as response:
            if response.status != 200:
                raise AdminAPIError(
                    f"Failed to list secrets: {response.status}",
                    response.status,
                    await response.json(),
                )
            return await response.json()

    async def delete(self, secret_id: str) -> bool:
        """Delete a secret."""
        async with self.session.delete(f"{self.base_url}/secrets/{secret_id}") as response:
            if response.status not in (200, 204):
                raise AdminAPIError(
                    f"Failed to delete secret: {response.status}",
                    response.status,
                    await response.json(),
                )
            return True


class ExecutionsClient:
    """Client for managing MCP executions."""

    def __init__(self, base_url: str, session: aiohttp.ClientSession):
        self.base_url = base_url
        self.session = session

    async def create(self, execution: ExecutionConfig) -> ExecutionResponse:
        """Create a new execution."""
        async with self.session.post(
            f"{self.base_url}/executions", json=execution.to_dict()
        ) as response:
            if response.status != 201:
                raise AdminAPIError(
                    f"Failed to create execution: {response.status}",
                    response.status,
                    await response.json(),
                )
            data = await response.json()
            return ExecutionResponse.from_dict(data)

    async def list(self, workspace_id: str | None = None) -> list[ExecutionResponse]:
        """List all executions."""
        params = {}
        if workspace_id:
            params["workspace_id"] = workspace_id

        async with self.session.get(f"{self.base_url}/executions", params=params) as response:
            if response.status != 200:
                raise AdminAPIError(
                    f"Failed to list executions: {response.status}",
                    response.status,
                    await response.json(),
                )
            data = await response.json()
            return [ExecutionResponse.from_dict(item) for item in data]

    async def get(self, execution_id: str) -> ExecutionResponse:
        """Get a specific execution."""
        async with self.session.get(f"{self.base_url}/executions/{execution_id}") as response:
            if response.status != 200:
                raise AdminAPIError(
                    f"Failed to get execution: {response.status}",
                    response.status,
                    await response.json(),
                )
            data = await response.json()
            return ExecutionResponse.from_dict(data)


class AdminClient:
    """
    Admin API client for MCP server management.

    Provides access to actions, secrets, executions, and health monitoring.

    Example:
        async with AdminClient("https://my-server.com") as admin:
            # Create an action
            action = ActionConfig(
                name="weather_api",
                type=ActionType.REST,
                description="Get weather data",
                config={"url": "https://api.weather.com"}
            )
            result = await admin.actions.create(action)

            # List all actions
            actions = await admin.actions.list()

            # Check health
            health = await admin.health()
    """

    def __init__(self, base_url: str, api_key: str | None = None, timeout: int = 30):
        """
        Initialize Admin API client.

        Args:
            base_url: Base URL of the MCP server (e.g., "https://my-server.com")
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        # Add admin API prefix if not already present
        if not self.base_url.endswith("/admin/api/v1"):
            self.base_url += "/admin/api/v1"
        self.api_key = api_key
        self.timeout = timeout
        self.session: aiohttp.ClientSession | None = None

        # Initialize sub-clients
        self.actions: ActionsClient | None = None
        self.secrets: SecretsClient | None = None
        self.executions: ExecutionsClient | None = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def connect(self):
        """Initialize the HTTP session and sub-clients."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self.session = aiohttp.ClientSession(headers=headers, timeout=timeout)

        # Initialize sub-clients
        self.actions = ActionsClient(self.base_url, self.session)
        self.secrets = SecretsClient(self.base_url, self.session)
        self.executions = ExecutionsClient(self.base_url, self.session)

    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None

    async def health(self) -> HealthResponse:
        """Get server health status."""
        if not self.session:
            raise AdminAPIError(
                "Client not connected. Use async context manager or call connect()."
            )

        # Health endpoint is at the root level, not under admin API
        health_url = self.base_url.replace("/admin/api/v1", "/health")
        async with self.session.get(health_url) as response:
            if response.status != 200:
                raise AdminAPIError(
                    f"Failed to get health status: {response.status}",
                    response.status,
                    await response.json(),
                )
            data = await response.json()
            return HealthResponse.from_dict(data)

    async def ping(self) -> bool:
        """Simple ping to check if server is responding."""
        try:
            await self.health()
            return True
        except Exception:
            return False


# Convenience functions for quick usage
async def create_action(
    base_url: str, action: ActionConfig, api_key: str | None = None
) -> ActionResponse:
    """Quick function to create an action."""
    async with AdminClient(base_url, api_key) as client:
        return await client.actions.create(action)


async def list_actions(base_url: str, api_key: str | None = None) -> list[ActionResponse]:
    """Quick function to list actions."""
    async with AdminClient(base_url, api_key) as client:
        return await client.actions.list()


async def check_health(base_url: str, api_key: str | None = None) -> HealthResponse:
    """Quick function to check server health."""
    async with AdminClient(base_url, api_key) as client:
        return await client.health()
