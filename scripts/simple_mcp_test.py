#!/usr/bin/env python3
"""Simple test showing FastMCP + OpenAI Agents SDK working together"""

import asyncio
import os
from fastmcp import FastMCP

# Initialize FastMCP
mcp = FastMCP("Test MCP Server")

@mcp.tool()
def hello_world(name: str) -> str:
    """Say hello to someone"""
    return f"Hello, {name}! This is from FastMCP."

@mcp.tool()
def add_numbers(a: int, b: int) -> int:
    """Add two numbers together"""
    return a + b

async def test_with_agents_sdk():
    """Test MCP with OpenAI Agents SDK"""
    try:
        # Import OpenAI Agents SDK
        from agents import Agent
        from agents.tool import Mcp
        
        # Set OpenAI API key from environment
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            print("❌ OPENAI_API_KEY not found in environment")
            return
        
        # Start MCP server using the correct method
        print("🚀 Starting FastMCP server...")
        import threading
        import time
        
        # Run server in thread
        def run_server():
            mcp.run(port=8091)
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        time.sleep(2)  # Wait for server to start
        
        server_url = "http://localhost:8091"
        print(f"✅ FastMCP server running at: {server_url}")
        
        # Create MCP configuration for Agents SDK
        mcp_config = Mcp(
            url=server_url,
            name="Test MCP"
        )
        
        # Create agent with MCP tools
        agent = Agent(
            name="MCP Test Agent",
            instructions="You are a helpful assistant that can use MCP tools.",
            model="gpt-4o-mini",
            tools=[mcp_config]
        )
        
        print("✅ Created agent with MCP tools")
        
        # Test the agent
        from agents import Runner
        result = await Runner.run(
            starting_agent=agent,
            input="Please say hello to 'FastMCP' and then add the numbers 15 and 27"
        )
        
        print(f"🎉 Agent response: {result.final_output}")
        
    except ImportError as e:
        print(f"❌ OpenAI Agents SDK not available: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_with_agents_sdk())