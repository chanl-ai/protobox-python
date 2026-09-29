#!/usr/bin/env python3
"""Unit tests for OpenAPIImportService.

These tests focus on the service logic for parsing OpenAPI specs and cURL commands,
validating the parsing logic, error handling, and data transformation.
"""

import json
import os
import sys
from dataclasses import asdict
from unittest.mock import Mock

import pytest

# Set required environment variables for tests
os.environ["MCP_SECRET_KEY"] = "test_secret_key_for_unit_tests"
os.environ["MCP_MONGODB_URL"] = "mongodb://test:test@localhost:27017/test"

# Add project src/ directory to Python import path for protobox package.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_DIR = os.path.join(ROOT, "src")
sys.path.insert(0, SRC_DIR)

from protobox.admin.services.openapi_import_service import (
    ImportedActionPreview,
    OpenAPIImportService,
)


class TestOpenAPIImportService:
    """Test cases for OpenAPIImportService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = OpenAPIImportService()

    def test_parse_simple_openapi_spec(self):
        """Test parsing a simple OpenAPI specification."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "servers": [{"url": "https://api.example.com"}],
            "paths": {
                "/users": {
                    "get": {
                        "summary": "List users",
                        "responses": {"200": {"description": "Success"}},
                    }
                }
            },
        }

        spec_content = json.dumps(spec)
        previews = self.service.parse_openapi_spec(spec_content)

        assert len(previews) == 1
        preview = previews[0]
        assert preview.name == "get-users"
        assert preview.description == "List users"
        assert preview.method == "GET"
        assert preview.url == "https://api.example.com/users"
        assert len(preview.variables) == 0

    def test_parse_openapi_with_path_parameters(self):
        """Test parsing OpenAPI spec with path parameters."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users/{id}": {
                    "get": {
                        "summary": "Get user by ID",
                        "parameters": [
                            {
                                "name": "id",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "integer", "example": 123},
                                "description": "User ID",
                            }
                        ],
                        "responses": {"200": {"description": "Success"}},
                    }
                }
            },
        }

        spec_content = json.dumps(spec)
        previews = self.service.parse_openapi_spec(spec_content)

        assert len(previews) == 1
        preview = previews[0]
        assert preview.name == "get-users-id"
        assert preview.method == "GET"
        assert len(preview.variables) == 1

        var = preview.variables[0]
        assert var["name"] == "id"
        assert var["type"] == "integer"
        assert var["required"] is True
        assert var["in"] == "path"
        assert var["example"] == 123
        assert "User ID" in var["description"]

    def test_parse_openapi_with_query_parameters(self):
        """Test parsing OpenAPI spec with query parameters."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "summary": "List users",
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "required": False,
                                "schema": {"type": "integer", "default": 10},
                                "description": "Number of users to return",
                            },
                            {
                                "name": "filter",
                                "in": "query",
                                "required": True,
                                "schema": {"type": "string"},
                                "description": "Filter criteria",
                            },
                        ],
                        "responses": {"200": {"description": "Success"}},
                    }
                }
            },
        }

        spec_content = json.dumps(spec)
        previews = self.service.parse_openapi_spec(spec_content)

        assert len(previews) == 1
        preview = previews[0]
        assert len(preview.variables) == 2

        # Check required query param
        filter_var = next(v for v in preview.variables if v["name"] == "filter")
        assert filter_var["required"] is True
        assert filter_var["in"] == "query"

        # Check optional query param
        limit_var = next(v for v in preview.variables if v["name"] == "limit")
        assert limit_var["required"] is False
        assert limit_var["in"] == "query"

    def test_parse_openapi_with_request_body(self):
        """Test parsing OpenAPI spec with request body."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "summary": "Create user",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "email": {"type": "string", "format": "email"},
                                            "age": {"type": "integer"},
                                        },
                                        "required": ["name", "email"],
                                    },
                                    "example": {
                                        "name": "John Doe",
                                        "email": "john@example.com",
                                        "age": 30,
                                    },
                                }
                            },
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }

        spec_content = json.dumps(spec)
        previews = self.service.parse_openapi_spec(spec_content)

        assert len(previews) == 1
        preview = previews[0]
        assert preview.method == "POST"

        # Should have request body variable
        body_vars = [v for v in preview.variables if v["in"] == "body"]
        assert len(body_vars) > 0

        # Check request example
        assert preview.request_example is not None
        assert preview.request_example["content_type"] == "application/json"
        assert "name" in preview.request_example["body"]

    def test_parse_openapi_with_response_examples(self):
        """Test parsing OpenAPI spec with response examples."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users/{id}": {
                    "get": {
                        "summary": "Get user",
                        "parameters": [
                            {
                                "name": "id",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string"},
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "User found",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "string"},
                                                "name": {"type": "string"},
                                            },
                                        },
                                        "example": {"id": "123", "name": "John Doe"},
                                    }
                                },
                            },
                            "404": {
                                "description": "User not found",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {"error": {"type": "string"}},
                                        },
                                        "example": {"error": "User not found"},
                                    }
                                },
                            },
                        },
                    }
                }
            },
        }

        spec_content = json.dumps(spec)
        previews = self.service.parse_openapi_spec(spec_content)

        assert len(previews) == 1
        preview = previews[0]

        # Check response examples
        assert preview.response_examples is not None
        assert "200" in preview.response_examples
        assert "404" in preview.response_examples

        success_response = preview.response_examples["200"]
        assert success_response["description"] == "User found"
        assert success_response["content_type"] == "application/json"
        assert "name" in success_response["body"]

    def test_parse_openapi_with_tags_and_security(self):
        """Test parsing OpenAPI spec with tags and security schemes."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "components": {"securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}}},
            "paths": {
                "/users": {
                    "get": {
                        "summary": "List users",
                        "tags": ["Users", "Public"],
                        "security": [{"bearerAuth": []}],
                        "responses": {"200": {"description": "Success"}},
                    }
                }
            },
        }

        spec_content = json.dumps(spec)
        previews = self.service.parse_openapi_spec(spec_content)

        assert len(previews) == 1
        preview = previews[0]
        assert preview.tags == ["Users", "Public"]
        assert preview.security_schemes == ["bearerAuth"]

    def test_parse_openapi_with_base_url_override(self):
        """Test parsing OpenAPI spec with base URL override."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "servers": [{"url": "https://api.example.com"}],
            "paths": {
                "/users": {
                    "get": {
                        "summary": "List users",
                        "responses": {"200": {"description": "Success"}},
                    }
                }
            },
        }

        spec_content = json.dumps(spec)
        previews = self.service.parse_openapi_spec(
            spec_content, base_url_override="https://custom.api.com"
        )

        assert len(previews) == 1
        assert previews[0].url == "https://custom.api.com/users"

    def test_parse_openapi_with_path_filters(self):
        """Test parsing OpenAPI spec with path inclusion/exclusion filters."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {"get": {"responses": {"200": {"description": "Success"}}}},
                "/admin/users": {"get": {"responses": {"200": {"description": "Success"}}}},
                "/public/health": {"get": {"responses": {"200": {"description": "Success"}}}},
            },
        }

        spec_content = json.dumps(spec)

        # Test include filter
        previews = self.service.parse_openapi_spec(spec_content, include_paths=["/users"])
        assert len(previews) == 2  # /users and /admin/users

        # Test exclude filter
        previews = self.service.parse_openapi_spec(spec_content, exclude_paths=["/admin"])
        assert len(previews) == 2  # /users and /public/health

    def test_parse_yaml_openapi_spec(self):
        """Test parsing YAML OpenAPI specification."""
        yaml_spec = """
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /users:
    get:
      summary: List users
      responses:
        '200':
          description: Success
        """

        previews = self.service.parse_openapi_spec(yaml_spec)

        assert len(previews) == 1
        assert previews[0].name == "get-users"
        assert previews[0].description == "List users"

    def test_parse_invalid_openapi_spec(self):
        """Test parsing invalid OpenAPI specification."""
        invalid_specs = [
            "invalid json",
            '{"not": "openapi spec"}',
            '{"openapi": "3.0.0"}',  # Missing required fields
        ]

        for invalid_spec in invalid_specs:
            with pytest.raises(ValueError, match="Failed to parse OpenAPI spec"):
                self.service.parse_openapi_spec(invalid_spec)

    def test_parse_simple_curl_command(self):
        """Test parsing a simple cURL command."""
        curl_command = "curl -X GET https://api.example.com/users"

        preview = self.service.parse_curl(curl_command)

        assert preview.name == "get-users"
        assert preview.method == "GET"
        assert preview.url == "https://api.example.com/users"
        assert len(preview.variables) == 0

    def test_parse_curl_with_headers(self):
        """Test parsing cURL command with headers."""
        curl_command = "curl -X POST https://api.example.com/users -H 'Content-Type: application/json' -H 'Authorization: Bearer token123'"

        preview = self.service.parse_curl(curl_command)

        assert preview.method == "POST"
        # Should extract headers as variables
        header_vars = [v for v in preview.variables if v["in"] == "header"]
        assert len(header_vars) >= 1

        # Check for Authorization header
        auth_var = next((v for v in header_vars if "authorization" in v["name"].lower()), None)
        assert auth_var is not None

    def test_parse_curl_with_data(self):
        """Test parsing cURL command with request data."""
        curl_command = 'curl -X POST https://api.example.com/users -d \'{"name": "John", "email": "john@example.com"}\' -H "Content-Type: application/json"'

        preview = self.service.parse_curl(curl_command)

        assert preview.method == "POST"
        # Should have body variable
        body_vars = [v for v in preview.variables if v["in"] == "body"]
        assert len(body_vars) > 0

    def test_parse_curl_with_query_params(self):
        """Test parsing cURL command with query parameters."""
        curl_command = "curl 'https://api.example.com/users?limit=10&sort=name'"

        preview = self.service.parse_curl(curl_command)

        # Should extract query parameters
        query_vars = [v for v in preview.variables if v["in"] == "query"]
        assert len(query_vars) == 2

        var_names = {v["name"] for v in query_vars}
        assert "limit" in var_names
        assert "sort" in var_names

    def test_parse_invalid_curl_command(self):
        """Test parsing invalid cURL commands."""
        invalid_commands = [
            "",
            "not a curl command",
            "curl",  # Missing URL
        ]

        for invalid_cmd in invalid_commands:
            with pytest.raises(ValueError):
                self.service.parse_curl(invalid_cmd)

    def test_generate_example_from_schema(self):
        """Test generating examples from OpenAPI schemas."""
        # Test object schema
        object_schema = Mock()
        object_schema.type = "object"
        object_schema.properties = {
            "name": Mock(type="string", example="John", default=None),
            "age": Mock(type="integer", example=None, default=25),
        }
        object_schema.example = None
        object_schema.default = None

        example = self.service._generate_example_from_schema(object_schema)
        assert isinstance(example, dict)
        assert example["name"] == "John"
        assert example["age"] == 25

        # Test array schema
        array_schema = Mock()
        array_schema.type = "array"
        array_schema.items = Mock(type="string", example="item", default=None)
        array_schema.example = None
        array_schema.default = None

        example = self.service._generate_example_from_schema(array_schema)
        assert example == ["item"]

        # Test string with format
        email_schema = Mock()
        email_schema.type = "string"
        email_schema.format = "email"
        email_schema.example = None
        email_schema.default = None
        email_schema.enum = None

        example = self.service._generate_example_from_schema(email_schema)
        assert example == "user@example.com"

        # Test enum
        enum_schema = Mock()
        enum_schema.type = "string"
        enum_schema.format = None
        enum_schema.example = None
        enum_schema.default = None
        enum_schema.enum = ["active", "inactive"]

        example = self.service._generate_example_from_schema(enum_schema)
        assert example == "active"

    def test_imported_action_preview_dataclass(self):
        """Test the ImportedActionPreview dataclass."""
        preview = ImportedActionPreview(
            name="test-action",
            description="Test action",
            method="GET",
            url="https://api.example.com/test",
            variables=[
                {
                    "name": "id",
                    "type": "string",
                    "required": True,
                    "description": "Test ID",
                    "in": "path",
                }
            ],
            request_example={"content_type": "application/json", "body": {}},
            response_examples={
                "200": {"description": "OK", "content_type": "application/json", "body": {}}
            },
            tags=["test"],
            security_schemes=["bearerAuth"],
        )

        # Test serialization
        preview_dict = asdict(preview)
        assert preview_dict["name"] == "test-action"
        assert preview_dict["method"] == "GET"
        assert len(preview_dict["variables"]) == 1
        assert preview_dict["variables"][0]["name"] == "id"


if __name__ == "__main__":
    pytest.main([__file__])
