"""
Base MCP Tool Implementation

Provides the abstract base class and context management for MCP tools.
"""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field


class MCPContext(BaseModel):
    """Context information for tool execution"""

    session_id: str
    tool_name: str
    request_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)
    shared_data: dict[str, Any] = Field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from shared data"""
        return self.shared_data.get(key, default)

    def set(self, key: str, value: Any):
        """Set value in shared data"""
        self.shared_data[key] = value

    def update_metadata(self, **kwargs):
        """Update metadata"""
        self.metadata.update(kwargs)


class MCPResult(BaseModel):
    """Result of tool execution"""

    success: bool
    content: Any
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def success_result(cls, content: Any, **metadata) -> "MCPResult":
        """Create a successful result"""
        return cls(success=True, content=content, metadata=metadata)

    @classmethod
    def error_result(cls, error: str, **metadata) -> "MCPResult":
        """Create an error result"""
        return cls(success=False, content=None, error=error, metadata=metadata)


class MCPTool(ABC):
    """Abstract base class for MCP tools"""

    def __init__(
        self, name: str, description: str, input_schema: dict[str, Any], version: str = "1.0.0"
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.version = version

        # Validate input schema
        self._validate_schema()

    def _validate_schema(self):
        """Validate the input schema"""
        required_fields = ["type", "properties"]
        for field in required_fields:
            if field not in self.input_schema:
                raise ValueError(f"Input schema missing required field: {field}")

        if self.input_schema["type"] != "object":
            raise ValueError("Input schema type must be 'object'")

    @abstractmethod
    async def execute(self, arguments: dict[str, Any], context: MCPContext) -> Any:
        """
        Execute the tool with the given arguments and context.

        Args:
            arguments: Tool input arguments
            context: Execution context

        Returns:
            Tool execution result
        """
        pass

    def validate_arguments(self, arguments: dict[str, Any]) -> bool:
        """
        Validate tool arguments against the input schema.

        Args:
            arguments: Arguments to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            # Basic validation - check required properties
            properties = self.input_schema.get("properties", {})
            required = self.input_schema.get("required", [])

            # Check required fields
            for field in required:
                if field not in arguments:
                    return False

            # Check field types (basic validation)
            for field, value in arguments.items():
                if field in properties:
                    expected_type = properties[field].get("type")
                    if expected_type and not self._check_type(value, expected_type):
                        return False

            return True

        except Exception:
            return False

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type"""
        type_mapping = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None),
        }

        expected_python_type = type_mapping.get(expected_type)
        if expected_python_type is None:
            return True  # Unknown type, allow it

        return isinstance(value, expected_python_type)

    def get_info(self) -> dict[str, Any]:
        """Get tool information for MCP protocol"""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


class RestActionTool(MCPTool):
    """MCP tool for REST API actions"""

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        url: str,
        method: str = "POST",
        headers: dict[str, str] | None = None,
        timeout: int = 30,
        retries: int = 2,
    ):
        super().__init__(name, description, input_schema)
        self.url = url
        self.method = method.upper()
        self.headers = headers or {}
        self.timeout = timeout
        self.retries = retries

    async def execute(self, arguments: dict[str, Any], context: MCPContext) -> Any:
        """Execute REST API call"""
        import ssl

        import aiohttp
        from tenacity import retry, stop_after_attempt, wait_exponential

        # Validate arguments
        if not self.validate_arguments(arguments):
            raise ValueError("Invalid arguments provided")

        # Format URL with arguments
        formatted_url = self.url.format(**arguments)

        # Prepare request data
        request_data = arguments.copy()

        # Create SSL context for HTTPS requests
        ssl_context = ssl.create_default_context()

        # Try to load system certificates on macOS
        try:
            import certifi

            cert_path = certifi.where()
            ssl_context.load_verify_locations(cert_path)
            logger.debug(f"Loaded SSL certificates from: {cert_path}")
        except ImportError:
            # Fallback: try common certificate locations
            cert_paths = [
                "/etc/ssl/certs/ca-certificates.crt",  # Debian/Ubuntu
                "/etc/ssl/certs/ca-bundle.crt",  # CentOS/RHEL
                "/usr/local/etc/openssl/cert.pem",  # Homebrew
                "/opt/homebrew/etc/openssl/cert.pem",  # Homebrew on Apple Silicon
                "/System/Library/OpenSSL/certs/cert.pem",  # macOS system
            ]

            cert_loaded = False
            for cert_path in cert_paths:
                try:
                    ssl_context.load_verify_locations(cert_path)
                    cert_loaded = True
                    break
                except (FileNotFoundError, ssl.SSLError):
                    continue

            if not cert_loaded:
                # Last resort: disable SSL verification for this request
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                logger.warning("Could not load SSL certificates, disabling SSL verification")

        # Create connector with SSL context
        connector = aiohttp.TCPConnector(ssl=ssl_context)

        # Setup retry logic
        @retry(
            stop=stop_after_attempt(self.retries + 1),
            wait=wait_exponential(multiplier=1, min=1, max=10),
        )
        async def make_request():
            async with aiohttp.ClientSession(
                connector=connector, timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as session, session.request(
                method=self.method,
                url=formatted_url,
                json=request_data if self.method in ["POST", "PUT", "PATCH"] else None,
                params=request_data if self.method == "GET" else None,
                headers=self.headers,
            ) as response:
                response.raise_for_status()

                # Try to parse as JSON, fallback to text
                try:
                    return await response.json()
                except:
                    return await response.text()

        try:
            result = await make_request()
            context.set(
                "last_api_call",
                {
                    "url": formatted_url,
                    "method": self.method,
                    "status": "success",
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            )
            return result

        except Exception as e:
            error_msg = f"REST API call failed: {str(e)}"
            context.set(
                "last_api_call",
                {
                    "url": formatted_url,
                    "method": self.method,
                    "status": "error",
                    "error": error_msg,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            )
            # Don't re-raise, return error info instead
            return {
                "error": error_msg,
                "url": formatted_url,
                "method": self.method,
                "details": str(e),
            }


class EchoTool(MCPTool):
    """Simple echo tool for testing"""

    def __init__(self):
        super().__init__(
            name="echo",
            description="Echo back the input message",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Message to echo back"}
                },
                "required": ["message"],
            },
        )

    async def execute(self, arguments: dict[str, Any], context: MCPContext) -> Any:
        """Echo the message back"""
        message = arguments.get("message", "")
        context.set("echo_count", context.get("echo_count", 0) + 1)

        return f"Echo: {message} (call #{context.get('echo_count')})"


class SearchTool(MCPTool):
    """Search tool compatible with ChatGPT Deep Research"""

    def __init__(self):
        super().__init__(
            name="search",
            description="Search for information across various sources",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        )

    async def execute(self, arguments: dict[str, Any], context: MCPContext) -> Any:
        """Execute search - for Phase 1X, return mock data"""
        query = arguments.get("query", "")
        limit = arguments.get("limit", 10)

        logger.info(f"Executing search for: {query}")

        # Mock search results for Phase 1X
        results = []
        for i in range(min(limit, 3)):  # Return up to 3 mock results
            results.append(
                {
                    "id": f"result_{i+1}",
                    "title": f"Search Result {i+1} for '{query}'",
                    "text": f"This is mock content for search result {i+1} about {query}. In a real implementation, this would contain actual search results from various sources.",
                    "url": f"https://example.com/result_{i+1}",
                    "source": "Mock Search Engine",
                    "relevance_score": 0.95 - (i * 0.1),
                }
            )

        return {"query": query, "total_results": len(results), "results": results}


class FetchTool(MCPTool):
    """Fetch tool compatible with ChatGPT Deep Research"""

    def __init__(self):
        super().__init__(
            name="fetch",
            description="Fetch detailed content from a specific source",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch content from"},
                    "extract_type": {
                        "type": "string",
                        "enum": ["full", "summary", "metadata"],
                        "description": "Type of content extraction",
                        "default": "summary",
                    },
                },
                "required": ["url"],
            },
        )

    async def execute(self, arguments: dict[str, Any], context: MCPContext) -> Any:
        """Execute fetch - for Phase 1X, return mock data"""
        url = arguments.get("url", "")
        extract_type = arguments.get("extract_type", "summary")

        logger.info(f"Executing fetch for: {url} (type: {extract_type})")

        # Mock fetch result for Phase 1X
        if extract_type == "metadata":
            content = {
                "url": url,
                "title": "Mock Page Title",
                "description": "Mock page description",
                "author": "Mock Author",
                "published_date": "2025-01-02",
                "content_type": "article",
                "language": "en",
            }
        elif extract_type == "full":
            content = {
                "url": url,
                "title": "Mock Page Title",
                "full_content": f"This is the full mock content from {url}. In a real implementation, this would contain the complete extracted content from the web page, including all text, headings, and structured data.",
                "word_count": 150,
                "reading_time": "1 minute",
            }
        else:  # summary
            content = {
                "url": url,
                "title": "Mock Page Title",
                "summary": f"This is a mock summary of content from {url}. In a real implementation, this would contain a concise summary of the key points from the fetched content.",
                "key_points": ["Mock key point 1", "Mock key point 2", "Mock key point 3"],
            }

        return content


class CalculatorTool(MCPTool):
    """Calculator tool for mathematical operations"""

    def __init__(self):
        super().__init__(
            name="calculator",
            description="Perform mathematical calculations",
            input_schema={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate (e.g., '2 + 3 * 4')",
                    }
                },
                "required": ["expression"],
            },
        )

    async def execute(self, arguments: dict[str, Any], context: MCPContext) -> Any:
        """Execute calculation"""
        expression = arguments.get("expression", "")

        logger.info(f"Executing calculation: {expression}")

        try:
            # Safe evaluation for basic math operations
            import ast
            import operator

            # Define allowed operations
            ops = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.Pow: operator.pow,
                ast.USub: operator.neg,
            }

            def eval_expr(node):
                if isinstance(node, ast.Constant):
                    return node.value
                if isinstance(node, ast.BinOp):
                    return ops[type(node.op)](eval_expr(node.left), eval_expr(node.right))
                if isinstance(node, ast.UnaryOp):
                    return ops[type(node.op)](eval_expr(node.operand))
                raise TypeError(node)

            result = eval_expr(ast.parse(expression, mode="eval").body)

            return {
                "expression": expression,
                "result": result,
                "formatted": f"{expression} = {result}",
            }

        except Exception as e:
            logger.error(f"Calculation error: {e}")
            return {
                "expression": expression,
                "error": f"Calculation error: {str(e)}",
                "help": "Please use basic mathematical expressions with +, -, *, /, ** operators",
            }
