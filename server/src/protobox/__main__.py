#!/usr/bin/env python3
"""
MCP package entry point

This allows running the MCP server with: python -m mcp
"""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
