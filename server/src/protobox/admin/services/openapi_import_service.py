"""Service to import actions from OpenAPI specifications and cURL commands."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

from openapi3 import OpenAPI
from openapi3.schemas import Schema


def _kebab_from_path(method: str, path: str) -> str:
    """Generate a kebab-case action name from method and path."""
    # Strip leading/trailing slashes, replace path params and slashes
    normalized = path.strip("/")
    normalized = re.sub(r"\{([^}/]+)\}", r"\1", normalized)
    normalized = normalized.replace("/", "-")
    normalized = re.sub(r"[^a-zA-Z0-9\-]", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return f"{method.lower()}-{normalized}" if normalized else method.lower()


@dataclass
class ImportedActionPreview:
    name: str
    description: str | None
    method: str
    url: str
    variables: list[dict[str, Any]]
    request_example: dict[str, Any] | None = None
    response_examples: dict[str, dict[str, Any]] | None = None  # status_code -> example
    tags: list[str] | None = None
    security_schemes: list[str] | None = None


class OpenAPIImportService:
    """Parses OpenAPI specs and cURL to produce action definitions/previews."""

    def __init__(self, default_tag: str = "imported") -> None:
        self.default_tag = default_tag

    def parse_openapi_spec(
        self,
        spec_content: str,
        base_url_override: str | None = None,
        include_paths: list[str] | None = None,
        exclude_paths: list[str] | None = None,
    ) -> list[ImportedActionPreview]:
        """Parse an OpenAPI (YAML or JSON) spec into action previews using openapi3 library.

        This provides much better validation, reference resolution, and type safety.

        Args:
            spec_content: OpenAPI spec as YAML or JSON string
            base_url_override: Override the base URL from spec servers
            include_paths: Only include paths containing these substrings
            exclude_paths: Exclude paths containing these substrings
        """
        try:
            # Parse the spec content as JSON or YAML first
            import json

            import yaml

            try:
                # Try JSON first
                raw_doc = json.loads(spec_content)
            except json.JSONDecodeError:
                # If JSON fails, try YAML
                try:
                    raw_doc = yaml.safe_load(spec_content)
                except yaml.YAMLError as yaml_err:
                    raise ValueError(f"Failed to parse spec as JSON or YAML: {yaml_err}")

            # Use openapi3 library for robust parsing and validation
            api = OpenAPI(raw_doc)
        except Exception as e:
            raise ValueError(f"Failed to parse OpenAPI spec: {e}")

        # Determine base URL
        base_url = base_url_override
        if not base_url and api.servers:
            base_url = api.servers[0].url

        previews: list[ImportedActionPreview] = []

        for path_pattern, path_item in api.paths.items():
            # Apply path filters
            if include_paths and not any(sub in path_pattern for sub in include_paths):
                continue
            if exclude_paths and any(sub in path_pattern for sub in exclude_paths):
                continue

            # Iterate through HTTP methods
            for method_name in ["get", "post", "put", "delete", "patch", "head", "options"]:
                operation = getattr(path_item, method_name, None)
                if not operation:
                    continue

                variables = self._extract_variables_from_operation(operation, path_item)

                # Build URL with template variables
                templated_path = re.sub(r"\{([^}/]+)\}", r"{{\\1}}", path_pattern)
                url = urljoin(base_url or "", templated_path)

                # Generate action name and description
                name = self._generate_action_name(method_name, path_pattern, operation)
                description = self._generate_description(operation, method_name, path_pattern)

                # Extract examples and additional metadata
                request_example = self._extract_request_example(operation)
                response_examples = self._extract_response_examples(operation)
                tags = operation.tags or []
                security_schemes = self._extract_security_schemes(operation)

                previews.append(
                    ImportedActionPreview(
                        name=name,
                        description=description,
                        method=method_name.upper(),
                        url=url,
                        variables=variables,
                        request_example=request_example,
                        response_examples=response_examples,
                        tags=tags,
                        security_schemes=security_schemes,
                    )
                )

        return previews

    def _extract_variables_from_operation(self, operation, path_item) -> list[dict[str, Any]]:
        """Extract variables from operation parameters and request body."""
        variables: list[dict[str, Any]] = []

        # Collect all parameters (path-level + operation-level)
        all_params = []
        if path_item.parameters:
            all_params.extend(path_item.parameters)
        if operation.parameters:
            all_params.extend(operation.parameters)

        # Process parameters
        for param in all_params:
            param_type = self._get_schema_type(param.schema) if param.schema else "string"

            variables.append(
                {
                    "name": param.name,
                    "type": param_type,
                    "required": param.required if param.in_ == "path" else param.required,
                    "description": param.description
                    or f"{param.in_.title()} parameter: {param.name}",
                    "in": param.in_,  # path, query, header, cookie
                    "example": self._get_schema_example(param.schema) if param.schema else None,
                }
            )

        # Process request body
        if operation.requestBody:
            content = operation.requestBody.content
            if content:
                # Get the first media type (usually application/json)
                media_type = next(iter(content.values()))
                body_type = (
                    self._get_schema_type(media_type.schema) if media_type.schema else "object"
                )

                variables.append(
                    {
                        "name": "body",
                        "type": body_type,
                        "required": operation.requestBody.required,
                        "description": operation.requestBody.description or "HTTP request body",
                        "in": "body",
                        "schema": (
                            self._schema_to_dict(media_type.schema) if media_type.schema else None
                        ),
                    }
                )

        return variables

    def _get_schema_type(self, schema: Schema | None) -> str:
        """Extract type from OpenAPI schema object."""
        if not schema:
            return "string"

        if schema.type:
            return schema.type
        if schema.allOf or schema.oneOf or schema.anyOf:
            return "object"  # Complex schemas default to object
        return "string"

    def _get_schema_example(self, schema: Schema | None) -> Any | None:
        """Extract example value from schema."""
        if not schema:
            return None

        if schema.example is not None:
            return schema.example
        if schema.default is not None:
            return schema.default
        if schema.enum:
            return schema.enum[0]
        return None

    def _schema_to_dict(self, schema: Schema | None) -> dict[str, Any] | None:
        """Convert schema to dictionary for frontend consumption."""
        if not schema:
            return None

        result = {}
        if schema.type:
            result["type"] = schema.type
        if schema.format:
            result["format"] = schema.format
        if schema.description:
            result["description"] = schema.description
        if schema.example is not None:
            result["example"] = schema.example
        if schema.enum:
            result["enum"] = schema.enum
        if schema.properties:
            result["properties"] = {
                name: self._schema_to_dict(prop) for name, prop in schema.properties.items()
            }
        if schema.required:
            result["required"] = schema.required

        return result

    def _generate_action_name(self, method: str, path: str, operation) -> str:
        """Generate a meaningful action name."""
        # Use operationId if available and clean
        if operation.operationId and re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", operation.operationId):
            return operation.operationId.replace("_", "-").lower()

        # Fall back to method + path
        return _kebab_from_path(method, path)

    def _generate_description(self, operation, method: str, path: str) -> str:
        """Generate a meaningful description."""
        if operation.summary:
            return operation.summary
        if operation.description:
            # Use first line of description if it's long
            first_line = operation.description.split("\n")[0].strip()
            return first_line if len(first_line) <= 100 else first_line[:97] + "..."
        return f"{method.upper()} {path}"

    def _extract_request_example(self, operation) -> dict[str, Any] | None:
        """Extract request body example from operation."""
        if not operation.requestBody or not operation.requestBody.content:
            return None

        # Get the first media type (usually application/json)
        media_type = next(iter(operation.requestBody.content.values()))
        if not media_type.schema:
            return None

        # Try to get example from schema
        example = self._generate_example_from_schema(media_type.schema)
        if example:
            return {
                "content_type": next(iter(operation.requestBody.content.keys())),
                "body": example,
            }
        return None

    def _extract_response_examples(self, operation) -> dict[str, dict[str, Any]] | None:
        """Extract response examples from operation."""
        if not operation.responses:
            return None

        examples = {}
        for status_code, response in operation.responses.items():
            if response.content:
                # Get the first media type
                media_type = next(iter(response.content.values()))
                if media_type.schema:
                    example = self._generate_example_from_schema(media_type.schema)
                    if example:
                        examples[status_code] = {
                            "description": response.description or f"Response {status_code}",
                            "content_type": next(iter(response.content.keys())),
                            "body": example,
                        }

        return examples if examples else None

    def _extract_security_schemes(self, operation) -> list[str] | None:
        """Extract security scheme names from operation."""
        if not operation.security:
            return None

        schemes = []
        for security_req in operation.security:
            schemes.extend(security_req.raw_element.keys())

        return schemes if schemes else None

    def _generate_example_from_schema(self, schema: Schema | None) -> Any | None:
        """Generate an example value from OpenAPI schema."""
        if not schema:
            return None

        # Use explicit example if available
        if schema.example is not None:
            return schema.example

        # Use default if available
        if schema.default is not None:
            return schema.default

        # Generate based on type
        if schema.type == "object" and schema.properties:
            example = {}
            for prop_name, prop_schema in schema.properties.items():
                prop_example = self._generate_example_from_schema(prop_schema)
                if prop_example is not None:
                    example[prop_name] = prop_example
            return example if example else None

        if schema.type == "array" and schema.items:
            item_example = self._generate_example_from_schema(schema.items)
            return [item_example] if item_example is not None else None

        if schema.type == "string":
            if schema.enum:
                return schema.enum[0]
            if schema.format == "email":
                return "user@example.com"
            if schema.format == "date":
                return "2024-01-01"
            if schema.format == "date-time":
                return "2024-01-01T12:00:00Z"
            return "string"

        if schema.type == "integer":
            return schema.enum[0] if schema.enum else 42

        if schema.type == "number":
            return schema.enum[0] if schema.enum else 3.14

        if schema.type == "boolean":
            return True

        return None

    def parse_curl(self, curl_command: str) -> ImportedActionPreview:
        """Very basic cURL parsing to produce a single REST action preview.

        Supports: -X/--request, URL, -H/--header, -d/--data/--data-raw/--data-binary
        """
        # Tokenize respecting quotes
        tokens = re.findall(r"(?:[^\s\"]+|\"[^\"]*\"|\'[^\']*\')+", curl_command)
        if not tokens or tokens[0].lower() != "curl":
            raise ValueError("Command must start with 'curl'")

        method = "GET"
        url = ""
        headers: dict[str, str] = {}
        body: str | None = None

        i = 1
        while i < len(tokens):
            t = tokens[i]
            if t in ("-X", "--request") and i + 1 < len(tokens):
                method = tokens[i + 1].strip("\"'")
                i += 2
                continue
            if t in ("-H", "--header") and i + 1 < len(tokens):
                h = tokens[i + 1].strip("\"'")
                if ":" in h:
                    k, v = h.split(":", 1)
                    headers[k.strip()] = v.strip()
                i += 2
                continue
            if t in ("-d", "--data", "--data-raw", "--data-binary") and i + 1 < len(tokens):
                body = tokens[i + 1].strip("\"'")
                method = "POST" if method == "GET" else method
                i += 2
                continue
            if t.startswith("http://") or t.startswith("https://") or t.strip("\"'").startswith("http://") or t.strip("\"'").startswith("https://"):
                url = t.strip("\"'")
                i += 1
                continue
            # Ignore other flags for now
            i += 1

        if not url:
            raise ValueError("cURL command missing URL")

        # Create variables for query parameters, headers and body
        variables: list[dict[str, Any]] = []

        # Parse query parameters from URL
        from urllib.parse import parse_qs, urlparse
        parsed_url = urlparse(url)
        if parsed_url.query:
            query_params = parse_qs(parsed_url.query)
            for param_name, param_values in query_params.items():
                # Use first value if multiple values exist
                param_value = param_values[0] if param_values else ""
                variables.append({
                    "name": param_name,
                    "type": "string",
                    "required": False,
                    "description": f"Query parameter: {param_name}",
                    "in": "query",
                    "default": param_value
                })

        # Add header variables
        for header_name, header_value in headers.items():
            # Skip standard headers that shouldn't be variableized
            if header_name.lower() not in ["user-agent", "accept"]:
                variables.append({
                    "name": header_name.lower().replace("-", "_"),
                    "type": "string",
                    "required": False,
                    "description": f"HTTP header: {header_name}",
                    "in": "header",
                    "default": header_value
                })

        if body:
            # If JSON-looking, encourage variableized body
            try:
                json.loads(body)
                variables.append(
                    {
                        "name": "body",
                        "type": "object",
                        "required": True,
                        "description": "HTTP request body (JSON)",
                        "in": "body"
                    }
                )
            except Exception:
                variables.append(
                    {
                        "name": "body",
                        "type": "string",
                        "required": True,
                        "description": "HTTP request body",
                        "in": "body"
                    }
                )

        name = _kebab_from_path(method, re.sub(r"https?://[^/]+", "", url))
        description = f"Imported from cURL: {method} {url}"

        return ImportedActionPreview(
            name=name,
            description=description,
            method=method.upper(),
            url=url,
            variables=variables,
        )
