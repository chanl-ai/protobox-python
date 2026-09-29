#!/usr/bin/env python3
"""
OpenAI MCP Client with Function Events

This example demonstrates event-driven MCP client capabilities including:
- Function call events and callbacks
- Real-time tool execution monitoring
- Event streaming and processing
- Webhook-style event handling
- Tool execution lifecycle events

Prerequisites:
- MCP server running (local/staging/production)
- OpenAI API key
- MCP server with configured tools

Usage:
    # Staging
    export MCP_SERVER_URL="http://localhost:8090"
    export OPENAI_API_KEY="your-api-key"
    python openai-mcp-events.py
    
    # Local testing
    export MCP_SERVER_URL="http://localhost:8080"
    export OPENAI_API_KEY="your-api-key"
    python openai-mcp-events.py
"""

import os
import sys
import json
import time
import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from openai import OpenAI


class EventType(Enum):
    """Types of MCP events"""
    TOOL_DISCOVERY_START = "tool_discovery_start"
    TOOL_DISCOVERY_COMPLETE = "tool_discovery_complete"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_COMPLETE = "tool_call_complete"
    TOOL_CALL_ERROR = "tool_call_error"
    CONVERSATION_START = "conversation_start"
    CONVERSATION_COMPLETE = "conversation_complete"
    STREAM_MESSAGE = "stream_message"
    PERFORMANCE_METRIC = "performance_metric"


@dataclass
class MCPEvent:
    """MCP event data structure"""
    event_type: EventType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    source: str = "mcp_client"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "correlation_id": self.correlation_id,
            "source": self.source
        }


class EventHandler:
    """Base class for MCP event handlers"""
    
    def handle_event(self, event: MCPEvent) -> None:
        """Handle an MCP event"""
        method_name = f"on_{event.event_type.value}"
        if hasattr(self, method_name):
            getattr(self, method_name)(event)
        else:
            self.on_unknown_event(event)
    
    def on_unknown_event(self, event: MCPEvent) -> None:
        """Handle unknown events"""
        pass


class ConsoleEventHandler(EventHandler):
    """Console-based event handler with colored output"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.event_count = 0
    
    def handle_event(self, event: MCPEvent) -> None:
        """Handle event with console output"""
        self.event_count += 1
        super().handle_event(event)
    
    def on_tool_discovery_start(self, event: MCPEvent) -> None:
        print(f"🔍 [EVENT] Tool discovery started")
    
    def on_tool_discovery_complete(self, event: MCPEvent) -> None:
        tools_count = event.data.get('tools_count', 0)
        print(f"✅ [EVENT] Tool discovery completed: {tools_count} tools found")
    
    def on_tool_call_start(self, event: MCPEvent) -> None:
        tool_name = event.data.get('tool_name', 'unknown')
        print(f"🛠️ [EVENT] Tool call started: {tool_name}")
        if self.verbose and 'arguments' in event.data:
            print(f"   Arguments: {json.dumps(event.data['arguments'], indent=2)}")
    
    def on_tool_call_complete(self, event: MCPEvent) -> None:
        tool_name = event.data.get('tool_name', 'unknown')
        duration = event.data.get('duration_ms', 0)
        print(f"✅ [EVENT] Tool call completed: {tool_name} ({duration:.2f}ms)")
        if self.verbose and 'result' in event.data:
            result = event.data['result']
            if isinstance(result, str) and len(result) > 100:
                result = result[:100] + "..."
            print(f"   Result: {result}")
    
    def on_tool_call_error(self, event: MCPEvent) -> None:
        tool_name = event.data.get('tool_name', 'unknown')
        error = event.data.get('error', 'Unknown error')
        print(f"❌ [EVENT] Tool call failed: {tool_name} - {error}")
    
    def on_conversation_start(self, event: MCPEvent) -> None:
        prompt = event.data.get('prompt', '')
        print(f"💬 [EVENT] Conversation started")
        if self.verbose:
            print(f"   Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    
    def on_conversation_complete(self, event: MCPEvent) -> None:
        tool_calls = event.data.get('tool_calls_count', 0)
        duration = event.data.get('duration_ms', 0)
        print(f"✅ [EVENT] Conversation completed: {tool_calls} tool calls ({duration:.2f}ms)")
    
    def on_performance_metric(self, event: MCPEvent) -> None:
        metric_name = event.data.get('metric_name', 'unknown')
        value = event.data.get('value', 0)
        unit = event.data.get('unit', '')
        print(f"📊 [EVENT] Performance metric: {metric_name} = {value}{unit}")
    
    def on_stream_message(self, event: MCPEvent) -> None:
        if self.verbose:
            message = event.data.get('message', '')
            print(f"📡 [EVENT] Stream: {message}")
    
    def get_stats(self) -> Dict[str, Any]:
        return {"total_events": self.event_count}


class MetricsEventHandler(EventHandler):
    """Event handler that collects metrics"""
    
    def __init__(self):
        self.metrics = {
            "tool_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_duration_ms": 0,
            "tools_used": set(),
            "conversations": 0,
            "events_processed": 0
        }
    
    def handle_event(self, event: MCPEvent) -> None:
        self.metrics["events_processed"] += 1
        super().handle_event(event)
    
    def on_tool_call_start(self, event: MCPEvent) -> None:
        self.metrics["tool_calls"] += 1
        tool_name = event.data.get('tool_name')
        if tool_name:
            self.metrics["tools_used"].add(tool_name)
    
    def on_tool_call_complete(self, event: MCPEvent) -> None:
        self.metrics["successful_calls"] += 1
        duration = event.data.get('duration_ms', 0)
        self.metrics["total_duration_ms"] += duration
    
    def on_tool_call_error(self, event: MCPEvent) -> None:
        self.metrics["failed_calls"] += 1
    
    def on_conversation_start(self, event: MCPEvent) -> None:
        self.metrics["conversations"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        metrics = self.metrics.copy()
        metrics["tools_used"] = list(metrics["tools_used"])
        metrics["average_duration_ms"] = (
            metrics["total_duration_ms"] / metrics["successful_calls"]
            if metrics["successful_calls"] > 0 else 0
        )
        metrics["success_rate"] = (
            metrics["successful_calls"] / metrics["tool_calls"]
            if metrics["tool_calls"] > 0 else 0
        )
        return metrics


class EventDrivenMCPClient:
    """Event-driven MCP client with comprehensive event handling"""
    
    def __init__(self, server_url: str, api_key: str, openai_api_key: str):
        self.server_url = server_url
        self.api_key = api_key
        self.openai_client = OpenAI(api_key=openai_api_key)
        
        # Determine environment
        if "localhost" in server_url or "127.0.0.1" in server_url:
            self.environment = "local"
        elif "staging" in server_url:
            self.environment = "staging"
        else:
            self.environment = "production"
        
        # Configure MCP server
        self.mcp_config = {
            "type": "mcp",
            "server_label": f"mcp-server-{self.environment}",
            "server_url": f"{server_url}/mcp/",
            "require_approval": "never",
        }
        
        # Add authentication if API key provided
        if api_key:
            self.mcp_config["headers"] = {
                "Authorization": f"Bearer {api_key}"
            }
        
        # Event handling
        self.event_handlers: List[EventHandler] = []
        self.event_queue: List[MCPEvent] = []
        
        # State
        self.tools = {}
        self.session_id = f"session_{int(time.time())}"
    
    def add_event_handler(self, handler: EventHandler) -> None:
        """Add an event handler"""
        self.event_handlers.append(handler)
    
    def emit_event(self, event_type: EventType, data: Dict[str, Any] = None, correlation_id: str = None) -> None:
        """Emit an event to all handlers"""
        event = MCPEvent(
            event_type=event_type,
            data=data or {},
            correlation_id=correlation_id or self.session_id
        )
        
        self.event_queue.append(event)
        
        for handler in self.event_handlers:
            try:
                handler.handle_event(event)
            except Exception as e:
                print(f"⚠️ Event handler error: {e}")
    
    def discover_tools_with_events(self) -> List[Dict[str, Any]]:
        """Discover tools with event emission"""
        correlation_id = f"discovery_{int(time.time())}"
        
        self.emit_event(
            EventType.TOOL_DISCOVERY_START,
            {"server_url": self.server_url},
            correlation_id
        )
        
        try:
            start_time = time.time()
            
            response = self.openai_client.responses.create(
                model="gpt-4o",
                tools=[self.mcp_config],
                input=[{
                    "type": "message",
                    "role": "user",
                    "content": "What tools are available? List each tool with its name, description, and parameters."
                }]
            )
            
            tools = []
            for output in response.output:
                if output.type == "mcp_call":
                    tools.append({
                        "name": output.name,
                        "description": getattr(output, 'description', 'No description available'),
                        "parameters": getattr(output, 'arguments', {}),
                        "result": output.output if output.output else None
                    })
            
            # Cache discovered tools
            self.tools = {tool['name']: tool for tool in tools}
            
            duration_ms = (time.time() - start_time) * 1000
            
            self.emit_event(
                EventType.TOOL_DISCOVERY_COMPLETE,
                {
                    "tools_count": len(tools),
                    "tools": [tool['name'] for tool in tools],
                    "duration_ms": duration_ms
                },
                correlation_id
            )
            
            return tools
            
        except Exception as e:
            self.emit_event(
                EventType.TOOL_CALL_ERROR,
                {"error": str(e), "phase": "discovery"},
                correlation_id
            )
            return []
    
    def execute_tool_with_events(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with comprehensive event emission"""
        correlation_id = f"tool_{tool_name}_{int(time.time())}"
        
        self.emit_event(
            EventType.TOOL_CALL_START,
            {
                "tool_name": tool_name,
                "arguments": arguments
            },
            correlation_id
        )
        
        start_time = time.time()
        
        try:
            response = self.openai_client.responses.create(
                model="gpt-4o",
                tools=[self.mcp_config],
                input=[{
                    "type": "message",
                    "role": "user",
                    "content": f"Use the {tool_name} tool with these arguments: {json.dumps(arguments)}"
                }]
            )
            
            # Process response
            for output in response.output:
                if output.type == "mcp_call" and output.name == tool_name:
                    duration_ms = (time.time() - start_time) * 1000
                    
                    if output.error:
                        self.emit_event(
                            EventType.TOOL_CALL_ERROR,
                            {
                                "tool_name": tool_name,
                                "error": output.error,
                                "duration_ms": duration_ms
                            },
                            correlation_id
                        )
                        return {"success": False, "error": output.error}
                    else:
                        self.emit_event(
                            EventType.TOOL_CALL_COMPLETE,
                            {
                                "tool_name": tool_name,
                                "result": output.output,
                                "duration_ms": duration_ms
                            },
                            correlation_id
                        )
                        return {"success": True, "result": output.output}
            
            # No matching tool call found
            duration_ms = (time.time() - start_time) * 1000
            self.emit_event(
                EventType.TOOL_CALL_ERROR,
                {
                    "tool_name": tool_name,
                    "error": "Tool call not found in response",
                    "duration_ms": duration_ms
                },
                correlation_id
            )
            return {"success": False, "error": "Tool call not found in response"}
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.emit_event(
                EventType.TOOL_CALL_ERROR,
                {
                    "tool_name": tool_name,
                    "error": str(e),
                    "duration_ms": duration_ms
                },
                correlation_id
            )
            return {"success": False, "error": str(e)}
    
    def conversation_with_events(self, prompt: str) -> Dict[str, Any]:
        """Have a conversation with comprehensive event tracking"""
        correlation_id = f"conv_{int(time.time())}"
        
        self.emit_event(
            EventType.CONVERSATION_START,
            {"prompt": prompt},
            correlation_id
        )
        
        start_time = time.time()
        
        try:
            response = self.openai_client.responses.create(
                model="gpt-4o",
                tools=[self.mcp_config],
                input=[{
                    "type": "message",
                    "role": "user",
                    "content": prompt
                }]
            )
            
            conversation_result = {
                "prompt": prompt,
                "tool_calls": [],
                "assistant_messages": [],
                "success": True,
                "error": None
            }
            
            for output in response.output:
                if output.type == "message":
                    message_content = output.content[0].text if output.content else ""
                    conversation_result["assistant_messages"].append({
                        "content": message_content,
                        "role": "assistant"
                    })
                    
                    self.emit_event(
                        EventType.STREAM_MESSAGE,
                        {"message": message_content, "type": "assistant"},
                        correlation_id
                    )
                    
                elif output.type == "mcp_call":
                    tool_call = {
                        "tool": output.name,
                        "arguments": output.arguments,
                        "result": output.output,
                        "error": output.error,
                        "success": not bool(output.error)
                    }
                    conversation_result["tool_calls"].append(tool_call)
                    
                    # Emit individual tool events
                    if output.error:
                        self.emit_event(
                            EventType.TOOL_CALL_ERROR,
                            {
                                "tool_name": output.name,
                                "error": output.error,
                                "context": "conversation"
                            },
                            correlation_id
                        )
                    else:
                        self.emit_event(
                            EventType.TOOL_CALL_COMPLETE,
                            {
                                "tool_name": output.name,
                                "result": output.output,
                                "context": "conversation"
                            },
                            correlation_id
                        )
            
            duration_ms = (time.time() - start_time) * 1000
            
            self.emit_event(
                EventType.CONVERSATION_COMPLETE,
                {
                    "tool_calls_count": len(conversation_result["tool_calls"]),
                    "messages_count": len(conversation_result["assistant_messages"]),
                    "duration_ms": duration_ms,
                    "success": True
                },
                correlation_id
            )
            
            return conversation_result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            self.emit_event(
                EventType.CONVERSATION_COMPLETE,
                {
                    "error": str(e),
                    "duration_ms": duration_ms,
                    "success": False
                },
                correlation_id
            )
            
            return {
                "prompt": prompt,
                "tool_calls": [],
                "assistant_messages": [],
                "success": False,
                "error": str(e)
            }
    
    def emit_performance_metrics(self) -> None:
        """Emit current performance metrics"""
        # Get metrics from handlers
        for handler in self.event_handlers:
            if isinstance(handler, MetricsEventHandler):
                metrics = handler.get_metrics()
                for metric_name, value in metrics.items():
                    if isinstance(value, (int, float)):
                        self.emit_event(
                            EventType.PERFORMANCE_METRIC,
                            {
                                "metric_name": metric_name,
                                "value": value,
                                "unit": "ms" if "duration" in metric_name else ""
                            }
                        )
    
    def get_event_history(self) -> List[Dict[str, Any]]:
        """Get the complete event history"""
        return [event.to_dict() for event in self.event_queue]


def main():
    """Main function demonstrating event-driven MCP client"""
    # Configuration from environment
    MCP_SERVER_URL = os.getenv("MCP_SERVER_URL")
    MCP_API_KEY = os.getenv("MCP_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Validate configuration
    if not MCP_SERVER_URL:
        print("❌ Please set MCP_SERVER_URL environment variable")
        sys.exit(1)
    
    if not OPENAI_API_KEY:
        print("❌ Please set OPENAI_API_KEY environment variable")
        sys.exit(1)
    
    print("🎭 Event-Driven OpenAI MCP Client")
    print(f"🔗 Server: {MCP_SERVER_URL}")
    print("=" * 60)
    
    # Initialize client
    client = EventDrivenMCPClient(MCP_SERVER_URL, MCP_API_KEY, OPENAI_API_KEY)
    
    # Add event handlers
    console_handler = ConsoleEventHandler(verbose=True)
    metrics_handler = MetricsEventHandler()
    
    client.add_event_handler(console_handler)
    client.add_event_handler(metrics_handler)
    
    try:
        # 1. Tool Discovery with Events
        print("\n📡 TOOL DISCOVERY WITH EVENTS")
        print("=" * 60)
        tools = client.discover_tools_with_events()
        
        if not tools:
            print("❌ No tools discovered. Exiting.")
            sys.exit(1)
        
        # 2. Individual Tool Execution with Events
        print("\n🛠️ TOOL EXECUTION WITH EVENTS")
        print("=" * 60)
        
        if "echo" in client.tools:
            client.execute_tool_with_events("echo", {"message": "Hello from event-driven client!"})
        
        if "calculator" in client.tools:
            client.execute_tool_with_events("calculator", {"expression": "2 ** 10"})
        
        # 3. Complex Conversation with Events
        print("\n💬 CONVERSATION WITH EVENTS")
        print("=" * 60)
        
        conversation_prompts = [
            "Calculate 25 * 4 and then echo the result with a congratulatory message",
            "Search for 'event-driven programming' and summarize the key concepts",
            "Use the echo tool to say hello, then calculate the square root of 144"
        ]
        
        for prompt in conversation_prompts:
            print(f"\n🎯 Prompt: {prompt[:50]}{'...' if len(prompt) > 50 else ''}")
            result = client.conversation_with_events(prompt)
            
        # 4. Performance Metrics
        print("\n📊 PERFORMANCE METRICS")
        print("=" * 60)
        
        client.emit_performance_metrics()
        
        # Display final metrics
        metrics = metrics_handler.get_metrics()
        print(f"\nFinal Metrics:")
        print(f"  Total tool calls: {metrics['tool_calls']}")
        print(f"  Successful calls: {metrics['successful_calls']}")
        print(f"  Failed calls: {metrics['failed_calls']}")
        print(f"  Success rate: {metrics['success_rate']:.1%}")
        print(f"  Average duration: {metrics['average_duration_ms']:.2f}ms")
        print(f"  Tools used: {', '.join(metrics['tools_used'])}")
        print(f"  Conversations: {metrics['conversations']}")
        print(f"  Events processed: {metrics['events_processed']}")
        
        # 5. Event History
        print("\n📜 EVENT HISTORY SUMMARY")
        print("=" * 60)
        
        event_history = client.get_event_history()
        event_types = {}
        for event in event_history:
            event_type = event['event_type']
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        print(f"Total events: {len(event_history)}")
        for event_type, count in sorted(event_types.items()):
            print(f"  {event_type}: {count}")
        
        print("\n✅ Event-driven MCP client demo completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⚠️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main() 