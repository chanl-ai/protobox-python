"""Anthropic Claude API integration."""

from typing import Any

from loguru import logger

from ..models.integration import IntegrationType
from .base_classes import ApiKeyIntegration, IntegrationHealth, IntegrationCapability


class AnthropicIntegration(ApiKeyIntegration):
    """Anthropic Claude API integration for AI-powered automation."""

    integration_type = IntegrationType.ANTHROPIC
    display_name = "Anthropic Claude"
    description = "Integrate Claude AI for content generation, analysis, and intelligent automation"
    
    # Capabilities for AI assistance
    capabilities = [
        IntegrationCapability.ANALYZE_DATA,
        IntegrationCapability.SEND_MESSAGE,  # Generate content
        IntegrationCapability.UPDATE_TASK,    # Process and transform data
    ]
    
    # API key configuration
    api_key_name = "ANTHROPIC_API_KEY"
    api_key_header = "x-api-key"
    api_key_prefix = ""  # No prefix for Anthropic
    
    # No webhook support
    supports_webhooks = False

    async def test_connection(self, credentials: dict[str, Any]) -> IntegrationHealth:
        """Test Anthropic connection by making a simple API call."""
        try:
            import httpx
            
            api_key = credentials.get("api_key")
            if not api_key:
                return IntegrationHealth(
                    is_healthy=False,
                    error_message="Missing API key",
                    details={"error": "no_api_key"}
                )
            
            async with httpx.AsyncClient() as client:
                # Make a minimal request to validate the API key
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": "claude-3-haiku-20240307",
                        "max_tokens": 10,
                        "messages": [{"role": "user", "content": "Hi"}]
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return IntegrationHealth(
                        is_healthy=True,
                        error_message="Connected to Anthropic Claude API",
                        details={
                            "model_used": data.get("model"),
                            "usage": data.get("usage", {}),
                            "api_version": "2023-06-01"
                        }
                    )
                elif response.status_code == 401:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message="Invalid API key",
                        details={"error": "invalid_api_key", "status": 401}
                    )
                elif response.status_code == 429:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message="Rate limit exceeded",
                        details={"error": "rate_limit", "status": 429}
                    )
                else:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message=f"Anthropic API error: {response.status_code}",
                        details={"status": response.status_code, "error": response.text}
                    )
                    
        except Exception as e:
            logger.error(f"Error testing Anthropic connection: {e}")
            return IntegrationHealth(
                is_healthy=False,
                error_message=f"Connection test failed: {str(e)}",
                details={"error": str(e)}
            )

    def get_capabilities(self) -> list[str]:
        """Get Anthropic integration capabilities."""
        return [
            "generate_text",
            "analyze_content",
            "translate_text",
            "summarize_document",
            "answer_questions",
            "generate_code",
            "review_code",
            "extract_data",
            "classify_text"
        ]
    
    def get_settings_schema(self) -> dict[str, Any]:
        """Get settings schema for Anthropic integration."""
        return {
            "type": "object",
            "properties": {
                "default_model": {
                    "type": "string",
                    "title": "Default Model",
                    "description": "Default Claude model to use",
                    "enum": [
                        "claude-3-opus-20240229",
                        "claude-3-sonnet-20240229",
                        "claude-3-haiku-20240307",
                        "claude-2.1",
                        "claude-2.0"
                    ],
                    "default": "claude-3-sonnet-20240229"
                },
                "max_tokens": {
                    "type": "integer",
                    "title": "Max Tokens",
                    "description": "Default maximum tokens for responses",
                    "minimum": 1,
                    "maximum": 200000,
                    "default": 4096
                },
                "temperature": {
                    "type": "number",
                    "title": "Temperature",
                    "description": "Creativity level (0=deterministic, 1=creative)",
                    "minimum": 0,
                    "maximum": 1,
                    "default": 0.7
                },
                "system_prompt": {
                    "type": "string",
                    "title": "System Prompt",
                    "description": "Default system prompt for all requests",
                    "examples": ["You are a helpful AI assistant focused on business automation."]
                },
                "safety_settings": {
                    "type": "object",
                    "title": "Safety Settings",
                    "properties": {
                        "block_harmful": {
                            "type": "boolean",
                            "title": "Block Harmful Content",
                            "default": True
                        },
                        "block_pii": {
                            "type": "boolean",
                            "title": "Block Personal Information",
                            "default": False
                        }
                    }
                },
                "use_cases": {
                    "type": "array",
                    "title": "Enabled Use Cases",
                    "description": "Types of tasks to use Claude for",
                    "items": {
                        "type": "string",
                        "enum": [
                            "content_generation",
                            "data_analysis",
                            "code_generation",
                            "customer_support",
                            "translation",
                            "summarization"
                        ]
                    },
                    "default": ["content_generation", "data_analysis"]
                }
            },
            "required": []
        }
    
    def get_mcp_tools(self) -> list[dict[str, Any]]:
        """Get MCP tools for Anthropic integration."""
        return [
            {
                "name": "claude_generate_text",
                "description": "Generate text content using Claude",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "User prompt"},
                        "system": {"type": "string", "description": "System instructions"},
                        "model": {"type": "string", "enum": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]},
                        "max_tokens": {"type": "integer", "minimum": 1, "maximum": 200000},
                        "temperature": {"type": "number", "minimum": 0, "maximum": 1}
                    },
                    "required": ["prompt"]
                }
            },
            {
                "name": "claude_analyze_data",
                "description": "Analyze data or documents with Claude",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "data": {"type": "string", "description": "Data to analyze"},
                        "analysis_type": {
                            "type": "string",
                            "enum": ["summary", "insights", "patterns", "anomalies", "recommendations"]
                        },
                        "format": {"type": "string", "enum": ["text", "json", "markdown"]},
                        "model": {"type": "string"}
                    },
                    "required": ["data", "analysis_type"]
                }
            },
            {
                "name": "claude_translate",
                "description": "Translate text between languages",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to translate"},
                        "target_language": {"type": "string", "description": "Target language"},
                        "source_language": {"type": "string", "description": "Source language (auto-detect if omitted)"},
                        "tone": {"type": "string", "enum": ["formal", "casual", "technical", "creative"]}
                    },
                    "required": ["text", "target_language"]
                }
            },
            {
                "name": "claude_code_assist",
                "description": "Generate or review code with Claude",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string", "enum": ["generate", "review", "refactor", "debug", "test"]},
                        "code": {"type": "string", "description": "Existing code (for review/refactor/debug)"},
                        "requirements": {"type": "string", "description": "Requirements or issue description"},
                        "language": {"type": "string", "description": "Programming language"},
                        "framework": {"type": "string", "description": "Framework/library if applicable"}
                    },
                    "required": ["task", "requirements"]
                }
            },
            {
                "name": "claude_customer_support",
                "description": "Generate customer support responses",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "customer_message": {"type": "string", "description": "Customer's message"},
                        "context": {"type": "string", "description": "Additional context"},
                        "tone": {"type": "string", "enum": ["professional", "friendly", "empathetic", "concise"]},
                        "include_actions": {"type": "boolean", "description": "Include suggested actions"}
                    },
                    "required": ["customer_message"]
                }
            }
        ]