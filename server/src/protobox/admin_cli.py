#!/usr/bin/env python3
"""
ProtoBox CLI

Command-line interface for managing ProtoBox MCP server actions, secrets, and workspaces.
"""

import argparse
import asyncio
import json
import os
import secrets
import sys
from pathlib import Path

import aiohttp
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

# Default server configuration
DEFAULT_SERVER_URL = os.getenv("PROTOBOX_SERVER_URL", "http://localhost:8090")
DEFAULT_CONFIG_DIR = Path.home() / ".protobox"

# Predefined environments
ENVIRONMENTS = {
    "local": "http://localhost:8090",
}

console = Console()


class MCPAdminClient:
    """Client for interacting with MCP Admin API"""

    def __init__(self, server_url: str, api_key: str | None = None):
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self.admin_url = f"{self.server_url}/admin/api/v1"

    async def request(self, method: str, endpoint: str, json_data: dict | None = None) -> dict:
        """Make an authenticated request to the admin API"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with aiohttp.ClientSession() as session:
            url = f"{self.admin_url}{endpoint}"
            async with session.request(method, url, json=json_data, headers=headers) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    raise Exception(f"API Error ({response.status}): {error_text}")
                return await response.json()

    # Action methods
    async def list_actions(self) -> list:
        """List all actions"""
        return await self.request("GET", "/actions")

    async def create_action(self, action_data: dict) -> dict:
        """Create a new action"""
        return await self.request("POST", "/actions", json_data=action_data)

    async def delete_action(self, action_id: str) -> dict:
        """Delete an action"""
        return await self.request("DELETE", f"/actions/{action_id}")

    # Secret methods
    async def list_secrets(self) -> list:
        """List all secrets"""
        return await self.request("GET", "/secrets")

    async def create_secret(self, secret_data: dict) -> dict:
        """Create a new secret"""
        return await self.request("POST", "/secrets", json_data=secret_data)

    async def delete_secret(self, secret_id: str) -> dict:
        """Delete a secret"""
        return await self.request("DELETE", f"/secrets/{secret_id}")


class Config:
    """Manage local configuration"""

    def __init__(self):
        self.config_dir = DEFAULT_CONFIG_DIR
        self.config_file = self.config_dir / "config.json"
        self.config_dir.mkdir(exist_ok=True)
        self._config = self._load_config()

    def _load_config(self) -> dict:
        """Load configuration from file"""
        if self.config_file.exists():
            with open(self.config_file) as f:
                return json.load(f)
        return {}

    def save(self):
        """Save configuration to file"""
        with open(self.config_file, "w") as f:
            json.dump(self._config, f, indent=2)

    @property
    def api_key(self) -> str | None:
        return self._config.get("api_key")

    @api_key.setter
    def api_key(self, value: str):
        self._config["api_key"] = value
        self.save()

    @property
    def server_url(self) -> str:
        return self._config.get("server_url", DEFAULT_SERVER_URL)

    @server_url.setter
    def server_url(self, value: str):
        self._config["server_url"] = value
        self.save()

    @property
    def workspace(self) -> str | None:
        return self._config.get("workspace")

    @workspace.setter
    def workspace(self, value: str):
        self._config["workspace"] = value
        self.save()


def generate_api_key() -> str:
    """Generate a secure API key"""
    return f"pb_key_{secrets.token_urlsafe(32)}"


def resolve_server_url(url_or_env: str) -> str:
    """Resolve server URL from environment name or direct URL"""
    # Check if it's a predefined environment
    if url_or_env.lower() in ENVIRONMENTS:
        return ENVIRONMENTS[url_or_env.lower()]

    # If it starts with http, assume it's a direct URL
    if url_or_env.startswith(("http://", "https://")):
        return url_or_env.rstrip("/")

    # Otherwise, treat as a hostname and add https
    return f"https://{url_or_env}"


async def cmd_init(args):
    """Initialize ProtoBox configuration"""
    config = Config()

    # Check if already initialized
    if config.api_key:
        console.print(f"[yellow]Already initialized for workspace: {config.workspace}[/yellow]")
        if not args.force:
            console.print("Use --force to reinitialize")
            return

    # Generate new configuration
    username = args.username
    api_key = generate_api_key()

    # Save configuration
    config.workspace = username
    config.api_key = api_key
    config.server_url = resolve_server_url(args.server_url)

    console.print(f"[green]✓ Created workspace:[/green] {username}")
    console.print(f"[green]✓ API Key:[/green] {api_key}")
    console.print(f"[green]✓ Server URL:[/green] {config.server_url}")
    console.print(f"[green]✓ Admin endpoint:[/green] {config.server_url}/admin/api/v1")
    console.print()
    console.print("[bold]Configuration saved to:[/bold]", str(config.config_file))


async def cmd_info(args):
    """Display ProtoBox server information"""
    config = Config()

    if not config.api_key:
        console.print("[red]Not initialized. Run 'protobox init' first.[/red]")
        return

    # Override server URL if --url is provided
    server_url = (
        resolve_server_url(args.url) if hasattr(args, "url") and args.url else config.server_url
    )

    console.print("[bold]ProtoBox Server Information[/bold]")
    console.print(f"Server URL: {server_url}")
    console.print(f"MCP Endpoint: {server_url}/mcp")
    console.print(f"Admin API: {server_url}/admin/api/v1")
    console.print(f"Workspace: {config.workspace}")
    console.print(f"API Key: {config.api_key}")
    console.print()

    # ChatGPT configuration
    console.print("[bold]For ChatGPT Custom GPT:[/bold]")
    chatgpt_config = {"type": "mcp", "server_url": f"{server_url}/mcp", "api_key": config.api_key}
    syntax = Syntax(json.dumps(chatgpt_config, indent=2), "json", theme="monokai")
    console.print(syntax)

    console.print()
    console.print("[bold]For Claude Desktop:[/bold]")
    console.print("Add to your Claude Desktop MCP settings:")
    claude_config = {
        "mcpServers": {"mcp-server": {"url": f"{server_url}/mcp", "apiKey": config.api_key}}
    }
    syntax = Syntax(json.dumps(claude_config, indent=2), "json", theme="monokai")
    console.print(syntax)


async def cmd_use(args):
    """Switch to a different server environment"""
    config = Config()

    # Resolve the server URL
    new_url = resolve_server_url(args.environment)
    config.server_url = new_url

    console.print(f"[green]✓ Switched to:[/green] {new_url}")

    # Show available environments
    if args.environment.lower() in ENVIRONMENTS:
        console.print(f"[dim]Environment:[/dim] {args.environment}")

    console.print(
        "\n[bold]Note:[/bold] You may need to run 'protobox init' if you haven't initialized this environment yet."
    )


def get_client_and_config(args) -> tuple[MCPAdminClient, Config]:
    """Get client and config, respecting --url flag if provided"""
    config = Config()

    # Override server URL if --url is provided
    if hasattr(args, "url") and args.url:
        server_url = resolve_server_url(args.url)
    else:
        server_url = config.server_url

    client = MCPAdminClient(server_url, config.api_key)
    return client, config


async def cmd_action_list(args):
    """List all actions"""
    client, config = get_client_and_config(args)

    try:
        actions = await client.list_actions()

        if not actions:
            console.print("[yellow]No actions found.[/yellow]")
            return

        table = Table(title="MCP Actions")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Description")
        table.add_column("Enabled", style="yellow")

        for action in actions:
            enabled = "✓" if action.get("enabled", True) else "✗"
            table.add_row(action["name"], action["type"], action.get("description", ""), enabled)

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


async def cmd_action_create(args):
    """Create a new action"""
    client, config = get_client_and_config(args)

    # Build action data
    action_data = {
        "workspace_id": config.workspace,  # Use workspace from config
        "name": args.name,
        "type": args.type,
        "description": args.description or f"{args.type} action: {args.name}",
        "default_config": {},
    }

    # Type-specific configuration
    if args.type == "REST":
        if not args.action_url:
            console.print("[red]Error: --action-url is required for REST actions[/red]")
            return
        action_data["default_config"] = {
            "url": args.action_url,
            "method": args.method or "GET",
            "headers": json.loads(args.headers) if args.headers else {},
        }
    elif args.type == "CODE_RUN":
        if not args.code:
            console.print("[red]Error: --code is required for CODE_RUN actions[/red]")
            return
        action_data["default_config"] = {"code": args.code}

    try:
        result = await client.create_action(action_data)
        # MongoDB returns _id, not id
        action_id = result.get("_id") or result.get("id")
        console.print(f"[green]✓ Created action:[/green] {result['name']} (ID: {action_id})")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


async def cmd_action_delete(args):
    """Delete an action"""
    client, config = get_client_and_config(args)

    try:
        # First, find the action by name
        actions = await client.list_actions()
        action = next((a for a in actions if a["name"] == args.name), None)

        if not action:
            console.print(f"[red]Action not found: {args.name}[/red]")
            return

        # Confirm deletion
        if not args.force:
            confirm = console.input(f"Delete action '{args.name}'? [y/N] ")
            if confirm.lower() != "y":
                console.print("[yellow]Cancelled.[/yellow]")
                return

        # MongoDB returns _id, not id
        action_id = action.get("_id") or action.get("id")
        await client.delete_action(action_id)
        console.print(f"[green]✓ Deleted action:[/green] {args.name}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


async def cmd_secret_list(args):
    """List all secrets"""
    client, config = get_client_and_config(args)

    try:
        secrets = await client.list_secrets()

        if not secrets:
            console.print("[yellow]No secrets found.[/yellow]")
            return

        table = Table(title="MCP Secrets")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Created At")

        for secret in secrets:
            table.add_row(secret["name"], secret["type"], secret.get("created_at", ""))

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


async def cmd_secret_create(args):
    """Create a new secret"""
    client, config = get_client_and_config(args)

    secret_data = {
        "workspace_id": config.workspace,  # Use workspace from config
        "name": args.name,
        "secret_type": args.type or "API_KEY",
        "secret_value": args.value,
    }

    try:
        result = await client.create_secret(secret_data)
        # MongoDB returns _id, not id
        secret_id = result.get("_id") or result.get("id")
        console.print(f"[green]✓ Created secret:[/green] {result['name']} (ID: {secret_id})")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def create_parser():
    """Create the argument parser"""
    parser = argparse.ArgumentParser(
        description="ProtoBox CLI - Manage your AI tool integrations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Environments: local, staging, production (or use custom URL)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Use command
    use_parser = subparsers.add_parser("use", help="Switch server environment")
    use_parser.add_argument(
        "environment", help="Environment name (local/staging/production) or URL"
    )

    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize ProtoBox configuration")
    init_parser.add_argument("--username", required=True, help="Your username")
    init_parser.add_argument(
        "--server-url", default="production", help="Server environment or URL (default: production)"
    )
    init_parser.add_argument("--force", action="store_true", help="Force reinitialization")

    # Info command
    info_parser = subparsers.add_parser("info", help="Display ProtoBox server information")
    info_parser.add_argument("--url", help="Override server URL")

    # Action commands
    action_parser = subparsers.add_parser("action", help="Manage actions")
    action_subparsers = action_parser.add_subparsers(dest="action_command")

    # Action list
    action_list = action_subparsers.add_parser("list", help="List all actions")
    action_list.add_argument("--url", help="Override server URL")

    # Action create
    action_create = action_subparsers.add_parser("create", help="Create a new action")
    action_create.add_argument("--url", help="Override server URL")
    action_create.add_argument("--name", required=True, help="Action name")
    action_create.add_argument(
        "--type", required=True, choices=["REST", "CODE_RUN", "O3", "DATABASE"], help="Action type"
    )
    action_create.add_argument("--description", help="Action description")
    action_create.add_argument(
        "--action-url", help="URL for REST actions (use {{var}} for templating)"
    )
    action_create.add_argument("--method", help="HTTP method for REST actions")
    action_create.add_argument("--headers", help="Headers for REST actions (JSON)")
    action_create.add_argument("--code", help="Code for CODE_RUN actions")

    # Action delete
    action_delete = action_subparsers.add_parser("delete", help="Delete an action")
    action_delete.add_argument("name", help="Action name")
    action_delete.add_argument("--force", action="store_true", help="Skip confirmation")
    action_delete.add_argument("--url", help="Override server URL")

    # Secret commands
    secret_parser = subparsers.add_parser("secret", help="Manage secrets")
    secret_subparsers = secret_parser.add_subparsers(dest="secret_command")

    # Secret list
    secret_list = secret_subparsers.add_parser("list", help="List all secrets")
    secret_list.add_argument("--url", help="Override server URL")

    # Secret create
    secret_create = secret_subparsers.add_parser("create", help="Create a new secret")
    secret_create.add_argument("--url", help="Override server URL")
    secret_create.add_argument("name", help="Secret name")
    secret_create.add_argument("value", help="Secret value")
    secret_create.add_argument(
        "--type",
        default="API_KEY",
        choices=["API_KEY", "DATABASE_URL", "OAUTH_TOKEN", "BASIC_AUTH", "CUSTOM"],
        help="Secret type",
    )

    return parser


async def main():
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Route commands
    if args.command == "init":
        await cmd_init(args)
    elif args.command == "use":
        await cmd_use(args)
    elif args.command == "info":
        await cmd_info(args)
    elif args.command == "action":
        if args.action_command == "list":
            await cmd_action_list(args)
        elif args.action_command == "create":
            await cmd_action_create(args)
        elif args.action_command == "delete":
            await cmd_action_delete(args)
        else:
            parser.print_help()
    elif args.command == "secret":
        if args.secret_command == "list":
            await cmd_secret_list(args)
        elif args.secret_command == "create":
            await cmd_secret_create(args)
        else:
            parser.print_help()
    else:
        parser.print_help()


def run():
    """Run the CLI"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    run()
