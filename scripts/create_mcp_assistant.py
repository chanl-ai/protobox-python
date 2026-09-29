#!/usr/bin/env python3
"""Create a new assistant with MCP tools enabled."""

import requests
import json

# Configuration
WORKSPACE_ID = "6883c972274b0349b71b5ff2"
BASE_URL = "http://localhost:8090"
API_BASE = f"{BASE_URL}/admin/api/v1/workspaces/{WORKSPACE_ID}"

def create_assistant():
    """Create a new assistant with MCP tools enabled."""
    print("Creating assistant with MCP tools...")
    
    assistant_data = {
        "name": "MCP Tools Test Assistant",
        "description": "Assistant configured to use MCP tools",
        "instructions": """You are a helpful AI assistant with access to MCP tools. 
        
When asked to echo a message, use the 'echo' tool.
When asked about the time, use the 'get_current_time' tool.

Always try to use the available tools when appropriate.""",
        "model": "gpt-4-turbo-preview",
        "enable_mcp_tools": True,
        "metadata": {
            "created_for": "MCP integration testing"
        }
    }
    
    response = requests.post(f"{API_BASE}/assistants", json=assistant_data)
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 200:
        assistant = response.json()
        print(f"Assistant created successfully!")
        print(f"ID: {assistant.get('id')}")
        print(f"Assistant ID: {assistant.get('assistant_id')}")
        print(f"Name: {assistant.get('name')}")
        print(f"Tools: {assistant.get('tools', [])}")
        return assistant
    else:
        print(f"Failed to create assistant: {response.text}")
        return None

if __name__ == "__main__":
    create_assistant()