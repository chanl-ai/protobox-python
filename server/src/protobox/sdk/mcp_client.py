"""
MCP Protocol Client for Tool Discovery and Execution

Provides a clean interface for MCP protocol operations:
- Initialize MCP connection
- List available tools
- Call tools with parameters
- Handle MCP protocol messages
"""

from typing import Any

import aiohttp

from .types import MCPTool, MCPToolResult


class MCPProtocolError(Exception):
    """Exception raised for MCP protocol errors."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        error_data: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.error_data = error_data


class MCPClient:
    """
    MCP Protocol client for tool discovery and execution.

    Handles the MCP protocol communication to discover and execute tools
    on a remote MCP server.

    Example:
        async with MCPClient("https://my-server.com/mcp") as mcp:
            # Initialize the connection
            await mcp.initialize()

            # List available tools
            tools = await mcp.list_tools()
            print(f"Available tools: {[t.name for t in tools]}")

            # Call a tool
            result = await mcp.call_tool("weather", {"city": "Tokyo"})
            print(f"Weather result: {result.content}")
    """

    def __init__(self, server_url: str, api_key: str | None = None, timeout: int = 30):
        """
        Initialize MCP protocol client.

        Args:
            server_url: URL of the MCP server endpoint
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.session: aiohttp.ClientSession | None = None
        self.initialized = False
        self.server_info: dict[str, Any] | None = None
        self.capabilities: dict[str, Any] | None = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def connect(self):
        """Initialize the HTTP session."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self.session = aiohttp.ClientSession(headers=headers, timeout=timeout)

    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
        self.initialized = False

    async def _send_request(
        self, method: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Send an MCP protocol request."""
        if not self.session:
            raise MCPProtocolError(
                "Client not connected. Use async context manager or call connect()."
            )

        request_data = {"jsonrpc": "2.0", "method": method, "id": 1}

        if params:
            request_data["params"] = params

        async with self.session.post(self.server_url, json=request_data) as response:
            if response.status != 200:
                raise MCPProtocolError(
                    f"HTTP error {response.status}: {response.reason}",
                    error_data={"status": response.status, "reason": response.reason},
                )

            data = await response.json()

            # Check for JSON-RPC error
            if "error" in data and data["error"] is not None:
                error = data["error"]
                raise MCPProtocolError(
                    error.get("message", "Unknown MCP error"), error.get("code"), error.get("data")
                )

            return data.get("result", {})

    async def initialize(self, client_info: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Initialize the MCP connection.

        Args:
            client_info: Optional client information to send to server

        Returns:
            Server initialization response with capabilities
        """
        if not client_info:
            client_info = {"name": "mcp-sdk", "version": "0.2.0"}

        params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "clientInfo": client_info,
        }

        result = await self._send_request("initialize", params)

        self.server_info = result.get("serverInfo", {})
        self.capabilities = result.get("capabilities", {})
        self.initialized = True

        return result

    async def list_tools(self) -> list[MCPTool]:
        """
        List all available tools on the MCP server.

        Returns:
            List of available tools
        """
        if not self.initialized:
            await self.initialize()

        result = await self._send_request("tools/list")
        tools_data = result.get("tools", [])

        return [MCPTool.from_dict(tool_data) for tool_data in tools_data]

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> MCPToolResult:
        """
        Call a specific tool with the provided arguments.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool

        Returns:
            Tool execution result
        """
        if not self.initialized:
            await self.initialize()

        params = {"name": tool_name, "arguments": arguments}

        result = await self._send_request("tools/call", params)
        return MCPToolResult.from_dict(result)

    async def get_server_info(self) -> dict[str, Any] | None:
        """Get server information (requires initialization)."""
        if not self.initialized:
            await self.initialize()
        return self.server_info

    async def get_capabilities(self) -> dict[str, Any] | None:
        """Get server capabilities (requires initialization)."""
        if not self.initialized:
            await self.initialize()
        return self.capabilities

    async def ping(self) -> bool:
        """Simple ping to check if server is responding."""
        try:
            await self.initialize()
            return True
        except Exception:
            return False


# Convenience functions for quick usage
async def discover_tools(server_url: str, api_key: str | None = None) -> list[MCPTool]:
    """Quick function to discover tools on an MCP server."""
    async with MCPClient(server_url, api_key) as client:
        return await client.list_tools()


async def call_tool(
    server_url: str, tool_name: str, arguments: dict[str, Any], api_key: str | None = None
) -> MCPToolResult:
    """Quick function to call a tool on an MCP server."""
    async with MCPClient(server_url, api_key) as client:
        return await client.call_tool(tool_name, arguments)


async def get_server_capabilities(server_url: str, api_key: str | None = None) -> dict[str, Any]:
    """Quick function to get server capabilities."""
    async with MCPClient(server_url, api_key) as client:
        await client.initialize()
        return client.capabilities or {}
