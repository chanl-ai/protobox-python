#!/usr/bin/env python3
"""
Simple 5-line chatbot using MCP SDK

This is the simplest possible example of creating a chatbot with MCP actions.
"""

import asyncio
from mcp_sdk import MCPClient

async def main():
    # 5-line chatbot implementation
    client = MCPClient("http://localhost:8080")
    response = await client.chat("What's the weather in Tokyo?", provider="openai")
    print(response.content)

if __name__ == "__main__":
    asyncio.run(main()) 