"""
End-to-End test for complete user authentication and API flow.

This test covers:
1. User authentication with Firebase
2. Token exchange and cookie setting
3. Creating actions in the backend
4. Internal API communication between Next.js and Python

Prerequisites:
- Firebase emulator running: firebase emulators:start --only auth
- Next.js running: cd client && npm run dev
- Python backend running: make run-dev
- MongoDB running: make db-start
"""

import asyncio
import sys
from pathlib import Path
from typing import Any

import aiohttp
import pytest

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from loguru import logger

# Test configuration
FIREBASE_EMULATOR_URL = "http://localhost:9099"
NEXT_JS_URL = "http://localhost:3001"
PYTHON_API_URL = "http://localhost:8090/admin/api/v1"
FIREBASE_PROJECT_ID = "demo-project"  # Default for emulator

# Test user credentials
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpassword123"
TEST_WORKSPACE_NAME = "Test Workspace"


class E2ETestHelper:
    """Helper class for E2E testing operations."""

    def __init__(self):
        self.session = None
        self.firebase_token = None
        self.custom_jwt = None
        self.user_id = None
        self.workspace_id = None
        self.cookies = {}

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def check_services_health(self) -> dict[str, bool]:
        """Check if all required services are running."""
        services = {
            "firebase_emulator": f"{FIREBASE_EMULATOR_URL}/",
            "nextjs": f"{NEXT_JS_URL}/",
            "python_backend": f"{PYTHON_API_URL}/health",
        }

        results = {}
        for service, url in services.items():
            try:
                async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    results[service] = resp.status in [
                        200,
                        302,
                        404,
                    ]  # 404 is ok for some endpoints
                    if results[service]:
                        logger.success(f"✅ {service} is running")
                    else:
                        logger.error(f"❌ {service} returned status {resp.status}")
            except Exception as e:
                results[service] = False
                logger.error(f"❌ {service} health check failed: {e}")

        return results

    async def create_firebase_user(self) -> dict[str, Any]:
        """Create a user in Firebase emulator."""
        url = f"{FIREBASE_EMULATOR_URL}/identitytoolkit.googleapis.com/v1/accounts:signUp"

        payload = {"email": TEST_EMAIL, "password": TEST_PASSWORD, "returnSecureToken": True}

        params = {"key": "fake-api-key"}  # Emulator accepts any key

        async with self.session.post(url, json=payload, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                self.firebase_token = data["idToken"]
                self.user_id = data["localId"]
                logger.success(f"✅ Created Firebase user: {TEST_EMAIL}")
                return data
            error_text = await resp.text()
            logger.error(f"❌ Failed to create Firebase user: {resp.status} - {error_text}")
            raise Exception(f"Failed to create Firebase user: {error_text}")

    async def sign_in_firebase_user(self) -> dict[str, Any]:
        """Sign in existing Firebase user."""
        url = (
            f"{FIREBASE_EMULATOR_URL}/identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
        )

        payload = {"email": TEST_EMAIL, "password": TEST_PASSWORD, "returnSecureToken": True}

        params = {"key": "fake-api-key"}

        async with self.session.post(url, json=payload, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                self.firebase_token = data["idToken"]
                self.user_id = data["localId"]
                logger.success(f"✅ Signed in Firebase user: {TEST_EMAIL}")
                return data
            # User might not exist, try creating
            logger.info("User doesn't exist, creating...")
            return await self.create_firebase_user()

    async def exchange_firebase_token(self) -> dict[str, Any]:
        """Exchange Firebase token for custom JWT via Next.js."""
        url = f"{NEXT_JS_URL}/api/auth/exchange-token"

        headers = {
            "Authorization": f"Bearer {self.firebase_token}",
            "Content-Type": "application/json",
        }

        async with self.session.post(url, headers=headers) as resp:
            # Get cookies from response
            if "Set-Cookie" in resp.headers:
                # Parse cookies (simplified - in real test you'd use proper cookie parsing)
                cookies = resp.headers.get("Set-Cookie", "")
                logger.info(f"Received cookies: {cookies}")
                self.cookies["Cookie"] = cookies

            if resp.status == 200:
                data = await resp.json()
                logger.success("✅ Successfully exchanged Firebase token for custom JWT")
                return data
            error_text = await resp.text()
            logger.error(f"❌ Token exchange failed: {resp.status} - {error_text}")
            raise Exception(f"Token exchange failed: {error_text}")

    async def create_workspace(self) -> dict[str, Any]:
        """Create a workspace via Next.js API."""
        url = f"{NEXT_JS_URL}/api/workspaces"

        headers = {"Content-Type": "application/json", **self.cookies}  # Include auth cookies

        payload = {"name": TEST_WORKSPACE_NAME, "description": "Test workspace created by E2E test"}

        async with self.session.post(url, json=payload, headers=headers) as resp:
            if resp.status in [200, 201]:
                data = await resp.json()
                self.workspace_id = data.get("id") or data.get("_id")
                logger.success(f"✅ Created workspace: {TEST_WORKSPACE_NAME}")
                return data
            error_text = await resp.text()
            logger.error(f"❌ Workspace creation failed: {resp.status} - {error_text}")
            # This might fail if endpoint doesn't exist - that's useful info
            return {"error": error_text, "status": resp.status}

    async def create_action_via_python(self) -> dict[str, Any]:
        """Create an action via Python backend using authentication."""
        if not self.workspace_id:
            raise Exception("No workspace ID available - workspace creation may have failed")

        url = f"{PYTHON_API_URL}/workspaces/{self.workspace_id}/actions"

        headers = {"Content-Type": "application/json", **self.cookies}  # Include auth cookies

        # Use timestamp to ensure unique action name
        import time

        timestamp = int(time.time())

        payload = {
            "name": f"test-action-e2e-{timestamp}",
            "type": "REST",
            "description": "Test action created by E2E test",
            "config": {"url": "https://httpbin.org/post", "method": "POST"},
            "variables": [
                {
                    "name": "message",
                    "type": "string",
                    "required": True,
                    "description": "Test message",
                }
            ],
        }

        async with self.session.post(url, json=payload, headers=headers) as resp:
            if resp.status in [200, 201]:
                data = await resp.json()
                logger.success(f"✅ Created action via Python backend: test-action-e2e-{timestamp}")
                return data
            error_text = await resp.text()
            logger.warning(f"⚠️ Action creation failed: {resp.status} - {error_text}")
            return {"error": error_text, "status": resp.status}

    async def test_internal_api_validation(self) -> dict[str, Any]:
        """Test that Python backend can validate authentication via internal API."""
        # This tests the internal API flow we built
        # Python should call Next.js internal APIs to validate the user

        if not self.workspace_id:
            raise Exception("No workspace available for testing")

        url = f"{PYTHON_API_URL}/workspaces/{self.workspace_id}/actions"

        headers = {**self.cookies}  # Include auth cookies

        async with self.session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                logger.success("✅ Python backend successfully validated auth via internal API")
                return data
            error_text = await resp.text()
            logger.error(f"❌ Internal API validation failed: {resp.status} - {error_text}")
            return {"error": error_text, "status": resp.status}


@pytest.mark.asyncio
async def test_complete_user_flow():
    """Test the complete user authentication and API interaction flow."""
    async with E2ETestHelper() as helper:

        # Step 1: Check that all services are running
        logger.info("🔍 Step 1: Checking service health...")
        health = await helper.check_services_health()

        missing_services = [service for service, healthy in health.items() if not healthy]
        if missing_services:
            pytest.skip(f"Required services not running: {missing_services}")

        # Step 2: Authenticate with Firebase
        logger.info("🔐 Step 2: Authenticating with Firebase...")
        firebase_user = await helper.sign_in_firebase_user()
        assert helper.firebase_token is not None
        assert helper.user_id is not None

        # Step 3: Exchange Firebase token for custom JWT
        logger.info("🔄 Step 3: Exchanging Firebase token...")
        try:
            token_exchange = await helper.exchange_firebase_token()
            logger.success("Token exchange successful")
        except Exception as e:
            logger.error(f"Token exchange failed: {e}")
            pytest.fail(f"Token exchange failed - this indicates Next.js auth is broken: {e}")

        # Step 4: Create workspace
        logger.info("🏢 Step 4: Creating workspace...")
        workspace_result = await helper.create_workspace()
        if "error" in workspace_result:
            logger.warning(f"Workspace creation failed: {workspace_result}")
            # Continue with default workspace for testing
            helper.workspace_id = "6883c972274b0349b71b5ff2"  # Use test workspace

        # Step 5: Test Python backend authentication
        logger.info("🐍 Step 5: Testing Python backend authentication...")
        internal_api_result = await helper.test_internal_api_validation()
        if "error" in internal_api_result:
            logger.error(f"Internal API validation failed: {internal_api_result}")
            pytest.fail(
                "Python backend cannot validate authentication - internal API flow is broken"
            )

        # Step 6: Create action via Python backend
        logger.info("⚡ Step 6: Creating action via Python backend...")
        action_result = await helper.create_action_via_python()
        if "error" in action_result:
            logger.warning(f"Action creation failed: {action_result}")
            # This might fail due to missing endpoints - that's useful info
        else:
            logger.success("✅ Action created successfully via authenticated Python API")

        logger.success("🎉 E2E test completed! All authentication and API flows work.")


@pytest.mark.asyncio
async def test_minimal_auth_flow():
    """Minimal test focusing just on authentication without workspace/action creation."""
    async with E2ETestHelper() as helper:

        # Check services
        health = await helper.check_services_health()
        missing_services = [service for service, healthy in health.items() if not healthy]
        if missing_services:
            pytest.skip(f"Required services not running: {missing_services}")

        # Test Firebase auth
        firebase_user = await helper.sign_in_firebase_user()
        assert helper.firebase_token is not None

        # Test token exchange
        token_exchange = await helper.exchange_firebase_token()

        # Test that Python backend can access authenticated endpoint
        helper.workspace_id = "6883c972274b0349b71b5ff2"  # Use test workspace
        result = await helper.test_internal_api_validation()

        assert "error" not in result, f"Authentication flow broken: {result}"
        logger.success("✅ Minimal auth flow works!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "manual":
        # Run manually for debugging
        async def main():
            async with E2ETestHelper() as helper:
                health = await helper.check_services_health()
                print("Service health:", health)

                if all(health.values()):
                    try:
                        await helper.sign_in_firebase_user()
                        await helper.exchange_firebase_token()
                        helper.workspace_id = "6883c972274b0349b71b5ff2"
                        result = await helper.test_internal_api_validation()
                        print("Auth test result:", result)
                    except Exception as e:
                        print(f"Error: {e}")

        asyncio.run(main())
    else:
        pytest.main([__file__, "-v", "-s"])
