"""OpenAI API key integration."""

import logging
from typing import Any

from ..models.integration import IntegrationType
from .base_classes import ApiKeyIntegration, IntegrationHealth

logger = logging.getLogger(__name__)


class OpenAIIntegration(ApiKeyIntegration):
    """OpenAI API key integration implementation."""

    integration_type = IntegrationType.OPENAI
    display_name = "OpenAI"
    description = "Connect to OpenAI for GPT models and AI capabilities"
    category = "ai"
    
    # Capabilities
    capabilities = []
    
    # API key configuration
    api_key_name = "OPENAI_API_KEY"
    api_key_header = "Authorization"
    api_key_prefix = "Bearer"
    
    def get_settings_schema(self) -> dict[str, Any]:
        """Get OpenAI-specific settings schema."""
        return {
            "type": "object",
            "properties": {
                "model_preferences": {
                    "type": "object",
                    "title": "Model Preferences",
                    "properties": {
                        "default_model": {
                            "type": "string",
                            "title": "Default Model",
                            "description": "Default GPT model to use",
                            "enum": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
                            "default": "gpt-4"
                        },
                        "temperature": {
                            "type": "number",
                            "title": "Temperature",
                            "description": "Randomness in responses (0-2)",
                            "minimum": 0,
                            "maximum": 2,
                            "default": 0.7
                        },
                        "max_tokens": {
                            "type": "integer",
                            "title": "Max Tokens",
                            "description": "Maximum response length",
                            "minimum": 1,
                            "maximum": 4096,
                            "default": 1000
                        }
                    }
                },
                "usage_limits": {
                    "type": "object",
                    "title": "Usage Limits",
                    "properties": {
                        "max_requests_per_minute": {
                            "type": "integer",
                            "title": "Max Requests/Minute",
                            "description": "Rate limiting",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 20
                        },
                        "monthly_budget": {
                            "type": "number",
                            "title": "Monthly Budget ($)",
                            "description": "Maximum monthly spend",
                            "minimum": 0,
                            "default": 100
                        }
                    }
                },
                "organization_id": {
                    "type": "string",
                    "title": "Organization ID",
                    "description": "OpenAI organization ID (optional)"
                }
            }
        }

    async def test_connection(self, credentials: dict[str, Any]) -> IntegrationHealth:
        """Test OpenAI connection by calling models endpoint."""
        try:
            import httpx
            
            api_key = credentials.get("api_key")
            if not api_key:
                return IntegrationHealth(
                    is_healthy=False,
                    error_message="Missing API key"
                )
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    model_count = len(data.get("data", []))
                    return IntegrationHealth(
                        is_healthy=True,
                        details={
                            "model_count": model_count,
                            "models": [m["id"] for m in data.get("data", [])[:5]]  # First 5 models
                        }
                    )
                elif response.status_code == 401:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message="Invalid API key"
                    )
                else:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message=f"OpenAI API error: {response.status_code}"
                    )
                    
        except Exception as e:
            logger.error(f"Error testing OpenAI connection: {e}")
            return IntegrationHealth(
                is_healthy=False,
                error_message=f"Connection test failed: {str(e)}"
            )

    def get_capabilities(self) -> list[str]:
        """Get OpenAI integration capabilities."""
        return [
            "chat_completion",
            "text_completion",
            "embeddings",
            "image_generation",
            "image_edit",
            "audio_transcription",
            "audio_translation",
            "moderation",
            "fine_tuning"
        ]

    def get_action_templates(self) -> list[str]:
        """Get available action template IDs for OpenAI."""
        return [
            "openai_chat_completion",
            "openai_text_embedding",
            "openai_image_generation",
            "openai_audio_transcription"
        ]