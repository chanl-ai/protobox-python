"""REST action executor for HTTP requests."""

import json
import re
import os
import time
import base64
from abc import ABC, abstractmethod
from datetime import datetime, UTC
from typing import Any, Iterable

import aiohttp
from loguru import logger
from liquid import Template

from ..models.action import ActionModel, ActionType
from ..models.execution import ExecutionModel, ExecutionStatus
from ..models.integration import OAuth2TokenData, IntegrationType
from ..models.secret import SecretUpdateRequest
from ..auth.oauth2_handler import OAuth2Handler
from .base import BaseActionExecutor


class BodyPreprocessor(ABC):
    """
    Base class for all body preprocessors.
    Body preprocessors are used to preprocess the request body before sending it to the server.
    """
    
    @abstractmethod
    def process(self, value: Any, options: dict[str, Any] = None) -> Any:
        """Process a value according to the preprocessor logic."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this preprocessor."""
        pass


class Base64BodyPreprocessor(BodyPreprocessor):
    """Base64 encode string values."""
    
    @property
    def name(self) -> str:
        return "base64"
    
    def process(self, value: Any, options: dict[str, Any] = None) -> Any:
        if not isinstance(value, str):
            raise ValueError(f"Base64 body preprocessor requires string value, got {type(value)}")
        
        encoding = options.get("encoding", "utf-8") if options else "utf-8"
        return base64.b64encode(value.encode(encoding)).decode("utf-8")


class UrlEncodeBodyPreprocessor(BodyPreprocessor):
    """URL encode string values."""
    
    @property
    def name(self) -> str:
        return "url_encode"
    
    def process(self, value: Any, options: dict[str, Any] = None) -> Any:
        if not isinstance(value, str):
            raise ValueError(f"URL encode body preprocessor requires string value, got {type(value)}")
        
        from urllib.parse import quote
        return quote(value, safe=options.get("safe", "") if options else "")


class JsonStringifyBodyPreprocessor(BodyPreprocessor):
    """Convert values to JSON strings."""
    
    @property
    def name(self) -> str:
        return "json_stringify"
    
    def process(self, value: Any, options: dict[str, Any] = None) -> Any:
        return json.dumps(value, ensure_ascii=options.get("ensure_ascii", False) if options else False)


class HtmlEscapeBodyPreprocessor(BodyPreprocessor):
    """Escape HTML special characters."""
    
    @property
    def name(self) -> str:
        return "html_escape"
    
    def process(self, value: Any, options: dict[str, Any] = None) -> Any:
        if not isinstance(value, str):
            raise ValueError(f"HTML escape body preprocessor requires string value, got {type(value)}")
        
        import html
        return html.escape(value)


class PreprocessorRegistry:
    """Registry for all available preprocessors."""
    
    def __init__(self):
        self._preprocessors: dict[str, BodyPreprocessor] = {}
        self._register_defaults()
    
    def _register_defaults(self):
        """Register the default preprocessors."""
        self.register(Base64BodyPreprocessor())
        self.register(UrlEncodeBodyPreprocessor())
        self.register(JsonStringifyBodyPreprocessor())
        self.register(HtmlEscapeBodyPreprocessor())
    
    def register(self, preprocessor: BodyPreprocessor):
        """Register a new preprocessor."""
        self._preprocessors[preprocessor.name] = preprocessor
    
    def get(self, name: str) -> BodyPreprocessor:
        """Get a preprocessor by name."""
        if name not in self._preprocessors:
            raise ValueError(f"Unknown preprocessor: {name}")
        return self._preprocessors[name]
    
    def list_available(self) -> list[str]:
        """List all available preprocessor names."""
        return list(self._preprocessors.keys())


_preprocessor_registry = PreprocessorRegistry()


class RestActionExecutor(BaseActionExecutor):
    """Executor for REST/HTTP actions."""

    def get_supported_action_types(self) -> list[str]:
        """Get the list of action types supported by this executor."""
        return [ActionType.REST.value]

    def get_configuration_schema(self) -> dict[str, Any]:
        """Get the JSON schema for REST action configuration."""
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "format": "uri", "description": "The HTTP endpoint URL"},
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
                    "description": "HTTP method",
                },
                "headers": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                    "description": "HTTP headers to send",
                },
                "timeout": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 300,
                    "default": 30,
                    "description": "Request timeout in seconds",
                },
                "verify_ssl": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to verify SSL certificates",
                },
                "follow_redirects": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to follow HTTP redirects",
                },
                "body": {"type": "string", "description": "Request body (for POST/PUT requests)"},
                "preprocessors": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["base64", "url_encode", "json_stringify", "html_escape"],
                                "description": "Type of preprocessing to apply"
                            },
                            "fields": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of field paths to apply preprocessing to (e.g., 'message.raw')"
                            },
                            "options": {
                                "type": "object",
                                "description": "Additional options for the preprocessor"
                            }
                        },
                        "required": ["type", "fields"]
                    },
                    "description": "List of preprocessing operations to apply to request data",
                    "default": []
                },
                "auth": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["bearer", "basic"]},
                        "secret": {
                            "type": "string",
                            "description": "Name of secret containing credentials",
                        },
                    },
                    "description": "Authentication configuration",
                },
            },
            "required": ["url", "method"],
        }

    async def execute(
        self, action: ActionModel, execution: ExecutionModel
    ) -> tuple[dict[str, Any], str | None]:
        """Execute a REST action.

        Args:
            action: The action to execute
            execution: The execution context

        Returns:
            Tuple of (output_data, error_message)
        """
        start_time = time.time()

        try:
            # Prepare the HTTP request
            logger.info(f"Preparing HTTP request for action: {action.name}")
            if isinstance(action.default_config["headers"], list):
                action.default_config["headers"] = {h["key"]: h["value"] for h in action.default_config["headers"]}
            request_config = await self._prepare_request(action, execution)

            # Execute the HTTP request
            logger.info(f"Executing HTTP request for action: {action.name}")
            async with aiohttp.ClientSession() as session:
                response_data = await self._make_request(session, request_config)

            execution_time_ms = int((time.time() - start_time) * 1000)

            # Prepare output data
            output_data = {
                "status_code": response_data["status_code"],
                "headers": response_data["headers"],
                "body": response_data["body"],
                "execution_time_ms": execution_time_ms,
                "request_config": {
                    "url": request_config["url"],
                    "method": request_config["method"],
                    "headers": {
                        k: "***" if self._is_sensitive_header(k) else v
                        for k, v in request_config.get("headers", {}).items()
                    },
                },
            }

            return output_data, None

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)

            # Prepare error output
            output_data = {
                "error": str(e),
                "error_type": type(e).__name__,
                "execution_time_ms": execution_time_ms,
            }

            logger.info(f"Returning error output for action: {action.name}")
            return output_data, str(e)

    async def _prepare_request(
        self, action: ActionModel, execution: ExecutionModel
    ) -> dict[str, Any]:
        """Prepare the HTTP request configuration.

        Args:
            action: The action model
            execution: The execution model

        Returns:
            Request configuration dictionary
        """
        logger.debug(
            f"Preparing HTTP request for action: {action.name} with input data: {json.dumps(execution.input_data, indent=2, ensure_ascii=False)}"
        )
        config = action.default_config.copy()
        input_data = execution.input_data

        # Base configuration
        request_config = {
            "url": config["url"],
            "method": config["method"].upper(),
            "headers": config.get("headers", {}).copy(),
            "timeout": config.get("timeout", 30),
            "allow_redirects": config.get("follow_redirects", True),
            "verify_ssl": config.get("verify_ssl", True),
        }

        # Handle request body with templating
        if "body" in config and config["body"]:
            request_config["data"] = self._inject_input_variables(config["body"], input_data)
        elif "body" in input_data and input_data["body"]:
            request_config["data"] = input_data["body"]

        # Handle JSON body from input data
        if "json" in input_data:
            logger.debug(f"Using json from input data: {input_data['json']}")
            request_config["json"] = input_data["json"]
            if "Content-Type" not in request_config["headers"]:
                request_config["headers"]["Content-Type"] = "application/json"
        # If using data with application/json content-type, convert to json
        elif "data" in request_config and request_config.get("headers", {}).get("Content-Type") == "application/json":
            logger.debug(f"Trying to convert data to json: {request_config['data']}")
            try:
                # Try to parse data as JSON and convert to json parameter
                if isinstance(request_config["data"], str):
                    json_data = json.loads(request_config["data"])
                else:
                    json_data = request_config["data"]
                request_config["json"] = json_data
                logger.debug(f"Converted data to json: {request_config['json']}")
                del request_config["data"]  # Remove data since we're using json now
            except (json.JSONDecodeError, TypeError):
                # If data can't be parsed as JSON, remove the application/json header
                if "Content-Type" in request_config["headers"]:
                    del request_config["headers"]["Content-Type"]

        # Apply body preprocessors to specified fields
        if "body_preprocessors" in config and config["body_preprocessors"]:
            await self._apply_preprocessors(request_config, config["body_preprocessors"])

        # Process URL parameters
        if "params" in input_data:
            request_config["params"] = input_data["params"]

        # Merge additional headers from input
        if "headers" in input_data:
            request_config["headers"].update(input_data["headers"])

        # Process secret references in headers and authentication
        logger.info(f"Processing secrets for action: {action.name}")
        await self._process_secrets(request_config, execution.workspace_id, execution.user_id)

        # Handle URL templating
        logger.info(f"Templating URL for action: {action.name}")
        request_config["url"] = self._inject_input_variables(request_config["url"], input_data)

        return request_config

    async def _make_request(
        self, session: aiohttp.ClientSession, config: dict[str, Any]
    ) -> dict[str, Any]:
        """Make the HTTP request.

        Args:
            session: The aiohttp session
            config: Request configuration

        Returns:
            Response data dictionary
        """
        # Headers and body can hold decrypted secrets, so only the method and URL are logged.
        logger.debug(f"Making HTTP request via worker: {config['method']} {config['url']}")

        worker_url = os.getenv("REST_EXECUTOR_WORKER_URL")
        if not worker_url:
            raise ValueError("REST_EXECUTOR_WORKER_URL is not set")
        # The worker makes outbound calls on the platform's behalf; without a shared token
        # anyone who can reach it can use it as an open proxy.
        worker_token = os.getenv("REST_EXECUTOR_WORKER_TOKEN")
        if not worker_token:
            raise ValueError("REST_EXECUTOR_WORKER_TOKEN is not set")

        # Prepare the request payload for the worker
        worker_payload = {
            "target_url": config["url"],
            "method": config["method"],
            "headers": config["headers"],
            "timeout": config["timeout"],
            "allow_redirects": config["allow_redirects"],
            "verify_ssl": config["verify_ssl"],
        }

        # Add body/data to worker payload
        if "json" in config:
            worker_payload["json"] = config["json"]
        elif "data" in config:
            worker_payload["data"] = config["data"]

        # Add query parameters
        if "params" in config:
            worker_payload["params"] = config["params"]

        # Make the request to the worker
        worker_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {worker_token}",
        }
        
        async with session.post(
            worker_url,
            json=worker_payload,
            headers=worker_headers,
            timeout=aiohttp.ClientTimeout(total=config["timeout"] + 10)  # Add buffer for worker processing
        ) as response:
            # Read response body from worker
            try:
                if response.content_type == "application/json":
                    worker_response = await response.json()
                else:
                    worker_response_text = await response.text()
                    try:
                        worker_response = json.loads(worker_response_text)
                    except json.JSONDecodeError:
                        worker_response = {"error": f"Worker returned non-JSON response: {worker_response_text}"}
            except Exception as e:
                logger.error(f"Error parsing worker response: {e}")
                worker_response = {"error": f"Failed to parse worker response: {str(e)}"}

            # Check if worker request was successful
            if response.status != 200:
                return {
                    "status_code": response.status,
                    "headers": dict(response.headers),
                    "body": worker_response,
                    "url": config["url"],
                    "reason": f"Worker error: {response.reason}",
                    "worker_error": True,
                }

            # Return the worker's response (which should contain the actual API response)
            return worker_response

    async def _process_secrets(
        self, config: dict[str, Any], workspace_id: str, user_id: str
    ) -> None:
        """Process secret references in the configuration.

        Args:
            config: Request configuration to modify
            workspace_id: The workspace ID
            user_id: The user ID
        """
        # Process headers for secret references
        headers = config.get("headers", {})
        for key, value in headers.items():
            logger.debug(f"Processing header: '{key}'")
            if isinstance(value, str):
                # Find all secret references in the value using regex
                secret_pattern = r'\$\{secret:([^}]+)\}'
                matches = re.findall(secret_pattern, value)
                
                if matches:
                    logger.debug(f"Found {len(matches)} secret reference(s) in header '{key}'")
                    processed_value = value
                    
                    for secret_reference in matches:
                        logger.debug(f"Resolving secret reference: {secret_reference}")
                        
                        # Parse secret name and optional field path
                        # Format: secret_name or secret_name.field_path
                        if '.' in secret_reference:
                            secret_name, field_path = secret_reference.split('.', 1)
                        else:
                            secret_name = secret_reference
                            field_path = None
                        
                        
                        secret = await self.secret_service.get_secret_by_name(workspace_id, secret_name)
                        if secret:
                            decrypted_value = await self.secret_service.decrypt_secret_value(
                                secret.id, user_id
                            )
                            if decrypted_value:
                                # Check if this is an OAuth token that might need refreshing
                                refreshed_value = await self._refresh_oauth_token_if_needed(
                                    secret, decrypted_value, workspace_id, user_id
                                )
                                
                                # Extract field value if field path is specified
                                final_value = refreshed_value
                                if field_path:
                                    try:
                                        # Parse as JSON and extract field
                                        secret_data = json.loads(refreshed_value)
                                        final_value = secret_data.get(field_path)
                                        if final_value is None:
                                            logger.error(f"Field '{field_path}' not found in secret '{secret_name}'")
                                            continue
                                        logger.debug(f"Extracted field '{field_path}' from secret '{secret_name}'")
                                    except json.JSONDecodeError:
                                        logger.error(f"Secret '{secret_name}' is not valid JSON, cannot extract field '{field_path}'")
                                        continue
                                
                                # Replace the specific secret placeholder with the final value
                                secret_placeholder = f"${{secret:{secret_reference}}}"
                                processed_value = processed_value.replace(secret_placeholder, final_value)
                            else:
                                logger.error(f"Failed to decrypt secret: {secret_name}")
                        else:
                            logger.error(f"Secret not found: {secret_name}")
                    
                    headers[key] = processed_value

        # Process authentication
        if "auth" in config:
            auth_config = config["auth"]
            if auth_config.get("type") == "bearer" and "secret" in auth_config:
                secret_name = auth_config["secret"]
                secret = await self.secret_service.get_secret_by_name(workspace_id, secret_name)
                if secret:
                    token = await self.secret_service.decrypt_secret_value(secret.id, user_id)
                    if token:
                        headers["Authorization"] = f"Bearer {token}"
            elif auth_config.get("type") == "basic" and "secret" in auth_config:
                secret_name = auth_config["secret"]
                secret = await self.secret_service.get_secret_by_name(workspace_id, secret_name)
                if secret:
                    credentials = await self.secret_service.decrypt_secret_value(secret.id, user_id)
                    if credentials:
                        # Assuming credentials are in format "username:password"
                        import base64

                        encoded_credentials = base64.b64encode(credentials.encode()).decode()
                        headers["Authorization"] = f"Basic {encoded_credentials}"

    def _inject_input_variables(self, target: Any, input_data: dict[str, Any]):
        """Apply templating to target with input data.

        Args:
            target: The target to inject input variables into
            input_data: Input data for templating

        Returns:
            Templated target
        """
        # Simple templating - replace {{key}} with values from input_data
        if isinstance(target, str):
            try:
                templated_target = Template(target).render(**input_data)
            except Exception as e:
                logger.error(f"Error templating target: {e}")
                raise e
        elif isinstance(target, dict):
            templated_target = {
                self._inject_input_variables(key, input_data): self._inject_input_variables(value, input_data)
                for key, value in target.items()
            }
        elif isinstance(target, Iterable):
            templated_target = [
                self._inject_input_variables(value, input_data)
                for value in target
            ]
        else:
            templated_target = target

        return templated_target

    async def _apply_preprocessors(
        self, request_config: dict[str, Any], preprocessors: list[dict[str, Any]]
    ) -> None:
        """Apply preprocessing operations to specified fields in the request.
        
        Args:
            request_config: The request configuration to modify
            preprocessors: List of preprocessor configurations
        """
        for preprocessor_config in preprocessors:
            try:
                preprocessor_type = preprocessor_config["type"]
                fields = preprocessor_config["fields"]
                options = preprocessor_config.get("options", {})
                
                preprocessor = _preprocessor_registry.get(preprocessor_type)
                
                # Apply to each specified field
                for field_path in fields:
                    if "json" in request_config:
                        self._apply_preprocessor_to_field(
                            request_config["json"], field_path, preprocessor, options
                        )
                    elif "data" in request_config and isinstance(request_config["data"], dict):
                        self._apply_preprocessor_to_field(
                            request_config["data"], field_path, preprocessor, options
                        )
                        
            except Exception as e:
                logger.warning(f"Failed to apply preprocessor {preprocessor_config}: {e}")

    def _apply_preprocessor_to_field(
        self, data: dict[str, Any], field_path: str, preprocessor: BodyPreprocessor, options: dict[str, Any]
    ) -> None:
        """Apply a preprocessor to a specific field in a nested dictionary.
        
        Args:
            data: The dictionary to modify
            field_path: Dot-separated path to the field (e.g., 'message.raw')
            preprocessor: The preprocessor to apply
            options: Preprocessor-specific options
        """
        parts = field_path.split('.')
        current = data
        
        # Navigate to the parent of the target field
        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                logger.warning(f"Field path '{field_path}' is invalid - '{part}' is not a dict")
                return
            current = current[part]
        
        # Apply the preprocessor to the target field
        target_field = parts[-1]
        if target_field in current:
            try:
                processed_value = preprocessor.process(current[target_field], options)
                current[target_field] = processed_value
                logger.debug(f"Applied {preprocessor.name} preprocessor to field '{field_path}'")
            except Exception as e:
                logger.error(f"Failed to apply {preprocessor.name} preprocessor to field '{field_path}': {e}")
        else:
            logger.warning(f"Field '{target_field}' not found in path '{field_path}'")

    def _is_sensitive_header(self, header_name: str) -> bool:
        """Check if header contains sensitive information.

        Args:
            header_name: The header name

        Returns:
            True if header is sensitive
        """
        sensitive_headers = [
            "authorization",
            "x-api-key",
            "x-auth-token",
            "cookie",
            "x-access-token",
            "bearer",
        ]
        return header_name.lower() in sensitive_headers

    async def validate_action(self, action: ActionModel) -> tuple[bool, str | None]:
        """Validate a REST action configuration.

        Args:
            action: The action to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            config = action.default_config

            # Check required fields
            if "url" not in config:
                return False, "Missing required field: url"
            if "method" not in config:
                return False, "Missing required field: method"

            # Validate URL
            url = config["url"]
            if not url.startswith(("http://", "https://")):
                return False, "URL must start with http:// or https://"

            # Validate method
            valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
            if config["method"].upper() not in valid_methods:
                return False, f"Invalid HTTP method. Must be one of: {', '.join(valid_methods)}"

            return True, None

        except Exception as e:
            return False, f"Validation error: {str(e)}"

    async def test_action(self, action: ActionModel, test_input: dict[str, Any]) -> dict[str, Any]:
        """Test a REST action with sample input.

        Args:
            action: The action to test
            test_input: Test input data

        Returns:
            Test result dictionary
        """
        # Create a mock execution for testing

        mock_execution = ExecutionModel(
            action_id=str(action.id) if action.id else "test",
            workspace_id=action.workspace_id,
            user_id=action.created_by,
            input_data=test_input,
            status=ExecutionStatus.PENDING,
        )

        # Execute the action
        output_data, error_message = await self.execute(action, mock_execution)

        return {
            "success": error_message is None,
            "output_data": output_data,
            "error_message": error_message,
            "test_input": test_input,
        }

    async def _refresh_oauth_token_if_needed(
        self, secret, decrypted_value: str, workspace_id: str, user_id: str
    ) -> str:
        """Check if OAuth token is expired and refresh if needed.
        
        Args:
            secret: The secret model
            decrypted_value: The decrypted secret value
            workspace_id: The workspace ID
            user_id: The user ID
            
        Returns:
            The original or refreshed secret value
        """
        try:
            # Check if this looks like an OAuth token (has access_token and expires_at)
            oauth_data = json.loads(decrypted_value)
            if not isinstance(oauth_data, dict) or 'access_token' not in oauth_data:
                return decrypted_value
                
            # Parse as OAuth2TokenData to validate structure
            token_data = OAuth2TokenData.model_validate(oauth_data)
            
            # Check if token is expired (with 5 minute buffer)
            if token_data.expires_at:
                now = datetime.now(UTC)
                expires_at = token_data.expires_at
                if isinstance(expires_at, str):
                    # Parse ISO string to datetime
                    expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                
                # Add 5 minute buffer to avoid using tokens that expire soon
                buffer_time = 5 * 60  # 5 minutes
                if (expires_at - now).total_seconds() > buffer_time:
                    logger.info(f"OAuth token for secret {secret.name} is still valid")
                    return decrypted_value
                    
                logger.warning(f"OAuth token for secret {secret.name} is expired or expiring soon, attempting refresh")
                
                # Attempt to refresh the token
                if not token_data.refresh_token:
                    logger.error(f"OAuth token for secret {secret.name} is expired but no refresh token available")
                    return decrypted_value
                
                # Determine integration type from secret name
                integration_type = self._get_integration_type_from_secret_name(secret.name)
                if not integration_type:
                    logger.error(f"Could not determine integration type from secret name: {secret.name}")
                    return decrypted_value
                
                # Initialize OAuth handler and refresh token
                oauth_handler = OAuth2Handler()
                refreshed_token_data = await oauth_handler.refresh_access_token(
                    integration_type, token_data.refresh_token
                )
                
                # Update the secret with new token data
                new_secret_value = refreshed_token_data.model_dump_json()
                update_request = SecretUpdateRequest(secret_value=new_secret_value)
                await self.secret_service.update_secret(
                    secret.id, update_request, user_id
                )
                
                logger.info(f"Successfully refreshed OAuth token for secret {secret.name}")
                return new_secret_value
            else:
                logger.info(f"OAuth token for secret {secret.name} has no expiry, using as-is")
                return decrypted_value
                
        except (json.JSONDecodeError, ValueError) as e:
            # Not a valid OAuth token, return as-is
            logger.debug(f"Secret {secret.name} is not a valid OAuth token: {e}")
            return decrypted_value
        except Exception as e:
            logger.error(f"Error refreshing OAuth token for secret {secret.name}: {e}")
            return decrypted_value
            
    def _get_integration_type_from_secret_name(self, secret_name: str) -> IntegrationType | None:
        """Extract integration type from secret name.
        
        Args:
            secret_name: The secret name (e.g., 'google_calendar_oauth_token')
            
        Returns:
            The corresponding IntegrationType or None
        """
        # Map common secret name patterns to integration types
        integration_mapping = {
            'google_calendar': IntegrationType.GOOGLE_CALENDAR,
            'gmail': IntegrationType.GMAIL,
            'slack': IntegrationType.SLACK,
            'hubspot': IntegrationType.HUBSPOT,
            'shopify': IntegrationType.SHOPIFY,
            'stripe': IntegrationType.STRIPE,
            # Add more mappings as needed
        }
        
        # Remove _oauth_token suffix and look for matches
        base_name = secret_name.replace('_oauth_token', '')
        return integration_mapping.get(base_name)
