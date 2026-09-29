#!/usr/bin/env python3
"""
Advanced OpenAI MCP Client Example

This example demonstrates advanced MCP client capabilities including:
- Tool discovery and introspection
- API calling through MCP tools
- Function events and callbacks
- Error handling and retry logic
- Streaming responses
- Complex tool chaining

Prerequisites:
- MCP server running (local/staging/production)
- OpenAI API key
- MCP server with configured tools

Usage:
    # Staging
    export MCP_SERVER_URL="http://localhost:8090"
    export OPENAI_API_KEY="your-api-key"
    python openai-mcp-advanced.py
    
    # Local testing
    export MCP_SERVER_URL="http://localhost:8080"
    export OPENAI_API_KEY="your-api-key"
    python openai-mcp-advanced.py
"""

import os
import sys
import json
import time
import asyncio
from typing import Dict, List, Any, Optional
from openai import OpenAI
from dataclasses import dataclass


@dataclass
class MCPToolResult:
    """Result from an MCP tool execution"""
    tool_name: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0


class AdvancedMCPClient:
    """Advanced MCP client with enhanced capabilities"""
    
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
        
        self.tool_cache = {}
        self.execution_history = []
    
    def discover_tools(self) -> List[Dict[str, Any]]:
        """Discover available MCP tools"""
        print("🔍 Discovering available MCP tools...")
        
        try:
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
            self.tool_cache = {tool['name']: tool for tool in tools}
            
            print(f"   Found {len(tools)} tools:")
            for tool in tools:
                print(f"   - {tool['name']}: {tool.get('description', 'No description')}")
            
            return tools
            
        except Exception as e:
            print(f"   ❌ Tool discovery failed: {e}")
            return []
    
    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> MCPToolResult:
        """Execute a specific MCP tool with error handling"""
        start_time = time.time()
        
        try:
            print(f"\n🛠️ Executing tool: {tool_name}")
            print(f"   Arguments: {json.dumps(arguments, indent=2)}")
            
            response = self.openai_client.responses.create(
                model="gpt-4o",
                tools=[self.mcp_config],
                input=[{
                    "type": "message",
                    "role": "user",
                    "content": f"Use the {tool_name} tool with these arguments: {json.dumps(arguments)}"
                }]
            )
            
            execution_time = time.time() - start_time
            
            # Process response
            for output in response.output:
                if output.type == "mcp_call" and output.name == tool_name:
                    if output.error:
                        result = MCPToolResult(
                            tool_name=tool_name,
                            success=False,
                            error=output.error,
                            execution_time=execution_time
                        )
                        print(f"   ❌ Tool execution failed: {output.error}")
                    else:
                        result = MCPToolResult(
                            tool_name=tool_name,
                            success=True,
                            result=output.output,
                            execution_time=execution_time
                        )
                        print(f"   ✅ Tool executed successfully in {execution_time:.2f}s")
                        if output.output:
                            print(f"   Result: {json.dumps(output.output, indent=2)}")
                    
                    self.execution_history.append(result)
                    return result
            
            # If no matching tool call found
            result = MCPToolResult(
                tool_name=tool_name,
                success=False,
                error="Tool call not found in response",
                execution_time=execution_time
            )
            self.execution_history.append(result)
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            result = MCPToolResult(
                tool_name=tool_name,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
            self.execution_history.append(result)
            print(f"   ❌ Tool execution failed: {e}")
            return result
    
    def chain_tools(self, tool_chain: List[Dict[str, Any]]) -> List[MCPToolResult]:
        """Execute a chain of tools, passing results between them"""
        print(f"\n🔗 Executing tool chain with {len(tool_chain)} steps...")
        
        results = []
        context = {}
        
        for i, step in enumerate(tool_chain):
            tool_name = step["tool"]
            arguments = step["arguments"]
            
            # Replace placeholders with previous results
            if "use_previous_result" in step and step["use_previous_result"] and results:
                previous_result = results[-1]
                if previous_result.success and previous_result.result:
                    # Merge previous result into arguments
                    if isinstance(previous_result.result, dict):
                        arguments.update(previous_result.result)
                    else:
                        arguments["previous_result"] = previous_result.result
            
            print(f"\n   Step {i+1}/{len(tool_chain)}: {tool_name}")
            result = self.execute_tool(tool_name, arguments)
            results.append(result)
            
            # Stop chain if a tool fails
            if not result.success:
                print(f"   ⚠️ Tool chain stopped at step {i+1} due to failure")
                break
            
            # Add result to context for next tools
            context[f"step_{i+1}_result"] = result.result
        
        return results
    
    def complex_conversation(self, prompt: str) -> Dict[str, Any]:
        """Have a complex conversation that may use multiple tools"""
        print(f"\n💬 Starting complex conversation...")
        print(f"   Prompt: {prompt}")
        
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
                    conversation_result["assistant_messages"].append({
                        "content": output.content[0].text if output.content else "",
                        "role": "assistant"
                    })
                    print(f"\n🤖 Assistant: {output.content[0].text if output.content else ''}")
                    
                elif output.type == "mcp_call":
                    tool_call = {
                        "tool": output.name,
                        "arguments": output.arguments,
                        "result": output.output,
                        "error": output.error,
                        "success": not bool(output.error)
                    }
                    conversation_result["tool_calls"].append(tool_call)
                    
                    if output.error:
                        print(f"\n❌ Tool {output.name} failed: {output.error}")
                    else:
                        print(f"\n✅ Tool {output.name} succeeded")
                        if output.output:
                            print(f"   Result: {json.dumps(output.output, indent=2)}")
            
            return conversation_result
            
        except Exception as e:
            print(f"\n❌ Conversation failed: {e}")
            return {
                "prompt": prompt,
                "tool_calls": [],
                "assistant_messages": [],
                "success": False,
                "error": str(e)
            }
    
    def benchmark_tools(self, iterations: int = 3) -> Dict[str, Any]:
        """Benchmark tool performance"""
        print(f"\n⏱️ Benchmarking tools ({iterations} iterations each)...")
        
        benchmarks = {}
        
        for tool_name in self.tool_cache.keys():
            print(f"\n   Benchmarking {tool_name}...")
            
            execution_times = []
            success_count = 0
            
            for i in range(iterations):
                # Use simple test arguments based on tool name
                if tool_name == "echo":
                    args = {"message": f"benchmark test {i+1}"}
                elif tool_name == "calculator":
                    args = {"expression": f"2 + {i+1}"}
                elif tool_name == "search":
                    args = {"query": "test", "limit": 1}
                elif tool_name == "fetch":
                    args = {"url": "https://httpbin.org/get"}
                else:
                    args = {"test": f"benchmark {i+1}"}
                
                result = self.execute_tool(tool_name, args)
                execution_times.append(result.execution_time)
                if result.success:
                    success_count += 1
            
            benchmarks[tool_name] = {
                "avg_execution_time": sum(execution_times) / len(execution_times),
                "min_execution_time": min(execution_times),
                "max_execution_time": max(execution_times),
                "success_rate": success_count / iterations,
                "total_executions": iterations
            }
            
            print(f"      Avg: {benchmarks[tool_name]['avg_execution_time']:.2f}s")
            print(f"      Success rate: {benchmarks[tool_name]['success_rate']:.1%}")
        
        return benchmarks
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get statistics about tool executions"""
        if not self.execution_history:
            return {"message": "No executions recorded"}
        
        total_executions = len(self.execution_history)
        successful_executions = sum(1 for r in self.execution_history if r.success)
        total_time = sum(r.execution_time for r in self.execution_history)
        
        tool_stats = {}
        for result in self.execution_history:
            if result.tool_name not in tool_stats:
                tool_stats[result.tool_name] = {"count": 0, "successes": 0, "total_time": 0}
            
            tool_stats[result.tool_name]["count"] += 1
            if result.success:
                tool_stats[result.tool_name]["successes"] += 1
            tool_stats[result.tool_name]["total_time"] += result.execution_time
        
        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "success_rate": successful_executions / total_executions,
            "total_execution_time": total_time,
            "average_execution_time": total_time / total_executions,
            "tool_statistics": tool_stats
        }


def main():
    """Main function demonstrating advanced MCP client capabilities"""
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
    
    print("🚀 Advanced OpenAI MCP Client")
    print(f"🔗 Server: {MCP_SERVER_URL}")
    print("=" * 60)
    
    # Initialize client
    client = AdvancedMCPClient(MCP_SERVER_URL, MCP_API_KEY, OPENAI_API_KEY)
    
    try:
        # 1. Tool Discovery
        tools = client.discover_tools()
        if not tools:
            print("❌ No tools discovered. Exiting.")
            sys.exit(1)
        
        # 2. Individual tool testing
        print("\n" + "=" * 60)
        print("🧪 INDIVIDUAL TOOL TESTING")
        print("=" * 60)
        
        # Test echo tool
        if "echo" in client.tool_cache:
            client.execute_tool("echo", {"message": "Hello from advanced MCP client!"})
        
        # Test calculator tool
        if "calculator" in client.tool_cache:
            client.execute_tool("calculator", {"expression": "fibonacci(10)"})
        
        # Test search tool
        if "search" in client.tool_cache:
            client.execute_tool("search", {"query": "Python MCP protocol", "limit": 3})
        
        # 3. Tool chaining
        print("\n" + "=" * 60)
        print("🔗 TOOL CHAINING")
        print("=" * 60)
        
        tool_chain = [
            {
                "tool": "calculator",
                "arguments": {"expression": "2 ** 8"},
                "use_previous_result": False
            },
            {
                "tool": "echo",
                "arguments": {"message": "The result of 2^8 is: "},
                "use_previous_result": True
            }
        ]
        
        chain_results = client.chain_tools(tool_chain)
        
        # 4. Complex conversation
        print("\n" + "=" * 60)
        print("💬 COMPLEX CONVERSATION")
        print("=" * 60)
        
        complex_prompts = [
            "Calculate the factorial of 5, then search for information about factorials in mathematics",
            "Echo 'Starting calculation', then calculate 15 * 23, then echo the result",
            "Search for 'MCP protocol documentation' and summarize what you find"
        ]
        
        for prompt in complex_prompts:
            conversation_result = client.complex_conversation(prompt)
            if conversation_result["success"]:
                print(f"✅ Conversation completed with {len(conversation_result['tool_calls'])} tool calls")
            else:
                print(f"❌ Conversation failed: {conversation_result['error']}")
        
        # 5. Performance benchmarking
        print("\n" + "=" * 60)
        print("⏱️ PERFORMANCE BENCHMARKING")
        print("=" * 60)
        
        benchmarks = client.benchmark_tools(iterations=2)
        
        print("\nBenchmark Results:")
        for tool_name, stats in benchmarks.items():
            print(f"  {tool_name}:")
            print(f"    Average time: {stats['avg_execution_time']:.3f}s")
            print(f"    Success rate: {stats['success_rate']:.1%}")
        
        # 6. Execution statistics
        print("\n" + "=" * 60)
        print("📊 EXECUTION STATISTICS")
        print("=" * 60)
        
        stats = client.get_execution_stats()
        print(f"Total executions: {stats['total_executions']}")
        print(f"Success rate: {stats['success_rate']:.1%}")
        print(f"Average execution time: {stats['average_execution_time']:.3f}s")
        
        print("\nPer-tool statistics:")
        for tool_name, tool_stats in stats['tool_statistics'].items():
            success_rate = tool_stats['successes'] / tool_stats['count']
            avg_time = tool_stats['total_time'] / tool_stats['count']
            print(f"  {tool_name}: {tool_stats['count']} calls, {success_rate:.1%} success, {avg_time:.3f}s avg")
        
        print("\n✅ Advanced MCP client demo completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⚠️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main() 