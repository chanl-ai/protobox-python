#!/usr/bin/env python3
"""Integration tests for importing actions from OpenAPI and cURL (feature-flagged).

These tests use the running server at http://localhost:8090 and exercise the routes:
- POST /admin/api/v1/workspaces/{workspace_id}/actions/import/openapi/preview
- POST /admin/api/v1/workspaces/{workspace_id}/actions/import/openapi/create
- POST /admin/api/v1/workspaces/{workspace_id}/actions/import/curl/preview
- POST /admin/api/v1/workspaces/{workspace_id}/actions/import/curl/create

They auto-skip if the feature is disabled (404) or auth/server unavailable.
"""

import json
import unittest

from httpx import Client

from .test_utils import ensure_test_workspace, get_emulator_auth_token

MINIMAL_OPENAPI_SPEC = """
openapi: 3.0.0
info:
  title: Sample API
  version: 1.0.0
servers:
  - url: https://api.example.com
paths:
  /echo:
    post:
      summary: Echo a message
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
      responses:
        '200':
          description: OK
  /users/{id}:
    get:
      summary: Get user by id
      parameters:
        - in: path
          name: id
          required: true
          schema:
            type: string
      responses:
        '200':
          description: OK
"""

COMPLEX_OPENAPI_SPEC = """
openapi: 3.0.0
info:
  title: Pet Store API
  version: 1.0.0
  description: A comprehensive pet store API
servers:
  - url: https://petstore.example.com/api/v1
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
    apiKey:
      type: apiKey
      in: header
      name: X-API-Key
  schemas:
    Pet:
      type: object
      required:
        - name
        - species
      properties:
        id:
          type: integer
          example: 123
        name:
          type: string
          example: "Fluffy"
        species:
          type: string
          enum: ["dog", "cat", "bird"]
          example: "cat"
        age:
          type: integer
          minimum: 0
          maximum: 30
          example: 3
paths:
  /pets:
    get:
      summary: List all pets
      tags:
        - pets
        - public
      parameters:
        - name: limit
          in: query
          required: false
          schema:
            type: integer
            default: 20
            minimum: 1
            maximum: 100
          description: Maximum number of pets to return
        - name: species
          in: query
          required: false
          schema:
            type: string
            enum: ["dog", "cat", "bird"]
          description: Filter by species
        - name: sort
          in: query
          required: false
          schema:
            type: string
            enum: ["name", "age", "created"]
            default: "name"
      responses:
        '200':
          description: List of pets
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Pet'
              example:
                - id: 1
                  name: "Buddy"
                  species: "dog"
                  age: 5
                - id: 2
                  name: "Whiskers"
                  species: "cat"
                  age: 2
    post:
      summary: Create a new pet
      tags:
        - pets
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Pet'
            example:
              name: "Max"
              species: "dog"
              age: 4
      responses:
        '201':
          description: Pet created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Pet'
        '400':
          description: Invalid input
          content:
            application/json:
              example:
                error: "Invalid pet data"
                details: "Name is required"
  /pets/{petId}:
    get:
      summary: Get a specific pet
      tags:
        - pets
      parameters:
        - name: petId
          in: path
          required: true
          schema:
            type: integer
          description: Pet ID
          example: 123
      responses:
        '200':
          description: Pet details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Pet'
        '404':
          description: Pet not found
          content:
            application/json:
              example:
                error: "Pet not found"
    put:
      summary: Update a pet
      tags:
        - pets
      security:
        - bearerAuth: []
        - apiKey: []
      parameters:
        - name: petId
          in: path
          required: true
          schema:
            type: integer
          description: Pet ID
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Pet'
      responses:
        '200':
          description: Pet updated successfully
        '404':
          description: Pet not found
    delete:
      summary: Delete a pet
      tags:
        - pets
      security:
        - bearerAuth: []
      parameters:
        - name: petId
          in: path
          required: true
          schema:
            type: integer
          description: Pet ID
      responses:
        '204':
          description: Pet deleted successfully
        '404':
          description: Pet not found
"""


class ActionsImportOpenAPITestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = Client(base_url="http://localhost:8090", timeout=10.0)
        # Verify server is running
        try:
            resp = cls.client.get("/admin/api/v1/health")
            assert resp.status_code == 200
        except Exception:
            cls.skip_tests = True
            cls.skip_reason = "Server not running at http://localhost:8090"
            return

        token, refresh_token, headers = get_emulator_auth_token(cls.client)
        if not token:
            cls.skip_tests = True
            cls.skip_reason = "Authentication not enabled or Firebase emulator not running"
            return
        cls.headers = headers

        ws = ensure_test_workspace(cls.client, cls.headers)
        if not ws:
            cls.skip_tests = True
            cls.skip_reason = "Failed to create or fetch a workspace"
            return
        cls.workspace_id = ws["id"]

    def api_post(self, endpoint: str, json: dict | None = None):
        return self.client.post(f"/admin/api/v1{endpoint}", json=json, headers=self.headers)

    def api_get(self, endpoint: str):
        return self.client.get(f"/admin/api/v1{endpoint}", headers=self.headers)

    def test_openapi_preview_and_create(self):
        if getattr(self, "skip_tests", False):
            self.skipTest(self.skip_reason)

        # Preview
        preview_resp = self.api_post(
            f"/workspaces/{self.workspace_id}/actions/import/openapi/preview",
            json={"spec_content": MINIMAL_OPENAPI_SPEC},
        )

        if preview_resp.status_code == 404:
            self.skipTest("Feature MCP_INTERNAL_TOOLS disabled on server")

        self.assertEqual(preview_resp.status_code, 200, preview_resp.text)
        preview = preview_resp.json()
        self.assertIn("actions_count", preview)
        self.assertGreaterEqual(preview["actions_count"], 2)  # /echo + /users/{id}
        self.assertIn("previews", preview)
        self.assertTrue(any(p["name"].startswith("post-echo") for p in preview["previews"]))

        # Create
        create_resp = self.api_post(
            f"/workspaces/{self.workspace_id}/actions/import/openapi/create",
            json={"spec_content": MINIMAL_OPENAPI_SPEC},
        )
        self.assertEqual(create_resp.status_code, 200, create_resp.text)
        created_summary = create_resp.json()
        self.assertIn("summary", created_summary)
        # Either actions were created or skipped (due to duplicates from previous runs)
        total_processed = created_summary["summary"].get("created", 0) + created_summary[
            "summary"
        ].get("skipped", 0)
        self.assertGreaterEqual(total_processed, 1)

        # Verify actions listed
        list_resp = self.api_get(f"/workspaces/{self.workspace_id}/actions")
        self.assertEqual(list_resp.status_code, 200, list_resp.text)
        actions = list_resp.json()
        names = {a.get("name") for a in actions}
        self.assertTrue(any(n.startswith("post-echo") for n in names))

    def test_curl_preview_and_create(self):
        if getattr(self, "skip_tests", False):
            self.skipTest(self.skip_reason)

        curl = "curl -X POST https://httpbin.org/anything -H 'Content-Type: application/json' -d '{\"message\":\"hi\"}'"
        preview_resp = self.api_post(
            f"/workspaces/{self.workspace_id}/actions/import/curl/preview",
            json={"curl_command": curl, "name": "post-httpbin-anything"},
        )

        if preview_resp.status_code == 404:
            self.skipTest("Feature MCP_INTERNAL_TOOLS disabled on server")

        self.assertEqual(preview_resp.status_code, 200, preview_resp.text)
        preview = preview_resp.json()
        self.assertEqual(preview.get("actions_count"), 1)
        self.assertEqual(preview["previews"][0]["name"], "post-httpbin-anything")

        create_resp = self.api_post(
            f"/workspaces/{self.workspace_id}/actions/import/curl/create",
            json={"curl_command": curl, "name": "post-httpbin-anything"},
        )
        self.assertEqual(create_resp.status_code, 200, create_resp.text)
        created = create_resp.json()
        self.assertIn("summary", created)
        self.assertIn(created["summary"]["created"], (0, 1))  # allow duplicate across runs

    def test_complex_openapi_preview_with_detailed_parsing(self):
        """Test complex OpenAPI spec parsing with detailed validation."""
        if getattr(self, "skip_tests", False):
            self.skipTest(self.skip_reason)

        preview_resp = self.api_post(
            f"/workspaces/{self.workspace_id}/actions/import/openapi/preview",
            json={"spec_content": COMPLEX_OPENAPI_SPEC},
        )

        if preview_resp.status_code == 404:
            self.skipTest("Feature MCP_INTERNAL_TOOLS disabled on server")

        self.assertEqual(preview_resp.status_code, 200, preview_resp.text)
        preview = preview_resp.json()

        # Should have multiple actions (GET /pets, POST /pets, GET /pets/{id}, PUT /pets/{id}, DELETE /pets/{id})
        self.assertGreaterEqual(preview["actions_count"], 5)

        previews = preview["previews"]
        action_names = {p["name"] for p in previews}

        # Verify specific actions exist
        self.assertTrue(any("get-pets" in name for name in action_names))
        self.assertTrue(any("post-pets" in name for name in action_names))
        self.assertTrue(
            any("get-pets-petid" in name or "get-pets-pet-id" in name for name in action_names)
        )

        # Find GET /pets action and validate its details
        get_pets_action = next(
            (p for p in previews if "get-pets" in p["name"] and p["method"] == "GET"), None
        )
        self.assertIsNotNone(get_pets_action, "GET /pets action not found")

        # Check query parameters
        query_vars = [v for v in get_pets_action["variables"] if v.get("in") == "query"]
        self.assertGreater(len(query_vars), 0, "Should have query parameters")

        param_names = {v["name"] for v in query_vars}
        self.assertIn("limit", param_names)
        self.assertIn("species", param_names)

        # Check tags
        self.assertIn("tags", get_pets_action)
        self.assertIn("pets", get_pets_action["tags"])

        # Find POST /pets action and validate request body
        post_pets_action = next(
            (p for p in previews if "post-pets" in p["name"] and p["method"] == "POST"), None
        )
        self.assertIsNotNone(post_pets_action, "POST /pets action not found")

        # Should have request example
        self.assertIsNotNone(post_pets_action.get("request_example"))
        self.assertEqual(post_pets_action["request_example"]["content_type"], "application/json")

        # Should have security schemes
        self.assertIsNotNone(post_pets_action.get("security_schemes"))
        self.assertIn("bearerAuth", post_pets_action["security_schemes"])

    def test_openapi_with_base_url_override(self):
        """Test OpenAPI parsing with base URL override."""
        if getattr(self, "skip_tests", False):
            self.skipTest(self.skip_reason)

        preview_resp = self.api_post(
            f"/workspaces/{self.workspace_id}/actions/import/openapi/preview",
            json={
                "spec_content": MINIMAL_OPENAPI_SPEC,
                "base_url_override": "https://custom.api.com",
            },
        )

        if preview_resp.status_code == 404:
            self.skipTest("Feature MCP_INTERNAL_TOOLS disabled on server")

        self.assertEqual(preview_resp.status_code, 200, preview_resp.text)
        preview = preview_resp.json()

        # All URLs should use the custom base URL
        for action in preview["previews"]:
            self.assertTrue(
                action["url"].startswith("https://custom.api.com"),
                f"Action {action['name']} URL should use custom base: {action['url']}",
            )

    def test_openapi_with_path_filters(self):
        """Test OpenAPI parsing with path inclusion/exclusion filters."""
        if getattr(self, "skip_tests", False):
            self.skipTest(self.skip_reason)

        # Test include paths
        preview_resp = self.api_post(
            f"/workspaces/{self.workspace_id}/actions/import/openapi/preview",
            json={
                "spec_content": COMPLEX_OPENAPI_SPEC,
                "include_paths": ["/pets/{"],  # Only include parameterized pet paths
            },
        )

        if preview_resp.status_code == 404:
            self.skipTest("Feature MCP_INTERNAL_TOOLS disabled on server")

        self.assertEqual(preview_resp.status_code, 200, preview_resp.text)
        preview = preview_resp.json()

        # Should only have actions for /pets/{petId}
        for action in preview["previews"]:
            self.assertIn(
                "{",
                action["url"],
                f"Action {action['name']} should be parameterized: {action['url']}",
            )

        # Test exclude paths
        preview_resp = self.api_post(
            f"/workspaces/{self.workspace_id}/actions/import/openapi/preview",
            json={
                "spec_content": COMPLEX_OPENAPI_SPEC,
                "exclude_paths": ["/pets/{"],  # Exclude parameterized pet paths
            },
        )

        self.assertEqual(preview_resp.status_code, 200, preview_resp.text)
        preview = preview_resp.json()

        # Should only have actions for /pets (without parameters)
        for action in preview["previews"]:
            self.assertNotIn(
                "{",
                action["url"],
                f"Action {action['name']} should not be parameterized: {action['url']}",
            )

    def test_curl_with_complex_headers_and_data(self):
        """Test parsing complex cURL commands with multiple headers and JSON data."""
        if getattr(self, "skip_tests", False):
            self.skipTest(self.skip_reason)

        complex_curl = """curl -X POST 'https://api.example.com/pets' \\
  -H 'Content-Type: application/json' \\
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIs...' \\
  -H 'X-API-Version: v1' \\
  -H 'User-Agent: MyApp/1.0' \\
  -d '{
    "name": "Buddy",
    "species": "dog",
    "age": 3,
    "tags": ["friendly", "trained"]
  }'"""

        preview_resp = self.api_post(
            f"/workspaces/{self.workspace_id}/actions/import/curl/preview",
            json={"curl_command": complex_curl, "name": "create-pet-complex"},
        )

        if preview_resp.status_code == 404:
            self.skipTest("Feature MCP_INTERNAL_TOOLS disabled on server")

        self.assertEqual(preview_resp.status_code, 200, preview_resp.text)
        preview = preview_resp.json()

        action = preview["previews"][0]
        self.assertEqual(action["name"], "create-pet-complex")
        self.assertEqual(action["method"], "POST")

        # Should have extracted headers as variables
        header_vars = [v for v in action["variables"] if v.get("in") == "header"]
        self.assertGreater(len(header_vars), 2, "Should have multiple header variables")

        header_names = {v["name"].lower() for v in header_vars}
        self.assertIn("authorization", header_names)
        self.assertIn("x-api-version", header_names)

        # Should have body variable
        body_vars = [v for v in action["variables"] if v.get("in") == "body"]
        self.assertGreater(len(body_vars), 0, "Should have body variables")

    def test_curl_with_query_parameters(self):
        """Test parsing cURL command with query parameters."""
        if getattr(self, "skip_tests", False):
            self.skipTest(self.skip_reason)

        curl_with_query = (
            "curl 'https://api.example.com/pets?limit=10&species=dog&sort=name&active=true'"
        )

        preview_resp = self.api_post(
            f"/workspaces/{self.workspace_id}/actions/import/curl/preview",
            json={"curl_command": curl_with_query, "name": "list-pets-filtered"},
        )

        if preview_resp.status_code == 404:
            self.skipTest("Feature MCP_INTERNAL_TOOLS disabled on server")

        self.assertEqual(preview_resp.status_code, 200, preview_resp.text)
        preview = preview_resp.json()

        action = preview["previews"][0]

        # Should have extracted query parameters
        query_vars = [v for v in action["variables"] if v.get("in") == "query"]
        self.assertEqual(len(query_vars), 4, "Should have 4 query parameters")

        param_names = {v["name"] for v in query_vars}
        expected_params = {"limit", "species", "sort", "active"}
        self.assertEqual(param_names, expected_params)

    def test_error_handling_invalid_specs(self):
        """Test error handling for invalid OpenAPI specs and cURL commands."""
        if getattr(self, "skip_tests", False):
            self.skipTest(self.skip_reason)

        # Test invalid OpenAPI spec
        invalid_openapi_resp = self.api_post(
            f"/workspaces/{self.workspace_id}/actions/import/openapi/preview",
            json={"spec_content": "invalid yaml: content: ["},
        )

        if invalid_openapi_resp.status_code != 404:  # Skip if feature disabled
            self.assertEqual(invalid_openapi_resp.status_code, 400)
            error_data = invalid_openapi_resp.json()
            self.assertIn("detail", error_data)

        # Test invalid cURL command
        invalid_curl_resp = self.api_post(
            f"/workspaces/{self.workspace_id}/actions/import/curl/preview",
            json={"curl_command": "not a valid curl command", "name": "invalid-test"},
        )

        if invalid_curl_resp.status_code != 404:  # Skip if feature disabled
            self.assertEqual(invalid_curl_resp.status_code, 400)
            error_data = invalid_curl_resp.json()
            self.assertIn("detail", error_data)

    def test_openapi_json_format(self):
        """Test parsing OpenAPI spec in JSON format."""
        if getattr(self, "skip_tests", False):
            self.skipTest(self.skip_reason)

        json_spec = {
            "openapi": "3.0.0",
            "info": {"title": "JSON API", "version": "1.0.0"},
            "servers": [{"url": "https://jsonapi.example.com"}],
            "paths": {
                "/test": {
                    "get": {"summary": "Test endpoint", "responses": {"200": {"description": "OK"}}}
                }
            },
        }

        preview_resp = self.api_post(
            f"/workspaces/{self.workspace_id}/actions/import/openapi/preview",
            json={"spec_content": json.dumps(json_spec)},
        )

        if preview_resp.status_code == 404:
            self.skipTest("Feature MCP_INTERNAL_TOOLS disabled on server")

        self.assertEqual(preview_resp.status_code, 200, preview_resp.text)
        preview = preview_resp.json()

        self.assertEqual(preview["actions_count"], 1)
        action = preview["previews"][0]
        self.assertEqual(action["name"], "get-test")
        self.assertTrue(action["url"].startswith("https://jsonapi.example.com"))
