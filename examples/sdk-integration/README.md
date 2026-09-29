# MCP SDK Integration Examples

This directory contains examples showing how to use the MCP SDK for simplified integration with AI providers and MCP servers.

## 🚀 Quick Start

### 1. Simple 5-Line Chatbot
```python
from mcp_sdk import MCPClient

client = MCPClient("http://localhost:8080")
response = await client.chat("What's the weather in Tokyo?")
print(response.content)
```

**File**: [`simple_chatbot.py`](simple_chatbot.py)

### 2. One-Line Bot Creation
```python
from mcp_sdk import QuickStart

# Weather bot in 1 line!
QuickStart.weather_bot().run()
```

**File**: [`quick_start_demo.py`](quick_start_demo.py)

## 🤖 Provider Integration Examples

### OpenAI Responses API (Native Remote MCP)
Uses OpenAI's new Responses API with native remote MCP server support.

```python
from mcp_sdk.providers import OpenAIResponses
from mcp_sdk.types import MCPServerConfig

client = OpenAIResponses(
    api_key="sk-...",
    mcp_servers=[MCPServerConfig(
        label="my-server",
        url="https://my-mcp-server.com/mcp",
        require_approval="never"
    )]
)

response = await client.chat("What's the weather in Tokyo?")
```

**File**: [`openai_responses_example.py`](openai_responses_example.py)

### Claude MCP Integration (Native Protocol)
Shows how to configure Claude Desktop to connect to your MCP server.

```python
from mcp_sdk.providers import ClaudeMCP

client = ClaudeMCP(mcp_config={
    "mcpServers": {
        "my-server": {
            "command": ["python", "-m", "mcp.server"],
            "args": ["--config", "config.yaml"]
        }
    }
})
```

**File**: [`claude_mcp_example.py`](claude_mcp_example.py)

## 📁 File Overview

| File | Description | Complexity |
|------|-------------|------------|
| `simple_chatbot.py` | 5-line chatbot example | ⭐ |
| `quick_start_demo.py` | QuickStart utilities demo | ⭐ |
| `openai_responses_example.py` | OpenAI Responses API with remote MCP | ⭐⭐ |
| `claude_mcp_example.py` | Claude native MCP integration | ⭐⭐ |

## 🛠️ Setup

### 1. Install SDK (Available Now)
```bash
# SDK is included in the project
pip install -e .
```

### 2. Set Environment Variables
```bash
export OPENAI_API_KEY="sk-your-openai-key"
export OPENWEATHER_API_KEY="your-weather-key"  # Optional
export NEWS_API_KEY="your-news-key"            # Optional
```

### 3. Start MCP Server
```bash
# Start with admin API
export ADMIN_SECRET_KEY="your-secret-key"
make start
```

### 4. Run Examples
```bash
# Simple chatbot
python examples/sdk-integration/simple_chatbot.py

# QuickStart demo
python examples/sdk-integration/quick_start_demo.py

# Interactive demo
python examples/sdk-integration/quick_start_demo.py --interactive

# OpenAI Responses API
python examples/sdk-integration/openai_responses_example.py

# Claude MCP setup
python examples/sdk-integration/claude_mcp_example.py
```

## 🎯 Use Cases

### 1. Simple Chatbots
Perfect for:
- Prototyping AI assistants
- Adding AI capabilities to existing apps  
- Learning MCP integration patterns

### 2. Enterprise Applications
Ideal for:
- Customer service bots
- Internal productivity tools
- Data analysis assistants
- Workflow automation

### 3. Multi-Provider Support
Enables:
- A/B testing different AI models
- Fallback providers for reliability
- Cost optimization across providers
- Feature comparison and evaluation

## 🔄 Migration Path

### From Custom Integration
```python
# Before: Complex custom implementation
# 50+ lines of HTTP client code, error handling, etc.

# After: Simple SDK usage
from mcp_sdk import MCPClient
client = MCPClient("http://localhost:8080")
response = await client.chat("Hello!")
```

### From OpenAI Function Calling
```python
# Before: Manual function calling setup
functions = [{"name": "get_weather", "parameters": {...}}]
response = openai.chat.completions.create(model="gpt-4", functions=functions)

# After: Automatic function discovery
from mcp_sdk.providers import ChatClient
client = ChatClient.openai(api_key="sk-...", mcp_client=mcp_client)
response = await client.chat("What's the weather?")
```

### To Native MCP Support
```python
# Current: SDK with function calling emulation
client = ChatClient.openai(api_key="sk-...", mcp_client=mcp_client)

# Future: Direct OpenAI Responses API
client = OpenAIResponses(api_key="sk-...", mcp_servers=[server_config])
```

## 📈 Performance Benefits

| Metric | Custom Implementation | MCP SDK | Improvement |
|--------|----------------------|---------|-------------|
| Setup Time | 30+ minutes | <5 minutes | 6x faster |
| Lines of Code | 100+ lines | 5 lines | 20x reduction |
| Error Handling | Manual | Built-in | More reliable |
| Provider Support | Single | Multiple | More flexible |
| Maintenance | High | Low | Less overhead |

## 🧪 Testing Examples

```bash
# Test server connection
python -c "
import asyncio
from mcp_sdk import MCPClient

async def test():
    client = MCPClient('http://localhost:8080')
    health = await client.get_health()
    print(f'Server health: {health}')
    
asyncio.run(test())
"

# Test action execution
python -c "
import asyncio
from mcp_sdk import MCPClient

async def test():
    client = MCPClient('http://localhost:8080')
    result = await client.execute_action('python_calculator', {'code': 'result = 2**10'})
    print(f'2^10 = {result}')
    
asyncio.run(test())
"
```

## 🤝 Contributing

Found an issue or want to improve these examples?

1. Fork the repository
2. Create your feature branch
3. Add your example
4. Submit a pull request

## 📚 Related Documentation

- [MCP Server Documentation](../../README.md)
- [Admin API Reference](../embedded-admin/README.md)
- [OpenAI Chatbot Integration](../openai-chatbot-integration/README.md)
- [Docker Code Executor](../../docker/code-executor/README.md)

---

These examples demonstrate the power of the MCP SDK to drastically simplify AI integration while providing access to powerful MCP server capabilities! 🚀 