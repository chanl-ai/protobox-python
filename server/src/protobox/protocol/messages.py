"""
MCP Protocol Message Types

Defines the message schemas and types used in the Model Context Protocol
for communication between clients and servers, with official MCP library compatibility.
"""

from enum import Enum
from typing import Any, Literal, Union

from pydantic import BaseModel, Field
import mcp.types


class MCPMessageType(str, Enum):
    """MCP message types"""

    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"


class MCPMethod(str, Enum):
    """MCP protocol methods"""

    # Initialization
    INITIALIZE = "initialize"
    INITIALIZED = "initialized"

    # Tools
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"

    # Resources
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    RESOURCES_SUBSCRIBE = "resources/subscribe"
    RESOURCES_UNSUBSCRIBE = "resources/unsubscribe"

    # Prompts
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"

    # Sampling
    SAMPLING_CREATE_MESSAGE = "sampling/createMessage"

    # Notifications
    NOTIFICATIONS_CANCELLED = "notifications/cancelled"
    NOTIFICATIONS_PROGRESS = "notifications/progress"
    NOTIFICATIONS_MESSAGE = "notifications/message"
    NOTIFICATIONS_RESOURCES_UPDATED = "notifications/resources/updated"


class MCPMessage(BaseModel):
    """Base MCP message with official MCP compatibility"""

    jsonrpc: Literal["2.0"] = "2.0"
    
    def to_official_type(self):
        """Convert to official MCP type"""
        # Override in subclasses
        raise NotImplementedError("Subclasses must implement to_official_type")
    
    @classmethod
    def from_official_type(cls, official_message):
        """Convert from official MCP type"""
        # Override in subclasses
        raise NotImplementedError("Subclasses must implement from_official_type")


class MCPRequest(MCPMessage):
    """MCP request message with official MCP compatibility"""

    id: str | int
    method: str
    params: dict[str, Any] | None = None
    
    def to_official_type(self):
        """Convert to official MCP request type"""
        # Create appropriate official MCP request based on method
        if self.method == "initialize":
            return mcp.types.InitializeRequest(
                id=self.id,
                method=self.method,
                params=mcp.types.InitializeRequestParams(
                    protocolVersion=self.params.get("protocolVersion", "2024-11-05") if self.params else "2024-11-05",
                    capabilities=mcp.types.ClientCapabilities(
                        **self.params.get("capabilities", {}) if self.params else {}
                    ),
                    clientInfo=mcp.types.Implementation(
                        **self.params.get("clientInfo", {"name": "unknown", "version": "1.0.0"}) if self.params else {"name": "unknown", "version": "1.0.0"}
                    )
                )
            )
        elif self.method == "tools/list":
            return mcp.types.ListToolsRequest(
                id=self.id,
                method=self.method,
                params=mcp.types.ListToolsRequestParams()
            )
        elif self.method == "tools/call":
            return mcp.types.CallToolRequest(
                id=self.id,
                method=self.method,
                params=mcp.types.CallToolRequestParams(
                    name=self.params.get("name") if self.params else "",
                    arguments=self.params.get("arguments", {}) if self.params else {}
                )
            )
        else:
            # Generic request for unknown methods
            return mcp.types.Request(
                id=self.id,
                method=self.method,
                params=self.params
            )
    
    @classmethod
    def from_official_type(cls, official_request):
        """Convert from official MCP request type"""
        params = None
        if hasattr(official_request, 'params') and official_request.params:
            params = official_request.params.model_dump() if hasattr(official_request.params, 'model_dump') else official_request.params
        
        return cls(
            id=official_request.id,
            method=official_request.method,
            params=params
        )


class MCPResponse(MCPMessage):
    """MCP response message with official MCP compatibility"""

    id: str | int
    result: Any | None = None
    error: dict[str, Any] | None = None
    
    def to_official_type(self):
        """Convert to official MCP response type"""
        if self.error:
            return mcp.types.ErrorResponse(
                id=self.id,
                error=mcp.types.Error(
                    code=self.error.get("code", -32603),
                    message=self.error.get("message", "Internal error"),
                    data=self.error.get("data")
                )
            )
        else:
            return mcp.types.Response(
                id=self.id,
                result=self.result
            )
    
    @classmethod
    def from_official_type(cls, official_response):
        """Convert from official MCP response type"""
        error = None
        if hasattr(official_response, 'error') and official_response.error:
            error = {
                "code": official_response.error.code,
                "message": official_response.error.message,
                "data": getattr(official_response.error, 'data', None)
            }
        
        return cls(
            id=official_response.id,
            result=getattr(official_response, 'result', None),
            error=error
        )


class MCPNotification(MCPMessage):
    """MCP notification message with official MCP compatibility"""

    method: str
    params: dict[str, Any] | None = None
    
    def to_official_type(self):
        """Convert to official MCP notification type"""
        if self.method == "initialized":
            return mcp.types.InitializedNotification(
                method=self.method,
                params=mcp.types.InitializedNotificationParams() if not self.params else mcp.types.InitializedNotificationParams(**self.params)
            )
        elif self.method == "notifications/cancelled":
            return mcp.types.CancelledNotification(
                method=self.method,
                params=mcp.types.CancelledNotificationParams(
                    requestId=self.params.get("requestId") if self.params else ""
                )
            )
        else:
            # Generic notification
            return mcp.types.Notification(
                method=self.method,
                params=self.params
            )
    
    @classmethod
    def from_official_type(cls, official_notification):
        """Convert from official MCP notification type"""
        params = None
        if hasattr(official_notification, 'params') and official_notification.params:
            params = official_notification.params.model_dump() if hasattr(official_notification.params, 'model_dump') else official_notification.params
        
        return cls(
            method=official_notification.method,
            params=params
        )


# Tool-related messages
class ToolInfo(BaseModel):
    """Tool information"""

    name: str
    description: str
    inputSchema: dict[str, Any]


class ToolCallRequest(MCPRequest):
    """Tool call request"""

    method: Literal[MCPMethod.TOOLS_CALL] = MCPMethod.TOOLS_CALL
    params: dict[str, Any] = Field(..., description="Tool call parameters")

    class Params(BaseModel):
        name: str
        arguments: dict[str, Any]


class ToolCallResponse(MCPResponse):
    """Tool call response"""

    class Result(BaseModel):
        content: list[dict[str, Any]]
        isError: bool | None = False

    result: Result | None = None


class ToolsListRequest(MCPRequest):
    """Tools list request"""

    method: Literal[MCPMethod.TOOLS_LIST] = MCPMethod.TOOLS_LIST


class ToolsListResponse(MCPResponse):
    """Tools list response"""

    class Result(BaseModel):
        tools: list[ToolInfo]

    result: Result | None = None


# Resource-related messages
class ResourceInfo(BaseModel):
    """Resource information"""

    uri: str
    name: str
    description: str | None = None
    mimeType: str | None = None


class ResourceContent(BaseModel):
    """Resource content"""

    uri: str
    mimeType: str
    text: str | None = None
    blob: str | None = None  # base64 encoded


class ResourceRequest(MCPRequest):
    """Resource read request"""

    method: Literal[MCPMethod.RESOURCES_READ] = MCPMethod.RESOURCES_READ

    class Params(BaseModel):
        uri: str

    params: Params


class ResourceResponse(MCPResponse):
    """Resource read response"""

    class Result(BaseModel):
        contents: list[ResourceContent]

    result: Result | None = None


class ResourcesListRequest(MCPRequest):
    """Resources list request"""

    method: Literal[MCPMethod.RESOURCES_LIST] = MCPMethod.RESOURCES_LIST


class ResourcesListResponse(MCPResponse):
    """Resources list response"""

    class Result(BaseModel):
        resources: list[ResourceInfo]

    result: Result | None = None


# Prompt-related messages
class PromptInfo(BaseModel):
    """Prompt information"""

    name: str
    description: str
    arguments: list[dict[str, Any]] | None = None


class PromptsListRequest(MCPRequest):
    """Prompts list request"""

    method: Literal[MCPMethod.PROMPTS_LIST] = MCPMethod.PROMPTS_LIST


class PromptsListResponse(MCPResponse):
    """Prompts list response"""

    class Result(BaseModel):
        prompts: list[PromptInfo]

    result: Result | None = None


# Progress notifications
class ProgressNotification(MCPNotification):
    """Progress notification"""

    method: Literal[MCPMethod.NOTIFICATIONS_PROGRESS] = MCPMethod.NOTIFICATIONS_PROGRESS

    class Params(BaseModel):
        progressToken: str | int
        progress: float  # 0.0 to 1.0
        total: float | None = None

    params: Params


# Error types
class MCPError(BaseModel):
    """MCP error"""

    code: int
    message: str
    data: Any | None = None


class MCPErrorCode(int, Enum):
    """MCP error codes"""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # MCP-specific errors
    TOOL_NOT_FOUND = -32000
    RESOURCE_NOT_FOUND = -32001
    PERMISSION_DENIED = -32002
    TIMEOUT = -32003


class MCPException(Exception):
    """MCP exception class that can be raised and caught"""
    
    def __init__(self, code: int, message: str, data: Any | None = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)
    
    def to_error_dict(self) -> dict:
        """Convert to MCP error dictionary format"""
        error_dict = {"code": self.code, "message": self.message}
        if self.data is not None:
            error_dict["data"] = self.data
        return error_dict


# Message union type for parsing
MCPMessageUnion = Union[MCPRequest, MCPResponse, MCPNotification]


# Utility functions for MCP message conversion
def convert_to_official_mcp(message: MCPMessage):
    """Convert our message to official MCP type"""
    return message.to_official_type()


def convert_from_official_mcp(official_message) -> MCPMessage:
    """Convert official MCP message to our format"""
    if hasattr(official_message, 'id'):
        if hasattr(official_message, 'method'):
            # It's a request
            return MCPRequest.from_official_type(official_message)
        else:
            # It's a response
            return MCPResponse.from_official_type(official_message)
    elif hasattr(official_message, 'method'):
        # It's a notification
        return MCPNotification.from_official_type(official_message)
    else:
        raise ValueError(f"Unknown official MCP message type: {type(official_message)}")


def create_error_response(request_id: str | int, code: int, message: str, data: Any = None) -> MCPResponse:
    """Create an error response using our message format"""
    return MCPResponse(
        id=request_id,
        error={
            "code": code,
            "message": message,
            "data": data
        }
    )


def create_success_response(request_id: str | int, result: Any) -> MCPResponse:
    """Create a success response using our message format"""
    return MCPResponse(
        id=request_id,
        result=result
    )
