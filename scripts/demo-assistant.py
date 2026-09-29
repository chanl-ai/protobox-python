#!/usr/bin/env python3
"""
Demo script to show AI assistant working with and without MCP tools
"""

import asyncio
import os
import sys
import json
from typing import Dict, Any
import aiohttp
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
API_BASE_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8090")
API_TOKEN = "dev_test_token"  # Using dev_test mode
WORKSPACE_ID = "6883c972274b0349b71b5ff2"  # Default test workspace

# Colors for output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


async def make_request(session: aiohttp.ClientSession, method: str, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Make an API request to the MCP server."""
    url = f"{API_BASE_URL}{endpoint}"
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    async with session.request(method, url, headers=headers, json=data) as response:
        response_data = await response.json()
        if response.status >= 400:
            print(f"{Colors.RED}Error {response.status}: {response_data}{Colors.ENDC}")
            raise Exception(f"API error: {response_data}")
        return response_data


async def create_sample_action(session: aiohttp.ClientSession) -> str:
    """Create a sample action for the assistant to use."""
    print(f"\n{Colors.CYAN}Creating sample action: 'get_current_time'{Colors.ENDC}")
    
    # First, try to get existing action
    try:
        actions = await make_request(
            session,
            "GET",
            f"/admin/api/v1/workspaces/{WORKSPACE_ID}/actions"
        )
        
        for action in actions:
            if action.get("name") == "get_current_time":
                print(f"{Colors.GREEN}✓ Action already exists with ID: {action['_id']}{Colors.ENDC}")
                return action["_id"]
    except:
        pass
    
    # Create new action if it doesn't exist
    action_data = {
        "name": "get_current_time",
        "description": "Get the current time in a specific timezone",
        "type": "CODE_RUN",
        "version": "1.0.0",
        "enabled": True,
        "config": {
            "language": "python",
            "code": """
import datetime
import pytz

timezone = variables.get('timezone', 'UTC')
try:
    tz = pytz.timezone(timezone)
    current_time = datetime.datetime.now(tz)
    return {
        "time": current_time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "timezone": timezone
    }
except:
    return {"error": f"Invalid timezone: {timezone}"}
"""
        },
        "variables": [
            {
                "name": "timezone",
                "type": "string",
                "description": "The timezone to get time for (e.g., 'US/Eastern', 'UTC')",
                "required": False,
                "default": "UTC"
            }
        ]
    }
    
    response = await make_request(
        session,
        "POST",
        f"/admin/api/v1/workspaces/{WORKSPACE_ID}/actions",
        action_data
    )
    
    action_id = response["_id"]
    print(f"{Colors.GREEN}✓ Created action with ID: {action_id}{Colors.ENDC}")
    return action_id


async def create_assistant(session: aiohttp.ClientSession, enable_tools: bool = False) -> Dict[str, Any]:
    """Create an assistant with or without MCP tools."""
    name = "ProtoBox Demo Assistant"
    if enable_tools:
        name += " (with Tools)"
        
    print(f"\n{Colors.CYAN}Creating assistant: {name}{Colors.ENDC}")
    
    assistant_data = {
        "name": name,
        "description": "Demo assistant for showcasing MCP capabilities",
        "instructions": """You are a helpful AI assistant for ProtoBox MCP server.
        
When tools are enabled, you have access to execute MCP actions defined in the workspace.
Currently available tools include:
- get_current_time: Get the current time in any timezone

When asked about the time, use the get_current_time tool to provide accurate information.""",
        "model": "gpt-4-turbo-preview",
        "enable_mcp_tools": enable_tools
    }
    
    response = await make_request(
        session,
        "POST",
        f"/admin/api/v1/workspaces/{WORKSPACE_ID}/assistants",
        assistant_data
    )
    
    print(f"{Colors.GREEN}✓ Created assistant: {response['name']}{Colors.ENDC}")
    return response


async def create_thread(session: aiohttp.ClientSession, assistant_id: str) -> str:
    """Create a conversation thread."""
    print(f"\n{Colors.CYAN}Creating conversation thread{Colors.ENDC}")
    
    thread_data = {
        "title": "Demo conversation",
        "metadata": {
            "created_by": "demo_script"
        }
    }
    
    response = await make_request(
        session,
        "POST",
        f"/admin/api/v1/workspaces/{WORKSPACE_ID}/assistants/{assistant_id}/threads",
        thread_data
    )
    
    thread_id = response["id"]
    print(f"{Colors.GREEN}✓ Created thread with ID: {thread_id}{Colors.ENDC}")
    return thread_id


async def send_message(session: aiohttp.ClientSession, thread_id: str, message: str) -> Dict[str, Any]:
    """Send a message to the assistant and get the response."""
    print(f"\n{Colors.BLUE}You: {message}{Colors.ENDC}")
    
    message_data = {
        "content": message,
        "metadata": {}
    }
    
    response = await make_request(
        session,
        "POST",
        f"/admin/api/v1/workspaces/{WORKSPACE_ID}/assistants/threads/{thread_id}/messages",
        message_data
    )
    
    # Extract the assistant's response
    if response.get("message"):
        assistant_message = response["message"]
        print(f"{Colors.GREEN}Assistant: {assistant_message.get('content', 'No response')}{Colors.ENDC}")
        
        # Show tool calls if any
        tool_calls = assistant_message.get("tool_calls", [])
        if tool_calls:
            print(f"\n{Colors.YELLOW}Tool calls made:{Colors.ENDC}")
            for tool in tool_calls:
                print(f"  - {tool.get('function', {}).get('name', 'Unknown')}")
    
    return response


async def demo_without_tools(session: aiohttp.ClientSession):
    """Demo assistant without tools."""
    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}DEMO 1: Assistant WITHOUT Tools{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
    
    # Create assistant without tools
    assistant = await create_assistant(session, enable_tools=False)
    
    # Create thread
    thread_id = await create_thread(session, assistant["id"])
    
    # Send messages
    await send_message(session, thread_id, "Hello! Can you tell me what time it is?")
    await send_message(session, thread_id, "What can you help me with regarding MCP server?")


async def demo_with_tools(session: aiohttp.ClientSession):
    """Demo assistant with tools."""
    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}DEMO 2: Assistant WITH Tools{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
    
    # Create assistant with tools
    assistant = await create_assistant(session, enable_tools=True)
    
    # Create thread
    thread_id = await create_thread(session, assistant["id"])
    
    # Send messages
    await send_message(session, thread_id, "Hello! Can you tell me what time it is in New York?")
    await send_message(session, thread_id, "What about the time in Tokyo?")
    await send_message(session, thread_id, "Can you explain how MCP actions work?")


async def main():
    """Run the demo."""
    print(f"{Colors.BOLD}ProtoBox AI Assistant Demo{Colors.ENDC}")
    print(f"Server: {API_BASE_URL}")
    print(f"Workspace: {WORKSPACE_ID}")
    
    async with aiohttp.ClientSession() as session:
        try:
            # Create a sample action first
            await create_sample_action(session)
            
            # Demo without tools
            await demo_without_tools(session)
            
            # Demo with tools
            await demo_with_tools(session)
            
            print(f"\n{Colors.GREEN}{Colors.BOLD}Demo completed successfully!{Colors.ENDC}")
            print(f"\n{Colors.CYAN}Key differences observed:{Colors.ENDC}")
            print("1. Without tools: Assistant can only provide general information")
            print("2. With tools: Assistant can execute actions and provide real-time data")
            
        except Exception as e:
            print(f"\n{Colors.RED}Error: {e}{Colors.ENDC}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())