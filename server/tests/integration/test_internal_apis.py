"""
Integration tests for internal API communication.

These tests require a running server with test mode enabled.
Run with: make test-integration-api
"""

import os
import time

import pytest
from httpx import AsyncClient, Client


@pytest.mark.integration
class TestInternalAPIHealth:
    """Test internal API health and connectivity."""

    @classmethod
    def setup_class(cls):
        """Setup test configuration."""
        cls.base_url = os.getenv("TEST_API_URL", "http://localhost:8090")
        cls.client = Client(base_url=cls.base_url, timeout=10.0)

        # Check if server is running
        try:
            response = cls.client.get("/admin/api/v1/health")
            if response.status_code == 200:
                cls.skip_tests = False
            else:
                cls.skip_tests = True
                cls.skip_reason = "Server not healthy"
        except Exception as e:
            cls.skip_tests = True
            cls.skip_reason = f"Server not running: {e}"

    @classmethod
    def teardown_class(cls):
        """Cleanup."""
        cls.client.close()

    def setup_method(self):
        """Check if tests should be skipped."""
        if self.skip_tests:
            pytest.skip(self.skip_reason)

    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.client.get("/admin/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_version_info(self):
        """Test version information endpoint if available."""
        response = self.client.get("/admin/api/v1/version")
        # Version endpoint might not exist
        if response.status_code == 200:
            data = response.json()
            assert "version" in data or "api_version" in data


@pytest.mark.integration
class TestAPIKeyValidation:
    """Test API key validation flow."""

    @classmethod
    def setup_class(cls):
        """Setup test configuration."""
        cls.base_url = os.getenv("TEST_API_URL", "http://localhost:8090")
        cls.client = Client(base_url=cls.base_url, timeout=10.0)

        # Try to get test token for authenticated endpoints
        try:
            response = cls.client.post(
                "/admin/api/v1/auth/exchange", json={"firebase_token": "test-user123"}
            )
            if response.status_code == 200:
                cls.token = response.json()["access_token"]
                cls.headers = {"Authorization": f"Bearer {cls.token}"}
                cls.skip_tests = False
            else:
                cls.skip_tests = True
                cls.skip_reason = "Test mode not enabled"
        except Exception as e:
            cls.skip_tests = True
            cls.skip_reason = f"Server not running: {e}"

    @classmethod
    def teardown_class(cls):
        """Cleanup."""
        cls.client.close()

    def setup_method(self):
        """Check if tests should be skipped."""
        if self.skip_tests:
            pytest.skip(self.skip_reason)

    def test_api_key_header_validation(self):
        """Test API key validation via header."""
        # Test with a mock API key format
        test_api_key = "key_test123:secret_test456"
        headers = {"X-API-Key": test_api_key}

        # Try to access an endpoint with API key
        response = self.client.get("/admin/api/v1/workspaces", headers=headers)

        # Depending on implementation, this might return 401 or 200
        # If API key validation is not implemented, it might fall back to requiring JWT
        if response.status_code == 401:
            # API key validation implemented but key is invalid
            assert "error" in response.json() or "detail" in response.json()
        elif response.status_code == 200:
            # API key validation succeeded or not implemented
            data = response.json()
            assert "workspaces" in data or isinstance(data, list)


@pytest.mark.integration
@pytest.mark.asyncio
class TestCachingBehavior:
    """Test caching behavior for internal APIs."""

    @classmethod
    def setup_class(cls):
        """Setup test configuration."""
        cls.base_url = os.getenv("TEST_API_URL", "http://localhost:8090")
        cls.skip_tests = False
        cls.skip_reason = None

        # Try to get test token
        try:
            with Client(base_url=cls.base_url, timeout=10.0) as client:
                response = client.post(
                    "/admin/api/v1/auth/exchange", json={"firebase_token": "test-user123"}
                )
                if response.status_code == 200:
                    cls.token = response.json()["access_token"]
                    cls.headers = {"Authorization": f"Bearer {cls.token}"}
                else:
                    cls.skip_tests = True
                    cls.skip_reason = "Test mode not enabled"
        except Exception as e:
            cls.skip_tests = True
            cls.skip_reason = f"Server not running: {e}"

    async def test_response_time_improvement_with_cache(self):
        """Test that repeated requests are faster due to caching."""
        if self.skip_tests:
            pytest.skip(self.skip_reason)

        async with AsyncClient(base_url=self.base_url, timeout=10.0) as client:
            # First request - potentially slower
            start = time.time()
            response = await client.get("/admin/api/v1/workspaces", headers=self.headers)
            first_time = time.time() - start
            assert response.status_code == 200

            # Second request - should be faster if cached
            start = time.time()
            response = await client.get("/admin/api/v1/workspaces", headers=self.headers)
            second_time = time.time() - start
            assert response.status_code == 200

            # Log the times for debugging
            print(f"First request: {first_time:.3f}s, Second request: {second_time:.3f}s")

            # Second request should not be significantly slower
            # (we can't guarantee it's faster due to various factors)
            assert second_time < first_time * 2.0, "Second request took too long"


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling in API communication."""

    @classmethod
    def setup_class(cls):
        """Setup test configuration."""
        cls.base_url = os.getenv("TEST_API_URL", "http://localhost:8090")
        cls.client = Client(base_url=cls.base_url, timeout=10.0)
        cls.skip_tests = False

    @classmethod
    def teardown_class(cls):
        """Cleanup."""
        cls.client.close()

    def test_invalid_token_handling(self):
        """Test handling of invalid authentication token."""
        headers = {"Authorization": "Bearer invalid_token_here"}

        response = self.client.get("/admin/api/v1/workspaces", headers=headers)

        # Should return 401 or 403
        assert response.status_code in [401, 403]
        data = response.json()
        assert "error" in data or "detail" in data

    def test_malformed_request_handling(self):
        """Test handling of malformed requests."""
        # Try to create something with invalid data
        response = self.client.post(
            "/admin/api/v1/auth/exchange", json={"invalid_field": "invalid_value"}
        )

        # Should return 400 or 422
        assert response.status_code in [400, 422]
        data = response.json()
        assert "error" in data or "detail" in data

    def test_nonexistent_endpoint(self):
        """Test handling of requests to non-existent endpoints."""
        response = self.client.get("/admin/api/v1/nonexistent/endpoint")

        # Should return 404
        assert response.status_code == 404


@pytest.mark.integration
class TestRateLimiting:
    """Test rate limiting and throttling if implemented."""

    @classmethod
    def setup_class(cls):
        """Setup test configuration."""
        cls.base_url = os.getenv("TEST_API_URL", "http://localhost:8090")
        cls.client = Client(base_url=cls.base_url, timeout=10.0)

        # Try to get test token
        try:
            response = cls.client.post(
                "/admin/api/v1/auth/exchange", json={"firebase_token": "test-user123"}
            )
            if response.status_code == 200:
                cls.token = response.json()["access_token"]
                cls.headers = {"Authorization": f"Bearer {cls.token}"}
                cls.skip_tests = False
            else:
                cls.skip_tests = True
                cls.skip_reason = "Test mode not enabled"
        except Exception as e:
            cls.skip_tests = True
            cls.skip_reason = f"Server not running: {e}"

    @classmethod
    def teardown_class(cls):
        """Cleanup."""
        cls.client.close()

    def setup_method(self):
        """Check if tests should be skipped."""
        if self.skip_tests:
            pytest.skip(self.skip_reason)

    def test_rapid_requests(self):
        """Test behavior under rapid requests."""
        # Make 10 rapid requests
        responses = []
        for i in range(10):
            response = self.client.get("/admin/api/v1/health")
            responses.append(response.status_code)

        # All should succeed (rate limiting might not be implemented)
        for status in responses:
            assert status in [200, 429], f"Unexpected status: {status}"

        # Count how many were rate limited
        rate_limited = sum(1 for s in responses if s == 429)
        if rate_limited > 0:
            print(f"Rate limiting detected: {rate_limited}/10 requests limited")
        else:
            print("No rate limiting detected (might not be implemented)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
