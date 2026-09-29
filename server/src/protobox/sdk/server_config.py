"""
Server Configuration Utilities for AI Provider Integration

Provides utilities to generate proper configurations for:
- OpenAI MCP server integration
- Claude Desktop MCP server integration
- Generic MCP server configurations
"""

import json
from pathlib import Path
from typing import Any

from .types import ClaudeServerConfig, OpenAIServerConfig


class ServerConfig:
    """
    Utility class for generating MCP server configurations for different AI providers.

    Example:
        # Generate OpenAI configuration
        openai_config = ServerConfig.for_openai(
            url="https://my-server.com/mcp",
            name="weather-service",
            api_key="sk-..."
        )

        # Generate Claude Desktop configuration
        claude_config = ServerConfig.for_claude(
            command=["python", "-m", "mcp_server"],
            args=["--port", "8080"],
            env={"API_KEY": "secret"}
        )

        # Save configurations
        ServerConfig.save_openai_config(openai_config, "~/.openai/mcp_servers.json")
        ServerConfig.save_claude_config(claude_config, "claude_desktop_config.json")
    """

    @staticmethod
    def for_openai(
        url: str,
        name: str = "mcp-server",
        description: str = "MCP Server",
        api_key: str | None = None,
    ) -> OpenAIServerConfig:
        """
        Generate OpenAI MCP server configuration.

        Args:
            url: MCP server URL
            name: Server name for OpenAI
            description: Server description
            api_key: Optional API key for authentication

        Returns:
            OpenAI server configuration
        """
        return OpenAIServerConfig(url=url, name=name, description=description, api_key=api_key)

    @staticmethod
    def for_claude(
        command: str | list[str],
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> ClaudeServerConfig:
        """
        Generate Claude Desktop MCP server configuration.

        Args:
            command: Command to run the MCP server (string or list)
            args: Optional command arguments
            env: Optional environment variables

        Returns:
            Claude server configuration
        """
        if isinstance(command, str):
            command = [command]

        return ClaudeServerConfig(command=command, args=args or [], env=env)

    @staticmethod
    def for_remote_server(
        url: str,
        name: str = "remote-mcp-server",
        description: str = "Remote MCP Server",
        api_key: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Generate configuration for a remote MCP server.

        Args:
            url: Remote server URL
            name: Server name
            description: Server description
            api_key: Optional API key
            headers: Optional HTTP headers

        Returns:
            Remote server configuration
        """
        config = {"type": "remote", "name": name, "description": description, "url": url}

        if api_key:
            config["api_key"] = api_key

        if headers:
            config["headers"] = headers

        return config

    @staticmethod
    def save_openai_config(
        config: OpenAIServerConfig, file_path: str | Path, server_name: str = "mcp-server"
    ) -> None:
        """
        Save OpenAI MCP server configuration to file.

        Args:
            config: OpenAI server configuration
            file_path: Path to save configuration file
            server_name: Name for the server in the config
        """
        file_path = Path(file_path).expanduser()

        # Load existing config if it exists
        if file_path.exists():
            with open(file_path) as f:
                existing_config = json.load(f)
        else:
            existing_config = {}

        # Add our server configuration
        existing_config[server_name] = config.to_dict()

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Save updated configuration
        with open(file_path, "w") as f:
            json.dump(existing_config, f, indent=2)

    @staticmethod
    def save_claude_config(
        config: ClaudeServerConfig, file_path: str | Path, server_name: str = "mcp-server"
    ) -> None:
        """
        Save Claude Desktop MCP server configuration to file.

        Args:
            config: Claude server configuration
            file_path: Path to save configuration file
            server_name: Name for the server in the config
        """
        file_path = Path(file_path).expanduser()

        # Load existing config if it exists
        if file_path.exists():
            with open(file_path) as f:
                existing_config = json.load(f)
        else:
            existing_config = {"mcpServers": {}}

        # Ensure mcpServers section exists
        if "mcpServers" not in existing_config:
            existing_config["mcpServers"] = {}

        # Add our server configuration
        existing_config["mcpServers"][server_name] = config.to_dict()

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Save updated configuration
        with open(file_path, "w") as f:
            json.dump(existing_config, f, indent=2)

    @staticmethod
    def load_openai_config(file_path: str | Path) -> dict[str, Any]:
        """
        Load OpenAI MCP server configuration from file.

        Args:
            file_path: Path to configuration file

        Returns:
            OpenAI server configurations
        """
        file_path = Path(file_path).expanduser()

        if not file_path.exists():
            return {}

        with open(file_path) as f:
            return json.load(f)

    @staticmethod
    def load_claude_config(file_path: str | Path) -> dict[str, Any]:
        """
        Load Claude Desktop MCP server configuration from file.

        Args:
            file_path: Path to configuration file

        Returns:
            Claude server configurations
        """
        file_path = Path(file_path).expanduser()

        if not file_path.exists():
            return {}

        with open(file_path) as f:
            config = json.load(f)
            return config.get("mcpServers", {})

    @staticmethod
    def generate_example_configs(server_url: str, api_key: str | None = None) -> dict[str, Any]:
        """
        Generate example configurations for both OpenAI and Claude.

        Args:
            server_url: MCP server URL
            api_key: Optional API key

        Returns:
            Dictionary with example configurations
        """
        openai_config = ServerConfig.for_openai(
            url=server_url, name="my-mcp-server", description="My MCP Server", api_key=api_key
        )

        claude_config = ServerConfig.for_claude(
            command=["python", "-m", "mcp_server"],
            args=["--url", server_url],
            env={"API_KEY": api_key} if api_key else None,
        )

        return {
            "openai": {
                "file_path": "~/.openai/mcp_servers.json",
                "config": openai_config.to_dict(),
            },
            "claude": {
                "file_path": "~/Library/Application Support/Claude/claude_desktop_config.json",
                "config": {"mcpServers": {"my-mcp-server": claude_config.to_dict()}},
            },
        }

    @staticmethod
    def validate_config(config: dict[str, Any], config_type: str = "openai") -> list[str]:
        """
        Validate MCP server configuration.

        Args:
            config: Configuration to validate
            config_type: Type of configuration ("openai" or "claude")

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if config_type == "openai":
            required_fields = ["url", "name"]
            for field in required_fields:
                if field not in config:
                    errors.append(f"Missing required field: {field}")

            if "url" in config and not config["url"].startswith(("http://", "https://")):
                errors.append("URL must start with http:// or https://")

        elif config_type == "claude":
            required_fields = ["command"]
            for field in required_fields:
                if field not in config:
                    errors.append(f"Missing required field: {field}")

            if "command" in config and not isinstance(config["command"], list):
                errors.append("Command must be a list")

        else:
            errors.append(f"Unknown config type: {config_type}")

        return errors
