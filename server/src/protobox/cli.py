#!/usr/bin/env python3
"""
MCP Server CLI

Command-line interface for running the MCP server with configuration support.
"""

import argparse
import asyncio
import os
import sys

from loguru import logger

from .config.settings import (
    DEFAULT_HTTP_CONFIG,
    DEFAULT_REMOTE_MCP_CONFIG,
    DEFAULT_STDIO_CONFIG,
    DEFAULT_WEBSOCKET_CONFIG,
    Config,
)
from .protocol.transport import HTTPTransport, StdioTransport, WebSocketTransport
from .server import MCPServer
from .tools.base import CalculatorTool, EchoTool, FetchTool, RestActionTool, SearchTool


def setup_logging(debug: bool = False):
    """Setup logging configuration"""
    logger.remove()

    log_level = "DEBUG" if debug else "INFO"
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}:{function}:{line}</cyan> - "
        "<level>{message}</level>"
    )

    logger.add(sys.stderr, level=log_level, format=log_format, colorize=True)


def create_tools_from_config(tool_configs):
    """Create tools from configuration"""
    tools = []

    for tool_config in tool_configs:
        if not tool_config.enabled:
            continue

        if tool_config.type == "builtin.echo":
            tools.append(EchoTool())

        elif tool_config.type == "builtin.search":
            tools.append(SearchTool())

        elif tool_config.type == "builtin.fetch":
            tools.append(FetchTool())

        elif tool_config.type == "builtin.calculator":
            tools.append(CalculatorTool())

        elif tool_config.type == "builtin.rest_api":
            config = tool_config.config
            rest_tool = RestActionTool(
                name=tool_config.name,
                description=config.get("description", f"REST API tool: {tool_config.name}"),
                input_schema=config.get(
                    "input_schema",
                    {
                        "type": "object",
                        "properties": {
                            "endpoint": {"type": "string", "description": "API endpoint to call"}
                        },
                        "required": ["endpoint"],
                    },
                ),
                url=config.get("url", "https://httpbin.org/{endpoint}"),
                method=config.get("method", "GET"),
                headers=config.get("headers", {}),
                timeout=config.get("timeout", 30),
                retries=config.get("retries", 2),
            )
            tools.append(rest_tool)

        else:
            logger.warning(f"Unknown tool type: {tool_config.type}")

    return tools


def create_sample_tools():
    """Create sample tools for testing (fallback)"""
    tools = []

    # Remote MCP tools for ChatGPT/Claude compatibility
    tools.append(SearchTool())
    tools.append(FetchTool())
    tools.append(CalculatorTool())

    # Classic tools
    tools.append(EchoTool())

    # Sample REST tool
    rest_tool = RestActionTool(
        name="httpbin_get",
        description="Test REST API call to httpbin.org",
        input_schema={
            "type": "object",
            "properties": {
                "endpoint": {
                    "type": "string",
                    "description": "Endpoint to call (e.g., 'ip', 'user-agent')",
                }
            },
            "required": ["endpoint"],
        },
        url="https://httpbin.org/{endpoint}",
        method="GET",
    )
    tools.append(rest_tool)

    return tools


async def run_stdio_server(debug: bool = False, config_file: str = None):
    """Run MCP server with stdio transport"""
    setup_logging(debug)
    logger.info("Starting MCP server with stdio transport")

    # Load configuration
    config = Config.from_file(config_file) if config_file else DEFAULT_STDIO_CONFIG

    # Override with environment variables
    env_config = Config.from_env()
    if env_config.dict(exclude_unset=True):
        config = Config(**(config.dict() | env_config.dict(exclude_unset=True)))

    # Check admin API compatibility
    if config.admin.enabled:
        logger.warning("Admin API cannot be enabled with stdio transport. Disabling admin API.")
        config.admin.enabled = False

    transport = StdioTransport()
    server = MCPServer(
        name=config.server.name, version=config.server.version, transport=transport, config=config
    )

    # Register tools from configuration
    tools = create_tools_from_config(config.tools)
    for tool in tools:
        server.register_tool(tool)

    await server.run_forever()


async def run_http_server(
    host: str = "localhost", port: int = 8080, debug: bool = False, config_file: str = None
):
    """Run MCP server with HTTP transport"""
    setup_logging(debug)
    logger.info(f"Starting MCP server with HTTP transport on {host}:{port}")

    # Load configuration - prefer environment variables
    if os.getenv("MCP_ADMIN_ENABLED") or os.getenv("MCP_SECRET_KEY"):
        # If we have MCP environment variables, use them directly
        logger.info("Loading configuration from environment variables")
        config = Config.from_env()
        # Always use the provided host/port for transport
        config.transport.host = host
        config.transport.port = port
    elif config_file:
        # Load from file if specified
        logger.info(f"Loading configuration from file: {config_file}")
        config = Config.from_file(config_file)
        # Override with any environment variables
        env_config = Config.from_env()
        env_dict = env_config.dict(exclude_unset=True)
        if env_dict:
            config_dict = config.dict()
            for key, value in env_dict.items():
                if (
                    key in config_dict
                    and isinstance(config_dict[key], dict)
                    and isinstance(value, dict)
                ):
                    config_dict[key].update(value)
                else:
                    config_dict[key] = value
            config = Config(**config_dict)
    else:
        # Use default config
        logger.info("Using default HTTP configuration")
        config = DEFAULT_HTTP_CONFIG
        config.transport.host = host
        config.transport.port = port

    # Validate admin API configuration if enabled
    if config.admin.enabled:
        if not config.admin.secret_key:
            logger.error("Admin API is enabled but secret_key is not configured")
            logger.error("Set MCP_SECRET_KEY environment variable or provide it in config file")
            sys.exit(1)

        logger.info(f"Admin API enabled with prefix: {config.admin.prefix}")
        logger.info(f"MongoDB URL: {config.admin.mongodb_url}")

    transport = HTTPTransport(host=config.transport.host, port=config.transport.port)
    server = MCPServer(
        name=config.server.name, version=config.server.version, transport=transport, config=config
    )

    # Register tools from configuration
    tools = create_tools_from_config(config.tools)
    for tool in tools:
        server.register_tool(tool)

    await server.run_forever()


async def run_websocket_server(
    host: str = "localhost", port: int = 8081, debug: bool = False, config_file: str = None
):
    """Run MCP server with WebSocket transport"""
    setup_logging(debug)
    logger.info(f"Starting MCP server with WebSocket transport on {host}:{port}")

    # Load configuration
    if config_file:
        config = Config.from_file(config_file)
    else:
        config = DEFAULT_WEBSOCKET_CONFIG
        config.transport.host = host
        config.transport.port = port

    # Override with environment variables
    env_config = Config.from_env()
    if env_config.dict(exclude_unset=True):
        config = Config(**(config.dict() | env_config.dict(exclude_unset=True)))

    # Check admin API compatibility
    # if config.admin.enabled:
    # logger.warning("Admin API cannot be enabled with WebSocket
    # transport. Disabling admin API.")
    # config.admin.enabled = False

    transport = WebSocketTransport(host=config.transport.host, port=config.transport.port)
    server = MCPServer(
        name=config.server.name, version=config.server.version, transport=transport, config=config
    )

    # Register tools from configuration
    tools = create_tools_from_config(config.tools)
    for tool in tools:
        server.register_tool(tool)

    await server.run_forever()


async def run_remote_server(
    host: str = "0.0.0.0", port: int = 8080, debug: bool = False, config_file: str = None
):
    """Run MCP server optimized for remote deployment (Phase 1X)"""
    setup_logging(debug)
    logger.info(f"Starting Remote MCP server on {host}:{port}")

    # Load configuration
    if config_file:
        config = Config.from_file(config_file)
    else:
        config = DEFAULT_REMOTE_MCP_CONFIG
        config.transport.host = host
        config.transport.port = port

    # Override with environment variables
    env_config = Config.from_env()
    if env_config.dict(exclude_unset=True):
        config = Config(**(config.dict() | env_config.dict(exclude_unset=True)))

    # Remote MCP servers have admin API disabled by default for Phase 1X
    if config.admin.enabled:
        logger.warning(
            "Admin API is disabled for remote servers in Phase 1X. Use 'http' command if you need admin API."
        )
        config.admin.enabled = False

    logger.info("🚀 Remote MCP Server Configuration:")
    logger.info(f"   Server: {config.server.name}")
    logger.info(f"   Endpoint: http://{host}:{port}")
    logger.info(f"   Health Check: http://{host}:{port}/health")
    logger.info(f"   MCP Endpoint: http://{host}:{port}/mcp")
    logger.info(f"   SSE Endpoint: http://{host}:{port}/mcp/sse")
    logger.info(f"   Tools: {len(config.tools)} configured")

    transport = HTTPTransport(host=config.transport.host, port=config.transport.port)
    server = MCPServer(
        name=config.server.name, version=config.server.version, transport=transport, config=config
    )

    # Register tools from configuration
    tools = create_tools_from_config(config.tools)
    for tool in tools:
        server.register_tool(tool)
        logger.info(f"   ✓ Registered tool: {tool.name}")

    logger.info("🎯 Ready for ChatGPT and Claude integration!")
    await server.run_forever()


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="MCP Server - A highly configurable Model Context Protocol server with optional admin API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with stdio transport (default)
  mcp-server stdio

  # Run with HTTP transport
  mcp-server http --host 0.0.0.0 --port 8080

  # Run with configuration file
  mcp-server --config config.yaml http

  # Run with admin API enabled
  MCP_SECRET_KEY=your-secret-key mcp-server --config config-with-admin.yaml http

  # Enable debug logging
  mcp-server --debug stdio

  # Use environment variables
  MCP_TRANSPORT_TYPE=http MCP_TRANSPORT_PORT=9000 mcp-server

Admin API Environment Variables:
  MCP_ADMIN_ENABLED=true          # Enable admin API
  MCP_SECRET_KEY=your-key         # Master encryption key (required)
  MCP_MONGODB_URL=mongodb://...   # MongoDB connection string
  MCP_ADMIN_PREFIX=/admin/api/v1  # API prefix
        """,
    )

    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    parser.add_argument("--config", type=str, help="Configuration file path (YAML or JSON)")

    subparsers = parser.add_subparsers(dest="transport", help="Transport type")

    # Stdio transport
    subparsers.add_parser("stdio", help="Use stdio transport (no admin API support)")

    # HTTP transport
    http_parser = subparsers.add_parser("http", help="Use HTTP transport (supports admin API)")
    http_parser.add_argument("--host", default="localhost", help="Host to bind to")
    http_parser.add_argument("--port", type=int, default=8080, help="Port to bind to")

    # Remote MCP transport (Phase 1X)
    remote_parser = subparsers.add_parser(
        "remote", help="Use remote MCP server optimized for ChatGPT/Claude (Phase 1X)"
    )
    remote_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    remote_parser.add_argument("--port", type=int, default=8080, help="Port to bind to")

    # WebSocket transport
    ws_parser = subparsers.add_parser(
        "websocket", help="Use WebSocket transport (no admin API support)"
    )
    ws_parser.add_argument("--host", default="localhost", help="Host to bind to")
    ws_parser.add_argument("--port", type=int, default=8081, help="Port to bind to")

    args = parser.parse_args()

    # Default to stdio if no transport specified
    if not args.transport:
        args.transport = "stdio"

    try:
        if args.transport == "stdio":
            asyncio.run(run_stdio_server(debug=args.debug, config_file=args.config))
        elif args.transport == "http":
            asyncio.run(
                run_http_server(
                    host=args.host, port=args.port, debug=args.debug, config_file=args.config
                )
            )
        elif args.transport == "websocket":
            asyncio.run(
                run_websocket_server(
                    host=args.host, port=args.port, debug=args.debug, config_file=args.config
                )
            )
        elif args.transport == "remote":
            asyncio.run(
                run_remote_server(
                    host=args.host, port=args.port, debug=args.debug, config_file=args.config
                )
            )
        else:
            # If no transport specified, try to determine from config or env
            if args.config:
                config = Config.from_file(args.config)
                transport_type = config.transport.type
            else:
                env_config = Config.from_env()
                transport_type = env_config.transport.type if env_config.transport else "stdio"

            logger.info(f"Auto-detected transport type: {transport_type}")

            if transport_type == "stdio":
                asyncio.run(run_stdio_server(debug=args.debug, config_file=args.config))
            elif transport_type == "http":
                asyncio.run(run_http_server(debug=args.debug, config_file=args.config))
            elif transport_type == "websocket":
                asyncio.run(run_websocket_server(debug=args.debug, config_file=args.config))
            elif transport_type == "remote":
                asyncio.run(run_remote_server(debug=args.debug, config_file=args.config))
            else:
                logger.error(f"Unknown transport: {transport_type}")
                sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error running server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
