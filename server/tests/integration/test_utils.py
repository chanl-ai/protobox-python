"""
Utility functions for integration tests.
"""

import os
import secrets
from pathlib import Path
from typing import Any

import requests
from httpx import Client


def create_firebase_emulator_user(
    email: str = "test@example.com", password: str = "testpassword123"
) -> str | None:
    """
    Create a user in Firebase emulator and return the ID token.

    Returns Firebase ID token or None if failed.
    """
    emulator_url = "http://localhost:9099"

    try:
        # Try to sign in first
        response = requests.post(
            f"{emulator_url}/identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=fake-api-key",
            json={"email": email, "password": password, "returnSecureToken": True},
        )

        if response.status_code == 200:
            return response.json().get("idToken")

        # If sign in fails, try to create the user
        create_response = requests.post(
            f"{emulator_url}/identitytoolkit.googleapis.com/v1/accounts:signUp?key=fake-api-key",
            json={"email": email, "password": password, "returnSecureToken": True},
        )

        if create_response.status_code == 200:
            return create_response.json().get("idToken")

    except Exception as e:
        print(f"✗ Failed to create/sign in Firebase user: {e}")

    return None


def get_auth_token(client: Client, environment: str = "local") -> tuple[str | None, str | None, str | None]:
    """
    Get authentication token for specified environment.
    
    Args:
        client: HTTP client
        environment: "local" (emulator), "staging", or "production"

    Returns (access_token, refresh_token, headers) or (None, None, None) if failed.
    """
    if environment == "local":
        return get_emulator_auth_token(client)
    elif environment in ["staging", "production"]:
        return get_remote_auth_token(client, environment)
    else:
        raise ValueError(f"Invalid environment: {environment}")


def get_remote_auth_token(client: Client, environment: str) -> tuple[str | None, str | None, str | None]:
    """
    Get authentication token for remote environment using cached credentials.
    
    Args:
        client: HTTP client
        environment: "staging" or "production"
    
    Returns (access_token, refresh_token, headers) or (None, None, None) if failed.
    """
    import json
    import subprocess
    from pathlib import Path
    
    # Cache file should be in project root
    project_root = Path(__file__).parent.parent.parent.parent
    cache_file = project_root / f".test-cache-{environment}.json"
    
    # Try to load cached token
    if cache_file.exists():
        try:
            with open(cache_file) as f:
                cache_data = json.load(f)
            
            token = cache_data.get("access_token")
            if token:
                headers = {"Authorization": f"Bearer {token}"}
                
                # Test if token is still valid
                try:
                    response = client.get("/admin/api/v1/auth/validate", headers=headers)
                    if response.status_code == 200:
                        print(f"✓ Using cached {environment} token")
                        return token, cache_data.get("refresh_token"), headers
                except Exception:
                    pass
        except Exception:
            pass
    
    # Token not cached or expired, try to refresh
    print(f"🔄 Refreshing {environment} authentication...")
    
    try:
        # Run the setup script to get fresh tokens
        # Look for script in project root, not relative to current directory
        script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "setup-remote-test-auth.sh"
        result = subprocess.run(
            [str(script_path), environment],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=script_path.parent.parent  # Run from project root
        )
        
        if result.returncode == 0:
            # Try to load the newly cached token
            if cache_file.exists():
                with open(cache_file) as f:
                    cache_data = json.load(f)
                
                token = cache_data.get("access_token")
                if token:
                    headers = {"Authorization": f"Bearer {token}"}
                    print(f"✓ Authenticated with {environment}")
                    return token, cache_data.get("refresh_token"), headers
    
    except Exception as e:
        print(f"✗ Failed to authenticate with {environment}: {e}")
    
    return None, None, None


def get_emulator_auth_token(client: Client) -> tuple[str | None, str | None, str | None]:
    """
    Get Firebase emulator authentication token.

    Returns tuple of (access_token, refresh_token, headers) or (None, None, None) if failed.
    """
    try:
        # Create or sign in Firebase user
        firebase_token = create_firebase_emulator_user()

        if not firebase_token:
            print("✗ Could not get Firebase token from emulator")
            return None, None, None

        # Exchange Firebase token for JWT
        response = client.post(
            "/admin/api/v1/auth/exchange", json={"firebase_token": firebase_token}
        )

        if response.status_code == 200:
            data = response.json()
            access_token = data["access_token"]
            refresh_token = data.get("refresh_token")
            headers = {"Authorization": f"Bearer {access_token}"}
            print("✓ Successfully exchanged Firebase token for JWT")
            return access_token, refresh_token, headers
        print(f"✗ Token exchange failed: {response.status_code} - {response.text}")
        return None, None, None

    except Exception as e:
        print(f"✗ Exception during token exchange: {e}")
        return None, None, None


def ensure_test_workspace(client: Client, headers: dict[str, str], name: str = None) -> dict[str, Any] | None:
    """
    Ensure a test workspace exists for the authenticated user.
    Creates one if it doesn't exist.
    
    Args:
        client: HTTP client for API calls
        headers: Authentication headers
        name: Optional custom name for workspace. If None, uses default "Test Workspace"
    
    Returns:
        Workspace data dict or None if failed.
    """
    try:
        # Get workspaces for the user
        response = client.get("/admin/api/v1/workspaces", headers=headers)

        if response.status_code == 200:
            data = response.json()
            # Support both list and {workspaces: [...]} shapes
            if isinstance(data, dict) and "workspaces" in data:
                workspaces = data["workspaces"]
            else:
                workspaces = data if isinstance(data, list) else []
            
            # If specific name requested, look for workspace with that name
            if name and workspaces:
                for workspace in workspaces:
                    if workspace.get("name") == name:
                        print(f"✓ Using existing workspace: {workspace['id']} (name: {name})")
                        return workspace
                # Name specified but not found - will create new one below
            elif workspaces and len(workspaces) > 0:
                # No specific name - use first available workspace
                print(f"✓ Using existing workspace: {workspaces[0]['id']}")
                return workspaces[0]

        # Create a new workspace if none exists or specific name requested
        workspace_name = name if name else "Test Workspace"
        
        # Generate safe slug from name
        import re
        base_slug = re.sub(r'[^a-zA-Z0-9_-]', '-', workspace_name.lower())
        base_slug = re.sub(r'-+', '-', base_slug).strip('-')
        workspace_slug = f"{base_slug}-{os.getpid()}" if not name else f"{base_slug}-{secrets.token_hex(4)}"
        
        workspace_data = {
            "name": workspace_name,
            "slug": workspace_slug,
            "description": f"Workspace for integration tests: {workspace_name}",
        }

        response = client.post("/admin/api/v1/workspaces", json=workspace_data, headers=headers)

        if response.status_code in [200, 201]:
            workspace = response.json()
            print(f"✓ Created new workspace: {workspace['id']} (name: {workspace_name})")
            return workspace
        print(f"✗ Failed to create workspace: {response.status_code} - {response.text}")
        return None

    except Exception as e:
        print(f"✗ Exception ensuring workspace: {e}")
        return None


def get_test_auth_and_workspace(client: Client) -> tuple[str | None, dict[str, str] | None, str | None]:
    """
    Get complete test setup: authentication token, headers, and workspace ID.
    
    This is the main function integration tests should use for authentication.
    It ensures both authentication AND workspace access.
    
    Returns:
        Tuple of (access_token, headers, workspace_id) or (None, None, None) if failed
    """
    try:
        # Step 1: Get authentication token
        access_token, refresh_token, headers = get_emulator_auth_token(client)
        if not access_token:
            print("✗ Failed to get authentication token")
            return None, None, None
        
        # Step 2: Ensure workspace exists and get workspace ID
        workspace = ensure_test_workspace(client, headers)
        if not workspace:
            print("✗ Failed to create or access workspace")
            return None, None, None
        
        workspace_id = workspace["id"]
        print(f"✓ Authentication and workspace ready - Workspace: {workspace_id}")
        
        return access_token, headers, workspace_id
        
    except Exception as e:
        print(f"✗ Exception during test setup: {e}")
        return None, None, None


def create_test_action(
    client: Client, 
    headers: dict[str, str], 
    workspace_id: str, 
    name: str, 
    action_type: str = "REST",
    config: dict[str, Any] | None = None,
    variables: list[dict[str, Any]] | None = None
) -> str | None:
    """
    Create a test action and return its ID.
    
    Args:
        client: HTTP client
        headers: Authentication headers
        workspace_id: Workspace ID
        name: Action name
        action_type: Action type (default: "REST")
        config: Action configuration (default: simple GET to httpbin.org)
        variables: Action variables (default: empty list)
    
    Returns:
        Action ID if successful, None if failed
    """
    action_config = config or {
        "url": "https://httpbin.org/get",
        "method": "GET",
        "headers": {"Content-Type": "application/json"}
    }
    
    action_data = {
        "workspace_id": workspace_id,  # Required by ActionCreateRequest model
        "name": name,
        "type": action_type,
        "description": f"Test action: {name}",
        "config": action_config
    }
    
    # Add variables if provided
    if variables:
        action_data["variables"] = variables
    
    try:
        response = client.post(
            f"/admin/api/v1/workspaces/{workspace_id}/actions",
            headers=headers,
            json=action_data
        )
        
        if response.status_code in [200, 201]:
            response_data = response.json()
            # Handle both id and _id fields depending on endpoint
            action_id = response_data.get("id") or response_data.get("_id")
            print(f"✓ Created test action: {name} ({action_id})")
            return action_id
        else:
            print(f"✗ Failed to create action: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"✗ Exception creating action: {e}")
        return None


# Removed stray test_mcp_endpoint function - tests should be in proper test files


class AuthenticatedTestCase:
    """Base class for integration tests that need authentication."""

    @classmethod
    def setup_auth(cls, base_url: str = None, environment: str = None):
        """
        Setup authentication for test class.
        
        Args:
            base_url: Base URL for API calls (auto-detected from environment if None)
            environment: "local", "staging", or "production" (auto-detected if None)
        """
        # Auto-detect environment from base_url or environment variables
        if environment is None:
            if base_url and "staging" in base_url:
                environment = "staging"
            elif base_url and "production" in base_url:
                environment = "production"
            else:
                environment = os.getenv("TEST_ENVIRONMENT", "local")
        
        # Set base_url based on environment if not provided
        if base_url is None:
            if environment == "staging":
                base_url = "http://localhost:8090"
            elif environment == "production":
                base_url = "http://localhost:8090"
            else:
                base_url = "http://localhost:8090"
        
        cls.environment = environment
        cls.base_url = base_url
        cls.client = Client(base_url=base_url, timeout=30.0)  # Longer timeout for remote

        # Check if server is running
        try:
            response = cls.client.get("/admin/api/v1/health")
            print(f"✓ Server running at {base_url} (status: {response.status_code})")
        except Exception as e:
            cls.skip_tests = True
            cls.skip_reason = f"Server not running at {base_url}: {e}"
            return

        # Environment-specific checks and authentication
        if environment == "local":
            # Check if Firebase emulator is running for local tests
            try:
                requests.get("http://localhost:9099", timeout=2)
                print("✓ Firebase emulator is running")
            except Exception:
                cls.skip_tests = True
                cls.skip_reason = "Firebase emulator not running. Run: make emulator-start"
                return

        # Get authentication token for the environment
        cls.token, cls.refresh_token, cls.headers = get_auth_token(cls.client, environment)

        if cls.token:
            cls.skip_tests = False
            print(f"✓ Authenticated with {environment} environment")
            
            # Ensure a test workspace exists
            cls.workspace = ensure_test_workspace(cls.client, cls.headers)
            if cls.workspace:
                cls.workspace_id = cls.workspace["id"]
                print(f"✓ Using workspace: {cls.workspace_id}")
            else:
                cls.workspace_id = None
                print("⚠️ No workspace available")
        else:
            cls.skip_tests = True
            cls.skip_reason = f"Could not authenticate with {environment} environment"

    @classmethod
    def teardown_auth(cls):
        """Cleanup authentication."""
        if hasattr(cls, "client"):
            cls.client.close()

    def setup_method(self):
        """Check if tests should be skipped."""
        if self.skip_tests:
            import pytest

            pytest.skip(self.skip_reason)


async def generate_test_mcp_token(workspace_id: str) -> str | None:
    """
    Generate a test MCP token for the given workspace.
    
    In our implementation, this returns a JWT token since we use Firebase authentication
    and our MCP endpoints support JWT tokens through MCPBearerAuth.
    
    Args:
        workspace_id: Workspace ID
    
    Returns:
        JWT token string or None if generation fails
    """
    try:
        # Read the cached test token from .test-token file (used by api* targets)
        from pathlib import Path
        token_file = Path(".test-token")
        if token_file.exists():
            token = token_file.read_text().strip()
            print(f"✓ Using cached JWT token for MCP authentication")
            return token
        else:
            print("✗ No cached token found (.test-token file missing)")
            return None
    except Exception as e:
        print(f"✗ Exception getting test token: {e}")
        return None


def get_workspace_scoped_jwt_token(client: Client, base_headers: dict[str, str], target_workspace_id: str) -> str | None:
    """
    Generate a JWT token with workspace_id claim for MCP authentication.
    
    Args:
        client: HTTP client
        base_headers: Base authentication headers (with valid JWT token)
        target_workspace_id: Workspace ID to include in token claims
        
    Returns:
        JWT token string with workspace_id claim or None if failed
    """
    try:
        # Validate that the workspace exists (checking via workspace list since 
        # individual workspace access might require workspace-scoped tokens)
        workspaces_response = client.get("/admin/api/v1/workspaces", headers=base_headers)
        
        if workspaces_response.status_code != 200:
            print(f"✗ Cannot access workspaces list: {workspaces_response.status_code}")
            return None
            
        workspaces_data = workspaces_response.json()
        available_workspace_ids = [
            ws["id"] for ws in workspaces_data.get("workspaces", [])
        ]
        
        if target_workspace_id not in available_workspace_ids:
            print(f"✗ Workspace {target_workspace_id} not found in user's workspaces: {available_workspace_ids}")
            # Note: During tests, workspaces are created dynamically and may not appear in user's 
            # workspace list immediately. We'll proceed with token creation anyway.
            print(f"ℹ️ Proceeding with token creation for test workspace: {target_workspace_id}")
            
        # Get user info from current token
        validate_response = client.get("/admin/api/v1/auth/validate", headers=base_headers)
        if validate_response.status_code != 200:
            print(f"✗ Token validation failed: {validate_response.status_code}")
            return None
            
        user_data = validate_response.json()
        uid = user_data.get("uid")
        email = user_data.get("email")
        
        if not uid or not email:
            print("✗ Missing user ID or email from token validation")
            return None
            
        # Create a new JWT token with the target workspace_id claim
        from protobox.admin.auth.jwt_auth import get_jwt_auth
        
        jwt_auth = get_jwt_auth()
        
        # Generate workspace-specific test token if in test mode
        if hasattr(jwt_auth, 'test_mode') and jwt_auth.test_mode:
            workspace_token = jwt_auth.create_test_token(
                uid=uid,
                email=email,
                workspace_id=target_workspace_id,
                role="admin",
                permissions=["read", "write", "admin"]
            )
        else:
            # Create regular token with workspace_id claim
            workspace_token = jwt_auth.create_access_token(
                uid=uid,
                email=email,
                workspace_id=target_workspace_id
            )
        
        print(f"✓ Created workspace-scoped JWT token for workspace: {target_workspace_id}")
        return workspace_token
            
    except Exception as e:
        print(f"✗ Exception generating workspace-scoped token: {e}")
        return None


def delete_test_action(client: Client, headers: dict[str, str], workspace_id: str, action_id: str) -> bool:
    """
    Delete a test action.
    
    Args:
        client: HTTP client
        headers: Authentication headers  
        workspace_id: Workspace ID
        action_id: Action ID to delete
    
    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        response = client.delete(
            f"/admin/api/v1/workspaces/{workspace_id}/actions/{action_id}",
            headers=headers
        )
        
        if response.status_code == 204:
            print(f"✓ Deleted test action: {action_id}")
            return True
        else:
            print(f"✗ Failed to delete action: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Exception deleting action: {e}")
        return False
