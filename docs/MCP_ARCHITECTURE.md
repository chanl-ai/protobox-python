# MCP Architecture & Migration Plan

## Todo List

- [ ] Create comprehensive test suite for MCP protocol compatibility
- [ ] Implement workspace isolation tests with action creation  
- [ ] Create OpenAI assistant integration tests
- [ ] Enhance protocol package with workspace-aware server
- [ ] Create workspace tool registry with database integration
- [ ] Implement native MCP router to replace FastMCP
- [ ] Add workspace manager for server instance management
- [ ] Update server.py to use native router
- [ ] Create migration documentation

## Overview

This document outlines the migration plan from FastMCP library dependency to our native MCP protocol implementation while maintaining full compatibility with FastMCP clients and enabling OpenAI assistant integration.

## Current State Analysis

### FastMCP Library (fastmcp-lib)
- **Server Architecture**: Complete MCP server with decorator-based tool registration, HTTP/SSE/Streamable-HTTP transports
- **Client Architecture**: Full client with SSE/HTTP transports, automatic reconnection
- **Features**: Authentication, middleware, resource management, tool management, OpenAPI integration
- **Transports**: stdio, HTTP, SSE, streamable-http with full MCP protocol compliance

### Our Protocol Package (server/src/protobox/protocol)
- **Basic Framework**: Core MCP message types, handler registry, transport abstractions
- **Missing**: Complete HTTP/SSE implementation, client compatibility, workspace isolation
- **Current Use**: Limited, mainly for basic MCP message handling
- **Integration**: Partially used in current routers but not production-ready

### Current Production Setup
- Uses FastMCP library for `/mcp/{workspace_id}/sse` endpoints
- WorkspaceMCPServer creates FastMCP instances per workspace
- Dynamic tool registration from database actions
- Authentication via MCP bearer tokens

## Gap Analysis

| Feature | FastMCP | Our Protocol | Status | Priority |
|---------|---------|--------------|--------|----------|
| **Server Framework** | Complete with decorators | Basic handler registry | ❌ Missing | High |
| **Transport Layer** | HTTP/SSE/streamable-http | Basic abstractions | ❌ Missing | High |
| **Workspace Isolation** | Not built-in | Not implemented | ❌ Critical | High |
| **Tool Management** | Dynamic registration | Static registration | ❌ Missing | High |
| **Client Compatibility** | FastMCP client compatible | Unknown compatibility | ❓ Unknown | High |
| **Authentication** | Built-in auth providers | Not implemented | ❌ Missing | Medium |

## Architecture Design

### Workspace Isolation Strategy

```mermaid
graph TD
    A[MCP Client] --> B[/mcp/{workspace_id}/sse]
    B --> C[WorkspaceAwareMCPServer]
    C --> D[WorkspaceToolRegistry]
    D --> E[Database Actions]
    
    F[MCP Client 2] --> G[/mcp/{workspace_id2}/sse]
    G --> H[WorkspaceAwareMCPServer 2]
    H --> I[WorkspaceToolRegistry 2]
    I --> J[Database Actions 2]
```

### Core Components

#### 1. WorkspaceAwareMCPServer
- Extends our protocol's MCPHandler
- Workspace-specific tool loading from database
- Complete isolation between workspaces
- Compatible with FastMCP clients

#### 2. WorkspaceToolRegistry
- Manages tools per workspace with caching
- Database-driven tool discovery
- Dynamic tool execution with workspace context
- Cache invalidation on tool changes

#### 3. Workspace Manager
- Server instance management per workspace
- Thread-safe server creation and caching
- Resource cleanup and lifecycle management

## Implementation Plan

### Phase 1: Test Foundation ⭐ **CURRENT**

**Objective**: Create comprehensive test suite before any code changes.

#### Test Files to Create:

1. **`server/tests/integration/test_protocol_compatibility.py`**
   - Test our protocol implementation against FastMCP client
   - Multiple workspace isolation tests
   - Tool discovery and execution tests
   - Authentication flow tests

2. **`server/tests/integration/test_workspace_isolation.py`**
   - Test workspace-specific tool isolation
   - Verify different tools per workspace
   - Test concurrent workspace operations
   - Data isolation verification with action creation

3. **`server/tests/integration/test_openai_mcp.py`**
   - Test OpenAI assistant with remote MCP
   - Test tool calling from OpenAI assistants
   - Verify assistant isolation per workspace

#### Key Test Scenarios:

```python
# Workspace Isolation Test
async def test_workspace_tool_isolation():
    # Create Workspace A with action1, action2
    workspace_a_id = await create_test_workspace()
    action1 = await create_test_action(workspace_a_id, "test_action_1", "REST")
    action2 = await create_test_action(workspace_a_id, "test_action_2", "REST")
    
    # Create Workspace B with action3, action4
    workspace_b_id = await create_test_workspace()
    action3 = await create_test_action(workspace_b_id, "test_action_3", "REST")
    action4 = await create_test_action(workspace_b_id, "test_action_4", "REST")
    
    # Verify clients only see their workspace tools
    client_a = FastMCPClient(SSETransport(f"http://localhost:8090/mcp/{workspace_a_id}/sse"))
    client_b = FastMCPClient(SSETransport(f"http://localhost:8090/mcp/{workspace_b_id}/sse"))
    
    async with client_a as ca, client_b as cb:
        tools_a = await ca.list_tools()
        tools_b = await cb.list_tools()
        
        tool_names_a = [t.name for t in tools_a]
        tool_names_b = [t.name for t in tools_b]
        
        # Verify isolation
        assert "test_action_1" in tool_names_a
        assert "test_action_2" in tool_names_a
        assert "test_action_3" not in tool_names_a
        assert "test_action_4" not in tool_names_a
        
        assert "test_action_3" in tool_names_b
        assert "test_action_4" in tool_names_b
        assert "test_action_1" not in tool_names_b
        assert "test_action_2" not in tool_names_b

# FastMCP Client Compatibility Test
async def test_fastmcp_client_connection():
    workspace_id = await create_test_workspace()
    await create_test_action(workspace_id, "search_kb", "REST", config={
        "url": "https://api.example.com/search",
        "method": "GET"
    })
    
    transport = SSETransport(
        url=f"http://localhost:8090/mcp/{workspace_id}/sse",
        headers={"Authorization": "Bearer test-mcp-client"}
    )
    
    async with FastMCPClient(transport) as client:
        # Test initialization
        await client.ping()
        
        # Test tool discovery
        tools = await client.list_tools()
        assert len(tools) > 0
        assert "search_kb" in [t.name for t in tools]
        
        # Test tool execution
        result = await client.call_tool("search_kb", {"query": "test"})
        assert result is not None

# OpenAI Assistant Integration Test
async def test_openai_assistant_with_mcp():
    workspace_id = await create_test_workspace()
    mcp_token = await generate_mcp_token(workspace_id)
    
    # Create action that assistant can use
    await create_test_action(workspace_id, "get_weather", "REST", config={
        "url": "https://api.weather.com/current",
        "method": "GET"
    })
    
    # Create assistant with MCP server
    assistant = await openai_client.beta.assistants.create(
        model="gpt-4",
        tools=[{
            "type": "mcp_server",
            "mcp_server": {
                "url": f"http://localhost:8090/mcp/{workspace_id}/sse",
                "headers": {"Authorization": f"Bearer {mcp_token}"}
            }
        }],
        instructions="Use available MCP tools to help users."
    )
    
    # Test tool usage through assistant
    thread = await openai_client.beta.threads.create()
    await openai_client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content="What's the weather like?"
    )
    
    run = await openai_client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )
    
    run = await wait_for_run_completion(run)
    assert run.status == "completed"
    
    # Verify MCP tool was called
    run_steps = await openai_client.beta.threads.runs.steps.list(
        thread_id=thread.id,
        run_id=run.id
    )
    
    mcp_calls = [
        step for step in run_steps.data
        if step.type == "tool_calls" and 
        any(call.type == "mcp_server" for call in step.step_details.tool_calls)
    ]
    
    assert len(mcp_calls) > 0
```

### Phase 2: Protocol Enhancement

**Objective**: Enhance our protocol package to be FastMCP-compatible with workspace isolation.

#### Implementation Components:

1. **Enhanced Server Framework** (`server/src/protobox/protocol/server.py`)
2. **Workspace Tool Registry** (`server/src/protobox/protocol/workspace_tools.py`)
3. **HTTP/SSE Transport Enhancement** (`server/src/protobox/protocol/transport.py`)
4. **Workspace Manager** (`server/src/protobox/protocol/workspace_manager.py`)

### Phase 3: Native Router Implementation

**Objective**: Create new router using our protocol that can replace FastMCP usage.

#### New Router: `server/src/protobox/admin/routers/mcp_native.py`

- Native MCP router using our protocol implementation
- FastMCP-compatible endpoints
- Workspace routing and authentication
- Drop-in replacement for FastMCP router

### Phase 4: OpenAI Integration

**Objective**: Enable OpenAI assistants to connect to our MCP servers.

#### Integration Points:
- Assistant configuration helpers
- MCP server URL generation
- Token management for assistants
- Third-party integration examples

### Phase 5: Production Migration

**Objective**: Replace FastMCP dependency with our native implementation.

#### Migration Strategy:
- Feature flag for gradual migration
- Performance monitoring and comparison
- Rollback procedures
- FastMCP dependency removal

## Success Criteria

1. **Functionality**: All existing MCP functionality works with native implementation
2. **Performance**: <10% performance degradation during migration
3. **Compatibility**: 100% FastMCP client compatibility maintained
4. **Isolation**: Complete workspace tool and data isolation
5. **Integration**: "FastMCP client", Claude and OpenAI assistants can successfully use MCP servers

## Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| FastMCP client incompatibility | High | Medium | Comprehensive compatibility tests |
| Performance degradation | Medium | Medium | Performance benchmarking & monitoring |
| Workspace isolation bugs | High | Low | Thorough isolation testing |
| Migration rollback needed | Medium | Low | Feature flags & rollback procedures |

## Testing Strategy

### Test Categories

1. **Unit Tests**: Individual component testing
2. **Integration Tests**: End-to-end workflow testing
3. **Compatibility Tests**: FastMCP client compatibility
4. **Performance Tests**: Baseline and comparison testing
5. **Security Tests**: Workspace isolation and authentication

### Test Environment Requirements

- Local development server running
- Test workspaces and actions
- FastMCP client library installed
- OpenAI API access for assistant tests
- Performance monitoring tools

## Next Steps

1. **✅ Analysis Complete**: Architecture and gap analysis finished
2. **🔄 Phase 1 Implementation**: Create comprehensive test suite
3. **⏳ Pending Review**: Wait for human approval before Phase 2
4. **⏳ Protocol Enhancement**: Implement workspace-aware components
5. **⏳ Native Router**: Create FastMCP replacement
6. **⏳ Production Migration**: Deploy and monitor

---

**Status**: Ready to begin Phase 1 - Test Foundation Implementation
**Next Action**: Create test files with isolated workspace and action creation